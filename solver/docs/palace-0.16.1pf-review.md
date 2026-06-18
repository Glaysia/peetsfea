# GOAL2 review — palace 0.16.1pf 복소 μ 패치 (Claude 검수)

검수일 2026-06-18 · 대상 commit `solver/palace` `bc8c335` "Add complex permeability
material support" · 증거: `palace-0.16.1pf-validation.md`, `palace-0.16.1pf-material-contract.md`.

## 판정: **PASS** (GOAL2 M-fork acceptance 충족, caveat 1건)

mock/stub 아님 — 실제 CUDA 빌드 + 실제 GPU solve 로그로 뒷받침됨(`run/palace/goal2/` 다수 로그,
`localhost/palace` 이미지 실재, GMRES/Driven/LumpedPort 마커 확인).

### 검증한 것 (Acceptance 대응)
1. **빌드 ✓** — `peetsfea-palace:0.16.1pf` 이미지(`fork_version=0.16.1pf`,
   `source_commit=bc8c335`, `cuda_arch=86`, `palace_with_cuda=ON`), `PEETSFEA_BUILD_INFO` 기록.
2. **회귀 무파손 ✓** — no-ferrite(cylinder/cpw) 0.16.1pf vs baseline-m1 델타 `1e-11~1e-10`
   (GPU float noise). upstream 거동 보존 확실.
3. **복소 μ 물리 active + 부호 정상 ✓** — CPW terminal(LumpedPort)에서 real μ vs `MagneticLossTan=0.00218`:
   `Re(Z11) 0.56695387 → 0.56695458`(증가). **자기손실이 terminal 저항을 올림 = passive·dissipative 방향 정확**
   (μ″가 curl-curl 어셈블리에 실제로 들어감을 solve 결과로 확인).
4. **분산(PermeabilityFreq) ✓** — single-point 테이블이 동일 주파수 static `MagneticLossTan`과 일치(델타 `1e-8`).
   → dispersion 경로가 Driven loop에서 실제 적용됨.
5. **schema+docs+contract ✓** — `domains.json`/`domains.md` 확장, GOAL1 emit 계약 문서 제공
   (`Permeability`+`MagneticLossTan|PermeabilityImag`, Driven-only, freq-table는 LumpedPort).
6. **fail-fast 가드 ✓(가산점)** — freq-dependent material + WavePort 조합을 명시 거부
   (wave-port는 static material만 쓰므로 misleading solve 방지). 좋은 엔지니어링.

### 코드 구조 (앞선 diff 검토)
`materialoperator`에 `mat_muinv_imag` 텐서 + `HasMagneticLoss()`/`GetDispersiveMaterialProperties(ω)`,
`spaceoperator`의 `AddImagStiffnessCoefficients`가 `GetInvPermeabilityImag()`를 복소 시스템 행렬
(real/imag, `a0` 분배)에 더함. upstream의 복소 ε 패턴을 μ로 대칭 확장 — 정석적이고 회귀 위험 낮음.

## Caveat (비차단, 다음 단계로)
- 손실 효과 **크기가 매우 작음**(Re Z 상대변화 ~1e-6). tanδ_m=0.00218 + 테스트 형상이라 물리적으로 그럴듯하나,
  **정량적 HFSS 대조는 아직 없음**. GOAL2 acceptance는 "방향 정합"만 요구하므로 통과지만,
  실제 SSW(MULL ferrite) 설계점에서 R/Q가 HFSS ferrite 값과 정량 일치하는지는
  **GOAL1↔GOAL2 통합(ferrite 단계)** 에서 확인해야 한다.
- ferrite-cylinder 케이스는 델타 ≈0(형상상 ferrite-H 중첩이 작음). CPW terminal 케이스가 유효 증거.

## 결론
GOAL2 M-fork는 **명세 기준 done**. 0.16.1pf 포크가 복소 μ(자기손실)+분산을 실제로 풀고, no-ferrite
회귀를 깨지 않으며, GOAL1이 ferrite config를 emit할 contract를 제공한다. 남은 건 GOAL1과 합쳐
실제 설계점에서 HFSS ferrite 수치와 정량 교차검증하는 것(별도 단계).
