# 개선 문서

- 작성 기준: 2026-10-22, 커밋 `cbca1cf` (`git log -1 --format=%h`)
- 공용 도크 모듈: `src/dock_layout.py` 는 복사본. `load_dock_layout()`(`src/timekit.py:37`)이 설치된 herdr-dock-grid 원본을 먼저 찾고, 없으면 이 복사본을 쓴다. 복사본은 herdr-dock-grid 0.7.1 원본과 내용이 같다(diff 확인).
- 할 일 목록: [todo.md](todo.md). 이미 적힌 항목(휴일, 사이드바, 2x2 배치 중복 등)은 옮기지 않고 거기서 관리한다.
- 표기: "확인됨" = 현재 코드에서 직접 본 내용. "확인 필요" = 코드로 추정만 했고 실행해 보지 않음.

## 개선 항목

- **[중간] 공용 herdr CLI 호출에 시간 제한이 없음** (확인 필요)
  - 근거: `src/herdr_api.py:42`(`cli()`), `src/herdr_api.py:140`(`installed_plugin_path()`)
  - herdr 가 응답하지 않으면 `subprocess.run` 이 끝나지 않아 host 루프가 멈출 수 있다. 같은 코드가 여섯 플러그인 복사본에 있으므로, 고칠 때는 herdr-dock-grid 원본을 먼저 바꾸고 복사본을 맞춘다(공용 모듈 규칙).

- **[낮음] 저장소에 CI가 없음** (확인됨)
  - 근거: 저장소 루트에 `.github/` 가 없다. herdr-stockpulse 의 `.github/workflows/test.yml` 은 세 OS 와 Python 3.8/3.12 에서 단위 테스트를 돌린다.
  - 같은 워크플로를 추가하면 `tests/` 의 단위 테스트(`test_timekit.py`, `test_holiday_source.py`, 합계 35개)가 OS 별로 자동 실행된다.

## 관련 기존 항목 (todo.md)

- 2x2 배치 함수 중복(`grid_split`, `ensure_intro`): [todo.md](todo.md) 의 "2x2 배치 함수 중복"
- 사이드바 줄 수 제한, 휴일 데이터, 다국어 문구: [todo.md](todo.md) 의 각 절

## 개선 제안 (2026-10-23)

### 1. config.json 쓰기가 원자적이지 않고 읽기-수정-쓰기가 겹칠 수 있음

- **현상**: 패널의 `b`(디자인 변경, `src/timekit.py:807-817`), `x`(마지막 시간대 제거, `:792-805`)와 CLI 의 `world-add`, `world-remove`, `world-clear`(`cmd_world`, `:1001-1036`)는 각각 `config.json` 을 읽고 고쳐서 통째로 다시 쓴다. 저장 함수 `save_config`(`:994-998`)는 임시 파일을 거치지 않는다. 쓰는 도중 멈추면 파일이 깨질 수 있고, 두 주체가 동시에 쓰면 한쪽 변경이 사라진다. 상태 파일 `write`(`:313-318`)는 임시 파일과 `os.replace` 를 쓰므로 설정 파일만 다르다.
- **개선안**: `save_config` 를 임시 파일과 `os.replace` 로 바꾸고, 저장 직전에 다시 읽어 바꿀 키만 고친다.
- **범위**: `src/timekit.py` (`save_config`, `change_box_style`, `remove_last_zone`, `cmd_world`), `docs/configuration.md`
- **확인**: 저장 중간에 끊긴 상황을 가정해 파일이 깨지지 않는지 보고, 두 명령을 거의 동시에 실행해 두 변경이 모두 남는지 본다. 경합은 실제로 재현하지 않았다(확인 필요).
→ 부분 완료: 임시 파일로 쓰고 저장 직전에 다시 읽는다. 같은 순간의 두 명령 경합은 잠금이 없어 아직 남아 있다 (결정 필요).

### 2. host.log 가 회전 없이 계속 쌓임

- **현상**: 휴일 갱신이 실패할 때마다 `host.log` 에 한 줄씩 덧붙인다(`src/timekit.py:658-659`). 크기 제한이 없다. 갱신은 국가나 연도가 바뀔 때만 일어나므로 늘어나는 속도는 느리다.
- **개선안**: 일정 크기를 넘으면 이전 파일로 넘기거나 마지막 몇 줄만 남긴다.
- **범위**: `src/timekit.py` (`Host.refresh_holidays` 안의 `log`), `docs/troubleshooting.md`
- **확인**: 실패 로그를 여러 번 남긴 뒤 파일 크기 변화를 본다.
→ 완료: host.log 가 1 MiB 를 넘으면 host.log.1 로 옮긴다 (최대 두 파일).

### 3. 시간대 이름을 찾을 때마다 전체 목록을 정렬함

- **현상**: `resolve_zone` 은 호출할 때마다 `zoneinfo.available_timezones()` 를 정렬하고 소문자 맵을 새로 만든다(`src/timekit.py:983-986`). 명령줄(`:1019`)과 패널의 `w` 입력(`:774`) 두 곳에서 부른다. 호출당 비용은 작을 것으로 보인다.
- **개선안**: 목록과 소문자 맵을 모듈 수준에서 한 번만 만든다.
- **범위**: `src/timekit.py` (`resolve_zone`)
- **확인**: 호출 한 번의 시간을 재서 차이가 의미 있는지 본다. 차이가 작으면 이 항목은 닫는다(확인 필요).
→ 완료: 시간대 이름 찾기가 한 실행 안에서 목록을 한 번만 만든다 (결과는 같다).
