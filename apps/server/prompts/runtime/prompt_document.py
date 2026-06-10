from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re


@dataclass(frozen=True)
class PromptDocument:
    domain: str
    name: str
    version: str
    metadata: dict[str, str]
    title: str | None
    body_markdown: str
    asset_path: str
    source_path: Path
    file_hash: str
    body_hash: str

    def snapshot(self) -> dict[str, str]:
        return {
            "domain": self.domain,
            "name": self.name,
            "version": self.version,
            "fileHash": self.file_hash,
            "bodyHash": self.body_hash,
            "assetPath": self.asset_path,
        }


def read_prompt_document(
    *,
    domain: str,
    name: str,
    version: str,
    path: Path,
    asset_path: str,
) -> PromptDocument:
    content = path.read_text(encoding="utf-8")
    metadata, body_start = _leading_metadata(content)
    metadata_domain = _required_metadata_value(metadata=metadata, key="domain")
    metadata_name = _required_metadata_value(metadata=metadata, key="name")
    metadata_version = _required_metadata_value(metadata=metadata, key="version")
    if metadata_domain != domain:
        raise ValueError(f"프롬프트 문서 domain이 경로와 다릅니다: 기대값={domain}, 실제값={metadata_domain}")
    if metadata_name != name:
        raise ValueError(f"프롬프트 문서 이름이 경로와 다릅니다: 기대값={name}, 실제값={metadata_name}")
    if metadata_version != version:
        raise ValueError(f"프롬프트 문서 버전이 경로와 다릅니다: 기대값={version}, 실제값={metadata_version}")

    title, body_markdown = _split_title(content[body_start:].lstrip())
    if not body_markdown:
        raise ValueError("프롬프트 문서의 실행 본문은 비어 있을 수 없습니다.")

    return PromptDocument(
        domain=domain,
        name=name,
        version=version,
        metadata=metadata,
        title=title,
        body_markdown=body_markdown,
        asset_path=asset_path,
        source_path=path,
        file_hash=sha256(content.encode("utf-8")).hexdigest()[:16],
        body_hash=sha256(body_markdown.encode("utf-8")).hexdigest()[:16],
    )


def _leading_metadata(content: str) -> tuple[dict[str, str], int]:
    metadata: dict[str, str] = {}
    position = 0
    length = len(content)
    while position < length:
        whitespace = re.match(r"\s*", content[position:])
        if whitespace is not None:
            position += whitespace.end()
        if not content.startswith("<!--", position):
            break
        end = content.find("-->", position)
        if end < 0:
            raise ValueError("프롬프트 문서 metadata 주석이 닫히지 않았습니다.")
        comment_body = content[position + 4 : end]
        metadata.update(_metadata_from_comment(comment_body))
        position = end + 3
    return metadata, position


def _metadata_from_comment(comment_body: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            entries[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for raw_line in comment_body.strip("\n").splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^\s*(?P<key>[a-zA-Z0-9_]+):\s*(?P<value>.*)$", line)
        if match is not None:
            flush()
            current_key = match.group("key")
            value = match.group("value")
            if value:
                current_lines.append(value)
            continue
        if current_key is not None:
            current_lines.append(line)
    flush()
    return entries


def _required_metadata_value(*, metadata: dict[str, str], key: str) -> str:
    if key not in metadata:
        raise ValueError(f"프롬프트 문서에 필요한 metadata가 없습니다: {key}")
    value = metadata[key].strip()
    if not value:
        raise ValueError(f"프롬프트 문서 metadata 값이 비어 있습니다: {key}")
    return value


def _split_title(content: str) -> tuple[str | None, str]:
    match = re.match(r"^# (?P<title>.+?)\s*$\n?", content, flags=re.MULTILINE)
    if match is None or match.start() != 0:
        return None, content.strip()
    title = match.group("title").strip()
    body = content[match.end() :].lstrip()
    return title, body.strip()
