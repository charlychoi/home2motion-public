# home2motion — 문구만 쓰면 만들어지는 30초 모션그래픽

홈페이지·브랜드 소개 내용을 `project.json` 한 파일에 적으면,
**모션그래픽 영상(mp4, 1920×1080, 30fps)** 과 **배경 효과음악**을 자동으로 만들어 주는 도구입니다.
이미지·영상·음원 샘플이 필요 없고, 음악은 코드로 직접 합성하므로 저작권 걱정이 없습니다.

## 빠른 시작

```bash
pip install -r requirements.txt
playwright install chromium        # 영상 캡처용 브라우저 (최초 1회)
# ffmpeg 도 필요합니다 (macOS: brew install ffmpeg / Ubuntu: apt install ffmpeg)

python build.py examples/demo/project.json            # → out/demo_30s.mp4
python build.py examples/demo/project.json --preview  # → out/preview/*.png (장면별 미리보기, 몇 초 만에)
```

## 내 영상 만들기

1. `examples/demo` 를 `projects/내이름/` 으로 복사해 `project.json` 을 고칩니다. (`projects/` 는 `.gitignore` 라서 실수로 공개되지 않습니다)
2. `python build.py projects/내이름/project.json --preview` 로 장면을 확인하며 문구를 다듬습니다.
3. `--preview` 없이 실행하면 `out/<output>.mp4` 가 만들어집니다. (30초 영상 약 2분)

### 홈페이지 URL에서 초안 만들기

```bash
python fetch_site.py https://내사이트.com projects/내이름
```
제목·설명·숫자 문구·대표 이미지를 모아 `project.json` 초안을 만듭니다. 자동으로 뽑은 문구이므로
**사실관계를 직접 확인하고 다듬은 뒤** 사용하세요. (로그인이 필요하거나 자바스크립트로만 그려지는 사이트는 내용이 비어 있을 수 있습니다)

> Claude Code 같은 AI 코딩 도구에서는 *"이 레포로 https://내사이트.com 을 30초 모션그래픽으로 만들어줘"* 라고 요청해도 됩니다.

## project.json 설명

```jsonc
{
  "output": "my_video",                       // 출력 파일 이름
  "brand": {
    "name": "브랜드명", "tagline": "한 줄 소개", "url": "www.example.com",
    "logo": "logo.png",                       // (선택) project.json 기준 경로. 없으면 첫 글자 원형 마크
    "colors": { "bg": "#0B2341", "accent": "#FF7A3D", "ink": "#0B2341", "light": "#F5F7FA" }
  },
  "music": { "bpm": 120, "mood": "bright" },  // mood: bright | calm | dramatic
  "scenes": [ ... ]                           // 아래 장면 종류를 원하는 순서로
}
```

글자 안에서 `*단어*` 처럼 별표로 감싸면 포인트 색으로 강조됩니다. 각 장면의 `duration`(초)은 음악 박자에 맞춰 자동 보정됩니다.
어두운/밝은 배경은 번갈아 적용되며 `"theme": "dark" | "light"` 로 바꿀 수 있습니다.

| type | 용도 | 주요 항목 |
|---|---|---|
| `intro` | 첫 화면(로고+이름+한 줄) | `tagline`(생략 시 brand.tagline) |
| `statement` | 핵심 메시지 | `eyebrow`, `lines`[], `sub`, `visual`("none"이면 오른쪽 네트워크 그래픽 끔) |
| `flow` | 2~4단계 흐름 | `eyebrow`, `title`, `steps`[{`label`,`sub`}] |
| `stats` | 숫자 카운트업 카드 | `title`, `items`[{`value`,`suffix`,`label`,`decimals`,`comma`}] |
| `showcase` | 큰 숫자 + 키워드 칩 | `title`, `big`{`value`,`suffix`}, `chips`[] |
| `list` | 체크 리스트 | `title`, `items`[] |
| `image` | 내 이미지 1장 | `title`, `image`(경로), `caption` |
| `outro` | 마무리(로고+문구+주소) | `line`, `url` |

권장 구성: 30초 = intro 4초 + 본문 4~5장면 + outro 3초. 한 화면에 글을 너무 많이 넣지 마세요.

## 선택 기능: 내레이션 음성

장면에 `"narration": "읽을 문장"` 을 넣고 `python build.py ... --voice` 로 실행하면 Google Gemini TTS 로 음성을 만들어 넣고,
음성이 길면 장면 길이를 자동으로 늘리며 말하는 동안 배경음악을 낮춥니다. `pip install google-genai` 와 환경변수 `GEMINI_API_KEY` 가 필요합니다.
**키는 저장소에 절대 커밋하지 마세요.** (이 기능은 외부 API 변경에 따라 모델명 등을 `project.json` 의 `"voice": {"model","name"}` 으로 조정해야 할 수 있으며, 기본 배경음악 영상 흐름만큼 검증되지는 않았습니다)

## 구조

| 파일 | 역할 |
|---|---|
| `build.py` | 설정 검사 → 장면 타이밍 → 프레임 캡처 → 음악 합성 → ffmpeg 합치기 |
| `engine.html` | 장면을 그리는 모션 엔진(HTML/CSS/JS, `render(t)` 로 임의 시점 렌더) |
| `bgm.py` | 배경음악·효과음 합성(코드 진행, 아르페지오, 비트, 장면 전환 whoosh, 요소 등장 팝) |
| `fetch_site.py` | URL → `project.json` 초안 |
| `tts.py` | (선택) 내레이션 생성 |
| `fonts/` | Pretendard (SIL OFL 1.1, `Pretendard-LICENSE.txt` 참고) |
| `examples/demo/` | 가상의 회사로 만든 예제 설정 |

## 문제 해결

- **한글이 네모로 보임**: `fonts/` 폴더가 있는지 확인하세요.
- **chromium 오류**: `playwright install chromium` 을 실행하세요.
- **`ffmpeg` 없음**: ffmpeg 를 설치하세요.
- 영상을 만들 때 쓴 문구·이미지의 권리는 사용자에게 있습니다. 타인의 상표·사진·글을 허가 없이 쓰지 마세요.

## 라이선스

코드는 [MIT License](LICENSE) 입니다. 단, `fonts/` 의 Pretendard 글꼴은 별도로 SIL Open Font License 1.1 을 따릅니다(`fonts/Pretendard-LICENSE.txt`).
