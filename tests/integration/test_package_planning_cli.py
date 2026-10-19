from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/planning"
pytestmark = pytest.mark.integration


def invoke(manifest: Path, registry: Path, config: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "procurement_intelligence_lab.interfaces.plan_package",
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
            "--config",
            str(config),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=manifest.parent,
    )


@pytest.mark.parametrize("domain", ["procurement", "conformance"])
def test_public_planning_cli_with_real_manifest_and_deployment_fixtures(
    tmp_path: Path, domain: str
) -> None:
    manifest = tmp_path / "manifest.json"
    if domain == "procurement":
        compiled = subprocess.run(
            [sys.executable, "-m", "procurement_intelligence_lab.interfaces.domain_package"],
            capture_output=True,
            check=True,
        )
        manifest.write_bytes(compiled.stdout)
    else:
        manifest.write_bytes((FIXTURES / "conformance-manifest.json").read_bytes())
    actual = invoke(
        manifest, FIXTURES / f"{domain}-registry.json", FIXTURES / f"{domain}-config.toml"
    )
    assert actual.returncode == 0, actual.stderr
    assert not actual.stderr
    envelope = json.loads(actual.stdout)
    payload = envelope["plan"]
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert envelope["plan_hash"] == hashlib.sha256(canonical).hexdigest()
    assert len(payload["stages"]) == 12
    assert payload["domain"]["id"] == domain
    assert len(payload["physical_steps"]) == (9 if domain == "procurement" else 1)
    assert payload["stages"][-1]["implementation"] is None
    assert payload["stages"][-1]["disposition"] == "TYPED_EMPTY"
    repeated = invoke(
        manifest, FIXTURES / f"{domain}-registry.json", FIXTURES / f"{domain}-config.toml"
    )
    assert repeated.stdout == actual.stdout


@pytest.mark.parametrize(
    ("target", "content", "issue"),
    [
        ("manifest", b"null", "invalid_record"),
        ("manifest", b"\xff", "invalid_json"),
        ("registry", b'{"schema_version":"1.0","implementations":[]}', "unknown_implementation"),
        ("registry", b'{"schema_version":"1.0","schema_version":"1.0"}', "duplicate_key"),
        ("config", b'schema_version="1.0"\nschema_version="1.0"', "invalid_toml"),
        ("config", None, "input_unreadable"),
    ],
)
def test_public_planning_cli_errors_are_typed_and_have_no_plan(
    tmp_path: Path, target: str, content: bytes | None, issue: str
) -> None:
    paths = {
        "manifest": FIXTURES / "conformance-manifest.json",
        "registry": FIXTURES / "conformance-registry.json",
        "config": FIXTURES / "conformance-config.toml",
    }
    bad = tmp_path / "bad-input"
    if content is not None:
        bad.write_bytes(content)
    paths[target] = bad
    result = invoke(paths["manifest"], paths["registry"], paths["config"])
    assert result.returncode == 2
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["code"] == "pil.input.package_planning_invalid"
    assert error["category"] == "input"
    assert issue in {x["code"] for x in error["issues"]}
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("target", ["manifest", "registry"])
@pytest.mark.parametrize("content", [b'{"x":1,"x":2}', b'{"x":NaN}'])
def test_json_hook_diagnostics_retain_input_context(
    tmp_path: Path, target: str, content: bytes
) -> None:
    paths = {
        "manifest": FIXTURES / "conformance-manifest.json",
        "registry": FIXTURES / "conformance-registry.json",
        "config": FIXTURES / "conformance-config.toml",
    }
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(content)
    paths[target] = invalid
    result = invoke(paths["manifest"], paths["registry"], paths["config"])
    assert result.returncode == 2 and not result.stdout
    assert all(x["path"].startswith(target) for x in json.loads(result.stderr)["issues"])


def test_registry_contract_diagnostics_retain_input_context(tmp_path: Path) -> None:
    payload = json.loads((FIXTURES / "conformance-registry.json").read_text())
    payload["implementations"][0]["input_contract"]["version"] = "broken"
    invalid = tmp_path / "invalid-registry.json"
    invalid.write_text(json.dumps(payload))
    result = invoke(
        FIXTURES / "conformance-manifest.json", invalid, FIXTURES / "conformance-config.toml"
    )
    assert result.returncode == 2 and not result.stdout
    assert (
        json.loads(result.stderr)["issues"][0]["path"]
        == "registry.implementations[0].input_contract.version"
    )
