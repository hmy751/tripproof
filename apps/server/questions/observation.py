from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import uuid4

from server.retrieval.models import AnswerContext
from server.retrieval.search import SourceRetrievalTrace
from server.runtime.config_snapshot import PromptRuntimeConfigSnapshot, RuntimeConfigSnapshot
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
    runtime_config_snapshot: RuntimeConfigSnapshot | None = None

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
    def __init__(self, *, runtime_config_snapshot: RuntimeConfigSnapshot | None = None) -> None:
        self._record_id = f"obs_question_{uuid4().hex[:12]}"
        self._runtime_config_snapshot = runtime_config_snapshot
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
            runtime_config_snapshot=self._runtime_config_snapshot,
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


class QuestionObservationReporter:
    def __init__(
        self,
        *,
        sink: QuestionObservationSink,
        runtime_config_snapshot: RuntimeConfigSnapshot | None = None,
    ) -> None:
        self._sink = sink
        self._recorder = QuestionObservationRecorder(
            runtime_config_snapshot=runtime_config_snapshot,
        )

    def query_succeeded(self, question: str) -> None:
        self._recorder.succeed("query_snapshot", facts={"question_length": len(question)})

    def query_empty(self) -> None:
        self._recorder.fail("query_snapshot", "empty_question", facts={"question_length": 0})
        self._recorder.finalize(None, failure_kind="empty_question")

    def ready_materials_selected(self, *, ready_material_ids: list[str]) -> None:
        self._recorder.succeed(
            "ready_material_selection",
            facts={
                "ready_material_count": len(ready_material_ids),
                "ready_material_ids": ready_material_ids,
            },
        )

    def ready_materials_missing(self) -> None:
        self._recorder.fail(
            "ready_material_selection",
            "no_ready_materials",
            facts={"ready_material_count": 0, "ready_material_ids": []},
        )
        self._recorder.succeed("question_status", facts={"status": "blocked"})
        self._recorder.finalize("blocked", failure_kind="no_ready_materials")

    def retrieval_records_loaded(
        self,
        *,
        source_unit_count: int,
        embedding_record_count: int,
    ) -> None:
        self._recorder.succeed(
            "retrieval_record_load",
            facts={
                "executed": True,
                "source_unit_count": source_unit_count,
                "embedding_record_count": embedding_record_count,
            },
        )

    def retrieval_records_failed(self) -> None:
        self._recorder.fail("retrieval_record_load", "retrieval_failed", facts={"executed": True})
        self._recorder.finalize(None, failure_kind="retrieval_failed")

    def source_context_retrieved(
        self,
        *,
        source_retrieval: SourceRetrievalTrace,
        answer_context: AnswerContext,
    ) -> None:
        self._recorder.succeed("source_retrieval", facts=source_retrieval_facts(source_retrieval))
        self._recorder.succeed(
            "context_assembly",
            facts={"executed": True, "target_id": answer_context.target_id},
        )
        self._recorder.succeed("candidate_summary", facts=retrieval_candidate_facts(answer_context))

    def source_retrieval_failed(self) -> None:
        self._recorder.fail("source_retrieval", "retrieval_failed", facts={"executed": True})
        self._recorder.finalize(None, failure_kind="retrieval_failed")

    def prompt_snapshotted(self, prompt: PromptRuntimeConfigSnapshot | None) -> None:
        self._recorder.succeed("prompt_snapshot", facts=prompt_snapshot_facts(prompt))

    def answer_composed(self, answer: ChatAnswerResponse) -> None:
        self._recorder.succeed("composer_call", facts={"result": "succeeded"})
        self._recorder.succeed("answer_projection", facts=answer_projection_facts(answer))

    def answer_composer_failed(self) -> None:
        self._recorder.fail("composer_call", "answer_composer_failed")
        self._recorder.finalize(None, failure_kind="answer_composer_failed")

    def question_accepted(self) -> None:
        self._recorder.succeed("question_status", facts={"status": "accepted"})
        self._recorder.finalize("accepted")

    def emit(self) -> None:
        emit_question_observation(sink=self._sink, recorder=self._recorder)


def prompt_snapshot_facts(
    prompt: PromptRuntimeConfigSnapshot | None,
) -> dict[str, QuestionObservationFactValue]:
    if prompt is None:
        return {"available": False}
    return {
        "available": True,
        "prompt_domain": prompt.domain,
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
        "prompt_body_hash": prompt.body_hash,
        "prompt_file_hash": prompt.file_hash,
        "prompt_asset_path": prompt.asset_path,
    }


def retrieval_candidate_facts(context: AnswerContext) -> dict[str, QuestionObservationFactValue]:
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
