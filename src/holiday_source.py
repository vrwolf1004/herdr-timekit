"""공휴일을 Nager.Date 공개 API 에서 받아 캐시한다.

- 받는 방식: 시작 연도부터 5년치를 받는다. 시작 연도로부터 5년째(인덱스 4)가 되면 현재 연도부터 다시 5년치를 받는다.
- 캐시: 상태 폴더의 holidays-cache.json (국가, 시작 연도, 날짜별 항목).
- 실패하면 예전 캐시를 그대로 쓴다. 캐시도 없으면 번들 holidays.json 만 쓴다.
- 이름: localName 은 name 으로, 영어 name 은 name_en 으로 저장한다 (timekit 의 표시 규칙과 같다).
"""

import json
import os
import urllib.request

API = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"
WINDOW_YEARS = 5
REFRESH_AFTER_YEARS = 4  # 시작 연도 + 4 = 5년째에 다시 받는다
TIMEOUT_SECONDS = 10
CACHE_FILE = "holidays-cache.json"
DEFAULT_COUNTRY = "US"
COUNTRY_BY_LANGUAGE = {"ko": "KR", "ja": "JP", "ru": "RU", "fr": "FR", "de": "DE", "es": "ES", "en": "US"}
DEFAULT_EMOJI = "🎉"
# 이름에 이 낱말이 있으면 이모지를 쓴다. 번들 holidays.json 의 항목이 있으면 그쪽 이모지가 우선한다.
EMOJI_RULES = [
    ("Lunar New Year", "🧧"), ("설날", "🧧"),
    ("Chuseok", "🌕"), ("추석", "🌕"),
    ("Christmas", "🎄"), ("크리스마스", "🎄"),
]


def country_for_language(language):
    return COUNTRY_BY_LANGUAGE.get(language, DEFAULT_COUNTRY)


def emoji_for(name_en, name_local):
    for keyword, emoji in EMOJI_RULES:
        if keyword in name_en or keyword in name_local:
            return emoji
    return DEFAULT_EMOJI


def parse_year(payload):
    """API 응답(목록)을 날짜 → 항목 사전으로 바꾼다. 날짜가 없는 항목은 건너뛴다."""
    entries = {}
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("date"), str):
            continue
        name_en = item.get("name") or item.get("localName") or ""
        name_local = item.get("localName") or name_en
        entries[item["date"]] = {
            "date": item["date"],
            "emoji": emoji_for(name_en, name_local),
            "name": name_local,
            "name_en": name_en,
        }
    return entries


def fetch_year(year, country, opener=urllib.request.urlopen):
    """한 해의 휴일. 받지 못하면 None."""
    try:
        with opener(API.format(year=year, country=country), timeout=TIMEOUT_SECONDS) as response:
            payload = json.load(response)
        return parse_year(payload) if isinstance(payload, list) else None
    except (OSError, ValueError):
        return None


def needs_refresh(cache, country, now_year):
    if not isinstance(cache, dict) or cache.get("country") != country:
        return True
    start = cache.get("start")
    if not isinstance(start, int):
        return True
    return now_year < start or now_year - start >= REFRESH_AFTER_YEARS


def refresh(country, now_year, fetch=fetch_year):
    """now_year 부터 WINDOW_YEARS 년치를 받는다. 한 해라도 못 받으면 None (예전 캐시를 유지하기 위해)."""
    entries = {}
    for year in range(now_year, now_year + WINDOW_YEARS):
        got = fetch(year, country)
        if got is None:
            return None
        entries.update(got)
    return {"country": country, "start": now_year, "entries": entries}


def load_cache(path):
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save_cache(path, data):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)
    os.replace(temp, path)


def holidays_for(state_dir, country, now_year, bundled=None, fetch=fetch_year):
    """화면에 쓸 휴일 사전. 필요하면 캐시를 새로 받고, 번들 항목(KR 만)을 우선해 합친다."""
    path = os.path.join(state_dir, CACHE_FILE)
    cache = load_cache(path)
    if needs_refresh(cache, country, now_year):
        fresh = refresh(country, now_year, fetch)
        if fresh is not None:
            try:
                save_cache(path, fresh)
            except OSError:
                pass  # 저장하지 못해도 이번 실행에서는 받은 값을 쓴다
            cache = fresh
    entries = dict(cache.get("entries", {})) if isinstance(cache, dict) else {}
    if bundled and country == "KR":
        entries.update(bundled)
    return entries
