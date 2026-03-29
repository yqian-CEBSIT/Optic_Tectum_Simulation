from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


NOTEBOOK_NOTES = {
    "Figure2/Figure2_Simulation_WholeOT_L.ipynb": [
        "# Notebook notes",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65`.",
        "- The six RGC input channels are scaled by `(1, 1, 1, 3, 3, 1)` for `RGC_SO`, `RGC_S12`, `RGC_S34`, `RGC_S56`, `RGC_SGC`, and `RGC_SAC`, respectively.",
        "- The 15 s analysis window is kept explicit in code, and a separate offset variable can be adjusted if calcium responses are shifted relative to nominal stimulus onset.",
    ],
    "Figure2/Figure2_Simulation_WholeOT_S.ipynb": [
        "# Notebook notes",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65`.",
        "- The six RGC input channels are scaled by `(1, 1, 1, 3, 3, 1)` for `RGC_SO`, `RGC_S12`, `RGC_S34`, `RGC_S56`, `RGC_SGC`, and `RGC_SAC`, respectively.",
        "- The 15 s analysis window is kept explicit in code, and a separate offset variable can be adjusted if calcium responses are shifted relative to nominal stimulus onset.",
    ],
    "Figure2/WholeOT_L_5ht.ipynb": [
        "# Notebook notes",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65` with channel gains `(1, 1, 1, 3, 3, 1)`.",
        "- Serotonergic modulation is implemented as discrete threshold lowering in selected neuron subsets rather than a continuous change in recurrent connectivity.",
        "- In the DL_5-HT / looming-biased condition, the baseline threshold `-50 mV` is lowered to `-52`, `-55`, or `-59 mV` depending on the targeted neuron subset.",
    ],
    "Figure2/WholeOT_S_5HT.ipynb": [
        "# Notebook notes",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65` with channel gains `(1, 1, 1, 3, 3, 1)`.",
        "- Serotonergic modulation is implemented as discrete threshold lowering in selected neuron subsets rather than a continuous change in recurrent connectivity.",
        "- In the SL_5-HT / orienting-biased condition, the baseline threshold `-50 mV` is lowered to `-52`, `-55`, or `-58 mV` depending on the targeted neuron subset.",
    ],
    "Figure3/F3_SNR_TIN_all.ipynb": [
        "# Notebook notes",
        "",
        "- The noisy-input SNN uses the same global gain coefficient `65` and channel gains `(1, 1, 1, 3, 3, 1)` as the main whole-OT model.",
        "- The noisy-input traces are stimulus-locked calcium tables. If calcium responses are shifted relative to stimulus onset, update the offset variables rather than rewriting the nominal 15 s window.",
    ],
    "Figure3/F3_SNR_TIN_all_5ht.ipynb": [
        "# Notebook notes",
        "",
        "- The noisy-input SNN uses the same global gain coefficient `65` and channel gains `(1, 1, 1, 3, 3, 1)` as the main whole-OT model.",
        "- Serotonergic modulation is implemented as discrete threshold lowering in selected neuron subsets.",
    ],
    "Figure4/F4_BD_Total.ipynb": [
        "# Notebook notes",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65` with channel gains `(1, 1, 1, 3, 3, 1)`.",
        "- The 15 s analysis window is represented with explicit duration and offset variables in code.",
        "- In the 5-HT bias simulations, baseline threshold `-50 mV` is lowered to `-52`, `-55`, `-58`, or `-59 mV` depending on the modeled condition and neuron subset.",
    ],
    "Figure4/F4_BD_remove.ipynb": [
        "# Notebook notes",
        "",
        "- Final whole-OT input scaling uses a global gain coefficient of `65` with channel gains `(1, 1, 1, 3, 3, 1)`.",
        "- The ablation analyses should keep a fixed 15 s output window and represent calcium timing shifts with an explicit offset variable.",
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
    "signal_window_nominal_start_ms = 15000\n"
    "signal_window_duration_ms = 15000\n"
    "signal_offset_ms = -2000  # negative values shift the response window earlier for calcium timing offsets\n"
    "signal_start_idx = int((signal_window_nominal_start_ms + signal_offset_ms) / dt_sim)\n"
    "signal_end_idx = signal_start_idx + int(signal_window_duration_ms / dt_sim)\n"
    "signal_slice = slice(signal_start_idx, signal_end_idx)\n"
    "baseline_end_idx = signal_start_idx\n"
    "baseline_start_idx = max(0, baseline_end_idx - int(signal_window_duration_ms / dt_sim))\n"
    "baseline_slice = slice(baseline_start_idx, baseline_end_idx)\n"
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
            if marker in source:
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

    if notebook_key.startswith("Figure3/F3_SNR_TIN_all"):
        if "signal_window_nominal_start_ms = 15000" not in code and "rate1[130000:,].sum()" in code:
            code = code.replace(
                "rate1 = bp.measure.firing_rate(tpn_e_spike, width=1000.)\nrate2 = bp.measure.firing_rate(tpn_o_spike, width=1000.)\n\nprint(",
                "rate1 = bp.measure.firing_rate(tpn_e_spike, width=1000.)\nrate2 = bp.measure.firing_rate(tpn_o_spike, width=1000.)\n\n"
                + NOISY_WINDOW_SETUP
                + "\nprint(",
            )
        code = code.replace("rate1[130000:,].sum()", "rate1[signal_slice].sum()")
        code = code.replace("rate1[:130000].sum()", "rate1[baseline_slice].sum()")
        code = code.replace("rate2[130000:,].sum()", "rate2[signal_slice].sum()")
        code = code.replace("rate2[:130000].sum()", "rate2[baseline_slice].sum()")

    return code


def annotate_notebook(notebook_key: str) -> None:
    path = ROOT / notebook_key
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
