"""
나만의 뉴스 팟캐스트 - Phase 2 파이프라인
RSS 수집 → 본문 추출 → 스크립트 생성 → 저장
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

from fetch_news import fetch_news_by_category, get_all_articles_flat
from generate_script import generate_podcast_script
from generate_audio import generate_podcast_audio


# 출력 디렉토리
OUTPUT_DIR = "output"


def save_script_txt(script: str, filepath: str) -> None:
    """사람이 읽을 수 있는 텍스트 파일로 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(script)


def parse_script_to_turns(script: str) -> list[dict]:
    """
    스크립트 텍스트를 턴별로 파싱한다.

    "HOST: 안녕하세요..." → {"speaker": "HOST", "text": "안녕하세요..."}
    """
    turns = []
    current_speaker = None
    current_text = []

    for line in script.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("HOST:"):
            # 이전 턴 저장
            if current_speaker:
                turns.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text).strip(),
                })
            current_speaker = "HOST"
            current_text = [line[5:].strip()]

        elif line.startswith("GUEST:"):
            if current_speaker:
                turns.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text).strip(),
                })
            current_speaker = "GUEST"
            current_text = [line[6:].strip()]

        else:
            # 여러 줄에 걸친 대사 이어붙이기
            current_text.append(line)

    # 마지막 턴 저장
    if current_speaker:
        turns.append({
            "speaker": current_speaker,
            "text": " ".join(current_text).strip(),
        })

    return turns


def save_script_json(script: str, articles: list[dict], filepath: str) -> None:
    """
    JSON 구조화 파일로 저장.
    나중에 TTS 연동 등에 활용 가능.
    """
    turns = parse_script_to_turns(script)

    data = {
        "generated_at": datetime.now().isoformat(),
        "article_count": len(articles),
        "articles": [
            {
                "title": a["title"],
                "source": a["source"],
                "category": a.get("category", ""),
                "link": a.get("link", ""),
            }
            for a in articles
        ],
        "script": {
            "total_turns": len(turns),
            "turns": turns,
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_pipeline(
    categories: list[str] | None = None,
    days: int = 3,
    skip_audio: bool = False,
) -> None:
    """전체 파이프라인 실행"""
    print("=" * 60)
    print("  🎙️  나만의 뉴스 팟캐스트 - Phase 2 파이프라인")
    print("=" * 60)

    # ── Step 1: 뉴스 수집 ──
    print("\n📡 Step 1: RSS에서 뉴스 수집 중...")
    news_by_category = fetch_news_by_category(categories, days=days)
    all_articles = get_all_articles_flat(news_by_category)

    if not all_articles:
        print("\n❌ 수집된 기사가 없습니다. RSS 피드를 확인해주세요.")
        return

    print(f"\n✅ 총 {len(all_articles)}개 기사 수집 완료")
    for i, article in enumerate(all_articles, 1):
        print(f"  [{i}] [{article['category']}] {article['title'][:50]}")

    # ── Step 2: 스크립트 생성 ──
    print("\n⏳ Step 2: Claude API로 팟캐스트 스크립트 생성 중...")
    script = generate_podcast_script(all_articles)
    print("✅ 스크립트 생성 완료")

    # ── Step 3: 저장 ──
    print("\n💾 Step 3: 파일 저장 중...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    txt_path = os.path.join(OUTPUT_DIR, f"podcast_{timestamp}.txt")
    save_script_txt(script, txt_path)
    print(f"  📝 텍스트: {txt_path}")

    json_path = os.path.join(OUTPUT_DIR, f"podcast_{timestamp}.json")
    save_script_json(script, all_articles, json_path)
    print(f"  📊 JSON:  {json_path}")

    # ── Step 4: TTS 오디오 생성 ──
    if not skip_audio:
        print("\n🎙️  Step 4: TTS 오디오 생성 중...")
        turns = parse_script_to_turns(script)
        if turns:
            audio_path = os.path.join(OUTPUT_DIR, f"podcast_{timestamp}.mp3")
            temp_dir = os.path.join(OUTPUT_DIR, f"temp_{timestamp}")
            try:
                generate_podcast_audio(turns, audio_path, temp_dir=temp_dir)
            except Exception as e:
                print(f"  ⚠️  오디오 생성 실패: {e}")
                print("  (스크립트는 정상 저장되었습니다)")
        else:
            print("  ⚠️  파싱된 턴이 없어 오디오 생성을 건너뜁니다.")

    # ── 완료 ──
    print(f"\n{'=' * 60}")
    print("  ✅ 파이프라인 완료!")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="나만의 뉴스 팟캐스트 스크립트 생성기"
    )
    parser.add_argument(
        "--category", "-c",
        nargs="+",
        choices=["국내", "국제", "테크"],
        default=None,
        help="수집할 카테고리 (미지정 시 전체). 예: --category 국내 테크",
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=3,
        help="최근 며칠치 기사를 가져올지 (기본: 3일)",
    )
    parser.add_argument(
        "--skip-audio",
        action="store_true",
        help="TTS 오디오 생성을 건너뜀 (스크립트만 생성)",
    )
    args = parser.parse_args()
    run_pipeline(
        categories=args.category,
        days=args.days,
        skip_audio=args.skip_audio,
    )


if __name__ == "__main__":
    main()
