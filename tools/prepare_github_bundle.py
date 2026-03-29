from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT.parent / "Project_code_github_ready"

FILES_TO_COPY = [
    "requirements.txt",
    "README.md",
    "tools/notebook_smoke_runner.py",
    "tools/annotate_main_notebooks.py",
    "tools/prepare_github_bundle.py",
    "Figure1/Figure1_TwoPathway.ipynb",
    "Figure1/local_connection_prob.csv",
    "Figure2/Figure2_Simulation_WholeOT_L.ipynb",
    "Figure2/Figure2_Simulation_WholeOT_S.ipynb",
    "Figure2/WholeOT_L_5ht.ipynb",
    "Figure2/WholeOT_S_5HT.ipynb",
    "Figure2/Looming_Ex.xlsx",
    "Figure2/SD_Ex.xlsx",
    "Figure2/neuron_number.csv",
    "Figure2/neuron_connections_whole.csv",
    "Figure2/accumulation/accumulation.py",
    "Figure2/accumulation/Looming.xlsx",
    "Figure2/accumulation/SD.xlsx",
    "Figure2/accumulation/NoisyLooming.xlsx",
    "Figure2/accumulation/Looming_Order.csv",
    "Figure2/accumulation/SD_Order.csv",
    "Figure2/accumulation/neuron_number.csv",
    "Figure2/accumulation/neuron_connections_whole.csv",
    "Figure3/F3_SNR_TIN_all.ipynb",
    "Figure3/F3_SNR_TIN_all_5ht.ipynb",
    "Figure3/F3_lorenz_sequence.ipynb",
    "Figure3/compressed_weight_matrix.npy",
    "Figure3/dense_matrix.csv",
    "Figure3/neuron_connections_whole.csv",
    "Figure3/neuron_number.csv",
    "Figure3/single_neuron_connections.csv",
    "Figure3/single_neuron_weights.npz",
    "Figure3/NLooming0.xlsx",
    "Figure3/NLooming001.xlsx",
    "Figure3/NLooming005.xlsx",
    "Figure3/NLooming01.xlsx",
    "Figure3/NLooming02.xlsx",
    "Figure3/NLooming05.xlsx",
    "Figure3/NSD0.xlsx",
    "Figure3/NSD001.xlsx",
    "Figure3/NSD005.xlsx",
    "Figure3/NSD01.xlsx",
    "Figure3/NSD02.xlsx",
    "Figure3/NSD05.xlsx",
    "Figure4/F4_BD_Total.ipynb",
    "Figure4/F4_BD_remove.ipynb",
    "Figure4/plot_bd16_calcium.py",
    "Figure4/BD_10.xlsx",
    "Figure4/BD_16.xlsx",
    "Figure4/neuron_number.csv",
    "Figure4/neuron_connections_whole.csv",
    "S14/Fig_4S13d_five_point_data.csv",
]

DIRS_TO_COPY = [
    "Figure1/SGC_SAC_P_RGC",
    "Figure1/SO_A_RGC",
    "Figure1/TPN-E",
    "Figure1/TPN-O",
    "S14/_generated_s13d_five_point",
    "S14/_generated_s13_s14",
    "S14/_generated_s14_replicates",
]


def strip_notebook_outputs(path: Path) -> None:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")


def copy_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BUNDLE_ROOT / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if dst.suffix == ".ipynb":
        strip_notebook_outputs(dst)


def copy_dir(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BUNDLE_ROOT / rel_path
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def write_bundle_readme() -> None:
    target = BUNDLE_ROOT / "README_GITHUB_BUNDLE.md"
    target.write_text(
        "# GitHub-ready bundle\n\n"
        "This bundle contains the curated notebooks, scripts, and input data that are most directly connected to the manuscript figures.\n\n"
        "## Included figure workflows\n\n"
        "- Figure 1 pathway-bias demo\n"
        "- Figure 2 whole-OT looming and SMD simulations\n"
        "- Figure 2 serotonergic variants\n"
        "- Figure 3 noisy-input and Lorenz benchmark workflows\n"
        "- Figure 4 BMD and ablation workflows\n\n"
        "## Included supplementary artifacts\n\n"
        "- Supplementary Figures 13-14 generated JSON/CSV snapshots that are already present in the current workspace\n\n"
        "## Notes\n\n"
        "- Notebook outputs were stripped to keep the bundle lighter and cleaner for GitHub.\n"
        "- The main notebooks were annotated with code-facing notes on input scaling, analysis-window offsets, and 5-HT threshold modulation.\n"
        "- The current `S14` folder does not yet contain the original source scripts used to make every supplementary panel, so the bundle includes the available generated data snapshots rather than a full rebuild pipeline for those panels.\n"
        "- Use `tools/notebook_smoke_runner.py` for quick non-Jupyter smoke tests.\n",
        encoding="utf-8",
    )


def write_gitignore() -> None:
    target = BUNDLE_ROOT / ".gitignore"
    target.write_text(
        "__pycache__/\n"
        ".ipynb_checkpoints/\n"
        "*.pyc\n"
        "*.pdf\n"
        "*.png\n"
        "*.svg\n"
        "*_exec_*.ipynb\n"
        "*.log\n",
        encoding="utf-8",
    )


def main() -> None:
    if BUNDLE_ROOT.exists():
        shutil.rmtree(BUNDLE_ROOT)
    BUNDLE_ROOT.mkdir(parents=True, exist_ok=True)

    for rel_path in FILES_TO_COPY:
        copy_file(rel_path)

    for rel_path in DIRS_TO_COPY:
        copy_dir(rel_path)

    write_bundle_readme()
    write_gitignore()
    print(f"Prepared GitHub-ready bundle at {BUNDLE_ROOT}")


if __name__ == "__main__":
    main()
