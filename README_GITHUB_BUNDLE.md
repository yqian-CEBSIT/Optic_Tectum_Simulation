# GitHub-ready bundle

This folder is a curated public-facing bundle derived from the local working directory.

## Included workflows

- `Figure1`
  - Two-pathway demonstration and local connection-probability input.
- `Figure2`
  - **Accuracy**: whole-OT looming and SMD simulations plus cumulative-ablation utilities and the referenced ablation connectivity tables.
- `Figure3`
  - **Robustness**: noisy-input analyses with calcium-derived noisy-input tables and whole-OT connectivity tables.
- `Figure4`
  - **Flexibility**: 10-degree BMD simulations and ablation analyses; `BD_16.xlsx` is retained as an alternative larger-BMD input, and `figure4_bmd_replay.py` implements the manuscript Table S3 threshold-modulation formula.
- `Figure5`
  - **Model follow-up**: scripted replay for the simulation-supported Figure 5 panels.
- `tools`
  - Helper scripts for smoke testing and bundle preparation.

## Notes

- Only the files currently present in this bundle are intended for upload.
- Raw `.swc` morphology files and manuscript-unrelated benchmark code are intentionally excluded.
- Notebook outputs were kept lightweight to make the repository easier to browse and upload.
- The main notebooks include code-facing notes on input scaling, manuscript-aligned analysis windows, calcium timing offsets, serotonergic threshold modulation, and the Figure 4 preference-index sign convention.
- `MANUSCRIPT_PANEL_MAP.md` lists the manuscript-to-code mapping for the public release.
- `tools/generate_manuscript_assets.py` regenerates the manuscript-aligned Figure 2 ablation matrices, cumulative-ablation order files, and Figure 4 Table S3 CSV.
- Use `tools/notebook_smoke_runner.py` for selected non-Jupyter smoke tests. Full BrainPy simulation cells can take several minutes on CPU-only machines.
