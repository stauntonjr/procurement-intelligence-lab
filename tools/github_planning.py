"""Audit and reconcile the repository's live GitHub planning control plane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / ".github" / "planning.json"

VIEW_QUERY = """
query($login:String!,$number:Int!){
  user(login:$login){
    projectV2(number:$number){
      id
      title
      views(first:100){
        totalCount
        nodes{id number name layout filter}
      }
    }
  }
}
"""

CREATE_VIEW_MUTATION = """
mutation($projectId:ID!,$name:String!,$layout:ProjectV2ViewLayout!){
  createProjectV2View(input:{projectId:$projectId,name:$name,layout:$layout}){
    projectV2View{id number name layout filter}
  }
}
"""

UPDATE_VIEW_MUTATION = """
mutation($viewId:ID!,$name:String!,$layout:ProjectV2ViewLayout!,$filter:String!){
  updateProjectV2View(
    input:{viewId:$viewId,name:$name,layout:$layout,filter:$filter}
  ){
    projectV2View{id number name layout filter}
  }
}
"""

DELETE_VIEW_MUTATION = """
mutation($viewId:ID!){
  deleteProjectV2View(input:{viewId:$viewId}){
    deletedViewId
  }
}
"""


@dataclass(frozen=True)
class DesiredView:
    """Declarative saved-view state."""

    name: str
    layout: str
    filter: str


@dataclass(frozen=True)
class ViewOperation:
    """A required idempotent view mutation."""

    action: str
    desired: DesiredView
    view_id: str | None = None


def run_gh(*args: str) -> str:
    """Run gh without a shell and return stdout."""
    completed = subprocess.run(
        ("gh", *args),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def run_gh_json(*args: str) -> Any:
    """Run gh and parse one JSON response."""
    return json.loads(run_gh(*args))


def load_config(path: Path) -> dict[str, Any]:
    """Load and minimally validate planning configuration."""
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("planning configuration must be a JSON object")
    for key in (
        "repository",
        "project",
        "required_fields",
        "required_milestones",
        "required_labels",
    ):
        if key not in value:
            raise ValueError(f"planning configuration is missing {key!r}")
    return cast(dict[str, Any], value)


def desired_views(config: dict[str, Any]) -> list[DesiredView]:
    """Return typed desired views from configuration."""
    project = cast(dict[str, Any], config["project"])
    raw_views = cast(list[dict[str, Any]], project["views"])
    views = [
        DesiredView(
            name=str(item["name"]),
            layout=str(item["layout"]),
            filter=str(item.get("filter", "")),
        )
        for item in raw_views
    ]
    names = [view.name for view in views]
    if len(names) != len(set(names)):
        raise ValueError("configured Project view names must be unique")
    return views


def plan_view_operations(
    existing: list[dict[str, Any]], desired: list[DesiredView]
) -> list[ViewOperation]:
    """Plan creates and updates without duplicating names."""
    by_name = {str(view["name"]): view for view in existing}
    operations: list[ViewOperation] = []
    for wanted in desired:
        current = by_name.get(wanted.name)
        if current is None:
            operations.append(ViewOperation("create", wanted))
            continue
        current_filter = str(current.get("filter") or "")
        if str(current["layout"]) != wanted.layout or current_filter != wanted.filter:
            operations.append(ViewOperation("update", wanted, str(current["id"])))
    return operations


def project_views(owner: str, number: int) -> tuple[str, list[dict[str, Any]]]:
    """Read a user-owned Project and all saved views."""
    response = cast(
        dict[str, Any],
        run_gh_json(
            "api",
            "graphql",
            "-f",
            f"query={VIEW_QUERY}",
            "-f",
            f"login={owner}",
            "-F",
            f"number={number}",
        ),
    )
    project = response.get("data", {}).get("user", {}).get("projectV2")
    if project is None:
        raise LookupError(f"user project {owner}/{number} was not found")
    if not isinstance(project, dict):
        raise TypeError("GitHub returned an invalid Project response")
    views = project.get("views", {}).get("nodes")
    if not isinstance(views, list):
        raise TypeError("GitHub returned an invalid Project views response")
    return str(project["id"]), cast(list[dict[str, Any]], views)


def mutate_view(project_id: str, operation: ViewOperation) -> None:
    """Apply one GraphQL view mutation."""
    wanted = operation.desired
    if operation.action == "create":
        response = cast(
            dict[str, Any],
            run_gh_json(
                "api",
                "graphql",
                "-f",
                f"query={CREATE_VIEW_MUTATION}",
                "-f",
                f"projectId={project_id}",
                "-f",
                f"name={wanted.name}",
                "-f",
                f"layout={wanted.layout}",
            ),
        )
        created = response.get("data", {}).get("createProjectV2View", {}).get("projectV2View")
        if not isinstance(created, dict):
            raise RuntimeError(f"GitHub did not return created view {wanted.name!r}")
        view_id = str(created["id"])
    elif operation.action == "update" and operation.view_id:
        view_id = operation.view_id
    else:
        raise ValueError(f"unsupported view operation: {operation}")

    run_gh_json(
        "api",
        "graphql",
        "-f",
        f"query={UPDATE_VIEW_MUTATION}",
        "-f",
        f"viewId={view_id}",
        "-f",
        f"name={wanted.name}",
        "-f",
        f"layout={wanted.layout}",
        "-f",
        f"filter={wanted.filter}",
    )


def missing_names(required: list[str], actual: list[str]) -> list[str]:
    """Return configured names absent from live state."""
    present = set(actual)
    return sorted(name for name in required if name not in present)


def audit(config: dict[str, Any]) -> int:
    """Audit planning objects and emit a bounded JSON report."""
    repository = str(config["repository"])
    project_config = cast(dict[str, Any], config["project"])
    owner = str(project_config["owner"])
    number = int(project_config["number"])

    viewer = cast(dict[str, Any], run_gh_json("api", "user"))
    project = cast(
        dict[str, Any],
        run_gh_json("project", "view", str(number), "--owner", owner, "--format", "json"),
    )
    fields_payload = cast(
        dict[str, Any],
        run_gh_json("project", "field-list", str(number), "--owner", owner, "--format", "json"),
    )
    items_payload = cast(
        dict[str, Any],
        run_gh_json(
            "project",
            "item-list",
            str(number),
            "--owner",
            owner,
            "--limit",
            "500",
            "--format",
            "json",
        ),
    )
    labels = cast(
        list[dict[str, Any]],
        run_gh_json("label", "list", "--repo", repository, "--limit", "200", "--json", "name"),
    )
    milestone_pages = cast(
        list[list[dict[str, Any]]],
        run_gh_json(
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repository}/milestones?state=all&per_page=100",
        ),
    )
    issues = cast(
        list[dict[str, Any]],
        run_gh_json(
            "issue",
            "list",
            "--repo",
            repository,
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number",
        ),
    )
    _, views = project_views(owner, number)

    field_names = [
        str(item["name"]) for item in cast(list[dict[str, Any]], fields_payload["fields"])
    ]
    label_names = [str(item["name"]) for item in labels]
    milestones = [item for page in milestone_pages for item in page]
    milestone_names = [str(item["title"]) for item in milestones]
    view_names = [str(item["name"]) for item in views]

    drift = {
        "fields": missing_names(cast(list[str], config["required_fields"]), field_names),
        "labels": missing_names(cast(list[str], config["required_labels"]), label_names),
        "milestones": missing_names(
            cast(list[str], config["required_milestones"]), milestone_names
        ),
        "views": missing_names([view.name for view in desired_views(config)], view_names),
    }
    report = {
        "viewer": viewer.get("login"),
        "repository": repository,
        "project": {
            "id": project.get("id"),
            "number": project.get("number"),
            "title": project.get("title"),
            "field_count": len(field_names),
            "item_count": int(items_payload.get("totalCount", len(items_payload.get("items", [])))),
            "view_count": len(views),
            "managed_views": sorted(
                set(view_names) & {view.name for view in desired_views(config)}
            ),
        },
        "issue_count": len(issues),
        "label_count": len(labels),
        "milestone_count": len(milestones),
        "missing": drift,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(any(drift.values()))


def sync_views(config: dict[str, Any], *, apply: bool) -> int:
    """Check or reconcile configured saved views."""
    project_config = cast(dict[str, Any], config["project"])
    owner = str(project_config["owner"])
    number = int(project_config["number"])
    project_id, existing = project_views(owner, number)
    operations = plan_view_operations(existing, desired_views(config))
    if not operations:
        print("Project views match .github/planning.json")
        return 0

    for operation in operations:
        print(f"{operation.action}: {operation.desired.name}")
    if not apply:
        print("Re-run with --apply to reconcile these views.")
        return 1

    for operation in operations:
        mutate_view(project_id, operation)

    _, verified = project_views(owner, number)
    remaining = plan_view_operations(verified, desired_views(config))
    if remaining:
        raise RuntimeError(f"Project view verification failed: {remaining}")
    print(f"Reconciled and verified {len(operations)} Project view(s).")
    return 0


def delete_view(config: dict[str, Any], *, name: str, apply: bool) -> int:
    """Delete one unmanaged view after an explicit dry run and apply flag."""
    configured = {view.name for view in desired_views(config)}
    if name in configured:
        raise ValueError(f"remove configured view {name!r} from .github/planning.json first")

    project_config = cast(dict[str, Any], config["project"])
    owner = str(project_config["owner"])
    number = int(project_config["number"])
    _, existing = project_views(owner, number)
    matches = [view for view in existing if str(view["name"]) == name]
    if not matches:
        print(f"Project view {name!r} is already absent.")
        return 0
    if len(matches) != 1:
        raise RuntimeError(f"refusing to delete ambiguous Project view name {name!r}")
    if not apply:
        print(f"delete: {name}")
        print("Re-run with --apply to delete this unmanaged view.")
        return 1

    view_id = str(matches[0]["id"])
    run_gh_json(
        "api",
        "graphql",
        "-f",
        f"query={DELETE_VIEW_MUTATION}",
        "-f",
        f"viewId={view_id}",
    )
    _, verified = project_views(owner, number)
    if any(str(view["id"]) == view_id for view in verified):
        raise RuntimeError(f"Project view deletion was not verified for {name!r}")
    print(f"Deleted and verified Project view {name!r}.")
    return 0


def preflight(config: dict[str, Any]) -> int:
    """Verify gh identity and planning access without changing GitHub."""
    repository = str(config["repository"])
    project_config = cast(dict[str, Any], config["project"])
    auth = run_gh("auth", "status")
    viewer = cast(dict[str, Any], run_gh_json("api", "user"))
    run_gh_json("repo", "view", repository, "--json", "nameWithOwner")
    project_views(str(project_config["owner"]), int(project_config["number"]))
    print(
        json.dumps(
            {
                "authenticated_as": viewer.get("login"),
                "repository": repository,
                "project_number": project_config["number"],
                "auth_status_verified": "Logged in" in auth,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight", help="verify gh identity and access")
    subparsers.add_parser("audit", help="audit live planning state")
    sync = subparsers.add_parser("sync-views", help="reconcile saved Project views")
    sync.add_argument("--apply", action="store_true", help="apply planned view changes")
    delete = subparsers.add_parser("delete-view", help="delete one unmanaged saved Project view")
    delete.add_argument("--name", required=True, help="exact saved view name")
    delete.add_argument("--apply", action="store_true", help="apply the planned deletion")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the selected planning operation."""
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.command == "preflight":
        return preflight(config)
    if args.command == "audit":
        return audit(config)
    if args.command == "sync-views":
        return sync_views(config, apply=bool(args.apply))
    if args.command == "delete-view":
        return delete_view(config, name=str(args.name), apply=bool(args.apply))
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        TypeError,
        ValueError,
        LookupError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"github planning failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
