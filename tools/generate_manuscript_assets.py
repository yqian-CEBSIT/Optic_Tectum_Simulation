from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIGURE2 = ROOT / "Figure2"
ACCUMULATION = FIGURE2 / "accumulation"
FIGURE3 = ROOT / "Figure3"
FIGURE4 = ROOT / "Figure4"

INPUT_TYPES = {"RGC_SO", "RGC_S12", "RGC_S34", "RGC_S56", "RGC_SGC", "RGC_SAC"}
OUTPUT_TYPES = {"TPN_E", "TPN_O"}
CRITICAL_LOOMING = {"I_S12", "I_SIN"}
CRITICAL_SMD = {"I_S12_S56", "I_S12_S56_SGC"}

SEROTONERGIC_CONNECTIONS = [
    ("E_ns", 0.038583, 0.0),
    ("E_SO", 0.0, 0.0),
    ("E_SO_S56", 0.029326, 0.0),
    ("E_SO_S56_SGC", 0.060932, 0.0),
    ("E_S12", 0.013441, 0.0),
    ("E_S12_S34_S56", 0.0, 0.0),
    ("E_S12_S34_S56_SGC", 0.0, 0.0),
    ("E_S12_S56", 0.014007, 0.00263),
    ("E_S12_S56_SGC", 0.039171, 0.01429),
    ("E_S12_SGC", 0.048387, 0.0),
    ("E_S34", 0.0, 0.0),
    ("E_S34_S56", 0.004608, 0.0),
    ("E_S34_S56_SGC", 0.0, 0.0),
    ("E_S34_SGC", 0.004301, 0.0),
    ("E_S34_SGC_SAC", 0.043733, 0.0),
    ("E_S56", 0.0, 0.0),
    ("E_S56_SGC", 0.0, 0.0),
    ("E_S56_SGC_SAC", 0.001241, 0.0),
    ("E_SGC", 0.0, 0.0),
    ("E_SAC", 0.032258, 0.0),
    ("I_ns", 0.044734, 0.0),
    ("I_SO", 0.025806, 0.0),
    ("I_SO_S12", 0.056452, 0.0),
    ("I_SO_S12_S56", 0.064516, 0.04667),
    ("I_SO_S56", 0.005161, 0.0),
    ("I_SO_S56_SGC", 0.010753, 0.0),
    ("I_S12", 0.008295, 0.02857),
    ("I_S12_S34_S56_SGC", 0.0, 0.0),
    ("I_S12_S34_SGC", 0.0, 0.0),
    ("I_S12_S56", 0.014461, 0.04345),
    ("I_S12_S56_SGC", 0.000949, 0.0),
    ("I_S12_SGC", 0.0681, 0.0),
    ("I_S34", 0.0, 0.0),
    ("I_S34_S56", 0.004032, 0.0),
    ("I_S34_S56_SGC", 0.011921, 0.00435),
    ("I_S34_SGC", 0.001898, 0.0),
    ("I_S34_SGC_SAC", 0.177419, 0.05),
    ("I_S56", 0.024516, 0.0),
    ("I_S56_SAC", 0.0, 0.0),
    ("I_S56_SGC", 0.026546, 0.00417),
    ("I_S56_SGC_SAC", 0.023297, 0.0),
    ("I_SGC", 0.002304, 0.0),
    ("I_SGC_SAC", 0.0, 0.0),
    ("I_SIN", 0.038306, 0.0297),
    ("TPN_E", 0.315536, 0.049),
    ("TPN_O", 0.049168, 0.20226),
]


def canonical_types() -> list[str]:
    counts = pd.read_csv(FIGURE2 / "neuron_number.csv")
    return counts["Type"].astype(str).tolist()


def tin_types(types: list[str]) -> list[str]:
    return [value for value in types if value not in INPUT_TYPES and value not in OUTPUT_TYPES]


def clean_order(path: Path, tins: list[str]) -> None:
    order = pd.read_csv(path).iloc[:, 0].astype(str).tolist()
    seen: set[str] = set()
    cleaned: list[str] = []
    missing_pool = [value for value in tins if value not in order]

    for value in order:
        if value not in tins:
            continue
        if value in seen:
            if not missing_pool:
                continue
            value = missing_pool.pop(0)
        cleaned.append(value)
        seen.add(value)

    for value in tins:
        if value not in seen:
            cleaned.append(value)
            seen.add(value)

    if len(cleaned) != len(tins) or len(set(cleaned)) != len(tins):
        raise RuntimeError(f"Could not repair {path} to exactly {len(tins)} unique TIN morphotypes.")
    pd.DataFrame({"Type": cleaned}).to_csv(path, index=False)


def zero_types(matrix: pd.DataFrame, types_to_zero: set[str]) -> pd.DataFrame:
    edited = matrix.copy()
    for neuron_type in sorted(types_to_zero):
        if neuron_type not in edited.index or neuron_type not in edited.columns:
            raise KeyError(f"{neuron_type} is absent from the canonical connection matrix.")
        edited.loc[neuron_type, :] = 0.0
        edited.loc[:, neuron_type] = 0.0
    return edited


def write_figure2_ablation_matrices(tins: list[str]) -> None:
    base = pd.read_csv(FIGURE2 / "neuron_connections_whole.csv", index_col=0)
    all_tins = set(tins)
    zero_types(base, all_tins).to_csv(FIGURE2 / "neuron_connections_whole_ab.csv")
    zero_types(base, CRITICAL_LOOMING).to_csv(FIGURE2 / "neuron_connections_whole_cri_L_test.csv")
    zero_types(base, all_tins - CRITICAL_LOOMING).to_csv(FIGURE2 / "neuron_connections_whole_noncri_L.csv")
    zero_types(base, CRITICAL_SMD).to_csv(FIGURE2 / "neuron_connections_whole_cri_S_test.csv")
    zero_types(base, all_tins - CRITICAL_SMD).to_csv(FIGURE2 / "neuron_connections_whole_noncri_S.csv")

    # Keep the cumulative-ablation folder on the same 52-type schema as the main Figure 2 model.
    pd.read_csv(FIGURE2 / "neuron_number.csv").to_csv(ACCUMULATION / "neuron_number.csv", index=False)
    base.to_csv(ACCUMULATION / "neuron_connections_whole.csv")


def write_serotonergic_connections(types: list[str]) -> None:
    df = pd.DataFrame(SEROTONERGIC_CONNECTIONS, columns=["Type", "DL_5HT", "SL_5HT"])
    expected = set(tin_types(types)) | OUTPUT_TYPES
    missing = sorted(expected - set(df["Type"]))
    extra = sorted(set(df["Type"]) - expected)
    if missing or extra:
        raise RuntimeError(f"Table S3 type mismatch. Missing={missing}; extra={extra}")
    df.to_csv(FIGURE4 / "serotonergic_connections.csv", index=False)


def clean_figure3_excel() -> None:
    path = FIGURE3 / "NSD005.xlsx"
    df = pd.read_excel(path, sheet_name="Sheet1").iloc[:, :7]
    df.to_excel(path, sheet_name="Sheet1", index=False)


def main() -> None:
    types = canonical_types()
    tins = tin_types(types)
    if len(tins) != 44:
        raise RuntimeError(f"Expected 44 TIN morphotypes, found {len(tins)}.")
    clean_order(ACCUMULATION / "Looming_Order.csv", tins)
    clean_order(ACCUMULATION / "SD_Order.csv", tins)
    write_figure2_ablation_matrices(tins)
    write_serotonergic_connections(types)
    clean_figure3_excel()
    print("Regenerated manuscript-aligned Figure 2 matrices, cumulative orders, Table S3 CSV, and cleaned NSD005.xlsx.")


if __name__ == "__main__":
    main()
