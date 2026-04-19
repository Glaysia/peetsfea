---
title: Sub-Agent Spawn Policy
created: 2026-04-19 @ 14:50
updated: 2026-04-19 @ 18:42
tags:
  - governance
  - agents
---

# Sub-Agent Spawn Policy

이 문서는 이 저장소에서 서브에이전트를 생성할 때 사용할 모델 조합, 실패 시 강등 순서, 금지 패턴을 고정한다.

## Goal
- 서브에이전트 생성 시 모델 선택을 임의로 바꾸지 않는다.
- 빠른 1차 시도와 보수적인 2차 시도를 같은 규칙으로 반복 가능하게 만든다.
- 생성 시 문맥과 모델 지정 방식을 항상 명시적으로 유지한다.

## Model Allowlist
- 기본 단일 서브에이전트 생성의 1차 생성은 `gpt-5.3-codex-spark`와 `reasoning_effort="medium"` 조합만 허용한다.
- 기본 단일 서브에이전트 생성의 1차 생성이 실패했을 때만 2차 생성으로 `gpt-5.3-codex`와 `reasoning_effort="medium"` 조합을 허용한다.
- 분배 모드의 1차 생성은 `gpt-5.3-codex-spark` `medium` 에이전트 2개만 동시에 작업에 투입한다.
- 분배 모드의 1차 생성 쌍 중 하나라도 실패했을 때만 2차 생성으로 `gpt-5.3-codex` `medium` 에이전트 2개를 동시에 작업에 투입한다.
- 분배 모드에서 Spark 에이전트와 non-Spark 에이전트를 섞은 조합은 금지한다.
- 위 두 조합 외의 모델 또는 reasoning effort는 사용하지 않는다.

## Default Retry Order
1. 먼저 `gpt-5.3-codex-spark` `medium`으로 생성한다.
2. 생성 호출 또는 초기 시작이 실패하면 같은 작업을 `gpt-5.3-codex` `medium`으로 다시 생성한다.
3. 2차도 실패하면 다른 모델로 우회하지 않는다. 상위 에이전트가 직접 처리하거나, 막힌 이유를 사용자에게 보고하고 다음 결정을 받는다.

분배 모드에서는 먼저 `gpt-5.3-codex-spark` `medium` 2개를 생성한다. 이 1차 생성 쌍 중 하나라도 실패하면 Spark 쌍을 완료 조합으로 취급하지 않고, 같은 작업 분배를 `gpt-5.3-codex` `medium` 2개로 다시 생성한다. 2차 non-Spark 쌍도 실패하면 다른 모델로 우회하지 않는다.

## Distribution Trigger
사용자가 `서브에이전트규칙을 읽고 일을 분배해`라고 요청하면 분배 모드로 처리한다.

분배 모드에서는 상위제어에이전트가 먼저 이 문서를 읽고 작업을 나눈 뒤, 해당 작업에 필요한 모든 SDD 문서 수정을 완료하고 나서 아래 두 서브에이전트를 생성한다. SDD 문서 수정이 남아 있으면 서브에이전트 스폰을 시작하지 않는다.

- `gpt-5.3-codex-spark` `medium` 에이전트 2개

위 Spark 쌍 생성 중 하나라도 실패하면 두 작업 모두 `gpt-5.3-codex` `medium` 에이전트 2개로 다시 생성한다. 분배 모드에서는 Spark 1개와 non-Spark 1개를 섞어 완료 조합으로 사용하지 않는다.

두 서브에이전트는 직접 코드 작성, 테스트 작성, 리팩터링, 버그 수정 같은 주요 구현 작업을 맡는다. 상위제어에이전트는 문서 수정, SDD note 갱신, 작업 분해, 충돌 조정, 최종 통합 검토를 직접 맡는다.
- 상위 에이전트의 직접 수정 범위는 기본적으로 Markdown/SDD 문서로 제한하고, 구현 `.py` 수정은 서브에이전트에 배정한다.
- 구현 서브에이전트의 완료 조건은 담당 `.py` 또는 Python test 변경이며, Markdown-only 변경은 완료로 인정하지 않는다.

분배 모드에서도 `fork_context=true`는 금지한다. 각 서브에이전트에는 필요한 범위의 파일 경로, 책임 범위, 금지 사항, 검증 기대치를 `message` 또는 `items`로 명시한다.

서브에이전트가 최초 요청만 받고 실제 코드 작성에 착수하지 않은 채 `done`, `completed`, 또는 `awaiting instruction` 상태가 되는 경우가 많으므로, 상위제어에이전트는 이 상태를 곧바로 완료로 취급하지 않는다. 상위제어에이전트는 서브에이전트 생성 직후 최초 착수 지시를 내리고, 30초 뒤 같은 작업에 대한 두 번째 착수 지시를 `send_input`으로 연속 전달한다. 이 30초 간격 2회 지시는 `awaiting instruction` 상태를 방지하기 위한 기본 절차이며 항상 수행한다. 해당 서브에이전트의 응답과 변경 파일을 확인하고, 코드 변경이나 테스트 변경이 없으면 `send_input`으로 실제 작업 착수 지시를 다시 보낸다.

재지시에는 반드시 구체적인 구현 목표, 담당 파일 또는 모듈, 수정 금지 범위, 기대 검증 명령을 포함한다. 서브에이전트가 실제 변경을 만들었거나, 구현 불가능한 명확한 차단 사유를 보고하기 전까지는 해당 작업을 완료로 표시하지 않는다.

## Failure Definition
아래 경우는 모두 1차 생성 실패로 간주한다.

- `spawn_agent` 호출 자체가 에러로 끝난 경우
- 에이전트가 생성되지 못했거나 시작 상태로 진입하지 못한 경우
- 생성 직후 모델/도구 레벨 오류로 종료된 경우

## Context Fork Rule
- `fork_context=true` 방식은 사용하지 않는다.
- 이 저장소 규칙에서는 컨텍스트 포크 방식으로는 생성 시 모델을 명시적으로 고정 지정할 수 없는 것으로 취급한다.
- 따라서 서브에이전트 생성은 항상 `fork_context=false`로 시작한다.
- 필요한 문맥은 전체 대화 포크 대신 `message` 또는 `items`에 필요한 범위만 명시적으로 전달한다.

## Canonical Spawn Shape
기본 단일 서브에이전트 생성:

```json
{
  "agent_type": "worker",
  "fork_context": false,
  "model": "gpt-5.3-codex-spark",
  "reasoning_effort": "medium",
  "message": "<bounded task>"
}
```

실패 시에는 같은 형태를 유지하고 `model`만 `gpt-5.3-codex`로 바꾼다.

분배 모드 1차 생성:

```json
{
  "agent_type": "worker",
  "fork_context": false,
  "model": "gpt-5.3-codex-spark",
  "reasoning_effort": "medium",
  "message": "<bounded implementation task A>"
}
```

```json
{
  "agent_type": "worker",
  "fork_context": false,
  "model": "gpt-5.3-codex-spark",
  "reasoning_effort": "medium",
  "message": "<bounded implementation task B>"
}
```

분배 모드 1차 생성 쌍 중 하나라도 실패했을 때의 2차 생성:

```json
{
  "agent_type": "worker",
  "fork_context": false,
  "model": "gpt-5.3-codex",
  "reasoning_effort": "medium",
  "message": "<bounded implementation task A>"
}
```

```json
{
  "agent_type": "worker",
  "fork_context": false,
  "model": "gpt-5.3-codex",
  "reasoning_effort": "medium",
  "message": "<bounded implementation task B>"
}
```

## Invariants
- 생성 시 모델 이름을 생략하지 않는다.
- 생성 시 reasoning effort를 생략하지 않는다.
- 컨텍스트 전달은 필요한 범위만 명시한다.
- 분배 모드에서는 Spark/Spark 또는 non-Spark/non-Spark 쌍만 완료 조합으로 인정한다.
- 분배 모드에서는 첫 `done` 또는 `awaiting instruction` 상태를 실제 완료로 간주하지 않는다.
- 분배 모드에서는 상위제어에이전트가 필요한 모든 SDD 문서 수정을 완료한 뒤에만 서브에이전트를 스폰한다.
- 분배 모드에서는 서브에이전트 생성 직후와 30초 뒤에 같은 작업의 착수 지시를 두 번 연속으로 내린다.
- 기본 단일 서브에이전트 생성의 fallback은 한 단계만 허용한다.
- 다른 모델 추가는 이 문서 자체를 갱신하는 변경으로만 허용한다.
