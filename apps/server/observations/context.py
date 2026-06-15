from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
import secrets
from typing import Literal

CorrelationIdSource = Literal["header", "request_id_fallback"]


@dataclass(frozen=True)
class ObservationRequestContext:
    request_id: str
    correlation_id: str
    correlation_id_source: CorrelationIdSource


_OBSERVATION_REQUEST_CONTEXT: ContextVar[ObservationRequestContext | None] = ContextVar(
    "tripproof_observation_request_context",
    default=None,
)


def new_observation_request_context(
    *,
    correlation_id: str | None = None,
    correlation_id_source: CorrelationIdSource = "request_id_fallback",
) -> ObservationRequestContext:
    request_id = _new_request_id()
    return ObservationRequestContext(
        request_id=request_id,
        correlation_id=correlation_id or request_id,
        correlation_id_source=correlation_id_source,
    )


def set_current_observation_request_context(
    context: ObservationRequestContext,
) -> Token[ObservationRequestContext | None]:
    return _OBSERVATION_REQUEST_CONTEXT.set(context)


def reset_current_observation_request_context(
    token: Token[ObservationRequestContext | None],
) -> None:
    _OBSERVATION_REQUEST_CONTEXT.reset(token)


def current_observation_request_context() -> ObservationRequestContext | None:
    return _OBSERVATION_REQUEST_CONTEXT.get()


def _new_request_id() -> str:
    return f"req_{secrets.token_hex(8)}"
