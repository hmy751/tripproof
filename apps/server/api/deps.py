from __future__ import annotations

from fastapi import Request

from server.answers.library_chat import LibraryChatAnswerComposer
from server.materials.observation import MaterialUploadObservationSink
from server.materials.store import MaterialStore


def get_material_store(request: Request) -> MaterialStore:
    return request.app.state.material_store


def get_material_upload_observation_sink(request: Request) -> MaterialUploadObservationSink:
    return request.app.state.material_upload_observation_sink


def get_library_chat_answer_composer(request: Request) -> LibraryChatAnswerComposer:
    return request.app.state.library_chat_answer_composer
