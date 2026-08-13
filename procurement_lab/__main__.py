from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> list[dict]:
    with (ROOT / "data" / name).open() as f:
        return [json.loads(line) for line in f if line.strip()]


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").split())


def resolve(
    query: str, records: list[dict], field: str = "description"
) -> list[tuple[float, dict]]:
    q = set(normalize(query).split())
    scored = []
    for record in records:
        candidates = [record.get(field, "")] + record.get("aliases", [])
        tokens = set().union(*(set(normalize(c).split()) for c in candidates))
        score = len(q & tokens) / max(len(q), 1)
        if score:
            scored.append((round(score, 3), record))
    return sorted(scored, reverse=True, key=lambda x: x[0])


def anomalies(commitments: list[dict], events: list[dict]) -> list[dict]:
    by_commitment = {e["commitment_id"]: e for e in events}
    results = []
    for c in commitments:
        e = by_commitment.get(c["commitment_id"])
        if e and e["observed_date"] > c["promised_date"]:
            results.append(
                {
                    "commitment_id": c["commitment_id"],
                    "kind": "late_delivery",
                    "expected": c["promised_date"],
                    "observed": e["observed_date"],
                    "evidence": [c["source_id"], e["source_id"]],
                }
            )
    return results


def main() -> None:
    items = load("items.jsonl")
    vendors = load("vendors.jsonl")
    commitments = load("commitments.jsonl")
    events = load("events.jsonl")
    print("Procurement Intelligence Lab — synthetic demo")
    print("Resolved:", resolve("24C OS2 fiber trunk", items)[0])
    print("Vendor match:", resolve("Vector Cable", vendors, "name")[0])
    print("Anomalies:", json.dumps(anomalies(commitments, events), indent=2))
    print(
        "Action proposal: notify project analyst (approval required; no external write performed)."
    )


if __name__ == "__main__":
    main()
