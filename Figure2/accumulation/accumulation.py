from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import brainpy as bp
import brainpy.math as bm
import numpy as np
import pandas as pd
from brainpy._src.math.object_transform.naming import clear_name_cache
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d


bm.enable_x64()
bm.set_platform("cpu")

INPUT_NEURON_TYPES = (
    "RGC_SO",
    "RGC_S12",
    "RGC_S34",
    "RGC_S56",
    "RGC_SGC",
    "RGC_SAC",
)


@dataclass(frozen=True)
class SimulationConfig:
    neuron_count_path: Path
    connection_path: Path
    data_path: Path
    order_path: Path
    output_path: Path
    target_pathway: str
    dt_sim_ms: float = 0.1
    sim_duration_ms: float = 25_000.0
    analysis_start_ms: float = 5_000.0
    analysis_end_ms: float = 20_000.0
    tau_calcium_s: float = 0.5
    smoothing_window_s: float = 0.1
    current_gain: float = 1.0
    gain_coeff: float = 70.0
    channel_gains: tuple[float, ...] = (1.0, 1.0, 1.0, 3.0, 3.0, 1.0)
    excitatory_weight: float = 0.6
    inhibitory_weight: float = -6.7
    excitatory_tau_ms: float = 5.0
    inhibitory_tau_ms: float = 10.0
    seed: int | None = None
    max_ablations: int | None = None

    @property
    def analysis_start_index(self) -> int:
        return int(round(self.analysis_start_ms / self.dt_sim_ms))

    @property
    def analysis_end_index(self) -> int:
        return int(round(self.analysis_end_ms / self.dt_sim_ms))


def simple_deconvolution(calcium_signal: np.ndarray, tau: float = 0.5, dt: float = 0.001) -> np.ndarray:
    """Approximate a spike train from a calcium trace with a first-order decay model."""
    spikes = np.zeros_like(calcium_signal, dtype=float)
    c_est = np.zeros_like(calcium_signal, dtype=float)
    alpha = float(np.exp(-dt / tau))
    beta = max(dt / tau, 1e-6)

    for t in range(1, len(calcium_signal)):
        c_pred = c_est[t - 1] * alpha
        s_t = max(0.0, (calcium_signal[t] - c_pred) / beta)
        c_est[t] = c_pred + s_t * beta
        spikes[t] = s_t

    return spikes


def infer_target_pathway(data_path: Path, explicit_target: str | None) -> str:
    if explicit_target:
        return explicit_target

    name = data_path.stem.lower()
    if "loom" in name:
        return "tpn_e"
    if "sd" in name or "smd" in name:
        return "tpn_o"
    raise ValueError("Could not infer the target pathway from the data filename. Use --target-pathway.")


def load_channel_inputs(config: SimulationConfig) -> tuple[np.ndarray, tuple[bm.Array, ...]]:
    data = pd.read_excel(config.data_path, sheet_name="Sheet1")
    time_points = data["Time"].to_numpy(dtype=float)
    calcium_signals = data.iloc[:, 1:7].to_numpy(dtype=float)
    dt_data = float(np.median(np.diff(time_points)))

    spike_trains = np.zeros_like(calcium_signals, dtype=float)
    for idx in range(calcium_signals.shape[1]):
        spike_trains[:, idx] = simple_deconvolution(
            calcium_signals[:, idx],
            tau=config.tau_calcium_s,
            dt=dt_data,
        )

    sigma = max(config.smoothing_window_s / dt_data, 1.0)
    firing_rates = np.zeros_like(spike_trains, dtype=float)
    for idx in range(spike_trains.shape[1]):
        firing_rates[:, idx] = gaussian_filter1d(spike_trains[:, idx], sigma=sigma)

    rgc_currents = firing_rates * config.current_gain
    sim_times = np.arange(0.0, config.sim_duration_ms, config.dt_sim_ms)
    interpolated = np.zeros((len(sim_times), len(INPUT_NEURON_TYPES)), dtype=float)
    data_times_ms = time_points * 1000.0

    for idx in range(rgc_currents.shape[1]):
        interp = interp1d(
            data_times_ms,
            rgc_currents[:, idx],
            kind="linear",
            bounds_error=False,
            fill_value=(rgc_currents[0, idx], rgc_currents[-1, idx]),
        )
        interpolated[:, idx] = interp(sim_times)

    gains = np.asarray(config.channel_gains, dtype=float) * config.gain_coeff
    scaled = bm.asarray(interpolated * gains[None, :])
    channel_inputs = tuple(scaled[:, idx] for idx in range(scaled.shape[1]))
    return sim_times, channel_inputs


class Exponential(bp.Projection):
    def __init__(self, pre: bp.DynamicalSystem, post: bp.DynamicalSystem, prob: float, g_max: float, tau: float):
        super().__init__()
        self.proj = bp.dyn.ProjAlignPostMg2(
            pre=pre,
            delay=None,
            comm=bp.dnn.EventCSRLinear(bp.conn.FixedProb(prob, pre=pre.num, post=post.num), g_max),
            syn=bp.dyn.Expon.desc(post.num, tau=tau),
            out=bp.dyn.CUBA.desc(),
            post=post,
        )


class WholeOT(bp.DynSysGroup):
    def __init__(
        self,
        neuron_types: Iterable[str],
        neuron_numbers: dict[str, int],
        conn_matrix: np.ndarray,
        config: SimulationConfig,
        method: str = "exp_auto",
    ):
        super().__init__()
        pars = dict(
            V_rest=-60.0,
            V_th=-50.0,
            V_reset=-60.0,
            tau=20.0,
            tau_ref=5.0,
            R=1.0,
            V_initializer=bp.init.Normal(-55.0, 2.0),
            method=method,
        )

        self.neurons: dict[str, bp.DynamicalSystem] = {}
        self.synapses: dict[str, Exponential] = {}
        neuron_type_list = list(neuron_types)

        for neuron_type in neuron_type_list:
            neuron_group = bp.dyn.LifRef(int(neuron_numbers[neuron_type]), **pars)
            setattr(self, neuron_type, neuron_group)
            self.neurons[neuron_type] = neuron_group

        for row_idx, src_type in enumerate(neuron_type_list):
            for col_idx, tar_type in enumerate(neuron_type_list):
                prob = float(conn_matrix[row_idx, col_idx])
                if prob <= 0.0:
                    continue

                pre_group = self.neurons[src_type]
                post_group = self.neurons[tar_type]
                if pre_group.num == 0 or post_group.num == 0:
                    continue

                is_inhibitory = src_type.startswith("I") or "I_" in src_type
                g_max = config.inhibitory_weight if is_inhibitory else config.excitatory_weight
                tau = config.inhibitory_tau_ms if is_inhibitory else config.excitatory_tau_ms
                syn_name = f"{src_type}_to_{tar_type}"
                synapse = Exponential(pre_group, post_group, prob=prob, g_max=g_max, tau=tau)
                setattr(self, syn_name, synapse)
                self.synapses[syn_name] = synapse

    def update(self, inp1: bm.Array, inp2: bm.Array, inp3: bm.Array, inp4: bm.Array, inp5: bm.Array, inp6: bm.Array):
        self.RGC_SO(inp1)
        self.RGC_S12(inp2)
        self.RGC_S34(inp3)
        self.RGC_S56(inp4)
        self.RGC_SGC(inp5)
        self.RGC_SAC(inp6)

        for neuron_type, neuron_group in self.neurons.items():
            if neuron_type not in INPUT_NEURON_TYPES:
                neuron_group()

        for synapse in self.synapses.values():
            synapse()

        return self.TPN_O.spike, self.TPN_E.spike


def compute_pathway_fraction(tpn_o_spike: bm.Array, tpn_e_spike: bm.Array, config: SimulationConfig) -> dict[str, float]:
    rate_e = np.asarray(bp.measure.firing_rate(tpn_e_spike, width=1000.0))
    rate_o = np.asarray(bp.measure.firing_rate(tpn_o_spike, width=1000.0))
    analysis = slice(config.analysis_start_index, config.analysis_end_index)
    auc_e = float(rate_e[analysis].sum())
    auc_o = float(rate_o[analysis].sum())
    total = auc_e + auc_o
    fraction = auc_e / total if config.target_pathway == "tpn_e" else auc_o / total
    return {
        "tpn_e_auc": auc_e,
        "tpn_o_auc": auc_o,
        "target_fraction": fraction if total > 0 else float("nan"),
    }


def run_single_ablation(
    neuron_types: list[str],
    neuron_numbers: dict[str, int],
    conn_matrix: np.ndarray,
    channel_inputs: tuple[bm.Array, ...],
    config: SimulationConfig,
) -> dict[str, float]:
    clear_name_cache()
    net = WholeOT(neuron_types=neuron_types, neuron_numbers=neuron_numbers, conn_matrix=conn_matrix, config=config)

    def run_net(t: bm.Array, inp1: bm.Array, inp2: bm.Array, inp3: bm.Array, inp4: bm.Array, inp5: bm.Array, inp6: bm.Array):
        bp.share.save(t=t)
        return net(inp1, inp2, inp3, inp4, inp5, inp6)

    with bm.environment(dt=config.dt_sim_ms):
        step_indices = bm.arange(len(channel_inputs[0]))
        tpn_o_spike, tpn_e_spike = bm.for_loop(run_net, (step_indices, *channel_inputs))

    return compute_pathway_fraction(tpn_o_spike, tpn_e_spike, config)


def run_cumulative_ablation(config: SimulationConfig) -> pd.DataFrame:
    neuron_num_df = pd.read_csv(config.neuron_count_path)
    neuron_types = neuron_num_df["Type"].tolist()
    base_neuron_numbers = {key: int(value) for key, value in neuron_num_df.set_index("Type")["number"].to_dict().items()}
    conn_matrix = pd.read_csv(config.connection_path, index_col=0).to_numpy(dtype=float).round(3)
    order_df = pd.read_csv(config.order_path)
    ablation_sequence = [value for value in order_df.iloc[:, 0].astype(str).tolist() if value and value.lower() != "nan"]

    if config.seed is not None:
        np.random.seed(config.seed)
        bm.random.seed(config.seed)

    _, channel_inputs = load_channel_inputs(config)
    active_neuron_numbers = base_neuron_numbers.copy()
    rows: list[dict[str, float | int | str]] = []

    for step, target_type in enumerate(ablation_sequence, start=1):
        if target_type in active_neuron_numbers:
            active_neuron_numbers[target_type] = 0

        metrics = run_single_ablation(
            neuron_types=neuron_types,
            neuron_numbers=active_neuron_numbers,
            conn_matrix=conn_matrix,
            channel_inputs=channel_inputs,
            config=config,
        )
        rows.append(
            {
                "ablation_step": step,
                "ablated_type": target_type,
                "remaining_neurons": sum(active_neuron_numbers.values()),
                **metrics,
            }
        )

        if config.max_ablations is not None and step >= config.max_ablations:
            break

    return pd.DataFrame(rows)


def parse_args() -> SimulationConfig:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run the legacy cumulative-ablation workflow with relative paths and explicit parameters."
    )
    parser.add_argument("--data", type=Path, default=root / "SD.xlsx", help="Calcium-input Excel file.")
    parser.add_argument("--order", type=Path, default=root / "SD_Order.csv", help="CSV file with cumulative ablation order.")
    parser.add_argument(
        "--counts",
        type=Path,
        default=root / "neuron_number.csv",
        help="CSV file with neuron counts.",
    )
    parser.add_argument(
        "--connections",
        type=Path,
        default=root / "neuron_connections_whole.csv",
        help="CSV file with connection probabilities.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path. Defaults to '<data stem>_accumulation_results.csv'.",
    )
    parser.add_argument(
        "--target-pathway",
        choices=("tpn_e", "tpn_o"),
        default=None,
        help="Pathway to quantify. If omitted, infer from the data filename.",
    )
    parser.add_argument("--dt-sim-ms", type=float, default=0.1)
    parser.add_argument("--sim-duration-ms", type=float, default=25_000.0)
    parser.add_argument("--analysis-start-ms", type=float, default=5_000.0)
    parser.add_argument("--analysis-end-ms", type=float, default=20_000.0)
    parser.add_argument("--tau-calcium-s", type=float, default=0.5)
    parser.add_argument("--smoothing-window-s", type=float, default=0.1)
    parser.add_argument("--current-gain", type=float, default=1.0)
    parser.add_argument("--gain-coeff", type=float, default=70.0)
    parser.add_argument(
        "--channel-gains",
        default="1,1,1,3,3,1",
        help="Comma-separated channel multipliers for RGC_SO/S12/S34/S56/SGC/SAC.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for deterministic initialization.")
    parser.add_argument(
        "--max-ablations",
        type=int,
        default=None,
        help="Optional cap for smoke-testing only the first N cumulative ablations.",
    )
    args = parser.parse_args()

    channel_gains = tuple(float(value) for value in args.channel_gains.split(","))
    if len(channel_gains) != len(INPUT_NEURON_TYPES):
        raise ValueError("Expected exactly six channel gains for the six RGC input channels.")

    data_path = args.data.resolve()
    output_path = args.output.resolve() if args.output else data_path.with_name(f"{data_path.stem}_accumulation_results.csv")
    return SimulationConfig(
        neuron_count_path=args.counts.resolve(),
        connection_path=args.connections.resolve(),
        data_path=data_path,
        order_path=args.order.resolve(),
        output_path=output_path,
        target_pathway=infer_target_pathway(data_path, args.target_pathway),
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        analysis_start_ms=args.analysis_start_ms,
        analysis_end_ms=args.analysis_end_ms,
        tau_calcium_s=args.tau_calcium_s,
        smoothing_window_s=args.smoothing_window_s,
        current_gain=args.current_gain,
        gain_coeff=args.gain_coeff,
        channel_gains=channel_gains,
        seed=args.seed,
        max_ablations=args.max_ablations,
    )


def main() -> None:
    config = parse_args()
    results = run_cumulative_ablation(config)
    results.to_csv(config.output_path, index=False)
    print(f"Wrote {len(results)} cumulative-ablation rows to {config.output_path}")
    if not results.empty:
        last_row = results.iloc[-1]
        print(
            "Last step:",
            f"ablated={last_row['ablated_type']}",
            f"target_fraction={last_row['target_fraction']:.6f}",
            f"tpn_e_auc={last_row['tpn_e_auc']:.2f}",
            f"tpn_o_auc={last_row['tpn_o_auc']:.2f}",
        )


if __name__ == "__main__":
    main()
