from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
from typing import Iterator


os.environ.setdefault("MPLBACKEND", "Agg")


def parse_cell_spec(spec: str, total_cells: int) -> list[int]:
    indices: list[int] = []
    for chunk in spec.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if end < start:
                raise ValueError(f"Invalid cell range '{part}'.")
            indices.extend(range(start, end + 1))
        else:
            indices.append(int(part))

    unique = []
    seen = set()
    for idx in indices:
        if idx < 0 or idx >= total_cells:
            raise IndexError(f"Cell index {idx} is out of range for a notebook with {total_cells} cells.")
        if idx not in seen:
            unique.append(idx)
            seen.add(idx)
    return unique


@contextlib.contextmanager
def temporary_workdir(path: Path) -> Iterator[None]:
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def load_notebook_code(notebook_path: Path, cell_indices: list[int]) -> list[tuple[int, str]]:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    cells = notebook["cells"]
    code_blocks: list[tuple[int, str]] = []
    for idx in cell_indices:
        cell = cells[idx]
        if cell.get("cell_type") != "code":
            raise ValueError(f"Cell {idx} is not a code cell.")
        source = "".join(cell.get("source", []))
        code_blocks.append((idx, source))
    return code_blocks


def evaluate_summaries(namespace: dict[str, object], summaries: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in summaries:
        if "=" not in item:
            raise ValueError(f"Summary expression '{item}' must use the form name=expression.")
        name, expression = item.split("=", 1)
        value = eval(expression, namespace)  # noqa: S307 - intentional developer utility for local notebook auditing.
        result[name.strip()] = to_jsonable(value)
    return result


def to_jsonable(value: object) -> object:
    try:
        import numpy as np
    except ImportError:  # pragma: no cover - numpy is available in this project environment.
        np = None

    if np is not None:
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute selected code cells from a notebook with plain Python, without relying on Jupyter kernel startup."
    )
    parser.add_argument("--notebook", type=Path, required=True, help="Path to the notebook to execute.")
    parser.add_argument(
        "--cells",
        required=True,
        help="Comma-separated cell indices or ranges, for example '0,1,5' or '0-2,8'.",
    )
    parser.add_argument(
        "--summary",
        action="append",
        default=[],
        help="Optional summary expression of the form name=expression. May be passed multiple times.",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="Optional working directory. Defaults to the notebook parent folder.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress cell stdout/stderr and only print the final JSON report.",
    )
    args = parser.parse_args()

    notebook_path = args.notebook.resolve()
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    cell_indices = parse_cell_spec(args.cells, total_cells=len(notebook["cells"]))
    code_blocks = load_notebook_code(notebook_path, cell_indices)
    namespace: dict[str, object] = {"__name__": "__main__"}
    workdir = args.workdir.resolve() if args.workdir else notebook_path.parent

    with temporary_workdir(workdir):
        for idx, source in code_blocks:
            if not source.strip():
                continue
            if args.quiet:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    exec(compile(source, f"{notebook_path}#cell{idx}", "exec"), namespace)  # noqa: S102
            else:
                exec(compile(source, f"{notebook_path}#cell{idx}", "exec"), namespace)  # noqa: S102

    payload = {
        "notebook": str(notebook_path),
        "workdir": str(workdir),
        "cells": cell_indices,
        "summaries": evaluate_summaries(namespace, args.summary),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
