# herdr-timekit

[English](README.md) | [**한국어**](README.ko.md)

지원 언어: 영어 · 한국어 · 러시아어 · 프랑스어 · 스페인어 · 독일어 · 일본어

herdr 사이드바 맨 아래 블록에 현재 시각, 세계 시간, 타이머, 카운터를 모아 보여 줍니다.
herdr 시작 시와 새 workspace 생성 시 블록이 자동으로 시작됩니다. 공유 `herdr-dock` workspace의 pane을 사용하며 `stop` 액션으로 숨길 수 있습니다.
공휴일은 Nager.Date에서 받아 5년치로 로컬에 캐시합니다. 캐시의 다섯 번째 연도에 이르거나 `holiday_country`가 바뀌면 새로 받습니다. 갱신에 실패하면 오류를 `host.log`에 기록하고 기존 캐시를 유지합니다. `host.log`가 1 MiB를 넘으면 `host.log.1`로 옮기고(이전 파일은 덮어씀), 로그 파일은 최대 두 개만 남깁니다. 한국(`KR`)에서는 함께 제공되는 한국 공휴일 달력도 적용됩니다.
카운터는 실행 중 초마다 증가하며 사이드바와 시계 상자에 같은 현재 값을 표시합니다.

## 대시보드 디자인

Agents 사이드바:

```text
┌────── 시각 ──────┐
│     13:45:08     │
│   3월 8일 토요일  │
│  서울    13:45   │
│  도쿄    13:45   │
└──────────────────┘
```

Timekit pane:

```text
╭──────────────────────────────────────────────╮
│               🐺  herdr-timekit  🌕          │
├──────────────────────────────────────────────┤
│  현재 시각                                    │
│  13:45:08  3월 8일 토요일                     │
│                                              │
│  세계 시간                                    │
│  서울        13:45   Asia/Seoul              │
│  뉴욕        23:45   America/New_York        │
├──────────────────────────────────────────────┤
│  타이머                카운터                │
│  20:00                 1,234                 │
│  [t] 시작/일시정지     [c] 시작/일시정지      │
│  [r] 초기화            [0] 초기화              │
├──────────────────────────────────────────────┤
│  [1-6] 프리셋  [w] 시간대 추가  [b] 디자인   │
╰──────────────────────────────────────────────╯
```

## 설치

```sh
herdr plugin install vrwolf1004/herdr-timekit
```

## 액션

| 액션 | 기능 |
| --- | --- |
| `start` / `stop` | 시간 블록 표시 또는 숨기기 |
| `counter-reset` | 카운터 초기화 |
| `timer-start` / `timer-pause` / `timer-reset` | 타이머 시작·일시 정지·초기화 |
| `world-list` / `world-clear` | 세계 시간 목록 확인 또는 모두 지우기 |

Windows에서는 각 액션 ID 뒤에 `-windows`를 붙입니다. 사이드바 설정, pane 조작, 프리셋, 세계 시간은 [사용법](docs/usage.ko.md)을 참고하세요.

## 요구 사항

- herdr 0.9.0 이상
- Windows, Linux, macOS
- Python 3.9 이상; Windows에서는 `python -m pip install tzdata`도 필요

## 문서

- [사용법 (한국어)](docs/usage.ko.md)
- [Usage (English)](docs/usage.md)
- [설정](docs/configuration.md)
- [구조](docs/architecture.md)
- [문제 해결](docs/troubleshooting.md)
- [개발](docs/development.md)

## 프로젝트 응원하기

프로젝트가 도움이 되셨다면 커피 한 잔으로 개발을 응원해 주세요.

[![Ko-fi에서 응원하기](https://img.shields.io/badge/Ko--fi-%EC%9D%91%EC%9B%90%ED%95%98%EA%B8%B0-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
