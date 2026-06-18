# GOAL 2 — HFSS no-ferrite 기준값 생성 (스트림 B)

이전 GOAL2(Palace 0.16.1pf 복소 μ 패치)는 **완료·PASS**.
판정: [solver/docs/palace-0.16.1pf-review.md](solver/docs/palace-0.16.1pf-review.md) ·
증거: [solver/docs/palace-0.16.1pf-validation.md](solver/docs/palace-0.16.1pf-validation.md).

## 지금 할 일
pfsolver(GOAL1) no-ferrite와 맞댈 **HFSS 정답 기준선이 없다**(현재 HFSS 값은 ferrite-enabled).
**HFSS no-ferrite를 1회 실행해 교차검증 §3.2 표를 채운다.**

## 방법
- 입력: `src/peetsfea/data/0.3.x_fixed.toml` (design_id `0_3_7_p6561d2a5c7808f6e`, 동일 형상).
- ferrite 제거 = **TX MULL ferrite body를 non-model**: `hfss.modeler.set_object_model_state(<ferrite_name>, False)`
  (`src/peetsfea/backend/pyaedt/ssw_ports.py`에 존재). 형상은 유지, EM solve에서만 제외.
- solve: 동일 `Setup1 @ 6.78 MHz`, 4 cores, GPU.
- 추출: 기존 출력변수 `Ltx_uH`·`Lrx_uH`·`M_uH`·`k_ratio`·`Qtx_ratio`·`Qrx_ratio`·`re|im Z11/Z12/Z22`.
- 환경: `peetsfea-main/.venv`(pyaedt 0.25.1), **warm ansysedt에 attach**(자체 기동 금지). gRPC 포트 확인 후 붙기.

## 산출 / 증거
- report CSV 경로 + solve 로그.
- ferrite가 non-model임을 ledger/design에서 확인.
- **교차검증 `docs/solver-vs-hfss-crossvalidation-plan.html` §3.2 표 채움**(Z11/Z22/Z12, L1/L2, M/k, R1/R2, Q1/Q2).
- sanity: ferrite-enabled(§3.1) 대비 방향 확인. HFSS 실측은 **k↓·R↓·Q↑** 및 ferrite solid loss 제거를 보였고,
  L1/L2는 +0.39%/+0.15%로 미세 증가했다. 따라서 기존 "L↓" 기대는 엄격한 pass/fail 조건으로 쓰지 않는다.

## Acceptance
- [x] HFSS에서 TX ferrite non-model로 6.78 MHz solve 완주, report 추출.
  증거: `run/hfss_no_ferrite_nonmodel_full/Results1_Pass.csv` · `Results2_Last.csv` · `hfss_no_ferrite_nonmodel_full.log`.
- [x] §3.2의 Z/L/M/k/R/Q가 실제 HFSS no-ferrite 실측으로 채워짐(placeholder 제거).
- [x] ferrite-enabled 대비 sanity 확인.
  증거: `run/hfss_ferrite_enabled_current_full/Results1_Pass.csv`; k 0.02957→0.02942, R1/R2 0.3699/0.2362 Ω→0.3539/0.2281 Ω, Q1/Q2 653.9/900.1→686.0/933.4.
  L1/L2는 5.6772/4.9912 µH→5.6993/4.9985 µH로 기존 L↓ 기대와 달라 문서에 caveat 기록.
- [x] 증거: report CSV + 로그 + ferrite non-model 확인.
  `run/hfss_no_ferrite_nonmodel_full/ssw_aedt_port_ledger.json`에서 `tx_mull_ferrite_sheet`가 `non_model_body_names`에 있고 `model_state=false`.

이게 채워지면 GOAL1의 numeric tolerance 비교(§3.2 기준)가 열린다.
