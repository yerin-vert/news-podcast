"""
RSS 피드 소스 설정
카테고리별로 관리하며, 필요에 따라 추가/삭제 가능
"""

RSS_FEEDS = {
    # ── 국내 뉴스 ──
    "연합뉴스_정치": "https://www.yna.co.kr/rss/politics.xml",
    "연합뉴스_경제": "https://www.yna.co.kr/rss/economy.xml",
    "연합뉴스_국제": "https://www.yna.co.kr/rss/international.xml",
    "한겨레": "https://www.hani.co.kr/rss/",
    "조선일보": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",

    # ── 국제 뉴스 (영어) ──
    "BBC_World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters_World": "https://www.reutersagency.com/feed/?best-topics=world",

    # ── IT / 테크 (영어) ──
    "TechCrunch": "https://techcrunch.com/feed/",
    "The_Verge": "https://www.theverge.com/rss/index.xml",
    "Hacker_News_Best": "https://hnrss.org/best",
}

# 카테고리 매핑 (스크립트 생성 시 분류용)
FEED_CATEGORIES = {
    "국내": ["연합뉴스_정치", "연합뉴스_경제", "연합뉴스_국제", "한겨레", "조선일보"],
    "국제": ["BBC_World", "Reuters_World"],
    "테크": ["TechCrunch", "The_Verge", "Hacker_News_Best"],
}

# 카테고리별 가져올 기사 수
ARTICLES_PER_CATEGORY = {
    "국내": 3,
    "국제": 2,
    "테크": 2,
}

# 본문 추출 시 최대 글자 수 (너무 긴 기사 방지)
MAX_ARTICLE_LENGTH = 3000

# 최근 며칠치 기사를 가져올지 (기본값)
DEFAULT_NEWS_DAYS = 3
