# 빌드 & 패치 가이드 (BUILD.md)

이 문서는 **패치를 직접 적용**하는 방법과, **소스에서 패치를 처음부터 재생성**하는 방법을
모두 설명합니다. 이 저장소만 있으면(게임 롬 제외) 누구나 동일한 결과물을 만들 수 있습니다.

> ⚠️ 게임 롬은 저작권상 포함되지 않습니다. 정품 게임과 **슈코넷의 한글패치 v0.9.1**이
> 적용된 롬을 직접 준비하셔야 합니다. (원본 롬 CRC32 `82804748`, 134,217,728 bytes)

---

## A. 이미 만들어진 패치를 그냥 적용하기 (일반 사용자)

가장 간단한 방법입니다. 빌드가 전혀 필요 없습니다.

1. **xdelta3** 또는 [xdelta UI](https://www.romhacking.net/utilities/598/)를 준비합니다.
2. 원본으로 **한글패치 v0.9.1이 적용된 롬**을 지정합니다. (MD5 `7AB930182FF9D0F4C4EFC96673E112D6`)
3. 패치로 다음 중 하나를 지정합니다.
   - `patch/SRWL_K_v0.9.1_Galmuri11_IMG.xdelta` — **폰트 + 이미지(권장)** → 결과 MD5 `A6FF7A389EF7AA1E4DB146E59755E8C1`
   - `patch/SRWL_K_v0.9.1_Galmuri11.xdelta` — 폰트만 → 결과 MD5 `36ADDB073C1223510B2BA48B16427DF6`

명령줄:
```bash
xdelta3 -d -s "SRWL_K_v0.9.1.nds" patch/SRWL_K_v0.9.1_Galmuri11_IMG.xdelta "SRWL_Galmuri11_IMG.nds"
```

적용 후 결과물 MD5가 위와 일치하면 정상입니다.

---

## B. 소스에서 패치를 처음부터 재생성하기 (개발자 / 수정하려는 분)

### 준비물
- **Python 3.9+**
- **Pillow**: `pip install pillow`  (또는 `pip install -r requirements.txt`)
- **xdelta3** (선택; 최종 `.xdelta`를 만들 때만 필요. 없으면 롬만 생성)
- **한글패치 v0.9.1 적용 롬** (입력)
- 한글 폰트:
  - **갈무리11** — `fonts/Galmuri11.ttf`로 저장소에 포함되어 있음 (SIL OFL 1.1)
  - **바탕(Myeongjo)·굴림(Gothic)** — 시나리오 제목/판권/정신기 축소자에 사용.
    Windows에서는 시스템 폰트를 자동 사용합니다. 다른 OS에서는 아래 환경변수로 지정하세요
    (지정하지 않으면 그 부분만 렌더가 달라지며, 배포된 xdelta는 Windows 폰트로 빌드되었습니다).

### 실행
```bash
# 1) 입력 롬 경로 지정
#    Windows(PowerShell):  $env:SRWL_SRC_ROM = "C:\path\to\SRWL_K_v0.9.1.nds"
#    macOS/Linux:          export SRWL_SRC_ROM=/path/to/SRWL_K_v0.9.1.nds
# 2) (다른 OS) 대체 폰트 지정 — 선택
#    export SRWL_BATANG=/path/to/AnyKoreanMyeongjo.ttf
#    export SRWL_GULIM=/path/to/AnyKoreanGothic.ttf
# 3) 빌드
python tools/build_all.py
```

결과물은 `build/` 아래에 생성됩니다:
- `build/SRWL_Galmuri11.nds` — 폰트만 적용 롬 (MD5 `36ADDB07…`)
- `build/SRWL_Galmuri11_IMG.nds` — 폰트+이미지 최종 롬 (MD5 `A6FF7A38…`)
- xdelta3가 PATH에 있으면 `build/*.xdelta`도 함께 생성

빌드가 끝나면 콘솔에 각 롬의 MD5가 출력됩니다. 위 값과 같으면 완전히 동일하게 재현된 것입니다.

### 환경변수 요약
| 변수 | 기본값 | 설명 |
|---|---|---|
| `SRWL_SRC_ROM` | `./source/SRWL_K_v0.9.1.nds` | 입력 롬(v0.9.1 적용본) 경로 |
| `SRWL_BUILD_DIR` | `./build` | 생성물 출력 폴더 |
| `SRWL_BATANG` | `C:\Windows\Fonts\batang.ttc` | 한국어 명조/세리프 폰트 |
| `SRWL_GULIM` | `C:\Windows\Fonts\gulim.ttc` | 한국어 고딕 폰트 |

---

## C. 번역·이미지를 수정하려면

수정 후 `python tools/build_all.py`만 다시 실행하면 됩니다. 각 데이터/스크립트 위치:

| 대상 | 파일 | 수정 방법 |
|---|---|---|
| 시나리오 제목 55개 | `tools/titles_ko.json` | `"3287": ["제1화", "부제…"]` 형태로 편집 |
| 정신기·스킬 명칭 | `tools/build_spirits4.py` (`SPIRITS`, `SKILLS` 딕셔너리) | 값 문자열 수정 |
| 전투 표시 라벨 | `tools/build_arc05.py` (`LABELS`) | 값 문자열 수정 |
| 전투 HUD 사전 단어 | `tools/build_hud.py` (`SHEETS`) | 값 문자열 수정 (좌표는 그대로) |
| 오프닝 텍스트 | `tools/build_intro.py` (`LINES`) | 줄 단위 수정 |
| 판권 화면 | `tools/build_credits.py` (`SCREENS`) | 줄 단위 수정 |
| 시간 경과 카드 | `tools/build_intro.py`/`build_titles.py` 참조 | — |
| 표준 용어 대응표 | `tools/terms_ko.py` | 참고용 SRW 용어 사전 |

폰트를 다른 것으로 바꾸려면 `tools/config.py`의 `GALMURI` 경로를 바꾸세요.

---

## 리포지토리 구조
```
├─ README.md                     개요·적용법·크레딧
├─ BUILD.md                      (이 문서) 빌드/수정 가이드
├─ ORIGINAL_PATCH_readme.txt     원 한글패치(슈코넷) readme 원문
├─ requirements.txt              Python 의존성 (pillow)
├─ patch/                        미리 만들어진 xdelta 패치
│   ├─ SRWL_K_v0.9.1_Galmuri11_IMG.xdelta   폰트+이미지
│   └─ SRWL_K_v0.9.1_Galmuri11.xdelta       폰트만
├─ fonts/
│   ├─ Galmuri11.ttf             본문 폰트 (SIL OFL 1.1)
│   └─ Galmuri11_OFL.txt         폰트 라이선스
├─ images/                       비교·미리보기 PNG
└─ tools/                        전체 빌드 파이프라인 (Python)
    ├─ config.py                 경로 설정 (환경변수로 오버라이드)
    ├─ build_all.py              전체 파이프라인 오케스트레이터
    ├─ (폰트) blz.py blz_enc.py blz_fit.py build_font.py build_rom.py ecd.py
    ├─ (이미지 공용) imglib.py compose.py kredraw.py rebuild.py
    ├─ (이미지 빌드) build_titles.py build_spirits4.py build_arc05.py
    │                build_intro.py build_credits.py build_hud.py
    │                add_area.py fix_crit_scr.py assemble_images.py
    ├─ verify_rom.py             완성 롬에서 리소스 되읽어 렌더(독립 검증)
    └─ (번역 데이터) titles_ko.json terms_ko.py
```

---

## 파이프라인 개요 (build_all.py가 실행하는 순서)
1. `blz.py` — 소스 롬에서 arm9 추출 + BLZ 압축 해제
2. `build_font.py` — arm9에 한글 2,350자(갈무리11) 삽입
3. `blz_fit.py` — arm9를 원본과 동일 크기로 재압축
4. `build_rom.py` — 폰트 롬 생성 (`SRWL_Galmuri11.nds`)
5. `build_credits.py` — 시나리오 제목·시간카드·오프닝·판권 화면 리소스 생성
6. `build_spirits4.py` — 정신기 발동 컷인
7. `build_hud.py` — 전투 HUD 사전 시트·크리티컬 (세이브/지형문자는 원본 유지)
8. `add_area.py` — 월드맵 지역명
9. `build_arc05.py` — 전투 표시 라벨
10. `fix_crit_scr.py` — 크리티컬 배너 잔여 조각 제거(SCR#10 리맵)
11. `assemble_images.py` — 폰트 롬 + 모든 이미지 리소스를 합쳐 최종 롬 생성

빌드 후 `python tools/verify_rom.py` 를 실행하면 **완성된 롬에서 리소스를 직접 되읽어** 제목·시간카드·정신기·전투 라벨을 PNG로 렌더합니다(`build/out/final_verify.png`). 빌드 중간 데이터가 아니라 롬에 실제로 들어간 내용을 확인하는 독립 검증입니다.

기술적 배경(폰트 셀 포맷, ECD/BLZ 압축, 타일맵 구조 등)은 README의 "기술 정보" 참조.
