from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from public_model_utils import (  # noqa: E402
    load_channel_inputs_with_shift,
    load_model_definition,
    make_config,
    pathway_metrics,
    run_spiking_trial,
    serotonergic_thresholds,
    signal_baseline_slices,
)


NOISE_FILES = {
    "looming": {
        0.0: ROOT / "Figure3" / "NLooming0.xlsx",
        0.01: ROOT / "Figure3" / "NLooming001.xlsx",
        0.05: ROOT / "Figure3" / "NLooming005.xlsx",
        0.1: ROOT / "Figure3" / "NLooming01.xlsx",
        0.2: ROOT / "Figure3" / "NLooming02.xlsx",
        0.5: ROOT / "Figure3" / "NLooming05.xlsx",
    },
    "smd": {
        0.0: ROOT / "Figure3" / "NSD0.xlsx",
        0.01: ROOT / "Figure3" / "NSD001.xlsx",
        0.05: ROOT / "Figure3" / "NSD005.xlsx",
        0.1: ROOT / "Figure3" / "NSD01.xlsx",
        0.2: ROOT / "Figure3" / "NSD02.xlsx",
        0.5: ROOT / "Figure3" / "NSD05.xlsx",
    },
}


def summarize_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    frame = pd.DataFrame(rows)
    result = {}
    for column in frame.columns:
        result[f"mean_{column}"] = float(frame[column].mean())
        result[f"sem_{column}"] = float(frame[column].sem()) if len(frame) > 1 else 0.0
    return result


def pathway_for_modality(modality: str) -> str:
    return "tpn_e" if modality == "looming" else "tpn_o"


def run_trials(
    *,
    counts_path: Path,
    connections_path: Path,
    data_path: Path,
    data_sheet: str,
    target_pathway: str,
    trials: int,
    seed: int,
    dt_sim_ms: float,
    sim_duration_ms: float,
    baseline_start_ms: float,
    baseline_end_ms: float,
    signal_start_ms: float,
    signal_end_ms: float,
    gain_coeff: float,
    channel_gains: tuple[float, ...],
    connection_decimals: int,
    calcium_lead_ms: float,
    threshold_overrides: dict[str, float] | None,
) -> list[dict[str, float]]:
    neuron_types, neuron_numbers, conn_matrix = load_model_definition(counts_path, connections_path, connection_decimals)
    config = make_config(
        counts_path=counts_path,
        connections_path=connections_path,
        data_path=data_path,
        target_pathway=target_pathway,
        data_sheet=data_sheet,
        dt_sim_ms=dt_sim_ms,
        sim_duration_ms=sim_duration_ms,
        analysis_start_ms=signal_start_ms,
        analysis_end_ms=signal_end_ms,
        gain_coeff=gain_coeff,
        channel_gains=channel_gains,
    )
    _, channel_inputs = load_channel_inputs_with_shift(config, lead_ms=calcium_lead_ms)
    baseline_slice, signal_slice = signal_baseline_slices(
        config=config,
        baseline_start_ms=baseline_start_ms,
        baseline_end_ms=baseline_end_ms,
        signal_start_ms=signal_start_ms,
        signal_end_ms=signal_end_ms,
    )

    rows = []
    for trial in range(trials):
        rate_e, rate_o = run_spiking_trial(
            neuron_types=neuron_types,
            neuron_numbers=neuron_numbers,
            conn_matrix=conn_matrix,
            channel_inputs=channel_inputs,
            config=config,
            seed=seed + trial,
            threshold_overrides=threshold_overrides,
        )
        rows.append(
            pathway_metrics(
                rate_e=rate_e,
                rate_o=rate_o,
                target_pathway=target_pathway,
                baseline_slice=baseline_slice,
                signal_slice=signal_slice,
            )
        )
    return rows


def analysis_related_accuracy(args: argparse.Namespace) -> dict[str, object]:
    serotonin_table = ROOT / "Figure4" / "serotonergic_connections.csv"
    counts = ROOT / "Figure2" / "neuron_number.csv"
    connections = ROOT / "Figure2" / "neuron_connections_whole.csv"
    looming_data = ROOT / "Figure2" / "Looming_Ex.xlsx"
    smd_data = ROOT / "Figure2" / "SD_Ex.xlsx"

    looming_control = run_trials(
        counts_path=counts,
        connections_path=connections,
        data_path=looming_data,
        data_sheet="Sheet1",
        target_pathway="tpn_e",
        trials=args.trials,
        seed=args.seed,
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        baseline_start_ms=args.baseline_start_ms,
        baseline_end_ms=args.baseline_end_ms,
        signal_start_ms=args.signal_start_ms,
        signal_end_ms=args.signal_end_ms,
        gain_coeff=args.gain_coeff,
        channel_gains=tuple(args.channel_gains),
        connection_decimals=args.connection_decimals,
        calcium_lead_ms=0.0,
        threshold_overrides={},
    )
    looming_dl = run_trials(
        counts_path=counts,
        connections_path=connections,
        data_path=looming_data,
        data_sheet="Sheet1",
        target_pathway="tpn_e",
        trials=args.trials,
        seed=args.seed,
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        baseline_start_ms=args.baseline_start_ms,
        baseline_end_ms=args.baseline_end_ms,
        signal_start_ms=args.signal_start_ms,
        signal_end_ms=args.signal_end_ms,
        gain_coeff=args.gain_coeff,
        channel_gains=tuple(args.channel_gains),
        connection_decimals=args.connection_decimals,
        calcium_lead_ms=0.0,
        threshold_overrides=serotonergic_thresholds(table_path=serotonin_table, dl_scale=1.0, sl_scale=0.0, max_threshold_shift_mv=args.max_threshold_shift_mv),
    )
    smd_control = run_trials(
        counts_path=counts,
        connections_path=connections,
        data_path=smd_data,
        data_sheet="Sheet1",
        target_pathway="tpn_o",
        trials=args.trials,
        seed=args.seed,
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        baseline_start_ms=args.baseline_start_ms,
        baseline_end_ms=args.baseline_end_ms,
        signal_start_ms=args.signal_start_ms,
        signal_end_ms=args.signal_end_ms,
        gain_coeff=args.gain_coeff,
        channel_gains=tuple(args.channel_gains),
        connection_decimals=args.connection_decimals,
        calcium_lead_ms=0.0,
        threshold_overrides={},
    )
    smd_sl = run_trials(
        counts_path=counts,
        connections_path=connections,
        data_path=smd_data,
        data_sheet="Sheet1",
        target_pathway="tpn_o",
        trials=args.trials,
        seed=args.seed,
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        baseline_start_ms=args.baseline_start_ms,
        baseline_end_ms=args.baseline_end_ms,
        signal_start_ms=args.signal_start_ms,
        signal_end_ms=args.signal_end_ms,
        gain_coeff=args.gain_coeff,
        channel_gains=tuple(args.channel_gains),
        connection_decimals=args.connection_decimals,
        calcium_lead_ms=0.0,
        threshold_overrides=serotonergic_thresholds(table_path=serotonin_table, dl_scale=0.0, sl_scale=1.0, max_threshold_shift_mv=args.max_threshold_shift_mv),
    )
    return {
        "analysis": "related_accuracy",
        "figure_panels": ["Figure 5H"],
        "looming_control": summarize_rows(looming_control),
        "looming_dl_activation": summarize_rows(looming_dl),
        "smd_control": summarize_rows(smd_control),
        "smd_sl_activation": summarize_rows(smd_sl),
    }


def analysis_noise_boost(args: argparse.Namespace) -> dict[str, object]:
    serotonin_table = ROOT / "Figure4" / "serotonergic_connections.csv"
    counts = ROOT / "Figure3" / "neuron_number.csv"
    connections = ROOT / "Figure3" / "neuron_connections_whole.csv"
    subtype = "dl" if args.modality == "looming" else "sl"
    target = pathway_for_modality(args.modality)
    activation = serotonergic_thresholds(
        table_path=serotonin_table,
        dl_scale=1.0 if subtype == "dl" else 0.0,
        sl_scale=1.0 if subtype == "sl" else 0.0,
        max_threshold_shift_mv=args.max_threshold_shift_mv,
    )
    rows = []
    for level in [float(value) for value in args.noise_levels]:
        data_path = NOISE_FILES[args.modality][level]
        control = run_trials(
            counts_path=counts,
            connections_path=connections,
            data_path=data_path,
            data_sheet="Sheet1",
            target_pathway=target,
            trials=args.trials,
            seed=args.seed,
            dt_sim_ms=args.dt_sim_ms,
            sim_duration_ms=args.sim_duration_ms,
            baseline_start_ms=args.baseline_start_ms,
            baseline_end_ms=args.baseline_end_ms,
            signal_start_ms=args.signal_start_ms,
            signal_end_ms=args.signal_end_ms,
            gain_coeff=args.gain_coeff,
            channel_gains=tuple(args.channel_gains),
            connection_decimals=args.connection_decimals,
            calcium_lead_ms=args.calcium_lead_ms,
            threshold_overrides={},
        )
        activated = run_trials(
            counts_path=counts,
            connections_path=connections,
            data_path=data_path,
            data_sheet="Sheet1",
            target_pathway=target,
            trials=args.trials,
            seed=args.seed,
            dt_sim_ms=args.dt_sim_ms,
            sim_duration_ms=args.sim_duration_ms,
            baseline_start_ms=args.baseline_start_ms,
            baseline_end_ms=args.baseline_end_ms,
            signal_start_ms=args.signal_start_ms,
            signal_end_ms=args.signal_end_ms,
            gain_coeff=args.gain_coeff,
            channel_gains=tuple(args.channel_gains),
            connection_decimals=args.connection_decimals,
            calcium_lead_ms=args.calcium_lead_ms,
            threshold_overrides=activation,
        )
        control_summary = summarize_rows(control)
        activated_summary = summarize_rows(activated)
        rows.append(
            {
                "noise_level": level,
                "control_snr": control_summary["mean_snr"],
                "activated_snr": activated_summary["mean_snr"],
                "fold_change_vs_control": activated_summary["mean_snr"] / control_summary["mean_snr"] if control_summary["mean_snr"] else float("nan"),
            }
        )
    return {
        "analysis": "noise_boost",
        "figure_panels": ["Figure 5I" if args.modality == "looming" else "Figure 5J"],
        "modality": args.modality,
        "rows": rows,
    }


def analysis_proxy_bias_curve(args: argparse.Namespace) -> dict[str, object]:
    serotonin_table = ROOT / "Figure4" / "serotonergic_connections.csv"
    counts = ROOT / "Figure4" / "neuron_number.csv"
    connections = ROOT / "Figure4" / "neuron_connections_whole.csv"
    data_path = ROOT / "Figure4" / "BD_10.xlsx"
    rows = []
    for dominance in args.dominance_values:
        dl_scale = max(0.0, 1.0 + dominance)
        sl_scale = max(0.0, 1.0 - dominance)
        activation = serotonergic_thresholds(
            table_path=serotonin_table,
            dl_scale=dl_scale,
            sl_scale=sl_scale,
            max_threshold_shift_mv=args.max_threshold_shift_mv,
        )
        trials = run_trials(
            counts_path=counts,
            connections_path=connections,
            data_path=data_path,
            data_sheet="Sheet1",
            target_pathway="tpn_e",
            trials=args.trials,
            seed=args.seed,
            dt_sim_ms=args.dt_sim_ms,
            sim_duration_ms=args.sim_duration_ms,
            baseline_start_ms=args.baseline_start_ms,
            baseline_end_ms=args.baseline_end_ms,
            signal_start_ms=args.signal_start_ms,
            signal_end_ms=args.signal_end_ms,
            gain_coeff=args.gain_coeff,
            channel_gains=tuple(args.channel_gains),
            connection_decimals=args.connection_decimals,
            calcium_lead_ms=0.0,
            threshold_overrides=activation,
        )
        summary = summarize_rows(trials)
        rows.append(
            {
                "dominance": dominance,
                "dl_scale": dl_scale,
                "sl_scale": sl_scale,
                "tpn_e_signal_auc": summary["mean_target_signal_auc"],
                "tpn_o_signal_auc": summary["mean_other_signal_auc"],
                "preference_index": summary["mean_preference_index"],
            }
        )
    return {
        "analysis": "proxy_bias_curve",
        "figure_panels": ["Figure 5D (public proxy using BD_10.xlsx; 8-degree BMD input is not included in this bundle)"],
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay the Figure 5 model panels supported by the public simulation bundle.")
    parser.add_argument("--analysis", choices=("related_accuracy", "noise_boost", "proxy_bias_curve"), required=True)
    parser.add_argument("--modality", choices=("looming", "smd"), default="looming")
    parser.add_argument("--noise-levels", type=float, nargs="+", default=[0.0, 0.01, 0.05, 0.1, 0.2, 0.5])
    parser.add_argument("--dominance-values", type=float, nargs="+", default=[-1.0, -0.5, 0.0, 0.5, 1.0])
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--dt-sim-ms", type=float, default=0.1)
    parser.add_argument("--sim-duration-ms", type=float, default=60_000.0)
    parser.add_argument("--baseline-start-ms", type=float, default=0.0)
    parser.add_argument("--baseline-end-ms", type=float, default=15_000.0)
    parser.add_argument("--signal-start-ms", type=float, default=30_000.0)
    parser.add_argument("--signal-end-ms", type=float, default=45_000.0)
    parser.add_argument("--calcium-lead-ms", type=float, default=2_000.0)
    parser.add_argument("--gain-coeff", type=float, default=65.0)
    parser.add_argument("--channel-gains", type=float, nargs=6, default=(1.0, 1.0, 1.0, 3.0, 3.0, 1.0))
    parser.add_argument("--connection-decimals", type=int, default=3)
    parser.add_argument("--max-threshold-shift-mv", type=float, default=9.0)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.analysis == "related_accuracy":
        payload = analysis_related_accuracy(args)
    elif args.analysis == "noise_boost":
        payload = analysis_noise_boost(args)
    else:
        payload = analysis_proxy_bias_curve(args)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload.get("rows"), list):
            pd.DataFrame(payload["rows"]).to_csv(args.output, index=False)
        else:
            args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
