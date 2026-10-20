"""Versioned typed JSON DAG; only explicitly registered immutable records are admitted."""

import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from hashlib import sha256
from types import UnionType
from typing import Any, TypeAliasType, cast, get_args, get_origin, get_type_hints

from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
)

MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_NODES = 50000


def canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    )


def digest(value: object) -> str:
    return sha256(canonical(value).encode()).hexdigest()


@lru_cache(maxsize=64)
def _hints(cls: type[object]) -> dict[str, Any]:
    return get_type_hints(cls)


def _matches(value: object, hint: Any) -> bool:
    if isinstance(hint, TypeAliasType):
        return _matches(value, hint.__value__)
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is UnionType:
        return any(_matches(value, x) for x in args)
    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        members = cast(tuple[object, ...], value)
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_matches(x, args[0]) for x in members)
        return len(members) == len(args) and all(
            _matches(v, t) for v, t in zip(members, args, strict=True)
        )
    if hint in (str, int, bool, Decimal, datetime, date, type(None)):
        return type(value) is hint
    return isinstance(value, hint)


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class SemanticCodec:
    def __init__(self, records: tuple[type[object], ...], enums: tuple[type[StrEnum], ...]) -> None:
        if any(
            not is_dataclass(cls)
            or not getattr(getattr(cls, "__dataclass_params__", None), "frozen", False)
            for cls in records
        ):
            raise ArchiveContractError("codec only supports registered frozen dataclasses")
        self.records = {x.__name__: x for x in records}
        self.enums = {x.__name__: x for x in enums}
        if len(self.records) != len(records) or len(self.enums) != len(enums):
            raise ArchiveContractError("codec registrations must have unique names")

    def _graph(self, value: object) -> dict[str, object]:
        nodes: dict[str, object] = {}
        memo: dict[int, object] = {}
        active: set[int] = set()

        def encode(item: Any, depth: int = 0) -> object:
            if depth > 64:
                raise ValueError("graph exceeds depth limit")
            if item is None:
                return ["null"]
            if type(item) in (str, bool, int):
                return [type(item).__name__, item]
            if type(item) is Decimal:
                if not item.is_finite():
                    raise ValueError("nonfinite decimal")
                return ["decimal", str(item)]
            if type(item) is datetime:
                if not isinstance(item.tzinfo, timezone):
                    raise ValueError("only aware fixed-offset times are portable")
                return ["datetime", item.isoformat()]
            if type(item) is date:
                return ["date", item.isoformat()]
            if isinstance(item, StrEnum):
                if self.enums.get(type(item).__name__) is not type(item):
                    raise ValueError("unregistered enum")
                return ["enum", type(item).__name__, item.value]
            if type(item) is tuple:
                return ["tuple", [encode(x, depth + 1) for x in cast(tuple[object, ...], item)]]
            cls = cast(type[object], type(item))
            if self.records.get(cls.__name__) is not cls or not is_dataclass(item):
                raise ValueError("unregistered record/value")
            if id(item) in active:
                raise ValueError("cyclic graph")
            if id(item) in memo:
                return memo[id(item)]
            active.add(id(item))
            values: list[list[object]] = []
            for field in fields(item):
                field_value = getattr(item, field.name)
                if not _matches(field_value, _hints(cls)[field.name]):
                    raise ValueError("record field has unsupported type")
                values.append([field.name, encode(field_value, depth + 1)])
            node = {"kind": cls.__name__, "fields": values}
            key = digest(node)
            nodes[key] = node
            if len(nodes) > MAX_NODES:
                raise ValueError("graph exceeds node limit")
            ref = ["ref", key]
            memo[id(item)] = ref
            active.remove(id(item))
            return ref

        root = encode(value)
        return {"schema": 1, "root": root, "records": nodes}

    def dumps(self, value: object) -> str:
        try:
            result = canonical(self._graph(value))
            if len(result.encode()) > MAX_PAYLOAD_BYTES:
                raise ValueError("graph exceeds payload limit")
            return result
        except (ValueError, TypeError, AttributeError, RecursionError):
            raise ArchiveContractError("unsupported archive value or record graph") from None

    def node_digest(self, value: object) -> str:
        return digest(self._graph(value)["root"])

    def loads(self, raw: str) -> Any:
        try:
            if len(raw.encode()) > MAX_PAYLOAD_BYTES:
                raise ValueError("payload limit")
            graph: dict[str, Any] = json.loads(raw, object_pairs_hook=_pairs)
            if (
                set(graph) != {"schema", "root", "records"}
                or type(graph["schema"]) is not int
                or graph["schema"] != 1
            ):
                raise ValueError("schema")
            candidate: object = graph["records"]
            if not isinstance(candidate, dict):
                raise TypeError("nodes")
            nodes = cast(dict[str, Any], candidate)
            if len(nodes) > MAX_NODES:
                raise TypeError("nodes")
            cache: dict[str, object] = {}
            active: set[str] = set()

            def decode(encoded: Any, depth: int = 0) -> Any:
                if depth > 64 or not isinstance(encoded, list) or not encoded:
                    raise ValueError("encoded value")
                parts = cast(list[Any], encoded)
                tag: Any = parts[0]
                if parts == ["null"]:
                    return None
                if tag in ("str", "int", "bool") and len(parts) == 2:
                    if type(parts[1]) is not {"str": str, "int": int, "bool": bool}[tag]:
                        raise ValueError("scalar type")
                    return parts[1]
                if (
                    tag in ("decimal", "date", "datetime")
                    and len(parts) == 2
                    and isinstance(parts[1], str)
                ):
                    return {
                        "decimal": Decimal,
                        "date": date.fromisoformat,
                        "datetime": datetime.fromisoformat,
                    }[tag](parts[1])
                if tag == "tuple" and len(parts) == 2 and isinstance(parts[1], list):
                    return tuple(decode(x, depth + 1) for x in cast(list[Any], parts[1]))
                if tag == "enum" and len(parts) == 3:
                    return self.enums[parts[1]](parts[2])
                if tag != "ref" or len(parts) != 2 or not isinstance(parts[1], str):
                    raise ValueError("unknown tag")
                key = parts[1]
                if key in active:
                    raise ValueError("cycle")
                if key in cache:
                    return cache[key]
                node: dict[str, Any] = nodes[key]
                if digest(node) != key or set(node) != {"kind", "fields"}:
                    raise ValueError("node digest")
                cls = self.records[node["kind"]]
                pairs: Any = node["fields"]
                if not isinstance(pairs, list):
                    raise TypeError("record field pairs")
                for candidate_pair in cast(list[object], pairs):
                    if not isinstance(candidate_pair, list):
                        raise TypeError("record field pair")
                    pair = cast(list[object], candidate_pair)
                    if len(pair) != 2 or not isinstance(pair[0], str):
                        raise TypeError("record field pair")
                if [x[0] for x in cast(list[list[Any]], pairs)] != [
                    f.name for f in fields(cast(Any, cls))
                ]:
                    raise ValueError("record fields")
                active.add(key)
                values: dict[str, Any] = {
                    name: decode(value, depth + 1) for name, value in node["fields"]
                }
                if any(not _matches(value, _hints(cls)[name]) for name, value in values.items()):
                    raise ValueError("field type")
                result = cast(Any, cls)(**values)
                cache[key] = result
                active.remove(key)
                return result

            result = decode(graph["root"])
            if self._graph(result) != graph:
                raise ValueError("noncanonical or unreachable records")
            return result
        except (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RecursionError,
            OverflowError,
            ArithmeticError,
        ):
            raise ArchiveIntegrityError("stored archive graph is invalid or unsupported") from None
