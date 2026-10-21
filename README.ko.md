# herdr-timekit

[English](README.md) | [**한국어**](README.ko.md)

🌐 UI 언어: 🇺🇸 English (en) · 🇰🇷 한국어 (ko) · 🇷🇺 Русский (ru) · 🇫🇷 Français (fr) · 🇪🇸 Español (es) · 🇩🇪 Deutsch (de) · 🇯🇵 日本語 (ja)

herdr 사이드바 맨 아래 블록에 현재 시각, 세계 시간, 타이머, 카운터를 모아 보여 줍니다.

## 대시보드 디자인

사이드바 블록에는 시각과 날짜, 실행 중인 타이머 또는 카운터가 표시됩니다. timekit pane에서 세부 정보를 보고 블록 디자인을 바꿀 수 있습니다.

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
- [문제 해결](docs/troubleshooting.md)
- [개발](docs/development.md)

## 프로젝트 응원하기

프로젝트가 도움이 되셨다면 커피 한 잔으로 개발을 응원해 주세요.

[![Ko-fi에서 응원하기](https://img.shields.io/badge/Ko--fi-%EC%9D%91%EC%9B%90%ED%95%98%EA%B8%B0-FF5E5B?style=for-the-badge&logo=buymeacoffee&logoColor=white)](https://ko-fi.com/dev_ohyt)
