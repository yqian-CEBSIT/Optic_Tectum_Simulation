from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from public_model_utils import (  # noqa: E402
    apply_tin_selection,
    e_tin_types,
    i_tin_types,
    load_channel_inputs_with_shift,
    load_model_definition,
    make_config,
    pathway_metrics,
    run_spiking_trial,
    signal_baseline_slices,
    tin_types,
)


NOISE_FILES = {
    "looming": {
        0.0: "NLooming0.xlsx",
        0.01: "NLooming001.xlsx",
        0.05: "NLooming005.xlsx",
        0.1: "NLooming01.xlsx",
        0.2: "NLooming02.xlsx",
        0.5: "NLooming05.xlsx",
    },
    "smd": {
        0.0: "NSD0.xlsx",
        0.01: "NSD001.xlsx",
        0.05: "NSD005.xlsx",
        0.1: "NSD01.xlsx",
        0.2: "NSD02.xlsx",
        0.5: "NSD05.xlsx",
    },
}


def canonical_noise_levels(values: list[float]) -> list[float]:
    return [float(value) for value in values]


def target_pathway(modality: str) -> str:
    return "tpn_e" if modality == "looming" else "tpn_o"


def noisy_paths(modality: str, levels: list[float]) -> list[tuple[float, Path]]:
    mapping = NOISE_FILES[modality]
    result = []
    for level in levels:
        if level not in mapping:
            raise ValueError(f"No workbook configured for modality={modality} at noise level {level}.")
        result.append((level, Path(__file__).resolve().parent / mapping[level]))
    return result


def base_setup(args: argparse.Namespace, modality: str, data_path: Path) -> tuple[list[str], dict[str, int], np.ndarray, tuple, object]:
    counts = (ROOT / "Figure3" / "neuron_number.csv").resolve()
    connections = (ROOT / "Figure3" / "neuron_connections_whole.csv").resolve()
    neuron_types, neuron_numbers, conn_matrix = load_model_definition(counts, connections, args.connection_decimals)
    config = make_config(
        counts_path=counts,
        connections_path=connections,
        data_path=data_path,
        target_pathway=target_pathway(modality),
        dt_sim_ms=args.dt_sim_ms,
        sim_duration_ms=args.sim_duration_ms,
        analysis_start_ms=args.signal_start_ms,
        analysis_end_ms=args.signal_end_ms,
        gain_coeff=args.gain_coeff,
        channel_gains=tuple(args.channel_gains),
    )
    _, channel_inputs = load_channel_inputs_with_shift(config, lead_ms=args.calcium_lead_ms)
    return neuron_types, neuron_numbers, conn_matrix, channel_inputs, config


def metric_slices(args: argparse.Namespace, config) -> tuple[slice, slice]:
    return signal_baseline_slices(
        config=config,
        baseline_start_ms=args.baseline_start_ms,
        baseline_end_ms=args.baseline_end_ms,
        signal_start_ms=args.signal_start_ms,
        signal_end_ms=args.signal_end_ms,
    )


def run_condition_trials(
    *,
    args: argparse.Namespace,
    modality: str,
    data_path: Path,
    neuron_numbers: dict[str, int],
) -> list[dict[str, float]]:
    neuron_types, _, conn_matrix, channel_inputs, config = base_setup(args, modality, data_path)
    baseline_slice, signal_slice = metric_slices(args, config)
    rows = []
    for trial in range(args.trials):
        rate_e, rate_o = run_spiking_trial(
            neuron_types=neuron_types,
            neuron_numbers=neuron_numbers,
            conn_matrix=conn_matrix,
            channel_inputs=channel_inputs,
            config=config,
            seed=args.seed + trial,
        )
        rows.append(
            pathway_metrics(
                rate_e=rate_e,
                rate_o=rate_o,
                target_pathway=target_pathway(modality),
                baseline_slice=baseline_slice,
                signal_slice=signal_slice,
            )
        )
    return rows


def summarize_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    frame = pd.DataFrame(rows)
    result = {}
    for column in frame.columns:
        result[f"mean_{column}"] = float(frame[column].mean())
        result[f"sem_{column}"] = float(frame[column].sem()) if len(frame) > 1 else 0.0
    return result


def analysis_response_curve(args: argparse.Namespace) -> dict[str, object]:
    rows = []
    reference_signal = None
    neuron_types, base_numbers, _, _, _ = base_setup(args, args.modality, noisy_paths(args.modality, args.noise_levels)[0][1])
    full_numbers = apply_tin_selection(base_numbers, neuron_types, keep_tins=set(tin_types(neuron_types)))
    for level, data_path in noisy_paths(args.modality, args.noise_levels):
        trial_rows = run_condition_trials(args=args, modality=args.modality, data_path=data_path, neuron_numbers=full_numbers)
        summary = summarize_rows(trial_rows)
        if reference_signal is None:
            reference_signal = summary["mean_target_signal_auc"]
        rows.append(
            {
                "noise_level": level,
                **summary,
                "mean_target_signal_norm": summary["mean_target_signal_auc"] / reference_signal if reference_signal else float("nan"),
                "mean_other_signal_norm": summary["mean_other_signal_auc"] / reference_signal if reference_signal else float("nan"),
            }
        )
    return {"analysis": "response_curve", "modality": args.modality, "rows": rows}


def analysis_family_compare(args: argparse.Namespace) -> dict[str, object]:
    neuron_types, base_numbers, _, _, _ = base_setup(args, args.modality, noisy_paths(args.modality, args.noise_levels)[0][1])
    all_tins = set(tin_types(neuron_types))
    families = {
        "no_tin": apply_tin_selection(base_numbers, neuron_types, keep_tins=set()),
        "e_tin_only": apply_tin_selection(base_numbers, neuron_types, keep_tins=set(e_tin_types(neuron_types))),
        "i_tin_only": apply_tin_selection(base_numbers, neuron_types, keep_tins=set(i_tin_types(neuron_types))),
        "full_tin": apply_tin_selection(base_numbers, neuron_types, keep_tins=all_tins),
    }
    rows = []
    for level, data_path in noisy_paths(args.modality, args.noise_levels):
        per_family = {}
        for label, numbers in families.items():
            trial_rows = run_condition_trials(args=args, modality=args.modality, data_path=data_path, neuron_numbers=numbers)
            per_family[label] = summarize_rows(trial_rows)
        baseline_snr = per_family["no_tin"]["mean_snr"]
        rows.append(
            {
                "noise_level": level,
                "no_tin_snr": baseline_snr,
                "e_tin_only_snr": per_family["e_tin_only"]["mean_snr"],
                "i_tin_only_snr": per_family["i_tin_only"]["mean_snr"],
                "full_tin_snr": per_family["full_tin"]["mean_snr"],
                "e_tin_only_fold_change": per_family["e_tin_only"]["mean_snr"] / baseline_snr if baseline_snr else float("nan"),
                "i_tin_only_fold_change": per_family["i_tin_only"]["mean_snr"] / baseline_snr if baseline_snr else float("nan"),
                "full_tin_fold_change": per_family["full_tin"]["mean_snr"] / baseline_snr if baseline_snr else float("nan"),
            }
        )
    return {"analysis": "family_compare", "modality": args.modality, "rows": rows}


def scan_fold_changes(
    *,
    args: argparse.Namespace,
    modality: str,
    levels: list[float],
    morphotypes: list[str],
) -> list[dict[str, object]]:
    neuron_types, base_numbers, _, _, _ = base_setup(args, modality, noisy_paths(modality, levels)[0][1])
    baseline_numbers = apply_tin_selection(base_numbers, neuron_types, keep_tins=set())
    rows = []
    for level, data_path in noisy_paths(modality, levels):
        baseline_rows = run_condition_trials(args=args, modality=modality, data_path=data_path, neuron_numbers=baseline_numbers)
        baseline_summary = summarize_rows(baseline_rows)
        baseline_snr = baseline_summary["mean_snr"]
        for morphotype in morphotypes:
            single_rows = run_condition_trials(
                args=args,
                modality=modality,
                data_path=data_path,
                neuron_numbers=apply_tin_selection(base_numbers, neuron_types, keep_tins={morphotype}),
            )
            summary = summarize_rows(single_rows)
            rows.append(
                {
                    "noise_level": level,
                    "morphotype": morphotype,
                    "family": "e_tin" if morphotype.startswith("E_") else "i_tin",
                    "mean_snr": summary["mean_snr"],
                    "fold_change_vs_no_tin": summary["mean_snr"] / baseline_snr if baseline_snr else float("nan"),
                }
            )
    return rows


def analysis_single_scan(args: argparse.Namespace) -> dict[str, object]:
    neuron_types, _, _, _, _ = base_setup(args, args.modality, noisy_paths(args.modality, args.noise_levels)[0][1])
    morphotypes = args.morphotypes or tin_types(neuron_types)
    rows = scan_fold_changes(args=args, modality=args.modality, levels=args.noise_levels, morphotypes=morphotypes)
    return {"analysis": "single_scan", "modality": args.modality, "rows": rows}


def rank_top4_from_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    frame = pd.DataFrame(rows)
    grouped = frame.pivot_table(index="morphotype", columns="noise_level", values="fold_change_vs_no_tin", aggfunc="mean")
    grouped = grouped.fillna(np.nan)
    grouped["robustness_score"] = grouped[[0.01, 0.05]].mean(axis=1) - grouped[0.0]
    grouped["family"] = ["e_tin" if idx.startswith("E_") else "i_tin" for idx in grouped.index]
    ranking = grouped.sort_values("robustness_score", ascending=False).reset_index()
    ranking = ranking.rename(columns={"index": "morphotype"})
    return ranking.to_dict(orient="records")


def analysis_rank_top4(args: argparse.Namespace) -> dict[str, object]:
    neuron_types, _, _, _, _ = base_setup(args, args.modality, noisy_paths(args.modality, [0.0])[0][1])
    rows = scan_fold_changes(args=args, modality=args.modality, levels=[0.0, 0.01, 0.05], morphotypes=tin_types(neuron_types))
    ranking = rank_top4_from_rows(rows)
    top4 = [row["morphotype"] for row in ranking if row["family"] == "e_tin"][:4]
    return {"analysis": "rank_top4", "modality": args.modality, "top4_e_tins": top4, "ranking": ranking}


def analysis_top4_ablation(args: argparse.Namespace) -> dict[str, object]:
    rank_result = analysis_rank_top4(args)
    top4 = set(rank_result["top4_e_tins"])
    neuron_types, base_numbers, _, _, _ = base_setup(args, args.modality, noisy_paths(args.modality, args.comparison_noise_levels)[0][1])
    all_e_tins = set(e_tin_types(neuron_types))
    specific_numbers = apply_tin_selection(base_numbers, neuron_types, ablate_tins=top4)
    nonspecific_numbers = apply_tin_selection(base_numbers, neuron_types, ablate_tins=all_e_tins - top4)
    full_numbers = dict(base_numbers)
    control_rows = []
    specific_rows = []
    nonspecific_rows = []
    for level, data_path in noisy_paths(args.modality, args.comparison_noise_levels):
        control_rows.extend(run_condition_trials(args=args, modality=args.modality, data_path=data_path, neuron_numbers=full_numbers))
        specific_rows.extend(run_condition_trials(args=args, modality=args.modality, data_path=data_path, neuron_numbers=specific_numbers))
        nonspecific_rows.extend(run_condition_trials(args=args, modality=args.modality, data_path=data_path, neuron_numbers=nonspecific_numbers))
    control_df = pd.DataFrame(control_rows)
    specific_df = pd.DataFrame(specific_rows)
    nonspecific_df = pd.DataFrame(nonspecific_rows)
    return {
        "analysis": "top4_ablation",
        "modality": args.modality,
        "top4_e_tins": sorted(top4),
        "control_summary": summarize_rows(control_rows),
        "specific_summary": summarize_rows(specific_rows),
        "nonspecific_summary": summarize_rows(nonspecific_rows),
        "specific_fold_change_vs_control": float(specific_df["snr"].mean() / control_df["snr"].mean()),
        "nonspecific_fold_change_vs_control": float(nonspecific_df["snr"].mean() / control_df["snr"].mean()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay the Figure 3 and Figure S5 robustness analyses from the public code bundle.")
    parser.add_argument("--analysis", choices=("response_curve", "family_compare", "single_scan", "rank_top4", "top4_ablation"), required=True)
    parser.add_argument("--modality", choices=("looming", "smd"), required=True)
    parser.add_argument("--noise-levels", type=float, nargs="+", default=[0.0, 0.01, 0.05, 0.1, 0.2, 0.5])
    parser.add_argument("--comparison-noise-levels", type=float, nargs="+", default=[0.01, 0.05])
    parser.add_argument("--morphotypes", nargs="*", default=None)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--dt-sim-ms", type=float, default=0.1)
    parser.add_argument("--sim-duration-ms", type=float, default=30_000.0)
    parser.add_argument("--baseline-start-ms", type=float, default=0.0)
    parser.add_argument("--baseline-end-ms", type=float, default=15_000.0)
    parser.add_argument("--signal-start-ms", type=float, default=15_000.0)
    parser.add_argument("--signal-end-ms", type=float, default=30_000.0)
    parser.add_argument("--calcium-lead-ms", type=float, default=2_000.0)
    parser.add_argument("--gain-coeff", type=float, default=65.0)
    parser.add_argument("--channel-gains", type=float, nargs=6, default=(1.0, 1.0, 1.0, 3.0, 3.0, 1.0))
    parser.add_argument("--connection-decimals", type=int, default=3)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    args.noise_levels = canonical_noise_levels(args.noise_levels)
    args.comparison_noise_levels = canonical_noise_levels(args.comparison_noise_levels)
    return args


def main() -> None:
    args = parse_args()
    if args.analysis == "response_curve":
        payload = analysis_response_curve(args)
    elif args.analysis == "family_compare":
        payload = analysis_family_compare(args)
    elif args.analysis == "single_scan":
        payload = analysis_single_scan(args)
    elif args.analysis == "rank_top4":
        payload = analysis_rank_top4(args)
    else:
        payload = analysis_top4_ablation(args)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload.get("rows"), list):
            pd.DataFrame(payload["rows"]).to_csv(args.output, index=False)
        elif isinstance(payload.get("ranking"), list):
            pd.DataFrame(payload["ranking"]).to_csv(args.output, index=False)
        else:
            args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
