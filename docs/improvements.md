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
