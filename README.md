# peetsfea

TOML 스펙을 입력으로 받아 HFSS(AEDT)용 설계를 결정론적으로 생성하는 Python 프로젝트다.  
핵심 목표는 "같은 스펙 + 같은 시드면 같은 결과"다.

영문 문서는 [README.en.md](README.en.md)를 참고한다.
릴리즈 노트는 `release-notes/` 폴더에서 버전별/언어별로 관리한다.

## 프로젝트 전체 목표
- TOML 스펙 하나로 HFSS 설계 생성 과정을 표준화한다.
- 동일 스펙/버전/시드에서 항상 같은 결과가 나오게 만든다(결정론).
- 단일 설계 생성을 넘어 배치 실행과 데이터셋 생성까지 같은 계약으로 확장 가능하게 유지한다.

## 이 프로젝트가 하는 일
- 입력: TOML 스펙(`examples/type1.toml`)
- 처리: 스펙 검증 + 파라미터 선택 + HFSS 설계 생성
- 출력: `0.2.8` 기준 zip 산출물(`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)

## type1 설계 개요
- `type1`은 TV/벽면 환경 IPT 기준에서 TX(`tx_dd`, `tx_vertical`)와 RX(`rx_dd`) 코일/PCB 배치를 생성하는 기본 설계다.
- 기본 실행 결과는 HFSS 설계 + `0.2.8` zip 산출물 계약(`aedt/repro/dataset/source`)으로 정리된다.
- 필수 제약/토폴로지 규칙은 `spec_version = "0.2.8"` 기준으로 고정된다.
- 상세 설명: [docs/type1.md](docs/type1.md)

## 빠른 시작
1. Python 3.12와 AEDT 환경을 준비한다.
2. 가상환경을 사용한다.
3. `run/` 기준으로 테스트를 실행한다.

```bash
cd run
../.venv/bin/pytest -q ../tests
```

기본 실행 예시는 `run.py`, 기본 스펙은 `examples/type1.toml`을 사용한다.

## 0.2.8 출력 계약(중요)
- 기본 산출물 단위는 `<design_id>.zip`이다.
- zip 내부는 아래 4개 파일로 고정된다.
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json`, `geometry_metadata_<design_id>.json`은 기본 비활성이다(옵션으로만 생성).

## 호환성 정책
- 장기 하위호환을 보장하지 않는다.
- 메이저/마이너 릴리즈에서 스펙 경로, 기본 동작, 산출물 계약이 변경될 수 있다.

## Authorship & Disclaimer
- 코드 생성: 이 저장소의 코드는 100% GPT-5.x Codex가 생성했다.
- 책임 범위: 코드/문서 사용으로 발생하는 문제에 대해 작성자는 보증이나 책임을 제공하지 않는다.
- 영문 문서 고지: README를 포함한 영문 문서는 AI가 생성했으며 별도 검토를 하지 않았다. 영문 문서의 정확성/완전성/적합성은 보장하지 않는다.

## 기여
아이디어/버그 제보/스펙 제안은 Issue로 받는다.
