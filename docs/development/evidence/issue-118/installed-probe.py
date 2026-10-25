"""Run the actual public state API regression/unit files against a clean wheel."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    wheel = args.wheel.resolve()
    output = args.output.resolve()
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    with tempfile.TemporaryDirectory(prefix="pil-118-installed-") as directory:
        work = Path(directory)
        venv = work / "venv"
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(venv)],
            check=True,
            capture_output=True,
            env=env,
        )
        python = venv / "bin/python"
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), str(wheel), "pytest", "hypothesis"],
            check=True,
            capture_output=True,
            env=env,
        )
        paths = [
            root / "tests/unit/test_state.py",
            root / "tests/regression/test_state_invariants.py",
        ]
        pins = {}
        copied = []
        for source in paths:
            target = work / source.name
            shutil.copyfile(source, target)
            pins[str(source.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
            copied.append(str(target))
        (work / "pytest.ini").write_text(
            "[pytest]\nmarkers =\n    regression: public state invariant regressions\n"
        )
        runtime = subprocess.check_output(
            [
                str(python),
                "-c",
                "import json,sys;from pathlib import Path;import procurement_intelligence_lab as p;assert Path(p.__file__).resolve().is_relative_to(Path(sys.prefix).resolve());print(json.dumps({'python':sys.version,'package':p.__file__,'prefix':sys.prefix}))",
            ],
            cwd=work,
            env=env,
            text=True,
        )
        command = [
            str(python),
            "-m",
            "pytest",
            "-q",
            "--junitxml=" + str(work / "results.xml"),
            *copied,
        ]
        run = subprocess.run(
            command, cwd=work, env=env, capture_output=True, text=True, check=False
        )
        cases = ET.parse(work / "results.xml").findall(".//testcase")
        receipt = {
            "code_revision": args.revision,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "runtime": json.loads(runtime),
            "cwd": str(work),
            "argv": command,
            "test_source_sha256": pins,
            "case_count": len(cases),
            "failures": sum(
                case.find("failure") is not None or case.find("error") is not None for case in cases
            ),
            "skips": sum(case.find("skipped") is not None for case in cases),
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
            "population": "Public deterministic/property contract cases; no production or agent-quality score.",
        }
        output.write_text(json.dumps(receipt, indent=2) + "\n")
        print(
            json.dumps(
                {
                    k: receipt[k]
                    for k in (
                        "code_revision",
                        "wheel_sha256",
                        "case_count",
                        "failures",
                        "skips",
                        "returncode",
                    )
                }
            )
        )
        return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
