"""
X(트위터) 레시피 데이터 수집 스크립트
snscrape 사용 (API 키 불필요)
"""

import snscrape.modules.twitter as sntwitter
import pandas as pd
import json
import os
from datetime import datetime

# 출력 경로
OUTPUT_DIR = "/Users/js/Documents/recipe/x_recipes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 검색 쿼리 목록
QUERIES = [
    # 한국어 기본
    "레시피 lang:ko min_faves:10",
    "요리법 lang:ko min_faves:5",
    "#레시피 lang:ko",
    "#자취요리 lang:ko",
    "찌개 만들기 lang:ko",
    "볶음밥 레시피 lang:ko",
    "반찬 레시피 lang:ko",
    # 트렌드
    "약과 만들기 lang:ko",
    "탕후루 레시피 lang:ko",
    # 영문
    "korean recipe min_faves:20",
    "kimchi recipe",
]

# 필터 키워드 (하나 이상 포함해야 함)
FILTER_KEYWORDS = ["레시피", "만들기", "요리", "넣고", "볶고", "recipe", "cook"]

# 수집 설정
TWEETS_PER_QUERY = 200
MIN_TEXT_LENGTH = 50


def contains_recipe_keyword(text: str) -> bool:
    """레시피 관련 키워드 포함 여부 확인"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in FILTER_KEYWORDS)


def collect_tweets(query: str, limit: int = 200) -> list:
    """단일 쿼리로 트윗 수집"""
    tweets = []
    try:
        scraper = sntwitter.TwitterSearchScraper(query)
        for i, tweet in enumerate(scraper.get_items()):
            if i >= limit:
                break

            # 길이 필터
            if len(tweet.rawContent) < MIN_TEXT_LENGTH:
                continue

            # 키워드 필터
            if not contains_recipe_keyword(tweet.rawContent):
                continue

            tweets.append({
                "id": tweet.id,
                "text": tweet.rawContent,
                "author": tweet.user.username if tweet.user else None,
                "likes": tweet.likeCount,
                "created_at": tweet.date.isoformat() if tweet.date else None,
                "media_urls": [m.fullUrl for m in (tweet.media or []) if hasattr(m, 'fullUrl')],
                "query": query,
            })

            if (i + 1) % 50 == 0:
                print(f"  {query[:30]}... : {len(tweets)}개 수집")

    except Exception as e:
        print(f"❌ 쿼리 실패 [{query}]: {e}")

    return tweets


def main():
    print("=" * 50)
    print("X(트위터) 레시피 수집 시작")
    print(f"쿼리 수: {len(QUERIES)}")
    print(f"쿼리당 목표: {TWEETS_PER_QUERY}개")
    print("=" * 50)

    all_tweets = []

    for i, query in enumerate(QUERIES, 1):
        print(f"\n[{i}/{len(QUERIES)}] 수집 중: {query}")
        tweets = collect_tweets(query, TWEETS_PER_QUERY)
        print(f"  → {len(tweets)}개 수집됨")
        all_tweets.extend(tweets)

    # 중복 제거 (id 기준)
    unique_tweets = {t["id"]: t for t in all_tweets}
    final_tweets = list(unique_tweets.values())

    print(f"\n총 수집: {len(all_tweets)}개")
    print(f"중복 제거 후: {len(final_tweets)}개")

    # CSV 저장
    csv_path = os.path.join(OUTPUT_DIR, "x_recipes_raw.csv")
    df = pd.DataFrame(final_tweets)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"✓ CSV 저장: {csv_path}")

    # JSON 저장
    json_path = os.path.join(OUTPUT_DIR, "x_recipes_raw.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_tweets, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON 저장: {json_path}")

    # 통계 출력
    print("\n" + "=" * 50)
    print("수집 완료!")
    print(f"- 총 트윗: {len(final_tweets)}개")
    if final_tweets:
        df_stats = pd.DataFrame(final_tweets)
        print(f"- 쿼리별 분포:")
        for q, cnt in df_stats.groupby("query").size().items():
            print(f"    {q[:40]}: {cnt}개")
    print("=" * 50)


if __name__ == "__main__":
    main()
