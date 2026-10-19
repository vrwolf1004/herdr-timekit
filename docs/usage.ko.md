# 사용법

[English](usage.md) | [**한국어**](usage.ko.md)

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

herdr는 사이드바 줄을 전부 합쳐 최대 16개까지만 허용하므로, 줄 수가 16을 넘지 않게 하세요.

## 상세 패널 키

timekit pane을 클릭해 포커스를 준 뒤 누르세요.

| 키 | 타이머 | 카운터 | 세계 시간 |
|----|--------|--------|-----------|
| `1`–`6` | 프리셋: 10초, 30초, 1분, 20분, 30분, 1시간 (멈춘 타이머만) | | |
| `t` | 시작 / 일시정지 | | |
| `r` | 타이머 초기화 | | |
| `c` | | 시작 / 일시정지 (1초마다 올라감) | |
| `0` | | 0으로 초기화 | |
| `w` | | | 시간대 추가 (이름 입력 후 Enter, Esc는 취소) |
| `x` | | | 마지막 시간대 삭제 |
| `b` | | | 시계 디자인 변경 (박스 모양을 순서대로 바꾸고 `box_style`에 저장) |

한글 입력도 됩니다: `ㅅ`는 `t`, `ㄱ`는 `r`, `ㅈ`는 `w`, `ㅊ`는 `c`입니다.

## 세계 시간

패널에서 `w`로 추가하거나 명령줄에서 추가할 수 있습니다.

```sh
python -X utf8 src/timekit.py world-add Seoul
python -X utf8 src/timekit.py world-remove Asia/Seoul
python -X utf8 src/timekit.py world-list
python -X utf8 src/timekit.py world-clear
```

`Seoul`이나 `New York` 같은 도시 이름, 또는 `America/New_York` 같은 IANA 시간대 이름을 입력할 수 있습니다. 도시 이름은 IANA 목록에서 찾으며, 대소문자는 구분하지 않습니다(`seoul`, `Seoul`, `SEOUL` 모두 가능). Windows에서는 세계 시간을 쓰려면 `tzdata`를 설치하세요.

## 명령

플러그인 폴더에서 실행합니다.

```sh
python -X utf8 src/timekit.py <명령>
```

| 명령 | 하는 일 |
|------|---------|
| `ensure` | timekit 블록이 꺼져 있으면 켭니다 |
| `stop` | 블록을 끕니다 |
| `counter-reset` | 카운터를 0으로 초기화합니다 |
| `timer-start` / `timer-pause` / `timer-reset` | 타이머를 조작합니다 |
| `world-add <시간대>` | 시간대를 추가합니다 |
| `world-remove <시간대>` | 시간대를 뺍니다 |
| `world-clear` | 시간대를 모두 뺍니다 |
| `world-list` | 시간대 목록을 봅니다 |

`world-clear`와 `world-list`는 herdr 액션으로도 쓸 수 있습니다. 추가와 삭제는 이름이 필요해서 명령줄에서만 하거나, 패널에서 `w`와 `x`로 합니다.

## 언어

패널, 박스 글자, 메시지는 언어 설정을 따릅니다. [설정: 언어](configuration.md#language)를 보세요(영문).
