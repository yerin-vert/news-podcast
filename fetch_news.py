"""
뉴스 수집 모듈
RSS 피드에서 기사 목록을 가져오고, 본문을 추출한다.
"""

from __future__ import annotations

import feedparser
import trafilatura
import requests
from datetime import datetime, timedelta, timezone
from config import RSS_FEEDS, FEED_CATEGORIES, ARTICLES_PER_CATEGORY, MAX_ARTICLE_LENGTH, DEFAULT_NEWS_DAYS


# requests 세션 (커넥션 재사용으로 속도 향상)
_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
})

# 요청 타임아웃 (초)
REQUEST_TIMEOUT = 15


def _parse_published_date(entry) -> datetime | None:
    """RSS 항목의 발행일을 datetime으로 파싱한다."""
    # feedparser가 파싱해주는 structured time 사용
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from time import mktime
        try:
            return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
        except Exception:
            pass

    # updated_parsed 도 시도
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        from time import mktime
        try:
            return datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
        except Exception:
            pass

    return None


def fetch_rss_entries(feed_url: str, max_entries: int = 10, days: int = DEFAULT_NEWS_DAYS) -> list[dict]:
    """
    RSS 피드 URL에서 최근 기사 목록을 가져온다.

    Args:
        feed_url: RSS 피드 URL
        max_entries: 최대 가져올 항목 수
        days: 최근 며칠치 기사만 가져올지

    Returns:
        [{"title": "...", "link": "...", "summary": "...", "published": "..."}, ...]
    """
    try:
        response = _session.get(feed_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"  ⚠️  RSS 가져오기 실패 ({feed_url}): {e}")
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    entries = []

    for entry in feed.entries:
        if len(entries) >= max_entries:
            break

        # 날짜 필터링: 발행일이 파싱 가능하면 cutoff 이전 기사 건너뛰기
        pub_date = _parse_published_date(entry)
        if pub_date and pub_date < cutoff:
            continue

        entries.append({
            "title": entry.get("title", "제목 없음"),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
        })
    return entries


def extract_article_body(url: str) -> str:
    """
    기사 URL에서 본문 텍스트를 추출한다.
    trafilatura 라이브러리를 사용하여 광고/메뉴 등을 제거하고
    기사 본문만 깔끔하게 가져온다.

    Returns:
        본문 텍스트 (추출 실패 시 빈 문자열)
    """
    try:
        response = _session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        body = trafilatura.extract(response.text, include_comments=False)
        if body and len(body) > MAX_ARTICLE_LENGTH:
            body = body[:MAX_ARTICLE_LENGTH] + "..."
        return body or ""
    except Exception as e:
        print(f"  ⚠️  본문 추출 실패 ({url}): {e}")
        return ""


def fetch_news_by_category(categories: list[str] | None = None, days: int = DEFAULT_NEWS_DAYS) -> dict[str, list[dict]]:
    """
    카테고리별로 뉴스를 수집한다.

    Args:
        categories: 수집할 카테고리 리스트 (None이면 전체)
        days: 최근 며칠치 기사만 가져올지

    Returns:
        {
            "국내": [{"title": "...", "source": "...", "content": "...", "link": "..."}, ...],
            "국제": [...],
            "테크": [...]
        }
    """
    if categories is None:
        categories = list(FEED_CATEGORIES.keys())

    print(f"  📅 최근 {days}일치 기사만 수집합니다.")

    results = {}

    for category in categories:
        if category not in FEED_CATEGORIES:
            print(f"  ⚠️  알 수 없는 카테고리: {category}")
            continue

        print(f"\n📂 [{category}] 카테고리 수집 중...")
        feed_names = FEED_CATEGORIES[category]
        max_articles = ARTICLES_PER_CATEGORY.get(category, 2)

        collected = []

        for feed_name in feed_names:
            if len(collected) >= max_articles:
                break

            feed_url = RSS_FEEDS.get(feed_name)
            if not feed_url:
                continue

            print(f"  📡 {feed_name} RSS 읽는 중...")
            entries = fetch_rss_entries(feed_url, max_entries=5, days=days)

            for entry in entries:
                if len(collected) >= max_articles:
                    break

                # 이미 같은 제목의 기사가 있으면 건너뛰기 (중복 방지)
                if any(a["title"] == entry["title"] for a in collected):
                    continue

                print(f"    📰 본문 추출: {entry['title'][:40]}...")
                body = extract_article_body(entry["link"])

                if not body:
                    # 본문 추출 실패 시 RSS 요약으로 대체
                    body = entry["summary"]

                if body:
                    collected.append({
                        "title": entry["title"],
                        "source": feed_name,
                        "link": entry["link"],
                        "content": body,
                    })
                    print(f"    ✅ 수집 완료 ({len(body)}자)")

        results[category] = collected
        print(f"  → {category}: {len(collected)}개 기사 수집됨")

    return results


def get_all_articles_flat(news_by_category: dict[str, list[dict]]) -> list[dict]:
    """
    카테고리별 뉴스를 하나의 리스트로 합친다.
    각 기사에 category 필드를 추가한다.
    """
    articles = []
    for category, news_list in news_by_category.items():
        for article in news_list:
            article_with_category = {**article, "category": category}
            articles.append(article_with_category)
    return articles


# ── 단독 실행 시 테스트 ──
if __name__ == "__main__":
    print("=" * 60)
    print("  📰 뉴스 수집 테스트")
    print("=" * 60)

    news = fetch_news_by_category()
    all_articles = get_all_articles_flat(news)

    print(f"\n{'=' * 60}")
    print(f"  총 {len(all_articles)}개 기사 수집 완료")
    print(f"{'=' * 60}")

    for i, article in enumerate(all_articles, 1):
        print(f"\n[{i}] [{article['category']}] {article['title']}")
        print(f"    출처: {article['source']}")
        print(f"    본문: {article['content'][:100]}...")
