# Optic Tectum Simulation

Curated notebooks, scripts, and input data for the optic tectum simulation analyses used in the manuscript.

This repository is organized around the main figure-level workflows. The code is notebook-centered rather than packaged as a Python module, and the included data files are the local inputs needed to rerun the curated analyses in this folder.

## Repository structure

- `Figure1`
  - Two-pathway demonstration linking anatomically distinct RGC groups to pathway-biased TPN outputs.
  - Includes the main notebook and local connection-probability table. Raw morphology `.swc` files are intentionally not included in this code release.
- `Figure2`
  - **Accuracy**: whole-OT simulations for looming and small-moving-dot (SMD) conditions.
  - Includes the main notebooks, input calcium-derived tables, baseline and ablation connectivity tables, and the cumulative-ablation utility in `Figure2/accumulation/`.
- `Figure3`
  - **Robustness**: noisy-input analyses for looming- and SMD-driven visuomotor transformations.
  - Includes the main noisy-input notebook, calcium-derived noisy-input tables, and the whole-OT connectivity table used by the robustness analyses.
- `Figure4`
  - **Flexibility**: big-moving-dot (BMD) simulations and in silico ablation analyses.
  - Includes the main 10-degree BMD notebooks plus the input and connectivity tables used by those analyses. `BD_16.xlsx` is retained as an alternative larger-BMD input for supplementary checks.
- `tools`
  - Helper utilities for quick smoke tests and repo preparation.

## Recommended entry points

- `Figure1/Figure1_TwoPathway.ipynb`
  - Minimal pathway-bias model for the `RGC -> TPN` demonstration.
- `Figure2/Figure2_Simulation_WholeOT_L.ipynb`
  - Main looming-driven whole-OT simulation.
- `Figure2/Figure2_Simulation_WholeOT_S.ipynb`
  - Main SMD-driven whole-OT simulation.
- `Figure2/accumulation/accumulation.py`
  - Standalone cumulative-ablation workflow.
- `Figure3/F3_SNR_TIN_all.ipynb`
  - Main noisy-input robustness analysis.
- `Figure4/F4_BD_Total.ipynb`
  - Main BMD pathway-bias simulation.
- `Figure4/F4_BD_remove.ipynb`
  - BMD ablation variants.

## Reproducibility notes

- The main workflows are notebook-driven.
- `MANUSCRIPT_PANEL_MAP.md` maps manuscript panels to the public code/data files and identifies panels that require raw morphology or wet-experiment source data outside this lightweight bundle.
- On macOS arm64, `jaxlib==0.4.14` is no longer installable from current wheels. The checked local environment uses `jax==0.4.18`, `jaxlib==0.4.18`, and `numba==0.59.1` with `brainpy==2.4.4`.
- The curated whole-OT notebooks use:
  - simulation step `dt = 0.1 ms`
  - a global input gain coefficient of `65`
  - channel multipliers `(1, 1, 1, 3, 3, 1)` for `RGC_SO`, `RGC_S12`, `RGC_S34`, `RGC_S56`, `RGC_SGC`, and `RGC_SAC`
  - baseline LIF parameters centered on `V_rest = -60 mV`, `V_th = -50 mV`, `V_reset = -60 mV`, `tau_m = 20 ms`, and `tau_ref = 5 ms`
  - synaptic weights `+0.6` for excitatory projections and `-6.7` for inhibitory projections
  - synaptic decay constants of `5 ms` for excitation and `10 ms` for inhibition
- `Figure4/figure4_bmd_replay.py` implements the STAR Methods serotonergic threshold formula from machine-readable Table S3 values in `Figure4/serotonergic_connections.csv`. The older notebooks are retained as the original exploratory workflow.
- Figure 4 preference index follows the manuscript sign convention: `(TPN-E AUC - TPN-O AUC) / (TPN-E AUC + TPN-O AUC)`, so positive values indicate escape bias.
- Figure 4 notebooks default to `BD_10.xlsx`, matching the main-text 10-degree BMD stimulus. `BD_16.xlsx` remains available as an alternative larger-BMD input.
- Noisy-input SNR analyses keep the manuscript-facing windows explicit: `slice(0, 1500)` for the 15 s baseline and `slice(1500, 3000)` for the 15-30 s stimulus response in 10 ms display-bin units. A 2 s calcium-response lead is corrected on the input timeline before interpolation rather than by shifting the AUC window.
- Notebook outputs were kept lightweight to make the repository easier to browse and upload.
- The curated repository includes the literal file inputs referenced by the public notebooks. The cumulative-ablation script also accepts command-line paths for alternative inputs.
- The Figure 2 cumulative-ablation utility replays supplied `*_Order.csv` sequences on cropped 25 s inputs with a 5-20 s analysis window; the main whole-OT notebooks use the 30-45 s response window in 60 s simulations.
- Raw `.swc` morphology files and manuscript-unrelated benchmark code are excluded from this public code bundle.
- Run `python tools/generate_manuscript_assets.py` after editing canonical connection/type tables; it regenerates Figure 2 ablation matrices, repairs cumulative-ablation order files, writes the Figure 4 Table S3 CSV, and cleans workbook columns used by the public scripts.
- Full BrainPy simulation cells can take several minutes on a CPU-only workstation. The helper below is intended for selected-cell checks rather than a complete rebuild of every notebook.

## Quick start

1. Create a Python environment and install the listed dependencies:

```bash
python3.10 -m venv .venv310
source .venv310/bin/activate
pip install -r requirements.txt
python -c "import brainpy, jax; print(brainpy.__version__, jax.__version__)"
```

2. Regenerate manuscript-aligned derived assets after any connection-table edit:

```bash
python tools/generate_manuscript_assets.py
```

3. Open the figure-level notebook you want to inspect, or use the smoke-test helper for a quick non-Jupyter run.

Example smoke tests:

```powershell
python .\tools\notebook_smoke_runner.py `
  --notebook .\Figure2\Figure2_Simulation_WholeOT_L.ipynb `
  --cells 1,2,6 `
  --summary acc=acc `
  --summary tpn_e_auc=rate1[analysis_slice].sum() `
  --summary tpn_o_auc=rate2[analysis_slice].sum() `
  --quiet
```

Figure 4/S6 BMD formula replay examples:

```bash
python Figure4/figure4_bmd_replay.py --subtype control
python Figure4/figure4_bmd_replay.py --subtype dl
python Figure4/figure4_bmd_replay.py --subtype sl
python Figure4/figure4_bmd_replay.py --data Figure4/BD_16.xlsx --sheet smoothed_repaired --subtype dl
```

For a fast installation check, shorten the simulation window:

```bash
python Figure4/figure4_bmd_replay.py --subtype dl --sim-duration-ms 1000 --analysis-start-ms 0 --analysis-end-ms 1000
```

```powershell
python .\tools\notebook_smoke_runner.py `
  --notebook .\Figure2\Figure2_Simulation_WholeOT_S.ipynb `
  --cells 1,2,4 `
  --summary acc=acc `
  --summary tpn_e_auc=rate1[analysis_slice].sum() `
  --summary tpn_o_auc=rate2[analysis_slice].sum() `
  --quiet
```

## Notes

- This folder is a curated release bundle rather than a full archival dump of the original working directory.
- File and notebook names are preserved as much as possible to stay close to the figure-generation workflow used during manuscript preparation.
