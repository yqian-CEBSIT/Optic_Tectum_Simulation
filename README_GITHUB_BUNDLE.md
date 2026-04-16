# GitHub-ready bundle

This folder is a curated public-facing bundle derived from the local working directory.

## Included workflows

- `Figure1`
  - Two-pathway demonstration and associated morphology inputs.
- `Figure2`
  - Whole-OT looming and SMD simulations plus cumulative-ablation utilities and the referenced ablation connectivity tables.
- `Figure3`
  - Noisy-input robustness analysis and Lorenz benchmark with the required TIN connectivity, population-size, mapping, and matrix files.
- `Figure4`
  - BMD simulations and ablation analyses.
- `tools`
  - Helper scripts for smoke testing and bundle preparation.

## Notes

- Only the files currently present in this bundle are intended for upload.
- Notebook outputs were kept lightweight to make the repository easier to browse and upload.
- The main notebooks include code-facing notes on input scaling, manuscript-aligned analysis windows, calcium timing offsets, and serotonergic threshold modulation.
- Use `tools/notebook_smoke_runner.py` for selected non-Jupyter smoke tests. Full BrainPy simulation cells can take several minutes on CPU-only machines.
