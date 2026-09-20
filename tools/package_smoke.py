"""Build, inspect, install, and run the distributable wheel in isolation."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = (
    "procurement_intelligence_lab/examples/synthetic_bom.xlsx",
    "procurement_intelligence_lab/examples/showcase_order_short.xlsx",
    "procurement_intelligence_lab/examples/showcase_order_matched.xlsx",
    "procurement_intelligence_lab/examples/showcase_bom_revision_a.xlsx",
    "procurement_intelligence_lab/examples/showcase_bom_revision_b.xlsx",
    "procurement_intelligence_lab/examples/showcase_bom_revision_b_equal.xlsx",
    "procurement_intelligence_lab/examples/anomaly_sources_v1.json",
    "procurement_intelligence_lab/examples/anomaly_lifecycle_v1.json",
)


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the package smoke test")

    with tempfile.TemporaryDirectory(prefix="procurement-package-smoke-") as directory:
        temporary = Path(directory)
        distribution = temporary / "dist"
        subprocess.run(
            [uv, "build", "--out-dir", str(distribution)],
            cwd=ROOT,
            check=True,
        )
        wheels = sorted(distribution.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        wheel = wheels[0]
        with ZipFile(wheel) as archive:
            missing = sorted(set(RESOURCES) - set(archive.namelist()))
            if missing:
                raise RuntimeError(f"wheel is missing runtime resources {missing}")

        environment = temporary / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
            cwd=temporary,
            check=True,
        )
        completed = subprocess.run(
            [str(python), "-m", "procurement_intelligence_lab"],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        if payload["claims"]["gpu_quantity"]["value"] != "4":
            raise RuntimeError("installed demo returned an unexpected GPU quantity")
        # Exercise the installed public caller from outside the repository.
        probe = ROOT / "tools/order_package_probe.py"
        subprocess.run([str(python), str(probe)], cwd=temporary, check=True)
        web_help = subprocess.run(
            [str(python), "-m", "procurement_intelligence_lab.interfaces.web", "--help"],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )
        if "--host" not in web_help.stdout or "--port" not in web_help.stdout:
            raise RuntimeError("installed web server does not document host and port options")

    print("package smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
