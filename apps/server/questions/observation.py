from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import uuid4

from server.retrieval.models import ContextPack
from server.retrieval.search import SourceRetrievalTrace
from server.schemas.answers import ChatAnswerResponse
from server.schemas.questions import QuestionStatus

QuestionObservationStepStatus = Literal["not_started", "succeeded", "failed"]
QuestionObservationStepName = Literal[
    "question_preparation",
    "query_snapshot",
    "material_scope",
    "ready_material_selection",
    "retrieval_record_load",
    "retrieval_pipeline",
    "source_retrieval",
    "context_assembly",
    "candidate_summary",
    "answer_pipeline",
    "prompt_snapshot",
    "composer_call",
    "answer_projection",
    "finalization",
    "question_status",
]
QuestionObservationFailureKind = Literal[
    "empty_question",
    "no_ready_materials",
    "retrieval_failed",
    "answer_composer_failed",
]
QuestionObservationFactValue = str | int | float | bool | None | dict[str, int] | list[str]

_STEP_ROOTS: tuple[QuestionObservationStepName, ...] = (
    "question_preparation",
    "material_scope",
    "retrieval_pipeline",
    "answer_pipeline",
    "finalization",
)
_STEP_CHILDREN: dict[QuestionObservationStepName, tuple[QuestionObservationStepName, ...]] = {
    "question_preparation": ("query_snapshot",),
    "material_scope": ("ready_material_selection", "retrieval_record_load"),
    "retrieval_pipeline": ("source_retrieval", "context_assembly", "candidate_summary"),
    "answer_pipeline": ("prompt_snapshot", "composer_call", "answer_projection"),
    "finalization": ("question_status",),
}
_ALL_STEP_NAMES: tuple[QuestionObservationStepName, ...] = (
    "question_preparation",
    "query_snapshot",
    "material_scope",
    "ready_material_selection",
    "retrieval_record_load",
    "retrieval_pipeline",
    "source_retrieval",
    "context_assembly",
    "candidate_summary",
    "answer_pipeline",
    "prompt_snapshot",
    "composer_call",
    "answer_projection",
    "finalization",
    "question_status",
)
_ALLOWED_FACT_KEYS: dict[QuestionObservationStepName, set[str]] = {
    "question_preparation": set(),
    "query_snapshot": {"question_length"},
    "material_scope": set(),
    "ready_material_selection": {"ready_material_count", "ready_material_ids"},
    "retrieval_record_load": {"executed", "source_unit_count", "embedding_record_count"},
    "retrieval_pipeline": set(),
    "source_retrieval": {
        "executed",
        "strategy",
        "query_embedding_attempted",
        "query_embedding_available",
        "vector_attempted",
        "vector_candidate_count",
        "fallback_used",
    },
    "context_assembly": {"executed", "target_id"},
    "candidate_summary": {
        "candidate_count",
        "candidates_with_vector_score",
        "candidates_with_lexical_score",
    },
    "answer_pipeline": set(),
    "prompt_snapshot": {
        "available",
        "prompt_domain",
        "prompt_name",
        "prompt_version",
        "prompt_body_hash",
        "prompt_file_hash",
        "prompt_asset_path",
    },
    "composer_call": {"result"},
    "answer_projection": {"item_count", "evidence_state_counts"},
    "finalization": set(),
    "question_status": {"status"},
}


@dataclass(frozen=True)
class QuestionObservationStep:
    name: QuestionObservationStepName
    status: QuestionObservationStepStatus
    facts: dict[str, QuestionObservationFactValue] = field(default_factory=dict)
    failure_kind: QuestionObservationFailureKind | None = None
    children: list[QuestionObservationStep] = field(default_factory=list)


@dataclass(frozen=True)
class QuestionObservationRecord:
    id: str
    operation: Literal["question_answer"]
    steps: list[QuestionObservationStep]
    final_question_status: QuestionStatus | None
    failure_kind: QuestionObservationFailureKind | None

    def step(self, name: QuestionObservationStepName) -> QuestionObservationStep:
        for step in self.steps:
            match = _find_step(step, name)
            if match is not None:
                return match
        raise KeyError(name)


class QuestionObservationSink(Protocol):
    def record_question_answer(self, record: QuestionObservationRecord) -> None:
        raise NotImplementedError


class NoopQuestionObservationSink:
    def record_question_answer(self, record: QuestionObservationRecord) -> None:
        return None


class InMemoryQuestionObservationSink:
    def __init__(self) -> None:
        self._records: list[QuestionObservationRecord] = []

    @property
    def records(self) -> list[QuestionObservationRecord]:
        return list(self._records)

    def record_question_answer(self, record: QuestionObservationRecord) -> None:
        self._records.append(record)


class QuestionObservationRecorder:
    def __init__(self) -> None:
        self._record_id = f"obs_question_{uuid4().hex[:12]}"
        self._steps = {
            step_name: QuestionObservationStep(name=step_name, status="not_started")
            for step_name in _ALL_STEP_NAMES
        }
        self._final_question_status: QuestionStatus | None = None
        self._failure_kind: QuestionObservationFailureKind | None = None

    def succeed(
        self,
        step_name: QuestionObservationStepName,
        *,
        facts: dict[str, QuestionObservationFactValue] | None = None,
    ) -> None:
        safe_facts = _merge_safe_facts(step_name, self._steps[step_name].facts, facts or {})
        self._steps[step_name] = QuestionObservationStep(
            name=step_name,
            status="succeeded",
            facts=safe_facts,
        )

    def fail(
        self,
        step_name: QuestionObservationStepName,
        failure_kind: QuestionObservationFailureKind,
        *,
        facts: dict[str, QuestionObservationFactValue] | None = None,
    ) -> None:
        safe_facts = _merge_safe_facts(step_name, self._steps[step_name].facts, facts or {})
        self._steps[step_name] = QuestionObservationStep(
            name=step_name,
            status="failed",
            facts=safe_facts,
            failure_kind=failure_kind,
        )
        self._failure_kind = failure_kind

    def finalize(
        self,
        status: QuestionStatus | None,
        *,
        failure_kind: QuestionObservationFailureKind | None = None,
    ) -> None:
        self._final_question_status = status
        if failure_kind is not None:
            self._failure_kind = failure_kind

    def build(self) -> QuestionObservationRecord:
        return QuestionObservationRecord(
            id=self._record_id,
            operation="question_answer",
            steps=[self._build_step(step_name) for step_name in _STEP_ROOTS],
            final_question_status=self._final_question_status,
            failure_kind=self._failure_kind,
        )

    def _build_step(self, step_name: QuestionObservationStepName) -> QuestionObservationStep:
        current = self._steps[step_name]
        children = [self._build_step(child_name) for child_name in _STEP_CHILDREN.get(step_name, ())]
        if not children:
            return current
        return QuestionObservationStep(
            name=current.name,
            status=_derive_parent_status(children),
            facts=current.facts,
            failure_kind=_first_child_failure(children),
            children=children,
        )


def prompt_snapshot_facts(answer_composer: object) -> dict[str, QuestionObservationFactValue]:
    try:
        prompt = getattr(answer_composer, "prompt", None)
        snapshot = prompt.snapshot() if prompt is not None and hasattr(prompt, "snapshot") else None
    except Exception:
        return {"available": False}
    if not isinstance(snapshot, dict):
        return {"available": False}

    return {
        "available": True,
        "prompt_domain": _string_snapshot_value(snapshot, "domain"),
        "prompt_name": _string_snapshot_value(snapshot, "name"),
        "prompt_version": _string_snapshot_value(snapshot, "version"),
        "prompt_body_hash": _string_snapshot_value(snapshot, "bodyHash"),
        "prompt_file_hash": _string_snapshot_value(snapshot, "fileHash"),
        "prompt_asset_path": _string_snapshot_value(snapshot, "assetPath"),
    }


def retrieval_candidate_facts(context: ContextPack) -> dict[str, QuestionObservationFactValue]:
    return {
        "candidate_count": len(context.candidates),
        "candidates_with_vector_score": sum(
            candidate.vector_score is not None for candidate in context.candidates
        ),
        "candidates_with_lexical_score": sum(
            candidate.lexical_score > 0 for candidate in context.candidates
        ),
    }


def source_retrieval_facts(trace: SourceRetrievalTrace) -> dict[str, QuestionObservationFactValue]:
    return {
        "executed": True,
        "strategy": trace.strategy,
        "query_embedding_attempted": trace.query_embedding_attempted,
        "query_embedding_available": trace.query_embedding_available,
        "vector_attempted": trace.vector_attempted,
        "vector_candidate_count": trace.vector_candidate_count,
        "fallback_used": trace.fallback_used,
    }


def answer_projection_facts(answer: ChatAnswerResponse) -> dict[str, QuestionObservationFactValue]:
    evidence_state_counts = dict(Counter(item.evidence_state.value for item in answer.items))
    return {
        "item_count": len(answer.items),
        "evidence_state_counts": evidence_state_counts,
    }


def emit_question_observation(
    *,
    sink: QuestionObservationSink,
    recorder: QuestionObservationRecorder,
) -> None:
    try:
        sink.record_question_answer(recorder.build())
    except Exception:
        return None


def _derive_parent_status(children: list[QuestionObservationStep]) -> QuestionObservationStepStatus:
    if any(child.status == "failed" for child in children):
        return "failed"
    if any(child.status == "succeeded" for child in children):
        return "succeeded"
    return "not_started"


def _first_child_failure(children: list[QuestionObservationStep]) -> QuestionObservationFailureKind | None:
    for child in children:
        if child.failure_kind is not None:
            return child.failure_kind
        nested = _first_child_failure(child.children)
        if nested is not None:
            return nested
    return None


def _find_step(
    step: QuestionObservationStep,
    name: QuestionObservationStepName,
) -> QuestionObservationStep | None:
    if step.name == name:
        return step
    for child in step.children:
        match = _find_step(child, name)
        if match is not None:
            return match
    return None


def _string_snapshot_value(snapshot: dict[object, object], key: str) -> str | None:
    value = snapshot.get(key)
    return value if isinstance(value, str) else None


def _safe_facts(
    step_name: QuestionObservationStepName,
    facts: dict[str, QuestionObservationFactValue],
) -> dict[str, QuestionObservationFactValue]:
    allowed_keys = _ALLOWED_FACT_KEYS[step_name]
    return {
        key: value
        for key, value in facts.items()
        if key in allowed_keys and _is_safe_fact_value(value)
    }


def _merge_safe_facts(
    step_name: QuestionObservationStepName,
    current: dict[str, QuestionObservationFactValue],
    updates: dict[str, QuestionObservationFactValue],
) -> dict[str, QuestionObservationFactValue]:
    return {
        **_safe_facts(step_name, current),
        **_safe_facts(step_name, updates),
    }


def _is_safe_fact_value(value: QuestionObservationFactValue) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, dict):
        return all(isinstance(key, str) and isinstance(item, int) for key, item in value.items())
    if isinstance(value, list):
        return all(isinstance(item, str) for item in value)
    return False
