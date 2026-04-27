from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIGURE2 = ROOT / "Figure2"
FIGURE3 = ROOT / "Figure3"
FIGURE4 = ROOT / "Figure4"
INPUT_TYPES = {"RGC_SO", "RGC_S12", "RGC_S34", "RGC_S56", "RGC_SGC", "RGC_SAC"}
OUTPUT_TYPES = {"TPN_E", "TPN_O"}


def canonical_tins() -> list[str]:
    types = pd.read_csv(FIGURE2 / "neuron_number.csv")["Type"].astype(str).tolist()
    return [value for value in types if value not in INPUT_TYPES and value not in OUTPUT_TYPES]


def assert_order(path: Path, tins: list[str]) -> None:
    order = pd.read_csv(path)["Type"].astype(str).tolist()
    if len(order) != len(tins) or set(order) != set(tins):
        raise AssertionError(f"{path} is not an exact 44-morphotype TIN order.")


def zeroed_tins(path: Path, tins: list[str]) -> set[str]:
    matrix = pd.read_csv(path, index_col=0)
    return {
        value
        for value in tins
        if np.allclose(matrix.loc[value].to_numpy(dtype=float), 0.0)
        and np.allclose(matrix[value].to_numpy(dtype=float), 0.0)
    }


def main() -> None:
    tins = canonical_tins()
    if len(tins) != 44:
        raise AssertionError(f"Expected 44 TIN morphotypes, found {len(tins)}.")
    assert_order(FIGURE2 / "accumulation" / "Looming_Order.csv", tins)
    assert_order(FIGURE2 / "accumulation" / "SD_Order.csv", tins)

    expected = {
        "neuron_connections_whole_ab.csv": set(tins),
        "neuron_connections_whole_cri_L_test.csv": {"I_S12", "I_SIN"},
        "neuron_connections_whole_noncri_L.csv": set(tins) - {"I_S12", "I_SIN"},
        "neuron_connections_whole_cri_S_test.csv": {"I_S12_S56", "I_S12_S56_SGC"},
        "neuron_connections_whole_noncri_S.csv": set(tins) - {"I_S12_S56", "I_S12_S56_SGC"},
    }
    for file_name, expected_zeroed in expected.items():
        actual = zeroed_tins(FIGURE2 / file_name, tins)
        if actual != expected_zeroed:
            raise AssertionError(f"{file_name} zeroed {sorted(actual)} but expected {sorted(expected_zeroed)}.")

    nsd005_columns = list(pd.read_excel(FIGURE3 / "NSD005.xlsx").columns)
    if nsd005_columns != ["Time", "RGC_SO", "RGC_S12", "RGC_S34", "RGC_S56", "RGC_SGC", "RGC_SAC"]:
        raise AssertionError(f"NSD005.xlsx has unexpected columns: {nsd005_columns}")

    serotonin = pd.read_csv(FIGURE4 / "serotonergic_connections.csv")
    expected_serotonin_types = set(tins) | OUTPUT_TYPES
    if set(serotonin["Type"]) != expected_serotonin_types:
        raise AssertionError("serotonergic_connections.csv does not match the 44 TIN types plus TPN_E/TPN_O.")

    print("Manuscript-aligned public assets validated.")


if __name__ == "__main__":
    main()
