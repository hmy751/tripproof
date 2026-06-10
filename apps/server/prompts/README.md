# Prompt Assets

이 폴더는 제품 경로에서 쓰는 prompt 문서와 renderer를 보관한다. prompt 문서는 실행 코드와 분리하되, 실행에 쓰인 document identity를 snapshot과 trace에 남길 수 있어야 한다.

## 디렉터리

```text
prompts/
  assets/
    answer/
      library_chat_answer/
        2026-06-10.md
    retrieval/
      source_unit_rerank/
        2026-xx-xx.md
    judge/
      answer_grounding_judge/
        2026-xx-xx.md
  runtime/
    prompt_document.py
    prompt_store.py
  renderers/
    answer/
      library_chat_answer.py
    retrieval/
      source_unit_rerank.py
    judge/
      answer_grounding_judge.py
```

- `assets/{domain}/{prompt_name}/{version}.md`는 실제 prompt 문서다.
- `domain`은 prompt가 붙는 제품/기술 관심사를 드러낸다. 예: `answer`, `retrieval`, `judge`, `extraction`.
- `runtime/`은 prompt 문서를 파일로 읽고 metadata, 실행 본문, hash, repo-relative path를 만든다.
- `runtime/`은 prompt 본문의 의미를 해석하지 않는다. `System`, `User`, rerank 기준, judge rubric, JSON output 같은 구조는 모른다.
- `renderers/`는 특정 prompt 문서를 실제 provider 입력으로 바꾼다. 필요한 section, placeholder, 출력 계약 검증은 여기에서만 다룬다.
- `{version}.md`는 prompt의 동작이 바뀔 때 새로 추가한다. 기존 version 파일을 덮어써서 의미를 바꾸지 않는다.

## Prompt 문서 계약

각 prompt version은 최소한 다음 metadata를 가진다.

```markdown
<!-- domain: answer -->
<!-- name: library_chat_answer -->
<!-- version: 2026-06-10 -->
<!-- display_name_ko: 자료함 질문 답변 -->
<!-- description_ko: 자료함 질문에 대해 제공된 source unit 근거만 사용해 답변 후보를 만든다. -->
<!--
translation_ko:
# 자료함 질문 답변 프롬프트

실행 prompt 원문을 한국어로 옮긴 전체 번역본을 둔다.
이 블록은 사람이 source에서 바로 읽기 위한 것이며 provider 입력으로 넘기지 않는다.
-->

# Library Chat Answer Prompt

<!-- 여기부터는 각 prompt family가 자유롭게 정하는 실행 prompt body다. -->
...
```

- `domain`, `name`, `version`은 경로와 같아야 한다.
- `display_name_ko`, `description_ko`는 사람이 source에서 바로 이해하기 위한 설명이다.
- `translation_ko` 주석 블록은 실행 prompt 원문을 통째로 옮긴 한국어 번역본이다.
- `# 제목`은 사람이 source에서 바로 이해하기 위한 제목이다.
- 실행 본문은 metadata 주석과 제목을 제외한 markdown body다.
- prompt 본문에 secret, API key, raw user material이나 test fixture를 넣지 않는다.
- trace/snapshot에는 prompt 전문 대신 `domain`, `name`, `version`, `fileHash`, `bodyHash`, repo-relative `assetPath`를 남긴다.
- 한글 설명 metadata와 번역 주석은 prompt source와 `PromptDocument.metadata`에서 확인한다. 기본 snapshot에는 넣지 않는다.
- 공통 runtime은 prompt body의 section 이름과 구조를 고정하지 않는다. 각 renderer가 필요한 section과 placeholder만 검증한다.
- renderer가 provider로 넘기는 값은 각 renderer가 고른 실행 본문 일부뿐이다. metadata, 번역 주석, 제목은 provider 입력에 섞지 않는다.

## 여러 prompt 추가 기준

```text
assets/
  answer/
    library_chat_answer/
      {version}.md
  retrieval/
    source_unit_rerank/
      {version}.md
  judge/
    answer_grounding_judge/
      {version}.md
```

- answer 생성 prompt는 `answer/`에 둔다.
- retrieval 보조 prompt는 `retrieval/`에 둔다. 예: source unit rerank, query rewrite.
- LLM-as-judge prompt는 `judge/`에 둔다. 예: answer grounding judge, answer quality judge.
- extraction prompt는 `extraction/`에 둘 수 있다.
- 새 prompt family를 추가할 때는 같은 이름의 renderer를 추가한다. 공통 runtime을 수정하지 않는다.

## 버전 관리

- prompt 의미, 출력 계약, grounding rule, writing rule이 바뀌면 새 version 파일을 추가한다.
- 오탈자나 주석처럼 실행 의미가 바뀌지 않는 수정만 기존 version에 할 수 있다.
- active version을 바꿀 때는 renderer/config 쪽에서 어떤 version을 쓰는지 드러나야 한다.
- product 응답 계약은 prompt file이 아니라 schema와 composer 검증 로직이 지킨다.
