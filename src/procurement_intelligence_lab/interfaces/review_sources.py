"""Visible composition for original fixed sources or the default admitted corpus."""

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files

from procurement_intelligence_lab.adapters.showcase_sources import MANIFEST, ShowcaseSources
from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
from procurement_intelligence_lab.application.corpus_agent_tools import Investigator
from procurement_intelligence_lab.application.corpus_investigation import CorpusInvestigationService
from procurement_intelligence_lab.application.original_showcase import OriginalShowcaseInvestigator
from procurement_intelligence_lab.application.showcase import ShowcaseScenario
from procurement_intelligence_lab.interfaces.agent_runs import PROJECTS
from procurement_intelligence_lab.ports.review_sources import ReviewSources

SOURCE_OPTIONS = ("corpus", "showcase-a-order", "showcase-a-b-order", "showcase-a-only")
REVIEW_PROJECTS = (*PROJECTS, "synthetic-project")


@dataclass(frozen=True)
class SourceComposition:
    reader: ReviewSources
    investigator: Investigator
    projects: tuple[str, ...]
    site: str
    fixture_version: str


def compose_sources(selection: str = "corpus") -> SourceComposition:
    if selection == "corpus":
        reader = SyntheticCorpusReader()
        manifest = (
            files("procurement_intelligence_lab.examples")
            .joinpath("corpus_v1/manifest.json")
            .read_bytes()
        )
        return SourceComposition(
            reader,
            CorpusInvestigationService(reader),
            PROJECTS,
            "lab",
            sha256(manifest).hexdigest(),
        )
    scenarios = {
        "showcase-a-order": ShowcaseScenario.ORDER_MISMATCH,
        "showcase-a-b-order": ShowcaseScenario.ORDER_UNRESOLVED,
        "showcase-a-only": ShowcaseScenario.ORDER_MISSING,
    }
    if selection not in scenarios:
        raise ValueError("unsupported review sources")
    original = ShowcaseSources(selection)
    manifest = files("procurement_intelligence_lab.examples").joinpath(MANIFEST).read_bytes()
    return SourceComposition(
        original,
        OriginalShowcaseInvestigator(original, scenarios[selection]),
        ("synthetic-project",),
        "synthetic-site",
        "original:" + sha256(manifest + b"\0" + selection.encode()).hexdigest(),
    )
