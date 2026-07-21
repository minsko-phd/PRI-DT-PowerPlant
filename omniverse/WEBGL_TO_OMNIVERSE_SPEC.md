# Sihwa Tidal Power Plant — WebGL(Three.js) → Omniverse/OpenUSD 이식 스펙

> 출처: `PRI-DT-PowerPlant/index.html`(Three.js 단일파일, 2035줄) 전수 분석.
> 목적: WebGL 데모의 지오메트리·물리·애니메이션·HUD를 NVIDIA Omniverse USD로 동일 재현(그래픽은 RTX로 대폭 상향).
> 관련 자산: `C:\Users\user\AIWorkspace\siwha_usd\Layout.usd`(실 CAD 수차, 45,812 prim), 빌드된 앱 `siwha.tidal_composer`(kit-app-template).

---

## 2. 좌표계 & 스케일 (먼저 읽을 것)
- **단위: 미터.** Y-up, right-handed(Three.js 기본).
- 축: `X` = 방조제 길이방향, `Z` = 방조제 횡단(**바다 = −Z, 호소 = +Z**), `Y` = 표고.
- 원점: 방조제 중앙(`BZ=0`), X=0 = 240m 방조제 중앙. 도로 상판 top `deckY=9`. 수위 기준(평균해수면) `Y=5.0`.
- 범위: 방조제 X −120…+120(길이 240), 방조제 깊이 Z −13…+13(폭 26). 바다면 Z≈−832…−12, 호소면 Z≈+12…+832. 해저면 2000×2000 @Y=−9. 하늘구 반경 2400. 최고점: 전망대 비콘 Y=71.
- 카메라: `Perspective(fov 48, near 0.5, far 5000)`. Fog `FogExp2(0xaecadb, 0.0014)`, `ACESFilmic exposure 1.08`, `PCFSoftShadow`.

레이아웃 상수:
```
BARRIER_LEN=240  BARRIER_W=26  BZ=0  deckY=9
TURB_SPAN=120    GATE_SPAN=96
turbX0 = -112    gateX0 = 16
TURB_PITCH = 12  GATE_PITCH = 12
```
좌→우(+X): **발전동(수차 10기, X −106…+2) → 전망대(X≈8) → 수문(8문, X +22…+106)**.

---

## 1. 지오메트리

### 1.1 재질 팔레트 (MeshStandardMaterial)
| 이름 | Hex | rough | metal | 비고 |
|---|---|---|---|---|
| matConcrete | 0xd8d2c4 | 0.88 | 0 | 밝은 콘크리트 |
| matConcreteD | 0xb6b0a1 | 0.92 | 0 | 어두운 콘크리트(수몰부) |
| matSteel | 0x5a6873 | 0.5 | 0.6 | |
| matSteelD | 0x36414b | 0.6 | 0.5 | |
| matGate | 0xc23b22 | 0.5 | 0.45 | 적색 수문 |
| matYellow | 0xf2b134 | 0.6 | 0 | 크레인/모터 |
| matWhite | 0xeef2f4 | 0.6 | 0 | 전망대 |
| matGlass | 0x24506b | 0.18 | 0.5 | 유리/포드 |
| matRock | 0x8f897c | 1.0 | 0 | flatShading 사석 |
| bladeMat | 0x95a8b7 | 0.35 | 0.7 | DoubleSide |
| glow ring | color 0xffd34d / emissive 0xffb020 | | | intensity 0→~1 애니 |
| Sea water | 0x3a6f8a | 0.08 | 0.4 | transp 0.82 |
| Lake water | 0x1f9e8f | 0.08 | 0.4 | transp 0.5 |
| Seabed | 0x6f6447 | 1.0 | 0 | |

### 1.2 방조제
- 제방 3개 `dyke(xc,w)`: 메인박스 `w×10×26`(matConcrete) @y=4 + 사석 toe `w×6×7`(matConcreteD) @z=−15.4, rot.x=0.5. 호출 xc=−120,+8,+120, w=16.
- 도로상판 `240×0.6×9`(matSteelD) @y=9.3. 중앙선 대시 `4×0.05×0.35`(0xefe7cd) X=−114부터 10m 간격 @y=9.62. 난간2 `240×0.7×0.15`(matSteel) @y=10, z=±4.4.

### 1.3 발전동
- 상부블록 `126×7×30`(matConcrete) @(−52,12.5,0). 수몰매스 `126×14×30`(matConcreteD) @(−52,−3,0).
- 갠트리 레일2 `126×0.4×1` @y=16.1,z=±7; 포털다리 `1×5×1` @X=−90; 황색 거더 `1.2×1.2×16` @y=20.8.
- 지붕 스카이라이트 리브×10 `10×1.6×31`(matConcreteD) @y=16.3(수차 bay마다). 측창×10 `8×3×0.3`(matGlass) @y=12.5,z=−15.2.
- LG PRI 사인보드: 양면 plane `30×8.6` @(−34,22,±0.35), 텍스처=LG로고+"PRI/DIGITAL TWIN · K-water 시화호", emissive 0x444444@0.12.

### 1.4 벌브 수차 10기 (핵심)
루프 i=0..9, 중심 **x = −112 + 12·(i+0.5)** → X=−106,−94,−82,−70,−58,−46,−34,−22,−10,+2. 피치 12m. 각 유닛 축=Z방향(바다→호소). 유닛당:
- 흡출관: `Cylinder(rT 2.4, rB 2.4, h 31, 20seg, open)` matSteelD, rot.x=π/2 @(x,1.0,0) → Z −15.5…+15.5. **러너 보어 반경 2.4m(Ø4.8m)**.
- 흡입림: `Torus(2.5,0.35,10,24)` matSteel @(x,1.0,−15.5).
- 러너(4엽) Group: 허브 `Sphere(0.9)` + 4블레이드 `Box(0.18,2.0,0.9)`(bladeMat) y=1.1,rot.z=0.5, arm rot.x=b·π/2. Group rot.x=π/2 @(x,1.0,−2). 로컬 Z축 회전.
- 노출 흡입팬(5엽, 눈에 띄는 프로펠러) Group: 노즈 `Cone(0.7,1.6)` z=−0.8; 5블레이드 `Box(0.14,2.1,0.8)` y=1.2,rot.z=0.6, arm rot.z=b·2π/5 @(x,1.0,−14.6). 로컬 Z 회전.
- 글로우링 `Torus(2.45,0.18,8,24)` emissive @(x,1.0,−15.3).
- 유동 파티클: 44 Points, 0xffe07a, size 0.8, additive.

> 고정밀 "CAD" 벌브(Ø7.5m 러너)는 §1.11 VTS 리그(정비훈련 전용). 운전중 플랜트 재현은 위 X위치 10기 모델링, VTS 벌브를 고정밀 레퍼런스로 사용. **실제로는 `siwha_usd\Water_Turbine.usd`가 이 고정밀 CAD임.**

### 1.5 수문 8문
`gateWidth=7.92`; 이동 **gateShutY=−2.0(닫힘) → gateOpenY=7.8(열림)**, 9.8m 수직.
- 하부매스 `100×10×26`(matConcreteD)@(64,−4,0); 문턱 `100×1.6×26`(matConcrete)@(64,−2.2,0).
- 게이트 i=0..7 중심 **x=16+12·(i+0.5)** → 22,34,46,58,70,82,94,106:
  - 피어 `4.08×17×27`(matConcrete)@(16+12i,5.5,0); i=7에 X=112 마감피어 추가.
  - 강재 게이트(Y이동) `7.92×8×0.9`(matGate)@(x,−2.0,−11.5); 리브5 `7.92×0.5×0.2`(matSteelD) local y=−3..3 step1.5, z=0.55.
  - 권양 트러스 `7.128×7×0.6`(matSteel)@(x,13.5,−11.5); 권양모터 `2.4×1.6×2.4`(matYellow)@(x,17,−11.5).
  - 배수 파티클: 40 Points, 0xcdeeff, size 0.8, additive.

### 1.6 시화나래 전망대 (base tx=8,tz=−3, 총 ≈71m)
문화관 base `20×8×16`(matWhite)@(8,0,5); 지붕 `20×0.5×16`@y=4.3. 샤프트 `Cyl(top1.6,bot3.6,h62,18)`(matWhite)@(8,31,−3) 테이퍼. 리브6 `0.3×62×0.3`(matSteel) 반경2.4. 전망포드 `Cyl(5.2,4.0,5,20)`(matGlass)@(8,56,−3); 데크 `11×0.5×11`@y=53.3; 지붕콘 `Cyl(0.6,5.6,2.4,20)`@y=59.7. 마스트 `Cyl(0.18,0.18,10)`@y=65.5; 항공비콘 `Sphere(0.6)` 0xff3b30 emissive 0xff2018@1.2 @(8,71,−3) 펄스.

### 1.7 수면
- `waterMesh`: `Plane(1800,820,60,28)`, rot.x=−π/2, z=side·422. 바다 0x3a6f8a op0.82 @Z=−422; 호소 0x1f9e8f op0.5 @Z=+422. renderOrder 2.
- 호소 미러: `Reflector(Plane(1700,780),1024², 0x95b6b0)` @Z=+422, y=호소수위−0.6. 바다는 미러 없음.

### 1.8 지형/사석/도로
- 해저 plane `2000×2000` 0x6f6447 @Y=−9. 육지스트립 `2000×7×16` @Z≈±839.
- 사석: `InstancedMesh(Icosahedron(1.0,0), matRock, 260)` X=−120…120 step3.2, 3행 z=−15−2.4r, y=2.5−1.6r, scale 0.9–1.9. → USD PointInstancer.
- 진입로: `Tube(CatmullRom[(120,9.4,0),(150,8,18),(190,2,70),(215,0.4,150)], r4.5)` matSteelD scale.y0.12 + 램프.
- IBL: 하늘구 r2400 canvas 그라디언트(주간 #2f6395→#79add4→#d6e7f1 / 야간 #05070e→#0a1430→#16294a); 별 700 Points; PMREM 베이크.
- 조명: `Hemisphere(0xd2ebff,0x55624a,0.9)`; `Directional(0xfff2dc,1.55)`@(135,170,80), shadow 2048², frustum±260.

### 1.9 게이지
`makeGauge`: 흰폴 `Cyl(0.18,0.18,17)`, 틱9 `1.3×0.14×0.14`, emissive ring `Torus(0.85,0.2)`. 바다게이지@(−118,y,−22) 0x53b9ff; 호소게이지@(116,y,+22) 0x36e0c4. 링 Y=수위추종.

### 1.10 CCTV폴+로봇
4폴 `0.35×6.5×0.35` @X=−126,−46,+44.8,+124(z=−5.6)+적색 LED. 로봇 PR-01(황색몸체 `1.7×0.75×1.15`+4휠+시안비콘) 상판 y≈9.6 순찰.

### 1.11 VTS 벌브 리그(고정밀 레퍼런스)
정비훈련 전용. 조립위치 T7(VTS_TX=−34), 정비베이 VTS_BAY=−138. 재질 matBulb 0x8fae9b(r0.42,m0.28) 등. 벌브바디 `Cyl(1.35,1.35,3.2)` + 캡/플랜지/콘/샤프트/노즈 + **4러너 `Box(0.45,3.1,1.55)` → Ø≈7.5m** + 가이드베어링(마모 적색→신품 녹색). 오버헤드 크레인 포함. → **`siwha_usd\Water_Turbine.usd`로 대체.**

---

## 3. 물리 & 시뮬레이션

### 3.1 플랜트 상수
```
nTurbines 10 · nGates 8 · ratedMW 25.4 · designHead 5.82
meanSea 5.0 · periodHr 12.42 · lakeArea 42e6 (42km²)
```
단류식 창조발전: 밀물(바다→호소) 발전, 썰물에 수문으로 배수.

### 3.2 조석
```
sea(t) = meanSea + amp·sin(2π·t/periodHr)   (t=시간)
rising = cos(2π·t/periodHr) > 0
head = sea − lake ;  rev = lake − sea
```
기본 amp 3.3 → 해수면 1.7…8.3m; 조차=2·amp=6.6m.

### 3.3 터빈출력 P=η·ρ·g·Q·H
```
smooth(a,b,x)=smoothstep
effH(H)=0.91·smooth(0.45,1.9,H)·(1−0.012·max(0,H−6.5))   // η peak≈0.91
turbFlow(H)=H≤0?0:min(205·√H,600)      // m³/s/터빈, cap 600
turbPow(H)=H≤0?0:min(effH(H)·1000·9.81·turbFlow(H)·H/1e6, 25.4)  // MW, cap 25.4
```
ρ=1000, g=9.81, cut-in H≈0.45, full η at H≥1.9, >6.5m derate. peak ≈254MW.

### 3.4 수문유량
```
gateFlow(rev)=rev≤0?0:min(700·√rev,1400)   // m³/s/문, cap 1400
```

### 3.5 상태기계 4단계
초기: sea=5.0, lake=2.0, state='WAIT'.
| 단계 | code | 의미 | 전이 |
|---|---|---|---|
| 1/4 | WAIT | 낙차축적,수문닫힘 | →GEN if rising&&head≥startHead; →SLUICE if !rising&&rev>0.15 |
| 2/4 | GEN | 발전,바다→호소 | →WAIT_HIGH if head<stopHead or (!rising&&head<startHead·0.6) |
| 3/4 | WAIT_HIGH | 만조정체 | →SLUICE if !rising&&rev>0.1 |
| 4/4 | SLUICE | 배수,수문개방 | →WAIT if rev≤0.05 or (rising&&head>0) |

### 3.6 적분(체적수지)
```
dtSec=dtHr·3600
GEN&&head>0: nT=max(0,nTurb−nOff); power=turbPow(head)·nT; qIn=turbFlow(head)·nT; cycE+=power·dtHr
totalMWh += power·dtHr
SLUICE&&rev>0: qOut=gateFlow(rev)·nGate
lake += (qIn−qOut)·dtSec/lakeArea
lake = clamp(lake, 0.8, 8.8)
```

### 3.7 최적화 스윕
- evalEnergy(startHead,amp): dt=0.01h, 10주기(12420스텝), 완료주기 에너지 평균(첫 주기 제외) → 정상상태 MWh/cycle.
- runSweep: startHead 0.4→4.0 step0.1(37점), best/bestSh 반환.
- 주기/일=1.932. 연간=best·1.932·365/1000 GWh, 설계목표 552.7 GWh.

---

## 4. 애니메이션
- 수면변위(정점): `z=base_z + sin(base_x·0.03+t)·0.42 + cos(base_y·0.045+t·1.3)·0.34 + sin(base_x·0.12+t·2.2)·0.12`; mesh.y=level. 호소 time·0.8.
- 터빈회전: `spin=(GEN)?0.5+head·0.22:0` rad/frame → runner.rot.z, fan.rot.z(유닛 on시). on = !offline && i<(GEN?nTurb:0).
- 터빈글로우: alarm 0xE03131 펄스; offline 회색@0.3; normal 0xffd34d intensity 0.7+0.3·sin(t·6+i).
- 터빈파티클: opacity→0.95, size=0.7+head·0.13, +Z advect speed=0.7+head·0.3, |z|=21 recycle.
- 수문: `open=SLUICE&&i<nGate`; pos+= (open?1:0−pos)·0.06; gate.y=−2+9.8·pos. 배수파티클 −Z.
- 물보라(makeSpray 220pts, gravity): 흡입포말 origin(−52,lake+0.3,+14.5) rate=min(qIn/650,8); 수문보라 origin(64,max(sea,1)+0.2,−14.5) rate=min(qOut/1100,10).
- 게이지링 Y=수위. 전망대비콘 0.5+|sin(t·2)|. sim clock: dtHr=dtReal·speed/3600.

---

## 5. HUD / 라벨
- 3D 라벨 sprite @world(−6,36,0): 상태텍스트 / 낙차 H `x.xx m`(흰) / 통수량 `Q ㎥/s`(#ffd34d) / 출력 `MW`(#7fe07a). 상태: WAIT→낙차 축적, GEN→발전 중, WAIT_HIGH→만조 정체, SLUICE→배수 중.
- 우상단 패널: power MW / powerbar(power/254·100%) / seaLv / lakeLv / head / nturb(GEN?nTurb−nOff:0)/10 / elapsed(D일 HH시간 MM분) / totMWh(≥1000시 GWh) / state.
- 우하단 성능비교: cycle MWh / daily(·1.932/1000 GWh) / annual(·365/1000 GWh) / %목표(552.7).

---

## 6. 컨트롤 (min/max/step/default)
| 라벨 | key | min | max | step | default |
|---|---|---|---|---|---|
| 발전 개시 낙차 | startHead | 0.4 | 4.0 | 0.1 | 1.0 |
| 발전 종료 낙차 | stopHead | 0.4 | 2.0 | 0.1 | 0.8 |
| 가동 터빈 수 | nTurb | 1 | 10 | 1 | 10 |
| 배수 수문 수 | nGate | 1 | 8 | 1 | 8 |
| 조석 조차 | amp | 2.4 | 4.2 | 0.1 | 3.3 (표시 v·2=6.6) |
| 재생 속도 | speed | 1 | 400 | 1 | 120 |
- 모드: 수동 / AI최적(runSweep→startHead=bestSh,stopHead=0.8,nTurb=10,nGate=8).

---

## 7. 카메라 프리셋 (position → target)
| # | 이름 | Position | Target |
|---|---|---|---|
| 0 | 조감 | (160,98,165) | (0,4,0) |
| 1 | 바다측 | (0,42,175) | (0,8,8) |
| 2 | 발전동 근접 | (100,24,30) | (−10,6,4) |
| 3 | 육지측 | (−150,60,90) | (−30,8,0) |
| 4 | 평면 | (0,185,3) | (0,0,0) |
- 시네마틱 투어: 폐곡선 CatmullRom, tourS+=dt·0.016(≈62s). pos/target 경로는 원문 §7.2.

---

## RTX/Omniverse 업그레이드 포인트 (WebGL에서 허접했던 부분)
1. **물** — Standard 평면+sine 정점변위, 호소만 저해상 Reflector. → OmniSurface/MDL water(반사+굴절+깊이흡수+caustics), flow map.
2. **물보라/포말/유동** — 단순 additive Points. → RTX 파티클/FLIP·SPH 유체, volumetric mist.
3. **터빈 블레이드** — 박스 프리미티브. → `Water_Turbine.usd` 고정밀 CAD 사용 + PBR steel/bronze MDL.
4. **글로우/비콘/사인** — post-bloom 없음. → RTX bloom + emissive MDL + 실제 area/point light.
5. **조명** — 단일 directional. → path-traced GI, area light.
6. **하늘/대기** — canvas 그라디언트+FogExp2. → physical sky/HDRI + RTX volumetric.
7. **콘크리트/사석/강재** — flat albedo. → tiled MDL(normal+AO+displacement), 사석은 USD PointInstancer.

**재현 우선순위**: §2 좌표계 + §3 상수/상태기계/최적화 정확히 일치 → 수차 10기(X −106…+2)·수문 8문(X +22…+106) 배치(피치 12) → §4대로 러너회전/게이트Y/수면Y/파티클을 동일 sim state로 구동.
