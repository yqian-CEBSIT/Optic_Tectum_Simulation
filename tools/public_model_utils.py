from __future__ import annotations

import sys
from pathlib import Path

import brainpy as bp
import brainpy.math as bm
import numpy as np
import pandas as pd
from brainpy._src.math.object_transform.naming import clear_name_cache
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d


ROOT = Path(__file__).resolve().parents[1]
ACCUMULATION = ROOT / "Figure2" / "accumulation"
if str(ACCUMULATION) not in sys.path:
    sys.path.insert(0, str(ACCUMULATION))

from accumulation import INPUT_NEURON_TYPES, SimulationConfig, WholeOT, simple_deconvolution  # noqa: E402


OUTPUT_NEURON_TYPES = ("TPN_E", "TPN_O")


def load_model_definition(
    counts_path: Path,
    connections_path: Path,
    connection_decimals: int,
) -> tuple[list[str], dict[str, int], np.ndarray]:
    counts = pd.read_csv(counts_path)
    neuron_types = counts["Type"].astype(str).tolist()
    neuron_numbers = {key: int(value) for key, value in counts.set_index("Type")["number"].to_dict().items()}
    conn_matrix = pd.read_csv(connections_path, index_col=0).to_numpy(dtype=float).round(connection_decimals)
    return neuron_types, neuron_numbers, conn_matrix


def tin_types(neuron_types: list[str]) -> list[str]:
    return [value for value in neuron_types if value not in INPUT_NEURON_TYPES and value not in OUTPUT_NEURON_TYPES]


def e_tin_types(neuron_types: list[str]) -> list[str]:
    return [value for value in tin_types(neuron_types) if value.startswith("E_")]


def i_tin_types(neuron_types: list[str]) -> list[str]:
    return [value for value in tin_types(neuron_types) if value.startswith("I_")]


def make_config(
    *,
    counts_path: Path,
    connections_path: Path,
    data_path: Path,
    target_pathway: str,
    data_sheet: str = "Sheet1",
    dt_sim_ms: float = 0.1,
    sim_duration_ms: float = 60_000.0,
    analysis_start_ms: float = 30_000.0,
    analysis_end_ms: float = 45_000.0,
    gain_coeff: float = 65.0,
    channel_gains: tuple[float, ...] = (1.0, 1.0, 1.0, 3.0, 3.0, 1.0),
) -> SimulationConfig:
    return SimulationConfig(
        neuron_count_path=counts_path.resolve(),
        connection_path=connections_path.resolve(),
        data_path=data_path.resolve(),
        order_path=Path("__unused_order__.csv"),
        output_path=Path("__unused_output__.csv"),
        target_pathway=target_pathway,
        data_sheet=data_sheet,
        dt_sim_ms=dt_sim_ms,
        sim_duration_ms=sim_duration_ms,
        analysis_start_ms=analysis_start_ms,
        analysis_end_ms=analysis_end_ms,
        gain_coeff=gain_coeff,
        channel_gains=channel_gains,
    )


def load_channel_inputs_with_shift(
    config: SimulationConfig,
    *,
    lead_ms: float = 0.0,
) -> tuple[np.ndarray, tuple[bm.Array, ...]]:
    data = pd.read_excel(config.data_path, sheet_name=config.data_sheet)
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
    data_times_ms = time_points * 1000.0 + lead_ms

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


def apply_tin_selection(
    base_numbers: dict[str, int],
    neuron_types: list[str],
    *,
    keep_tins: set[str] | None = None,
    ablate_tins: set[str] | None = None,
) -> dict[str, int]:
    edited = dict(base_numbers)
    all_tins = set(tin_types(neuron_types))
    if keep_tins is not None:
        unknown = sorted(keep_tins - all_tins)
        if unknown:
            raise ValueError(f"Unknown TINs in keep_tins: {unknown}")
        for value in all_tins - keep_tins:
            edited[value] = 0
    if ablate_tins is not None:
        unknown = sorted(ablate_tins - all_tins)
        if unknown:
            raise ValueError(f"Unknown TINs in ablate_tins: {unknown}")
        for value in ablate_tins:
            edited[value] = 0
    return edited


def run_spiking_trial(
    *,
    neuron_types: list[str],
    neuron_numbers: dict[str, int],
    conn_matrix: np.ndarray,
    channel_inputs: tuple[bm.Array, ...],
    config: SimulationConfig,
    seed: int,
    threshold_overrides: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    np.random.seed(seed)
    bm.random.seed(seed)
    clear_name_cache()
    net = WholeOT(
        neuron_types=neuron_types,
        neuron_numbers=neuron_numbers,
        conn_matrix=conn_matrix,
        config=config,
        threshold_overrides=threshold_overrides,
    )

    def run_net(t: bm.Array, inp1: bm.Array, inp2: bm.Array, inp3: bm.Array, inp4: bm.Array, inp5: bm.Array, inp6: bm.Array):
        bp.share.save(t=t)
        return net(inp1, inp2, inp3, inp4, inp5, inp6)

    with bm.environment(dt=config.dt_sim_ms):
        step_indices = bm.arange(len(channel_inputs[0]))
        tpn_o_spike, tpn_e_spike = bm.for_loop(run_net, (step_indices, *channel_inputs))

    rate_e = np.asarray(bp.measure.firing_rate(tpn_e_spike, width=1000.0))
    rate_o = np.asarray(bp.measure.firing_rate(tpn_o_spike, width=1000.0))
    return rate_e, rate_o


def signal_baseline_slices(
    *,
    config: SimulationConfig,
    baseline_start_ms: float,
    baseline_end_ms: float,
    signal_start_ms: float,
    signal_end_ms: float,
) -> tuple[slice, slice]:
    baseline = slice(int(round(baseline_start_ms / config.dt_sim_ms)), int(round(baseline_end_ms / config.dt_sim_ms)))
    signal = slice(int(round(signal_start_ms / config.dt_sim_ms)), int(round(signal_end_ms / config.dt_sim_ms)))
    return baseline, signal


def pathway_metrics(
    *,
    rate_e: np.ndarray,
    rate_o: np.ndarray,
    target_pathway: str,
    baseline_slice: slice,
    signal_slice: slice,
) -> dict[str, float]:
    target_rate = rate_e if target_pathway == "tpn_e" else rate_o
    other_rate = rate_o if target_pathway == "tpn_e" else rate_e
    target_signal = float(target_rate[signal_slice].sum())
    target_baseline = float(target_rate[baseline_slice].sum())
    other_signal = float(other_rate[signal_slice].sum())
    other_baseline = float(other_rate[baseline_slice].sum())
    total_signal = target_signal + other_signal
    accuracy = target_signal / total_signal if total_signal > 0 else float("nan")
    snr = target_signal / target_baseline if target_baseline > 0 else float("nan")
    preference = (float(rate_e[signal_slice].sum()) - float(rate_o[signal_slice].sum())) / total_signal if total_signal > 0 else float("nan")
    return {
        "target_signal_auc": target_signal,
        "target_baseline_auc": target_baseline,
        "other_signal_auc": other_signal,
        "other_baseline_auc": other_baseline,
        "accuracy": accuracy,
        "snr": snr,
        "preference_index": preference,
    }


def block_filter(block: str) -> set[str]:
    if block == "none":
        return set()
    if block == "tpn_e":
        return {"TPN_E"}
    if block == "tpn_o":
        return {"TPN_O"}
    if block == "e_tin":
        return {"E"}
    if block == "i_tin":
        return {"I"}
    if block == "tin":
        return {"E", "I"}
    raise ValueError(f"Unsupported block value: {block}")


def is_blocked(neuron_type: str, blocked: set[str]) -> bool:
    if neuron_type in blocked:
        return True
    if "E" in blocked and neuron_type.startswith("E_"):
        return True
    if "I" in blocked and neuron_type.startswith("I_"):
        return True
    return False


def serotonergic_thresholds(
    *,
    table_path: Path,
    dl_scale: float = 0.0,
    sl_scale: float = 0.0,
    max_threshold_shift_mv: float = 9.0,
    block: str = "none",
    base_threshold_mv: float = -50.0,
) -> dict[str, float]:
    blocked = block_filter(block)
    table = pd.read_csv(table_path)
    max_p = float(max(table["DL_5HT"].max(), table["SL_5HT"].max()))
    if max_p <= 0:
        raise ValueError("No positive serotonergic connection probability found in the Table S3 CSV.")
    gamma = max_threshold_shift_mv / max_p
    thresholds: dict[str, float] = {}
    for row in table.itertuples(index=False):
        neuron_type = str(row.Type)
        if is_blocked(neuron_type, blocked):
            continue
        total_probability = dl_scale * float(row.DL_5HT) + sl_scale * float(row.SL_5HT)
        if total_probability <= 0:
            continue
        thresholds[neuron_type] = base_threshold_mv - gamma * total_probability
    return thresholds
