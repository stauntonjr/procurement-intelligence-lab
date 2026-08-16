"""Executable contract for the repository's Dependabot policy."""

from pathlib import Path

CONFIG = Path(".github/dependabot.yml")


def _section(text: str, ecosystem: str) -> str:
    marker = f'package-ecosystem: "{ecosystem}"'
    start = text.index(marker)
    next_start = text.find("\n  - package-ecosystem:", start + len(marker))
    return text[start : next_start if next_start != -1 else len(text)]


def test_dependabot_config_covers_uv_and_actions_with_bounded_updates() -> None:
    text = CONFIG.read_text(encoding="utf-8")

    assert text.startswith("version: 2\nupdates:\n")
    assert text.count('package-ecosystem: "') == 2

    for ecosystem, limit, time in (
        ("uv", "open-pull-requests-limit: 3", 'time: "04:00"'),
        ("github-actions", "open-pull-requests-limit: 2", 'time: "04:30"'),
    ):
        section = _section(text, ecosystem)
        assert 'directory: "/"' in section
        assert 'interval: "weekly"' in section
        assert 'day: "monday"' in section
        assert time in section
        assert 'timezone: "America/New_York"' in section
        assert limit in section
        assert "cooldown:" in section
        assert "default-days: 3" in section
        assert "groups:" in section
        assert 'patterns:\n          - "*"' in section

    uv = _section(text, "uv")
    assert 'update-types:\n          - "minor"\n          - "patch"' in uv


def test_dependabot_policy_does_not_enable_auto_merge_or_ai_review_gate() -> None:
    policy = Path("docs/development/dependabot-policy.md").read_text(encoding="utf-8")

    assert "No auto-merge" in policy
    assert "AI review is advisory" in policy
    assert "A human maintainer must" in policy
