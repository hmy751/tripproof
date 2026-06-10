# 답변 Prompt Assets

이 폴더는 answer 생성에 쓰는 prompt asset을 보관한다. prompt는 실행 코드와 분리하되, 실행에 쓰인 asset identity를 snapshot과 trace에 남길 수 있어야 한다.

## 디렉터리

```text
prompts/
  loaders/
    markdown_prompt_asset.py
    llm_prompt_file_loader.py
    library_chat_answer_prompt.py
  llm/
    {prompt_name}/
      {version}.md
```

- `loaders/`는 저장된 prompt file을 읽고 product path에서 사용할 prompt를 선택하는 코드다.
- `markdown_prompt_asset.py`는 markdown prompt file을 `PromptAsset`으로 읽는 공통 parser/identity 로직이다.
- `llm_prompt_file_loader.py`는 `llm/` 아래 versioned prompt file을 찾는 loader다.
- `library_chat_answer_prompt.py`는 Library Chat answer composer가 사용할 active prompt와 필요한 section/placeholder를 정한다.
- `llm/`은 LLM provider에 전달되는 prompt asset을 둔다.
- `{prompt_name}`은 product path에서 쓰는 안정적인 이름이다. 예: `library_chat_answer`.
- `{version}.md`는 prompt의 동작이 바뀔 때 새로 추가한다. 기존 version 파일을 덮어써서 의미를 바꾸지 않는다.

## Asset 계약

각 prompt version은 최소한 다음 metadata를 가진다.

```markdown
<!-- name: library_chat_answer -->
<!-- version: 2026-06-10 -->
<!-- display_name_ko: 자료함 질문 답변 -->
<!-- description_ko: 자료함 질문에 대해 제공된 source unit 근거만 사용해 답변 후보를 만든다. -->
<!--
translation_ko:
실행 prompt 원문을 한국어로 옮긴 전체 번역본을 둔다.
이 블록은 사람이 source에서 바로 읽기 위한 것이며 LLM 입력으로 넘기지 않는다.
-->

# 자료함 질문 답변 프롬프트
```

- `name`은 폴더 이름과 같아야 한다.
- `version`은 파일명과 같아야 한다.
- `display_name_ko`, `description_ko`는 사람이 source에서 바로 이해하기 위한 설명이다.
- `translation_ko` 주석 블록은 실행 prompt 원문을 통째로 옮긴 한국어 번역본이다.
- placeholder는 `{{placeholder_name}}` 형식으로 명시한다.
- prompt 본문에 secret, API key, raw user material이나 test fixture를 넣지 않는다.
- trace/snapshot에는 prompt 전문 대신 `name`, `version`, `category`, `contentHash`, repo-relative `assetPath`를 남긴다.
- 한글 설명 metadata는 prompt source와 `PromptAsset.metadata`에서 확인한다. 기본 snapshot에는 넣지 않는다.
- prompt body의 section 이름과 구조는 전역 README가 고정하지 않는다. 각 prompt family의 loader가 필요한 section과 placeholder만 검증한다.
- loader가 LLM provider로 넘기는 값은 각 prompt family가 고른 section뿐이다. metadata, 번역 주석, 제목은 prompt 입력에 섞지 않는다.

## 버전 관리

- prompt 의미, 출력 계약, grounding rule, writing rule이 바뀌면 새 version 파일을 추가한다.
- 오탈자나 주석처럼 실행 의미가 바뀌지 않는 수정만 기존 version에 할 수 있다.
- active version을 바꿀 때는 loader/config 쪽에서 어떤 version을 쓰는지 드러나야 한다.
- product 응답 계약은 prompt file이 아니라 schema와 composer 검증 로직이 지킨다.
