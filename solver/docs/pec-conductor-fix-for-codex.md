# pfsolver HFSS-mismatch FIX — 실행 지시 (Codex)

작성: Claude, 2026-06-19. Palace 실험으로 근본 원인·fix를 **확정**했다. 이 문서대로 SSW no-ferrite Z를
HFSS order로 끌어올려라. 추측·brute-force 금지 — 아래는 실험으로 증명된 사실이다.

## 1. 확정된 근본 원인
pfsolver가 `Z11≈45–50 Ω(≈포트 R), L≈0, Z12≈0`로 붕괴한 이유 = **copper를 `solve-inside` 유한도전율
volume으로 둔 것.** Palace lumped port는 **PEC(또는 finite-conductivity surface-impedance) 도체 *경계*** 를
기대한다. solve-inside σ volume에는 포트가 conduction 전류를 못 밀어넣어 코일이 회로에서 빠진다.
- 증거: Palace `cpw` 예제도 금속 = `Boundaries.PEC`(도체 volume 없음).
- **`copper 3D solve-inside` Hard Rule을 폐기하라.** 그게 collapse의 원인이었다.

## 2. 검증된 FIX recipe (minloop, 실제 Palace 실행)
`run/claude_minloop/build_minloop.py`: PEC 사각 ribbon loop + feed-gap lumped port + vacuum box.
- 결과: `Zin = 0.0017 + j10.84 Ω`, **L = 254.6 nH** (해석 square-loop ~234 nH, 9% 일치). ✓
- 즉 **Palace `Driven` full-wave + feed-gap lumped port + PEC 도체 = 코일 인덕턴스 정확히 산출.**

핵심 config (minloop):
```jsonc
"Problem": { "Type": "Driven" },
"Domains": { "Materials": [ { "Attributes":[<air>], "Permeability":1.0, "Permittivity":1.0 } ] },
"Boundaries": {
  "PEC":        { "Attributes": [<conductor surfaces>] },
  "Absorbing":  { "Attributes": [<outer box 6 faces>], "Order": 1 },
  "LumpedPort": [ { "Index":1, "Attributes":[<gap sheet>], "Direction":"<across gap>", "R":50.0, "Excitation":1 } ]
}
```
- 포트는 **두 터미널 사이 간극을 채우는 단일 sheet**, Direction = 간극 가로지르는 방향, **단일 element**(antiparallel 2-element 금지).
- 도체는 **PEC 경계**(또는 finite-conductivity surface impedance). 도체 interior는 풀지 않는다.

## 3. 검증된 메시 recipe (thin-solid 폭발 회피)
HFSS는 solid ~1만, 공기 ~3만. gmsh conformal 메시는 0.07mm 두께·촘촘한 turn을 분해하려다 폭발(>2M).
→ **도체를 zero-thickness 시트로**, 그리고:
```python
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
gmsh.option.setNumber("Mesh.MeshSizeMin", 5~8)   # coarse seed
gmsh.option.setNumber("Mesh.MeshSizeMax", 100~150)
# Distance/Threshold field로 도체 근처만 약간 finer
```
minloop은 이 방식으로 깨끗한 메시 + 정확한 L. SSW 평면-시트도 이 방식으로 **150k tets, solve 완주**까지 됨
(`run/claude_ssw_sheet/`). HFSS처럼 coarse seed면 충분하고, 필요시 **Palace AMR**(`Solver`에 refinement, Palace native)로 turn-gap을 적응 세분.

## 4. 남은 핵심 난제 — 전체 3D 코일을 "연결된" 시트로
평면-face 시트(`run/claude_ssw_sheet/`)는 coarse하지만 **여전히 붕괴**(Z≈50Ω). 원인 두 가지를 풀어야 한다:
1. **연결성**: `occ.copy`로 copper face를 개별 복사하면 공유 모서리가 끊겨 도체가 전기적으로 분리된다.
   → 도체 시트들이 **하나의 연결된 surface**가 되게 하라(공유 모서리 병합; copy 대신 full-shell에서 한쪽 면 추출 후 fragment로 재병합, 또는 아래 옵션).
2. **완전성**: TX는 main coil(XY) + under-coil(YZ)이 **직렬**인 3D 코일이다(`GOAL.md` tx_under_coil). 단일 평면 시트는 under-coil을 빠뜨려 루프 미완성. → 전체 코일(main+under)을 포함하는 연결 surface가 필요.

### 추천 구현 순서 (쉬운 것부터)
- **(C, 추천 1순위) 도체 두께 인위적 확대 → full-shell void.** copper solid를 ~1–2mm로 두껍게(예: outer offset/dilate, 또는 STEP 생성 단계에서 copper_thickness를 임시 상향) 하면 full shell void가 **연결성 유지 + coarse-mesh 가능**. L/M/k는 도체 두께에 둔감하므로 parity 1차 통과 가능. R은 이후 보정.
- **(A) full 3D 코일 mid-surface 추출.** 가장 정석이나 gmsh로 robust하게 구현 난도 높음.
- **(B) full copper shell을 finite-conductivity surface-impedance boundary로** 두고(연결성 OK) Palace AMR로 thin-shell seed를 적응. L+R 동시. 단 thin-shell seed 메시 자체가 어려움.

(B)는 L뿐 아니라 R/skin까지 맞으므로 **최종 목표는 (B) 또는 (A)**. 빠른 parity 확인은 (C)로.

## 5. Acceptance (HFSS no-ferrite §3.2, `run/hfss_no_ferrite_fixed_full/`)
HFSS final @ 6.78 MHz: `Z11=0.280+j241.68`, `Z22=0.215+j214.66`, `Z12=0.00885+j6.489`,
`Ltx=5.673µH, Lrx=5.039µH, M=0.1523µH, k=0.02849`.
- [ ] minloop을 먼저 재현해 툴체인이 PEC 도체로 코일 L을 내는지 확인(`Zin≈j10.8`).
- [ ] SSW Z11/Z22가 HFSS order(`j240`대)로 산출(붕괴 탈출).
- [ ] L/M ±5%, |Z| ±5%, k ±10%, R ±15% (R은 finite-conductivity 도입 후).
- [ ] §4·§5 pfsolver 열 채움 + 실제 Palace 실행 증거.

## 6. 시작점 (재사용)
- `run/claude_minloop/build_minloop.py` — 검증된 PEC-loop recipe(복붙 베이스).
- `run/claude_ssw_sheet/build_ssw_sheet.py` — SSW zero-thickness 시트 + coarse 메시(150k) 베이스. 연결성/under-coil만 해결하면 됨.
- pfsolver 본체(`solver/pfsolver/src/pfsolver/{mesh,palace_config}.py`)는 copper를 volume→**PEC/impedance 경계**로 바꾸는 리팩터가 핵심.
