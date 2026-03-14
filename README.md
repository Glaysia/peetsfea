# peetsfea

TOML 스펙을 입력으로 받아 HFSS(AEDT)용 설계를 결정론적으로 생성하는 Python 프로젝트다.  
핵심 목표는 "같은 스펙 + 같은 시드면 같은 결과"다.

영문 문서는 [README.en.md](README.en.md)를 참고한다.
릴리즈 노트는 `release-notes/` 폴더에서 버전별/언어별로 관리한다.

## 프로젝트 목표
- TOML 스펙 하나로 HFSS 설계 생성 과정을 표준화한다.
- 동일 스펙/버전/시드에서 같은 설계를 재현 가능하게 유지한다.
- 단일 설계 생성과 데이터셋 생성이 같은 계약 위에서 동작하도록 유지한다.

## 현재 문서 기준
- 현재 문서 정리의 기준 릴리즈는 `0.2.17`다.
- 공개 요약은 이 README가 담당하고, 세부 설계는 `PLANS/` 문서가 담당한다.
- 구현 규칙은 [AGENTS.md](AGENTS.md), 장기 원칙은 [PLANS/LONGTERM_PLAN.md](PLANS/LONGTERM_PLAN.md)를 참고한다. `PLANS/V0_2_11.md`는 0.2.11 계획 기록이다.

## 이 프로젝트가 보장하려는 것
- 입력: TOML 스펙(`examples/type1.toml`)
- 처리: 스펙 검증 + deterministic selection + HFSS 설계 생성
- 출력: HFSS 설계와 스냅샷 데이터(`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)
- `repro.toml`: realized design을 다시 실행할 수 있는 exact replay artifact
- `dataset.toml`: 최종 설계에 영향을 주는 canonical sampled owner coordinate를 담는 exact ledger artifact

## 빠른 시작
1. Python 3.12와 AEDT 환경을 준비한다.
2. 가상환경을 사용한다.
3. `run/` 기준으로 테스트를 실행한다.

```bash
cd run
../.venv/bin/pytest -q ../tests
```

기본 실행은 `entry/multi_sample.py`로 batch별 resolved TOML과 manifest를 만들고, 이어서 `entry/build.py` 또는 `entry/multi_build.py`로 `run/aedt/` 아래 AEDT를 생성한다. `entry/build_one.py`는 TOML 100개를 만든 뒤 GUI를 켠 상태로 순차 build하고, `entry/sample_one_build.py`는 같은 흐름의 1개 버전이다. 기본 스펙은 `examples/type1.toml`을 사용한다.

## 핵심 산출물
- zip 산출물은 현재 임시 비활성화 상태다.
- 실행 결과에서는 아래 4개 payload가 `RunResult` 스냅샷으로 유지된다.
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json`, `geometry_metadata_<design_id>.json`은 기본 비활성이다(옵션으로만 생성).

## 0.2.17 기준 큰 계약
- sampling ownership은 canonical owner 기준으로만 관리한다.
- alias/derived path는 독립 sampled dimension으로 세지지 않는다.
- `dataset.toml`은 `coil_groups[*].count_*` 같은 inline sampled owner도 포함하고, derived alias와 fixed field는 제외한다.
- `dataset.toml`과 `repro.toml`은 서로 다른 역할을 가지며, replay safety는 둘의 대응 관계로 관리한다.
- `design_id`의 마지막 두 조각은 서로 다른 의미다: `design_unique_hash`는 realized design identity, `toml_space_hash`는 원본 `source.toml` sampling space identity다. `retry_attempt`도 파일명 suffix에 반영된다.
- ferrite는 전역 `ferrite.present` 플래그 하나로만 제어하고, RX/TX 모두 실제 코일 footprint 기준으로 배치하며 RX `2.0mm` / TX `2.0mm` / `mu_r=500`을 기본 spec 계약으로 둔다.
- TX ferrite gap은 `ferrite.tx_gap_mm` sampled path가 소유하고, 기본 예제는 `3.1..12.0`, `count=8`이다.
- TX ferrite는 최하단 TX XY FR4 아래 그 gap을 유지해야 하며, 캡처된 TX coil copper, TX bridge object, TX port sheet object, TX FR4 sheet object와 접촉하면 안 된다.
- `coil_groups_params.{tx_dd,tx_vertical,rx_dd}.turn_count_max`는 모두 기본 `2..4` 범위를 사용하고, 런타임 상한도 `4`까지 허용한다.
- TX DD 상단 배치는 `coil_placement.tx_dd_top_clearance_ratio` sampled path가 소유하고, 기본 예제는 `0.0..0.3`, `count=10`이다. 내부 `tx_dd_top_clearance_mm`는 `tx.region.z_parts.dd_z_mm`에 대한 파생값이다.
- TX vertical 배치는 이제 sampled `coil_placement.tx_vertical_layout_mode`가 소유한다. `1`은 기존 `ZX` 모드, `2`는 새 `YZ` 모드다.
- `coil_spacing.tx_vertical_mode2_pair_spacing_ratio`는 mode 2의 RX-DD-style vertical DD pair 내부 gap을 `tx.region.outer_h_mm` 기준 `0.0..0.03`, `count=25`로 제어한다. 내부 `tx_vertical_mode2_pair_spacing_mm`는 파생값이다.
- `coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center`는 mode 2의 RX-DD-style vertical DD pair `X`를 underlying TX DD 폭의 RX-far side `70%..100%`, `count=10` 구간으로 정한다. 공개 path 이름은 유지하지만 실제 식은 `tx_dd_min_x + ratio * tx_dd_outer_x`다.
- mode 2의 `tx_vertical`은 보드당 DD pair 1개만 실현한다. 기본 예제는 `coil_groups.tx_vertical.count_range = [true, 1, 1, 1]`로 고정하고, 커스텀 spec에서 count를 더 크게 줘도 realized `selected_count`는 `1`로 clamp 된다.
- 공개 스펙에서는 기존 `coil_placement.tx_vertical_plane` path를 더 이상 받지 않고, realized plane은 내부 `selected_parameters.tx_vertical_plane`에서 `ZX` 또는 `YZ`로 파생된다.
- mode 2 (`YZ`)에는 현재 legacy `Y`-side bridge no-pierce gate를 적용하지 않는다. 그 guard는 `ZX` 계약으로만 유지한다.
- `[outputs]`는 AEDT output variable과 단일 data-table report의 SSOT다.
- 기본 `[outputs]`에는 `S22_mag_ratio`와 8개의 WPT 파생 효율 지표가 포함된다.
- `eta_*_from_*`, `eta_s21_two_sided_norm_ratio`는 normalized proxy metric이라 acceptance term이 0에 가까우면 불안정해질 수 있다.
- adaptive 기본값은 `percent_refinement=20`, `maximum_passes=13`, `minimum_converged_passes=10`, `max_delta_s=0.007` 기준으로 정리한다.
- 세부 설계는 아래 문서로 분리되어 있다.
  - [PLANS/V0_2_11.md](PLANS/V0_2_11.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00A_SAMPLING_LEDGER_AND_PREFLIGHT.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00A_SAMPLING_LEDGER_AND_PREFLIGHT.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00B_SELECTION_API_SIMPLIFICATION_AND_REFACTOR.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00B_SELECTION_API_SIMPLIFICATION_AND_REFACTOR.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00C_REPLAY_DATASET_AND_SEEDSET_CONTRACT.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00C_REPLAY_DATASET_AND_SEEDSET_CONTRACT.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_01_SPEC_AND_POLICY.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_01_SPEC_AND_POLICY.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_02_FERRITE_GEOMETRY_AND_METADATA.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_02_FERRITE_GEOMETRY_AND_METADATA.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_03_TESTS_AND_ACCEPTANCE.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_03_TESTS_AND_ACCEPTANCE.md)

## type1 참고 문서
- 설계 개요: [docs/type1.md](docs/type1.md)
- 영문 설계 개요: [docs/type1.en.md](docs/type1.en.md)

## 호환성 정책
- 장기 하위호환을 보장하지 않는다.
- 메이저/마이너 릴리즈에서 스펙 경로, 기본 동작, 산출물 계약이 변경될 수 있다.

## Authorship & Disclaimer
- 코드 생성: 이 저장소의 코드와 문서는 100% GPT-5.x Codex가 생성했다.
- 책임 범위: 코드/문서 사용으로 발생하는 문제에 대해 작성자는 보증이나 책임을 제공하지 않는다.
- 영문 문서 고지: README를 포함한 영문 문서는 AI가 생성했으며 별도 검토를 하지 않았다. 영문 문서의 정확성/완전성/적합성은 보장하지 않는다.

## 기여
아이디어/버그 제보/스펙 제안은 Issue로 받는다.
