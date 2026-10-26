"""Build-independent installed public probes; test bundles contain no product source."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def command(argv, *, cwd, env, log):
    p = subprocess.run(
        argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=1200, check=False
    )
    Path(log).write_text(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError(f"qualification command failed; inspect {log}")
    return p.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--python312", required=True)
    parser.add_argument("--python313", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    args.artifacts.mkdir(parents=True, exist_ok=True)
    wheel = args.wheel.resolve()
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    assert env.get("PIL_TEST_POSTGRES_DSN"), "explicit owned disposable Postgres required"
    records = []
    expected = {}
    with zipfile.ZipFile(wheel) as z:
        for name in z.namelist():
            if name.startswith("procurement_intelligence_lab/") and not name.endswith("/"):
                data = z.read(name)
                assert data == (root / "src" / name).read_bytes(), name
                expected[name] = hashlib.sha256(data).hexdigest()
    sys.path.insert(0, str(root))  # Fixture authoring only; child probes remove PYTHONPATH.
    from tests.integration.test_resolved_processing_jobs_cli import submission_inputs

    for version, interpreter in (("3.12", args.python312), ("3.13", args.python313)):
        for mode in ("base", "storage"):
            work = Path(tempfile.mkdtemp(prefix=f"{version}-{mode}-", dir=args.artifacts))
            venv = work / "venv"
            command(
                ["uv", "venv", "--python", interpreter, str(venv)],
                cwd=work,
                env=env,
                log=work / "venv.log",
            )
            python = venv / "bin/python"
            command(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    str(wheel) + ("[storage]" if mode == "storage" else ""),
                ],
                cwd=work,
                env=env,
                log=work / "install.log",
            )
            inspect = """import json,sys,pathlib,hashlib,importlib.metadata
import procurement_intelligence_lab as p
package=pathlib.Path(p.__file__).resolve().parent
assert package.is_relative_to(pathlib.Path(sys.prefix).resolve())
print(json.dumps({"python":sys.version,"package":str(package),"sys_prefix":sys.prefix,"distributions":{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},"files":{str(f.relative_to(package.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in package.rglob('*') if f.is_file() and '__pycache__' not in str(f)}}))"""
            proof = json.loads(
                command(
                    [str(python), "-I", "-c", inspect], cwd=work, env=env, log=work / "import.json"
                )
            )
            assert proof["files"] == expected
            record = {
                "version": version,
                "mode": mode,
                "import": proof,
                "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
            if mode == "base":
                assert set(proof["distributions"]) == {"procurement-intelligence-lab"}, proof[
                    "distributions"
                ]
                fixture = work / "inputs"
                fixture.mkdir()
                submission, _, _ = submission_inputs(fixture)
                six = submission[1:-4]
                result = json.loads(
                    command(
                        [
                            str(python),
                            "-I",
                            "-m",
                            "procurement_intelligence_lab.interfaces.execute_resolved_package",
                            *six,
                        ],
                        cwd=work,
                        env=env,
                        log=work / "six.json",
                    )
                )
                assert [e["status"] for e in result["execution_receipt"]["entries"]] == [
                    "SUCCEEDED"
                ] * 6 + ["NOT_EXECUTED"] * 6
                outcome = result["resolution"]["outcomes"][0]
                assert outcome["canonical_key"] == "GPU-A" and outcome["status"] == "resolved"
                assert outcome["evidence"][0]["evidence"]["location"]["row"] == 7
                command(
                    [
                        str(python),
                        "-I",
                        "-m",
                        "procurement_intelligence_lab.interfaces.resolved_processing_jobs",
                        "--help",
                    ],
                    cwd=work,
                    env=env,
                    log=work / "help.log",
                )
                unavailable_env = {**env, "PIL_ASSERTION_ARCHIVE_DSN": env["PIL_TEST_POSTGRES_DSN"]}
                p = subprocess.run(
                    [
                        str(python),
                        "-I",
                        "-m",
                        "procurement_intelligence_lab.interfaces.resolved_processing_jobs",
                        *submission,
                    ],
                    cwd=work,
                    env=unavailable_env,
                    text=True,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                assert p.returncode == 2 and p.stdout == ""
                error = json.loads(p.stderr)
                assert error["code"] == "pil.infrastructure.resolved_prefix_job_unavailable"
                assert error["job_id"].startswith("local-resolved-prefix-job-v1:")
                record.update(
                    public_cases=3,
                    source_example={
                        "sku": "GPU-A",
                        "source_row": 7,
                        "catalog_keys": ["GPU-A"],
                        "canonical_key": outcome["canonical_key"],
                        "status": outcome["status"],
                    },
                    missing_storage=error["code"],
                )
            else:
                tools = [
                    f"pytest=={importlib.metadata.version('pytest')}",
                    f"hypothesis=={importlib.metadata.version('hypothesis')}",
                ]
                command(
                    ["uv", "pip", "install", "--python", str(python), *tools],
                    cwd=work,
                    env=env,
                    log=work / "qa-install.log",
                )
                bundle = work / "bundle"
                bundle.mkdir()
                shutil.copytree(
                    root / "tests",
                    bundle / "tests",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                (bundle / "pytest.ini").write_text(
                    "[pytest]\npythonpath = .\nmarkers =\n    integration: public integration\n    contract: contract\n    regression: regression\n"
                )
                (bundle / "conftest.py").write_text("""from pathlib import Path
import sys
import procurement_intelligence_lab as p
def pytest_sessionstart(session):
    assert Path(p.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert not (Path(__file__).parent / 'src').exists()
""")
                modules = [
                    "tests/integration/test_resolved_processing_jobs_cli.py",
                    "tests/contract/test_resolved_processing_jobs_public_main.py",
                    "tests/integration/test_processing_jobs_cli.py",
                    "tests/contract/test_processing_jobs_public_main.py",
                ]
                output = command(
                    [str(python), "-I", "-m", "pytest", "-q", *modules],
                    cwd=bundle,
                    env=env,
                    log=work / "public-tests.log",
                )
                assert "skipped" not in output
                count = int(re.search(r"(\d+) passed", output).group(1))
                assert count == 74, output
                record.update(
                    public_tests_passed=count,
                    public_tests_skipped=0,
                    qa_tools=tools,
                    test_bundle_contains_product_source=False,
                )
            records.append(record)
            args.output.write_text(
                json.dumps(
                    {
                        "wheel": str(wheel),
                        "records": records,
                        "completion": "ready" if len(records) == 4 else "in_progress",
                    },
                    indent=2,
                )
                + "\n"
            )
            print(f"installed {version} {mode}: passed", flush=True)


if __name__ == "__main__":
    main()
