# 시화 조력발전소 디지털트윈 — Omniverse 구현

WebGL(Three.js) 데모(이 저장소의 `index.html`)를 **NVIDIA Omniverse / OpenUSD + RTX**로 재구현.
절차적 모델링 대신 **실 CAD(`Layout.usd`, 45,812 prim)를 히어로**로 참조하고,
시화 조력발전소 실사·구글맵·공개자료를 대조 검증해 **방조제·301호선 도로·수문·시화나래 전망대**를
실제 배치에 맞게 모델링한 뒤, 소스 빌드한 **USD Composer**(kit-app-template) 위에서
**단류식 창조발전 조석 시뮬레이션**을 RTX로 실시간 구동합니다.

## 데모 영상
- [발전 — 바다→호소 통수](../media/sihwa_omniverse_gen.mp4)
- [배수 — 호소→바다 방류](../media/sihwa_omniverse_sluice.mp4)
- 정적 렌더: [서해측 전면](../media/sihwa_omniverse_render.png) · [탑다운(배치검증)](../media/sihwa_omniverse_topview.png)

## 다른 PC에서 열기 (요약)
실 CAD(`Layout.usd` 112MB 등)는 GitHub 100MB 제한 때문에 원본 그대로는 올릴 수 없어,
**[`cad_source/Sihwa_USD_Package.zip`](cad_source/Sihwa_USD_Package.zip)** (59MB, 압축)에 담았습니다.
`siwha_env.py`는 **자기 파일 위치를 기준으로 `Layout.usd`를 자동으로 찾으므로**, 압축만 풀면
경로 수정 없이 바로 동작합니다. 상세한 단계별 설치 가이드(kit-app-template 빌드부터)는
zip 안의 **`SETUP_README.txt`**를 참고하세요. 요약:

```powershell
# 1) USD Composer 앱 빌드 (최초 1회)
git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git
cd kit-app-template
$env:PYTHONUTF8 = "1"                 # 한국어(cp949) Windows 필수
.\repo.bat template new               # Application → USD Composer 선택, 나머지 기본값
.\repo.bat build

# 2) 이 zip을 아무 폴더에나 압축 해제

# 3) 실행
$env:PYTHONUTF8 = "1"
$rel = "<1단계 경로>\_build\windows-x86_64\release"
& "$rel\kit\kit.exe" "$rel\apps\<1단계에서 만든 이름>.kit" --exec "<2단계 경로>\siwha_env.py"
```
준비물: Windows 10/11 · NVIDIA RTX GPU(드라이버 ≥551.78) · Git · 인터넷(빌드 시 + **실행 중**에도
필요 — 하늘/수목/바위를 NVIDIA 콘텐츠 서버에서 실시간으로 불러옵니다). Visual Studio 불필요.

## 구성 파일
| 파일 | 내용 |
|---|---|
| **`siwha_env.py`** | **메인.** CAD 참조(축치환 재배향·접지) + 실측 환경(방조제·301호선·수문·전망대·수면) + 조석 물리 시뮬 + 물살/파도 애니메이션 + HUD + 크레인/게이트 리깅 |
| `place_cad.py` | CAD 배치(축/스케일) 검증용 |
| `cad_source/Sihwa_USD_Package.zip` | 실 CAD(`Layout.usd` 등 8개 USD) + 스크립트 + 설치 안내 |
| `WEBGL_TO_OMNIVERSE_SPEC.md` | WebGL(index.html) 원본 전수 분석 스펙 — 좌표계·물리식·상태기계·애니메이션 |

## 구현 내용
- **실 CAD 히어로**: `Layout.usd`(Z-up, 긴축=방조제방향 472m)를 명시적 축치환 행렬로 Y-up 씬에 정렬·접지. 수차 10기·통수로·드래프트튜브·갠트리 크레인·수문 일부가 CAD 원본 그대로 렌더.
- **실측 배치 검증**(실사진·구글맵 대조): 발전동(−X)–전망대 곶(바다측, −Z)·수문 8문(+X)·방조제가 실제 순서·방향과 일치하도록 교정. 301호선 도로가 CAD 도로와 정렬되어 끊김 없이 관통. 좌우 이음부는 사다리꼴 제방(마루+사석사면)으로 윙월을 감싸 자연스럽게 연결. 양끝 물방울형 도류제 섬 + 큰가리섬 추가.
- **시화나래 달전망대**: 테이퍼 샤프트 + UFO형 유리 포드 + 녹색 링 + 항공비콘, 실사진 특징 반영.
- **크레인·수문 동작**: CAD 진품 크레인(`CR001`)을 리깅해 발전동-수문 접합부를 실제로 왕복 이동. 수문 게이트 1문(`SluiceGate`) 리깅해 배수 시 인양.
- **조석 발전 시뮬**(단류식 창조발전): 4단계 상태기계(낙차축적→발전→만조정체→배수), `sea=평균+진폭·sin(2πt/12.42h)`, 터빈출력 `P=η·ρ·g·Q·H`(정격 25.4MW×10=254MW), 체적수지 호소수위, HUD 실시간 표시(출력·낙차·통수량·수위·가동대수·누적·연환산 552GWh 목표).
- **물 애니메이션**: 원거리 평면 + 근거리 파도 그리드(정점 변위로 출렁임), 발전 중 터빈 통수 물살(바다→호소)·배수 중 수문 방류 물살(호소→바다) 파티클, 수위가 조석에 맞춰 실시간 승강.
- **NVIDIA Omniverse 콘텐츠 활용**: HDRI 하늘(Skies/Clear), 립랩 사석(Vegetation/Rocks), 수목(Vegetation/Trees) — `https://omniverse-content-production.s3.us-west-2.amazonaws.com/Assets/...` 참조(cm 단위이므로 스케일 보정 필요, README 하단 참고).

## 조정 파라미터 (`siwha_env.py` 상단)
`GAP_HALF`·`SEAWALL_END`·`SEAWALL_ZW`(방조제 치수), `DECK_Y`(도로 높이), `WATER_Y`(평균 수위),
`GATE_X0`·`PROM_X`(수문/전망대 X 위치), `HDRI`·`TREES`(NVIDIA 콘텐츠 경로).
`Sim.speed`(재생 속도), `Sim.startHead/stopHead/nTurb/nGate/amp`(운전 변수).

## 알려진 한계 / 다음 단계
1. **수차 회전 애니메이션 미구현** — CAD 러너가 벌브 하우징에 병합돼 있어 개별 리깅 불가 판정(시도 후 되돌림). 노출형 스타일 러너를 절차적으로 오버레이하면 가능.
2. **수문 게이트 8문 중 1문만 리깅** — 나머지 7문은 CAD 프리즘 명명 불일치로 자동 탐지 실패.
3. HUD 한글 미지원(omni.ui가 CJK 글리프 래스터 불가) — 현재 영문 라벨.
4. OmniSurface/MDL 물(반사·굴절·caustics), PathTracing 극사실 렌더는 미시도.
5. 개시낙차 최적화 스윕 UI, K-TOP/SCADA 실데이터 바인딩은 WebGL 버전에만 존재.
