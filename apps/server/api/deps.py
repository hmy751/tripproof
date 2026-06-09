from __future__ import annotations

from fastapi import Request

from server.answers.library_chat import LibraryChatAnswerComposer
from server.extraction.checkin import CheckinFactProposer
from server.materials.store import MaterialStore


def get_material_store(request: Request) -> MaterialStore:
    return request.app.state.material_store


def get_checkin_fact_proposer(request: Request) -> CheckinFactProposer:
    return request.app.state.checkin_fact_proposer


def get_library_chat_answer_composer(request: Request) -> LibraryChatAnswerComposer:
    return request.app.state.library_chat_answer_composer
