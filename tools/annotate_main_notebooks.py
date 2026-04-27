from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


NOTEBOOK_NOTES = {
    "Figure2/Figure2_Simulation_WholeOT_L.ipynb": [
        "# Figure 2 - Accuracy",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65`.",
        "- The six RGC input channels are scaled by `(1, 1, 1, 3, 3, 1)` for `RGC_SO`, `RGC_S12`, `RGC_S34`, `RGC_S56`, `RGC_SGC`, and `RGC_SAC`, respectively.",
        "- The 15 s analysis window is kept explicit in code, and a separate offset variable can be adjusted if calcium responses are shifted relative to nominal stimulus onset.",
    ],
    "Figure2/Figure2_Simulation_WholeOT_S.ipynb": [
        "# Figure 2 - Accuracy",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65`.",
        "- The six RGC input channels are scaled by `(1, 1, 1, 3, 3, 1)` for `RGC_SO`, `RGC_S12`, `RGC_S34`, `RGC_S56`, `RGC_SGC`, and `RGC_SAC`, respectively.",
        "- The 15 s analysis window is kept explicit in code, and a separate offset variable can be adjusted if calcium responses are shifted relative to nominal stimulus onset.",
    ],
    "Figure3/F3_SNR_TIN_all.ipynb": [
        "# Figure 3 - Robustness",
        "",
        "- The noisy-input SNN uses the same global gain coefficient `65` and channel gains `(1, 1, 1, 3, 3, 1)` as the main whole-OT model.",
        "- Noisy-input SNR uses the manuscript-aligned 15 s baseline window and 15-30 s stimulus window; in 10 ms display bins these are `slice(0, 1500)` and `slice(1500, 3000)`.",
        "- A 2 s calcium-response lead is corrected on the input timeline before interpolation, so AUC quantification remains aligned to the nominal stimulus window.",
    ],
    "Figure4/F4_BD_Total.ipynb": [
        "# Figure 4 - Flexibility",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65` with channel gains `(1, 1, 1, 3, 3, 1)`.",
        "- The public main-figure workflow defaults to `BD_10.xlsx`, matching the 10-degree BMD stimulus described for Figure 4; `BD_16.xlsx` is retained as an alternative larger-BMD input.",
        "- The 15 s analysis window is represented with explicit duration and offset variables in code.",
        "- Preference index follows the manuscript sign convention: `(TPN-E AUC - TPN-O AUC) / (TPN-E AUC + TPN-O AUC)`, so positive values indicate escape bias.",
        "- For STAR Methods-aligned serotonergic modulation, use `figure4_bmd_replay.py`, which reads `serotonergic_connections.csv` and applies `Vth_i(5HT) = Vth_i - gamma * p_i`.",
    ],
    "Figure4/F4_BD_remove.ipynb": [
        "# Figure 4 - Flexibility",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65` with channel gains `(1, 1, 1, 3, 3, 1)`.",
        "- The public ablation workflow defaults to `BD_10.xlsx`, matching the 10-degree BMD stimulus described for Figure 4; `BD_16.xlsx` is retained as an alternative larger-BMD input.",
        "- The ablation analyses should keep a fixed 15 s output window and represent calcium timing shifts with an explicit offset variable.",
        "- Preference index follows the manuscript sign convention: `(TPN-E AUC - TPN-O AUC) / (TPN-E AUC + TPN-O AUC)`, so positive values indicate escape bias.",
        "- For STAR Methods-aligned serotonergic modulation, use `figure4_bmd_replay.py`, which reads `serotonergic_connections.csv` and applies `Vth_i(5HT) = Vth_i - gamma * p_i`.",
    ],
}


INPUT_SCALE_BLOCK_RE = re.compile(
    r"Gain_coeff\s*=\s*65[^\n]*\n"
    r"(?:rgc_inputs_bm\s*=\s*bm\.array\(rgc_inputs\)[^\n]*\n)?"
    r"inp1\s*=\s*rgc_inputs_bm\[:,\s*0\]\s*\*\s*Gain_coeff\s*\n"
    r"inp2\s*=\s*rgc_inputs_bm\[:,\s*1\]\s*\*\s*Gain_coeff\s*\n"
    r"inp3\s*=\s*rgc_inputs_bm\[:,\s*2\]\s*\*\s*Gain_coeff\s*\n"
    r"inp4\s*=\s*rgc_inputs_bm\[:,\s*3\]\s*\*\s*3\s*\*\s*Gain_coeff\s*\n"
    r"inp5\s*=\s*rgc_inputs_bm\[:,\s*4\]\s*\*\s*3\s*\*\s*Gain_coeff\s*\n"
    r"inp6\s*=\s*rgc_inputs_bm\[:,\s*5\]\s*\*\s*Gain_coeff"
)

INPUT_SCALE_REPLACEMENT = (
    "# Input scaling used in the final whole-OT model.\n"
    "input_gain_coeff = 65\n"
    "rgc_inputs_bm = bm.array(rgc_inputs)  # shape (6, simulation steps)\n"
    "input_channel_gains = (1, 1, 1, 3, 3, 1)  # RGC_SO, RGC_S12, RGC_S34, RGC_S56, RGC_SGC, RGC_SAC\n"
    "inp1 = rgc_inputs_bm[:, 0] * input_channel_gains[0] * input_gain_coeff\n"
    "inp2 = rgc_inputs_bm[:, 1] * input_channel_gains[1] * input_gain_coeff\n"
    "inp3 = rgc_inputs_bm[:, 2] * input_channel_gains[2] * input_gain_coeff\n"
    "inp4 = rgc_inputs_bm[:, 3] * input_channel_gains[3] * input_gain_coeff\n"
    "inp5 = rgc_inputs_bm[:, 4] * input_channel_gains[4] * input_gain_coeff\n"
    "inp6 = rgc_inputs_bm[:, 5] * input_channel_gains[5] * input_gain_coeff"
)

WINDOW_SETUP = (
    "analysis_window_start_ms = 30000\n"
    "analysis_window_duration_ms = 15000\n"
    "analysis_offset_ms = 0  # adjust if calcium responses are shifted relative to nominal stimulus onset\n"
    "analysis_start_idx = int((analysis_window_start_ms + analysis_offset_ms) / dt_sim)\n"
    "analysis_end_idx = analysis_start_idx + int(analysis_window_duration_ms / dt_sim)\n"
    "analysis_slice = slice(analysis_start_idx, analysis_end_idx)\n"
)

NOISY_WINDOW_SETUP = (
    "# Manuscript-aligned AUC windows.\n"
    "# Display-bin slices make the intended windows explicit to readers: 0-15 s and 15-30 s.\n"
    "display_bin_ms = 10\n"
    "display_bin_steps = int(display_bin_ms / dt_sim)\n"
    "baseline_window_nominal_slice = slice(0, 1500)\n"
    "signal_window_nominal_slice = slice(1500, 3000)\n"
    "baseline_slice = slice(\n"
    "    baseline_window_nominal_slice.start * display_bin_steps,\n"
    "    baseline_window_nominal_slice.stop * display_bin_steps,\n"
    ")\n"
    "signal_slice = slice(\n"
    "    signal_window_nominal_slice.start * display_bin_steps,\n"
    "    signal_window_nominal_slice.stop * display_bin_steps,\n"
    ")\n"
)

FIGURE4_PREFERENCE_OLD = (
    "acc = (rate2[analysis_slice].sum()-rate1[analysis_slice].sum())/(rate2[analysis_slice].sum()+rate1[analysis_slice].sum())\n"
    "rate1[analysis_slice].sum(), rate2[analysis_slice].sum(), acc.sum()"
)

FIGURE4_PREFERENCE_NEW = (
    "tpn_e_auc = rate1[analysis_slice].sum()\n"
    "tpn_o_auc = rate2[analysis_slice].sum()\n"
    "preference_index = (tpn_e_auc - tpn_o_auc) / (tpn_e_auc + tpn_o_auc)\n"
    "acc = preference_index  # compatibility alias for earlier notebook summaries\n"
    "tpn_e_auc, tpn_o_auc, preference_index.sum()"
)

STALE_COMMENT_LINES = (
    "# \u8bfb\u53d6\u635f\u6bc1\u987a\u5e8f\u7684CSV\u6587\u4ef6\n",
    "# NLooming_order = pd.read_csv('./NoisyLooming_Order_test.csv')  # \u5047\u8bbe\u6587\u4ef6\u540d\u4e3adamage_order.csv\n",
    "# NLooming_shuffle_sequence = NLooming_order.iloc[:, 0].tolist()  # \u63d0\u53d6\u7b2c\u4e00\u5217\u4f5c\u4e3a\u635f\u6bc1\u987a\u5e8f\n",
)


def load_notebook(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_notebook(path: Path, notebook: dict) -> None:
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")


def ensure_note_cell(notebook: dict, lines: list[str]) -> None:
    marker = lines[0]
    for cell in notebook["cells"]:
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            if marker in source or source.startswith("# Notebook notes"):
                cell["source"] = [line + "\n" for line in lines[:-1]] + [lines[-1]]
                return
    notebook["cells"].insert(
        0,
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in lines[:-1]] + [lines[-1]],
        },
    )


def update_source(code: str, notebook_key: str) -> str:
    code = INPUT_SCALE_BLOCK_RE.sub(INPUT_SCALE_REPLACEMENT, code)
    code = re.sub(r"sim_duration\s*=\s*60000[^\n]*", "sim_duration = 60000  # simulation duration: 60 s (ms)", code)
    code = re.sub(r"sim_duration\s*=\s*30000[^\n]*", "sim_duration = 30000  # simulation duration: 30 s (ms)", code)
    code = re.sub(
        r"(conn_prob_df = pd\.read_csv\('[^']+', index_col=0\))\s+## neuron_connections_whole neuron_connections_TIN_ablation\.csv",
        r"\1",
        code,
    )
    code = code.replace("sim_times = np.arange(0, sim_duration, dt_sim)  # \u6beb\u79d2\u5355\u4f4d", "sim_times = np.arange(0, sim_duration, dt_sim)  # ms")
    for stale_line in STALE_COMMENT_LINES:
        code = code.replace(stale_line, "")

    if notebook_key.startswith("Figure2/Figure2_Simulation_WholeOT_") or notebook_key.startswith("Figure4/"):
        if "analysis_window_start_ms = 30000" not in code and "rate1[300000:450000" in code:
            code = code.replace(
                "rate1 = bp.measure.firing_rate(tpn_e_spike, width=1000.)\nrate2 = bp.measure.firing_rate(tpn_o_spike, width=1000.)\n\nacc = ",
                "rate1 = bp.measure.firing_rate(tpn_e_spike, width=1000.)\nrate2 = bp.measure.firing_rate(tpn_o_spike, width=1000.)\n\n"
                + WINDOW_SETUP
                + "\nacc = ",
            )
        code = code.replace("rate1[300000:450000,].sum()", "rate1[analysis_slice].sum()")
        code = code.replace("rate2[300000:450000,].sum()", "rate2[analysis_slice].sum()")
        code = code.replace("rate1[300000:450000].sum()", "rate1[analysis_slice].sum()")
        code = code.replace("rate2[300000:450000].sum()", "rate2[analysis_slice].sum()")

    if notebook_key.startswith("Figure4/"):
        code = code.replace("data = pd.read_excel('BD_16.xlsx', header=0, sheet_name='Sheet1')", "data = pd.read_excel('BD_10.xlsx', header=0, sheet_name='Sheet1')")
        code = code.replace(FIGURE4_PREFERENCE_OLD, FIGURE4_PREFERENCE_NEW)

    if notebook_key.startswith("Figure3/F3_SNR_TIN_all"):
        if "calcium_response_lead_ms = 2000" not in code and "data_times_ms = time_points * 1000" in code:
            code = code.replace(
                "    data_times_ms = time_points * 1000\n",
                "    # Align calcium responses to the manuscript's nominal stimulus timeline.\n"
                "    # The raw calcium response leads the nominal stimulus epoch by 2 s.\n"
                "    calcium_response_lead_ms = 2000\n"
                "    data_times_ms = time_points * 1000 + calcium_response_lead_ms\n",
            )

        if "signal_window_nominal_slice = slice(1500, 3000)" not in code and "rate1[signal_slice].sum()" in code:
            code = code.replace(
                "rate1 = bp.measure.firing_rate(tpn_e_spike, width=1000.)\nrate2 = bp.measure.firing_rate(tpn_o_spike, width=1000.)\n\nprint(",
                "rate1 = bp.measure.firing_rate(tpn_e_spike, width=1000.)\nrate2 = bp.measure.firing_rate(tpn_o_spike, width=1000.)\n\n"
                + NOISY_WINDOW_SETUP
                + "\nprint(",
            )

    return code


def annotate_notebook(notebook_key: str) -> None:
    path = ROOT / notebook_key
    if not path.exists():
        print(f"Skipping missing notebook {path}")
        return
    notebook = load_notebook(path)
    ensure_note_cell(notebook, NOTEBOOK_NOTES[notebook_key])

    changed = False
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        updated = update_source(source, notebook_key)
        if updated != source:
            cell["source"] = updated.splitlines(keepends=True)
            changed = True

    if changed or notebook["cells"][0].get("cell_type") == "markdown":
        save_notebook(path, notebook)


def main() -> None:
    for notebook_key in NOTEBOOK_NOTES:
        annotate_notebook(notebook_key)
        print(f"Annotated {ROOT / notebook_key}")


if __name__ == "__main__":
    main()
