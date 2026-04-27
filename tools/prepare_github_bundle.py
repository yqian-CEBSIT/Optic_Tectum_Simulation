from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT.parent / "Project_code_github_ready"

FILES_TO_COPY = [
    "requirements.txt",
    "README.md",
    "README_GITHUB_BUNDLE.md",
    "MANUSCRIPT_PANEL_MAP.md",
    "tools/notebook_smoke_runner.py",
    "tools/annotate_main_notebooks.py",
    "tools/generate_manuscript_assets.py",
    "tools/prepare_github_bundle.py",
    "Figure1/Figure1_TwoPathway.ipynb",
    "Figure1/local_connection_prob.csv",
    "Figure2/Figure2_Simulation_WholeOT_L.ipynb",
    "Figure2/Figure2_Simulation_WholeOT_S.ipynb",
    "Figure2/Looming_Ex.xlsx",
    "Figure2/SD_Ex.xlsx",
    "Figure2/neuron_number.csv",
    "Figure2/neuron_connections_whole.csv",
    "Figure2/neuron_connections_whole_ab.csv",
    "Figure2/neuron_connections_whole_cri_L_test.csv",
    "Figure2/neuron_connections_whole_cri_S_test.csv",
    "Figure2/neuron_connections_whole_noncri_L.csv",
    "Figure2/neuron_connections_whole_noncri_S.csv",
    "Figure2/accumulation/accumulation.py",
    "Figure2/accumulation/Looming.xlsx",
    "Figure2/accumulation/SD.xlsx",
    "Figure2/accumulation/NoisyLooming.xlsx",
    "Figure2/accumulation/Looming_Order.csv",
    "Figure2/accumulation/SD_Order.csv",
    "Figure2/accumulation/neuron_number.csv",
    "Figure2/accumulation/neuron_connections_whole.csv",
    "Figure3/F3_SNR_TIN_all.ipynb",
    "Figure3/neuron_connections_whole.csv",
    "Figure3/neuron_number.csv",
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
    "Figure4/figure4_bmd_replay.py",
    "Figure4/BD_10.xlsx",
    "Figure4/BD_16.xlsx",
    "Figure4/neuron_number.csv",
    "Figure4/neuron_connections_whole.csv",
    "Figure4/serotonergic_connections.csv",
]

DIRS_TO_COPY: list[str] = []


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
    if not src.exists():
        raise FileNotFoundError(f"Configured bundle input does not exist: {src}")
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
        "- Figure 2 accuracy workflows\n"
        "- Figure 3 robustness workflows\n"
        "- Figure 4 flexibility workflows, defaulting to the 10-degree BMD input\n\n"
        "## Notes\n\n"
        "- Notebook outputs were stripped to keep the bundle lighter and cleaner for GitHub.\n"
        "- Raw `.swc` morphology files and manuscript-unrelated benchmark code are intentionally excluded.\n"
        "- `MANUSCRIPT_PANEL_MAP.md` maps manuscript panels to public code/data files.\n"
        "- Figure 2 includes the baseline, ablated, critical, and non-critical connectivity matrices referenced by the curated notebooks.\n"
        "- Figure 3 includes the calcium-derived noisy-input tables and whole-OT connectivity table used by the robustness analyses.\n"
        "- Figure 4 uses the manuscript sign convention for preference index: TPN-E AUC minus TPN-O AUC over their sum.\n"
        "- `Figure4/figure4_bmd_replay.py` implements the manuscript Table S3 threshold-modulation formula.\n"
        "- Use `tools/notebook_smoke_runner.py` for selected non-Jupyter smoke tests; full simulation cells can take several minutes.\n",
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
        "*.swc\n"
        "*_exec_*.ipynb\n"
        "*.log\n",
        encoding="utf-8",
    )


def main() -> None:
    if ROOT.resolve() == BUNDLE_ROOT.resolve():
        raise RuntimeError(
            "Refusing to prepare a bundle in-place. Run this script from a separate source checkout, "
            "or change BUNDLE_ROOT before running."
        )

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
