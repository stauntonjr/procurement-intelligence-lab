"""Deterministic evidence of literal catalog mentions; aliases stay unresolved."""

import re


def canonical_item_mentions(question: str, items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                item
                for item in items
                if re.search(
                    r"(?<![\w-])" + re.escape(item) + r"(?![\w-])", question, re.IGNORECASE
                )
            }
        )
    )
