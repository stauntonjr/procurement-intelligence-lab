"""Explicit internal-SKU namespace and the existing unique normalized-exact rule."""

from dataclasses import asdict, dataclass

from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
from procurement_intelligence_lab.platform.execution.identity import digest
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    ResolutionPolicyEvidence,
    admit,
)


@dataclass(frozen=True)
class BomResolutionPolicy:
    profile: str
    entity_type: str
    identifier_namespace: str
    normalization: str
    matching: str

    def __post_init__(self) -> None:
        admit(
            tuple(vars(self).values())
            == (
                "bom-normalized-exact@1",
                "procurement_item",
                "internal_sku",
                "casefold-alnum@1",
                "unique-normalized-match@1",
            )
            and all(type(v) is str for v in vars(self).values())
        )

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_parameters(cls, parameters: tuple[tuple[str, str], ...]) -> "BomResolutionPolicy":
        admit(
            type(parameters) is tuple
            and all(
                type(p) is tuple and len(p) == 2 and all(type(v) is str for v in p)
                for p in parameters
            )
        )
        values = dict(parameters)
        admit(
            len(values) == len(parameters)
            and set(values)
            == {"profile", "entity_type", "identifier_namespace", "normalization", "matching"}
        )
        return cls(
            values["profile"],
            values["entity_type"],
            values["identifier_namespace"],
            values["normalization"],
            values["matching"],
        )

    @property
    def reference_id(self) -> str:
        return "bom-normalized-exact@1:" + digest(self.as_dict())

    @property
    def evidence(self) -> ResolutionPolicyEvidence:
        return ResolutionPolicyEvidence(
            ResolvedReference(
                "procurement.resolve/normalized-exact@1", self.reference_id, digest(self.as_dict())
            ),
            self.entity_type,
            self.identifier_namespace,
            tuple(sorted(self.as_dict().items())),
        )
