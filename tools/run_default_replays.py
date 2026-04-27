from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURE3_RESULTS = ROOT / "Figure3" / "results"
FIGURE5_RESULTS = ROOT / "Figure5" / "results"


def spawn_command(command: list[str], *, label: str, log_path: Path) -> subprocess.Popen[str]:
    print(f"[run] {label}", flush=True)
    print(" ".join(command), flush=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    process._log_file = log_file  # type: ignore[attr-defined]
    return process


def main() -> None:
    python = sys.executable
    FIGURE3_RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURE5_RESULTS.mkdir(parents=True, exist_ok=True)
    max_parallel = min(8, max(1, (os.cpu_count() or 4) - 2))

    jobs = [
        (
            "figure3_looming_response_curve",
            [
                python,
                str(ROOT / "Figure3" / "figure3_s5_replay.py"),
                "--analysis",
                "response_curve",
                "--modality",
                "looming",
                "--output",
                str(FIGURE3_RESULTS / "figure3_looming_response_curve.csv"),
            ],
            FIGURE3_RESULTS / "figure3_looming_response_curve.log",
        ),
        (
            "figure3_smd_response_curve",
            [
                python,
                str(ROOT / "Figure3" / "figure3_s5_replay.py"),
                "--analysis",
                "response_curve",
                "--modality",
                "smd",
                "--output",
                str(FIGURE3_RESULTS / "figure3_smd_response_curve.csv"),
            ],
            FIGURE3_RESULTS / "figure3_smd_response_curve.log",
        ),
        (
            "figure3_looming_family_compare",
            [
                python,
                str(ROOT / "Figure3" / "figure3_s5_replay.py"),
                "--analysis",
                "family_compare",
                "--modality",
                "looming",
                "--output",
                str(FIGURE3_RESULTS / "figure3_looming_family_compare.csv"),
            ],
            FIGURE3_RESULTS / "figure3_looming_family_compare.log",
        ),
        (
            "figure3_smd_family_compare",
            [
                python,
                str(ROOT / "Figure3" / "figure3_s5_replay.py"),
                "--analysis",
                "family_compare",
                "--modality",
                "smd",
                "--output",
                str(FIGURE3_RESULTS / "figure3_smd_family_compare.csv"),
            ],
            FIGURE3_RESULTS / "figure3_smd_family_compare.log",
        ),
        (
            "figure5_related_accuracy",
            [
                python,
                str(ROOT / "Figure5" / "figure5_model_replay.py"),
                "--analysis",
                "related_accuracy",
                "--output",
                str(FIGURE5_RESULTS / "figure5_related_accuracy.json"),
            ],
            FIGURE5_RESULTS / "figure5_related_accuracy.log",
        ),
        (
            "figure5_noise_boost_looming",
            [
                python,
                str(ROOT / "Figure5" / "figure5_model_replay.py"),
                "--analysis",
                "noise_boost",
                "--modality",
                "looming",
                "--output",
                str(FIGURE5_RESULTS / "figure5_noise_boost_looming.csv"),
            ],
            FIGURE5_RESULTS / "figure5_noise_boost_looming.log",
        ),
        (
            "figure5_noise_boost_smd",
            [
                python,
                str(ROOT / "Figure5" / "figure5_model_replay.py"),
                "--analysis",
                "noise_boost",
                "--modality",
                "smd",
                "--output",
                str(FIGURE5_RESULTS / "figure5_noise_boost_smd.csv"),
            ],
            FIGURE5_RESULTS / "figure5_noise_boost_smd.log",
        ),
        (
            "figure5_bias_curve",
            [
                python,
                str(ROOT / "Figure5" / "figure5_model_replay.py"),
                "--analysis",
                "proxy_bias_curve",
                "--output",
                str(FIGURE5_RESULTS / "figure5_bias_curve.csv"),
            ],
            FIGURE5_RESULTS / "figure5_bias_curve.log",
        ),
    ]

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": python,
        "jobs": [],
    }

    pending = list(jobs)
    running: list[tuple[str, list[str], Path, subprocess.Popen[str]]] = []

    while pending or running:
        while pending and len(running) < max_parallel:
            label, command, log_path = pending.pop(0)
            process = spawn_command(command, label=label, log_path=log_path)
            running.append((label, command, log_path, process))

        next_running: list[tuple[str, list[str], Path, subprocess.Popen[str]]] = []
        for label, command, log_path, process in running:
            code = process.poll()
            if code is None:
                next_running.append((label, command, log_path, process))
                continue
            if code != 0:
                process._log_file.close()  # type: ignore[attr-defined]
                raise subprocess.CalledProcessError(code, command)
            process._log_file.close()  # type: ignore[attr-defined]
            print(f"[done] {label} -> {log_path}", flush=True)
            manifest["jobs"].append({"label": label, "command": command, "log_path": str(log_path.relative_to(ROOT))})
        running = next_running
        if running:
            time.sleep(5)

    (FIGURE3_RESULTS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (FIGURE5_RESULTS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("[done] all default replay jobs")


if __name__ == "__main__":
    main()
