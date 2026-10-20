# 문서 개선 사항 (Documentation TODO)

기능 개선은 [todo.md](todo.md)에 있습니다. 이 문서는 docs와 README에서 고칠 점만 모았습니다.

## 언어 맞춤

- [ ] `docs/configuration.md`의 한국어 버전 작성 (현재 영문만 있음)
- [ ] `docs/development.md`의 한국어 버전 작성 (현재 영문만 있음)
- [ ] `docs/usage.md`와 `docs/usage.ko.md`의 키 표와 명령 표가 같은 내용인지 줄 단위로 대조

## 빠진 설명

- [ ] 타이머 프리셋(`1`~`6`)과 진행바 계산 방식 설명 (`docs/usage`)
- [ ] 타이머와 카운터의 동시 실행 제한과 알림 문구 설명 (`docs/usage`)
- [ ] 시계 박스가 타이머·카운터 값을 어떻게 바꿔 보여 주는지 설명 (`docs/usage`)
- [ ] 세계 시간 여러 줄 표시와 `+N more` 규칙 설명 (`docs/usage`)
- [ ] 상태 파일 위치와 역할(`timer.json`, `counter.json`, `heartbeat`) 설명 (`docs/development.md`)
- [ ] 사이드바 행 제한(16)과 행 배치 예시를 한눈에 보이는 표로 정리

## 문제 해결 문서

- [x] `docs/troubleshooting.md` 추가
  - 사이드바에 시계가 안 나옴 (`config.toml` 줄 누락, `server reload-config` 필요)
  - 세계 시간이 안 나옴 (Windows에서 `tzdata` 미설치)
  - 키를 눌러도 반응 없음 (pane 포커스 필요, 숫자 키가 herdr에 가로채일 가능성)
  - 언어가 기대와 다름 (`HERDR_TIMEKIT_LANG`, `config.json`의 `lang`, OS 언어 순서)
  - host가 멈춘 것 같음 (`stop` 후 `ensure`로 재시작)

## 예시와 그림

- [ ] README 대시보드 예시를 현재 패널 출력으로 다시 만들기 (코드 변경 때마다 갱신)
- [ ] 10가지 박스 디자인 미리보기를 `docs/configuration.md`에 넣기 (이미 표가 있으니 예시 한 줄씩 추가)
- [ ] 실제 사이드바와 패널 스크린샷 추가 (글꼴에 따른 모양 차이 확인용)

## 데이터와 버전

- [ ] `holidays.json` 연도별 목록을 문서에 요약 (2026 외 연도 추가 시 갱신)
- [ ] 변경 기록(CHANGELOG) 파일 추가
- [ ] `herdr-plugin.toml`의 `version`과 CHANGELOG 항목을 맞추는 절차 정리

## 정리

- [ ] `docs/usage.md`, `docs/usage.ko.md`의 "Commands" 표에서 herdr 액션으로 되는 명령과 명령줄만 되는 명령을 구분해서 표기
- [ ] README의 "Dashboard design" 섹션 제목과 `docs/usage`의 키 설명 용어를 통일 (예: "panel" 대 "detail panel")
