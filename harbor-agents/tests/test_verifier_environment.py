"""Exercise the real verifier launcher without package downloads or model calls."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("canonical", "native", "expected"),
    [
        ("fixture-gemini-key", None, "fixture-gemini-key"),
        ("fixture-gemini-key", "fixture-legacy-key", "fixture-gemini-key"),
        (None, "fixture-legacy-key", "fixture-legacy-key"),
        (None, None, "unset"),
    ],
)
def test_verifier_forwards_gemini_key_to_grader(tmp_path, canonical, native, expected):
    tasks_dir = os.environ.get("TASKS_DIR")
    if not tasks_dir:
        pytest.skip("set TASKS_DIR to the downloaded GDP-XLSX task directory")
    task_root = Path(tasks_dir).expanduser().resolve()
    assert task_root.is_dir(), f"TASKS_DIR is not a directory: {task_root}"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Stub only the external installation/copy/grading commands. The actual
    # launcher still runs, exports credentials, and starts the grader process.
    commands = {
        "pip": "exit 0\n",
        "cp": "exit 0\n",
        "python3": 'printf "%s" "${GOOGLE_GENERATIVE_AI_API_KEY-unset}"\n',
    }
    for name, body in commands.items():
        command = bin_dir / name
        command.write_text("#!/bin/sh\n" + body)
        command.chmod(0o755)

    env = dict(os.environ)
    for name, value in (("GEMINI_API_KEY", canonical), ("GOOGLE_GENERATIVE_AI_API_KEY", native)):
        env.pop(name, None)
        if value is not None:
            env[name] = value
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    env["TMPDIR"] = str(tmp_path)
    scripts = sorted(task_root.glob("*/tests/test.sh"))
    # Every task ships the same entrypoint, so exercise that entrypoint once
    # per credential scenario and catch drift between the shipped copies.
    assert scripts
    assert len({script.read_bytes() for script in scripts}) == 1
    result = subprocess.run(
        ["/bin/bash", str(scripts[0])],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == expected
