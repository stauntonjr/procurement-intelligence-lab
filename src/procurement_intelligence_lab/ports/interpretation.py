"""Model interpretation and durable attempt mechanics behind explicit ports."""

from typing import Protocol

from procurement_intelligence_lab.platform.semantics.interpretation import (
    InterpretationCall,
    ModelReply,
)


class QuestionInterpreter(Protocol):
    def interpret(
        self, question: str, items: tuple[str, ...], project: str, as_of: str
    ) -> ModelReply: ...


class InterpretationStore(Protocol):
    def create(self, call: InterpretationCall) -> None: ...
    def finish(self, call: InterpretationCall) -> None: ...
    def get(self, run_id: str) -> InterpretationCall: ...
