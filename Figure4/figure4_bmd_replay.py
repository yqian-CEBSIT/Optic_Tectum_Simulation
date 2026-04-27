from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import brainpy as bp
import brainpy.math as bm
import numpy as np
import pandas as pd
from brainpy._src.math.object_transform.naming import clear_name_cache


ROOT = Path(__file__).resolve().parents[1]
ACCUMULATION = ROOT / "Figure2" / "accumulation"
sys.path.insert(0, str(ACCUMULATION))

from accumulation import INPUT_NEURON_TYPES, SimulationConfig, WholeOT, load_channel_inputs  # noqa: E402


def load_model_inputs(args: argparse.Namespace) -> tuple[list[str], dict[str, int], np.ndarray, tuple[bm.Array, ...], SimulationConfig]:
    counts = pd.read_csv(args.counts)
    neuron_types = counts["Type"].astype(str).tolist()
    neuron_numbers = {key: int(value) for key, value in counts.set_index("Type")["number"].to_dict().items()}
    conn_matrix = pd.read_csv(args.connections, index_col=0).to_numpy(dtype=float).round(args.connection_decimals)
    data_path = args.data.resolve()
    config = SimulationConfig(
        neuron_count_path=args.counts.resolve(),
        connection_path=args.connections.resolve(),
        data_path=data_path,
        order_path=Path("__unused_order__.csv"),
        output_path=Path("__unused_output__.csv"),
        target_pathway="tpn_e",
        data_sheet=args.sheet,
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        analysis_start_ms=args.analysis_start_ms,
        analysis_end_ms=args.analysis_end_ms,
        gain_coeff=args.gain_coeff,
        channel_gains=tuple(args.channel_gains),
    )
    _, channel_inputs = load_channel_inputs(config)
    return neuron_types, neuron_numbers, conn_matrix, channel_inputs, config


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
    table_path: Path,
    subtype: str,
    max_threshold_shift_mv: float,
    block: str,
    base_threshold_mv: float = -50.0,
) -> dict[str, float]:
    if subtype == "control":
        return {}
    column = {"dl": "DL_5HT", "sl": "SL_5HT"}[subtype]
    table = pd.read_csv(table_path)
    max_p = float(table[column].max())
    if max_p <= 0:
        raise ValueError(f"No positive serotonergic probabilities found in {column}.")
    gamma = max_threshold_shift_mv / max_p
    blocked = block_filter(block)
    thresholds: dict[str, float] = {}
    for row in table.itertuples(index=False):
        neuron_type = str(row.Type)
        probability = float(getattr(row, column))
        if probability <= 0 or is_blocked(neuron_type, blocked):
            continue
        thresholds[neuron_type] = base_threshold_mv - gamma * probability
    return thresholds


def run_trial(
    neuron_types: list[str],
    neuron_numbers: dict[str, int],
    conn_matrix: np.ndarray,
    channel_inputs: tuple[bm.Array, ...],
    config: SimulationConfig,
    threshold_overrides: dict[str, float],
    seed: int,
) -> dict[str, float]:
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
    analysis = slice(config.analysis_start_index, config.analysis_end_index)
    auc_e = float(rate_e[analysis].sum())
    auc_o = float(rate_o[analysis].sum())
    preference = (auc_e - auc_o) / (auc_e + auc_o) if auc_e + auc_o > 0 else float("nan")
    return {"tpn_e_auc": auc_e, "tpn_o_auc": auc_o, "preference_index": preference}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay Figure 4/S6 BMD simulations with the manuscript Table S3 threshold-modulation formula."
    )
    parser.add_argument("--data", type=Path, default=Path("BD_10.xlsx"), help="BMD calcium-input workbook.")
    parser.add_argument("--sheet", default="Sheet1", help="Input workbook sheet. Use smoothed_repaired for BD_16.xlsx.")
    parser.add_argument("--counts", type=Path, default=ROOT / "Figure4" / "neuron_number.csv")
    parser.add_argument("--connections", type=Path, default=ROOT / "Figure4" / "neuron_connections_whole.csv")
    parser.add_argument("--serotonin-table", type=Path, default=ROOT / "Figure4" / "serotonergic_connections.csv")
    parser.add_argument("--subtype", choices=("control", "dl", "sl"), default="control")
    parser.add_argument("--block", choices=("none", "tpn_e", "tpn_o", "e_tin", "i_tin", "tin"), default="none")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--dt-sim-ms", type=float, default=0.1)
    parser.add_argument("--sim-duration-ms", type=float, default=60_000.0)
    parser.add_argument("--analysis-start-ms", type=float, default=30_000.0)
    parser.add_argument("--analysis-end-ms", type=float, default=45_000.0)
    parser.add_argument("--gain-coeff", type=float, default=65.0)
    parser.add_argument("--channel-gains", type=float, nargs=6, default=(1.0, 1.0, 1.0, 3.0, 3.0, 1.0))
    parser.add_argument("--connection-decimals", type=int, default=3)
    parser.add_argument("--max-threshold-shift-mv", type=float, default=9.0)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    neuron_types, neuron_numbers, conn_matrix, channel_inputs, config = load_model_inputs(args)
    thresholds = serotonergic_thresholds(
        table_path=args.serotonin_table,
        subtype=args.subtype,
        max_threshold_shift_mv=args.max_threshold_shift_mv,
        block=args.block,
    )
    rows = []
    for trial in range(args.trials):
        metrics = run_trial(
            neuron_types=neuron_types,
            neuron_numbers=neuron_numbers,
            conn_matrix=conn_matrix,
            channel_inputs=channel_inputs,
            config=config,
            threshold_overrides=thresholds,
            seed=args.seed + trial,
        )
        rows.append({"trial": trial + 1, "condition": args.subtype, "block": args.block, **metrics})

    df = pd.DataFrame(rows)
    summary = {
        "data": str(args.data),
        "sheet": args.sheet,
        "condition": args.subtype,
        "block": args.block,
        "trials": args.trials,
        "threshold_overrides": len(thresholds),
        "mean_tpn_e_auc": float(df["tpn_e_auc"].mean()),
        "mean_tpn_o_auc": float(df["tpn_o_auc"].mean()),
        "mean_preference_index": float(df["preference_index"].mean()),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False)
    print(json.dumps({"summary": summary, "trials": rows}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
