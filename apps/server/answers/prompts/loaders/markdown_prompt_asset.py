from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re


@dataclass(frozen=True)
class PromptAsset:
    category: str
    name: str
    version: str
    metadata: dict[str, str]
    sections: dict[str, str]
    asset_path: str
    source_path: Path
    content_hash: str

    def section(self, name: str) -> str:
        try:
            return self.sections[name]
        except KeyError as exc:
            raise ValueError(f"프롬프트 asset에 필요한 section이 없습니다: {name}") from exc

    def render_section(self, name: str, **values: str) -> str:
        rendered = self.section(name)
        for key, value in values.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        missing = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", rendered)))
        if missing:
            raise ValueError(f"프롬프트 렌더링에 필요한 placeholder 값이 없습니다: {', '.join(missing)}")
        return rendered

    def snapshot(self) -> dict[str, str]:
        return {
            "category": self.category,
            "name": self.name,
            "version": self.version,
            "contentHash": self.content_hash,
            "assetPath": self.asset_path,
        }


def load_markdown_prompt_asset(
    *,
    category: str,
    name: str,
    version: str,
    path: Path,
    asset_path: str,
    required_sections: tuple[str, ...] = (),
    required_placeholders: tuple[str, ...] = (),
) -> PromptAsset:
    content = path.read_text(encoding="utf-8")
    metadata = _metadata(content=content)
    metadata_name = _required_metadata_value(metadata=metadata, key="name")
    metadata_version = _required_metadata_value(metadata=metadata, key="version")
    if metadata_name != name:
        raise ValueError(f"프롬프트 asset 이름이 경로와 다릅니다: 기대값={name}, 실제값={metadata_name}")
    if metadata_version != version:
        raise ValueError(f"프롬프트 asset 버전이 경로와 다릅니다: 기대값={version}, 실제값={metadata_version}")
    sections = _sections(content=content)
    _ensure_sections(sections, required_sections=required_sections)
    _ensure_placeholders(sections, required_placeholders=required_placeholders)
    return PromptAsset(
        category=category,
        name=name,
        version=version,
        metadata=metadata,
        sections=sections,
        asset_path=asset_path,
        source_path=path,
        content_hash=sha256(content.encode("utf-8")).hexdigest()[:16],
    )


def _metadata(*, content: str) -> dict[str, str]:
    return {
        match.group("key").strip(): match.group("value").strip()
        for match in re.finditer(
            r"^<!--\s*(?P<key>[a-zA-Z0-9_]+):\s*(?P<value>.*?)\s*-->$",
            content,
            flags=re.MULTILINE,
        )
    }


def _required_metadata_value(*, metadata: dict[str, str], key: str) -> str:
    if key not in metadata:
        raise ValueError(f"프롬프트 asset에 필요한 metadata가 없습니다: {key}")
    value = metadata[key].strip()
    if not value:
        raise ValueError(f"프롬프트 asset metadata 값이 비어 있습니다: {key}")
    return value


def _sections(*, content: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## (?P<heading>.+?)\s*$", content, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group("heading").strip()
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        body = content[body_start:body_end].strip()
        if not heading:
            raise ValueError("프롬프트 asset section 제목은 비어 있을 수 없습니다.")
        if not body:
            raise ValueError(f"프롬프트 asset section 본문은 비어 있을 수 없습니다: {heading}")
        sections[heading] = body
    return sections


def _ensure_sections(sections: dict[str, str], *, required_sections: tuple[str, ...]) -> None:
    missing = [section for section in required_sections if section not in sections]
    if missing:
        raise ValueError(f"프롬프트 asset에 필요한 section이 없습니다: {', '.join(missing)}")


def _ensure_placeholders(sections: dict[str, str], *, required_placeholders: tuple[str, ...]) -> None:
    content = "\n\n".join(sections.values())
    missing = [
        placeholder for placeholder in required_placeholders if f"{{{{{placeholder}}}}}" not in content
    ]
    if missing:
        raise ValueError(f"프롬프트 asset에 필요한 placeholder가 없습니다: {', '.join(missing)}")
