# herdr-timekit

한국어 · [English](README.md)

herdr 사이드바 맨 아래 블록에 현재 시간, 세계 시간, 타이머, 카운터를 한데 모아 보여 주는 플러그인입니다. AI 코딩 에이전트와 함께 작업하는 동안 시간을 계속 볼 수 있습니다.

- **손목시계 모양의 시간 박스**: 사이드바에 나오며, 휴일에는 이모지가 붙고, 타이머가 돌 때는 타이머 값이 나옵니다.
- **타이머**: 줄어드는 카운트다운, 일시정지, 초기화를 지원합니다.
- **카운터**: 1초마다 올라가게 시작할 수 있고, 직접 증감할 수도 있습니다.
- **세계 시간**: IANA 시간대 이름으로 여러 도시를 추가할 수 있습니다.
- **상세 화면**: 키보드로 조작하고, 한국어 또는 영어 글자를 고를 수 있습니다.

## 설치

```sh
herdr plugin install vrwolf1004/herdr-timekit
```

## 요구 사항

- herdr 0.9.0 이상
- Windows, Linux, macOS
- Python 3.9 이상
- Windows에서 세계 시간을 쓰려면 `tzdata` 패키지가 필요합니다: `python -m pip install tzdata`

## 사이드바 설정

herdr는 사이드바 레이아웃에 들어 있는 토큰만 그립니다. herdr의 `config.toml`에 있는 `[ui.sidebar.agents]`에 timekit 줄을 넣고 `herdr server reload-config`를 실행하세요.

```toml
[ui.sidebar.agents]
rows = [
  # ...기존 줄...
  [{ token = "$tk_box1", fg = "#8b949e" }],
  [{ token = "$tk_box2", fg = "#d2a8ff" }],
  [{ token = "$tk_box3", fg = "#e6edf3", bold = true }],
  [{ token = "$tk_box4", fg = "#7ee787" }],
  [{ token = "$tk_box5", fg = "#d2a8ff" }],
  [{ token = "$tk_box6", fg = "#8b949e" }],
]
```

herdr는 사이드바 줄을 최대 16개까지만 허용하므로, 전체 줄 수가 16을 넘지 않게 하세요.

## 키 (상세 화면)

timekit pane을 클릭해 포커스를 준 뒤 누르세요.

| 키 | 타이머 | 카운터 |
|----|--------|--------|
| `t` | 시작 / 일시정지 | |
| `r` | 타이머 초기화 | |
| `c` | | 시작 / 일시정지 (1초마다 올라감) |
| `+` / `-` | | 한 칸씩 증감 |
| `0` | | 0으로 초기화 |

한글 입력도 됩니다: `ㅅ`는 `t`, `ㄱ`는 `r`, `ㅊ`는 `c`입니다.

## 명령

플러그인 폴더에서 실행합니다.

```sh
python -X utf8 src/timekit.py <명령>
```

| 명령 | 하는 일 |
|------|---------|
| `ensure` | timekit 블록이 꺼져 있으면 켭니다 |
| `stop` | 블록을 끕니다 |
| `counter-inc` / `counter-dec` / `counter-reset` | 카운터를 바꿉니다 |
| `timer-start` / `timer-pause` / `timer-reset` | 타이머를 조작합니다 |
| `world-add <시간대>` | 시간대를 추가합니다. 예: `Asia/Seoul` |
| `world-remove <시간대>` | 시간대를 뺍니다 |
| `world-clear` | 시간대를 모두 뺍니다 |
| `world-list` | 시간대 목록을 봅니다 |

`world-clear`와 `world-list`는 herdr 액션으로도 쓸 수 있습니다. 추가와 삭제는 이름을 인자로 받아야 해서 명령줄에서만 쓸 수 있습니다.

## 설정

설정은 플러그인 설정 폴더의 `config.json`에 둡니다. 모든 키는 [설정 문서](docs/configuration.md)에 있습니다.

```json
{
  "lang": "ko",
  "timezones": ["Asia/Seoul", "America/New_York"],
  "default_timer_seconds": 1500,
  "now_style": "hm",
  "box_style": "double_star",
  "holiday_theme": true
}
```

- `lang`: `en`, `ko`, `ru`, `fr`, `es`, `de`, `ja` 중 하나입니다. 없으면 OS 언어를 쓰고, 지원하지 않으면 영어를 씁니다.
- `box_style`: `double_star`, `square_dot`, `round_star`, `heavy_diamond`, `round_heart`, `emoji_flower`, `emoji_sparkle`, `emoji_person`, `emoji_tulip`, `emoji_rose` 중 하나입니다.
- `now_style`: `hm`, `12h`, `date`, `week`, `dateweek`, `compact`, `ymd`, `ymdhm`, `kor12`, `full_kor`, `full_en` 중 하나입니다.
- `holiday_theme`: 휴일이면 박스에 이모지를 붙입니다. 휴일 목록은 `holidays.json`에 있습니다.

## 문서

- [설정](docs/configuration.md)
- [개발](docs/development.md)

---

## 프로젝트 응원하기

프로젝트가 도움이 되셨다면 커피 한 잔으로 개발을 응원해 주세요.

[![Ko-fi에서 응원하기](https://img.shields.io/badge/Ko--fi-%EC%9D%91%EC%9B%90%ED%95%98%EA%B8%B0-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
