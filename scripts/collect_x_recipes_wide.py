"""
X(트위터) 레시피 - 넓은 쿼리로 대량 수집 후 좋아요 Top 분석
"""

import os
import json
import httpx
import pandas as pd
from datetime import datetime

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_API_URL = "https://api.x.ai/v1/chat/completions"

OUTPUT_DIR = "/Users/js/Documents/recipe/x_recipes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 넓은 쿼리 - 다양하게
WIDE_QUERIES = [
    # 일반 레시피
    "레시피 인기",
    "요리 꿀팁",
    "집밥 레시피",
    "혼밥 요리",
    "야식 레시피",
    "간단 요리법",
    "초간단 레시피",
    "자취생 요리",
    "원룸 요리",
    # 카테고리별
    "국물요리 레시피",
    "볶음요리 레시피",
    "찌개 레시피",
    "반찬 만들기",
    "밑반찬 레시피",
    "일품요리",
    "면요리 레시피",
    "밥요리",
    # 트렌드/바이럴
    "약과 만들기",
    "탕후루",
    "크로플",
    "마라탕 만들기",
    "떡볶이 레시피",
    "치킨 만들기",
    "파스타 레시피",
    # 건강/다이어트
    "다이어트 레시피",
    "건강식 요리",
    "단백질 요리",
    "샐러드 레시피",
    # 시간대별
    "아침식사 레시피",
    "점심 도시락",
    "저녁메뉴 추천",
    "야식 만들기",
    "간식 레시피",
    # 재료별
    "계란요리",
    "두부요리",
    "닭가슴살 요리",
    "돼지고기 요리",
    "소고기 요리",
]


def search_wide(query: str) -> list:
    """넓은 검색 - 좋아요 높은 것 위주"""

    prompt = f"""X(트위터)에서 "{query}" 관련 가장 인기있는(좋아요 많은) 게시물들을 찾아줘.

실제 바이럴됐거나 많이 공유된 레시피 트윗 위주로.

JSON 배열로 반환:
[
  {{
    "text": "트윗 전체 내용",
    "author": "@아이디",
    "likes": 좋아요수(숫자),
    "retweets": 리트윗수(숫자),
    "recipe_name": "요리명",
    "ingredients": ["재료1", "재료2"],
    "key_tip": "이 레시피의 핵심 포인트/꿀팁"
  }}
]

좋아요 100개 이상인 것 위주로 최대 30개. JSON만 반환."""

    try:
        response = httpx.post(
            XAI_API_URL,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-2-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
            },
            timeout=90.0,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        # JSON 파싱
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        recipes = json.loads(content.strip())
        for r in recipes:
            r["query"] = query
        return recipes

    except Exception as e:
        print(f"  ❌ {query}: {e}")
        return []


def main():
    print("=" * 60)
    print("🔥 X 레시피 대량 수집 - 좋아요 Top 분석")
    print(f"쿼리 수: {len(WIDE_QUERIES)}")
    print("=" * 60)

    all_recipes = []

    for i, query in enumerate(WIDE_QUERIES, 1):
        print(f"[{i}/{len(WIDE_QUERIES)}] {query}...", end=" ")
        recipes = search_wide(query)
        print(f"→ {len(recipes)}개")
        all_recipes.extend(recipes)

    # 중복 제거 (recipe_name + author 기준)
    seen = set()
    unique = []
    for r in all_recipes:
        key = (r.get("recipe_name", ""), r.get("author", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"\n총 수집: {len(all_recipes)}개 → 중복제거: {len(unique)}개")

    # 좋아요 순 정렬
    unique.sort(key=lambda x: x.get("likes", 0), reverse=True)

    # 저장
    json_path = os.path.join(OUTPUT_DIR, "x_recipes_wide.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON: {json_path}")

    # CSV
    csv_data = []
    for r in unique:
        csv_data.append({
            "likes": r.get("likes", 0),
            "retweets": r.get("retweets", 0),
            "recipe_name": r.get("recipe_name", ""),
            "author": r.get("author", ""),
            "key_tip": r.get("key_tip", ""),
            "ingredients": ", ".join(r.get("ingredients", [])),
            "text": r.get("text", "")[:200],
            "query": r.get("query", ""),
        })

    csv_path = os.path.join(OUTPUT_DIR, "x_recipes_wide.csv")
    df = pd.DataFrame(csv_data)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"✓ CSV: {csv_path}")

    # Top 20 출력
    print("\n" + "=" * 60)
    print("🏆 좋아요 TOP 20")
    print("=" * 60)

    for i, r in enumerate(unique[:20], 1):
        likes = r.get("likes", 0)
        rts = r.get("retweets", 0)
        name = r.get("recipe_name", "?")
        tip = r.get("key_tip", "")[:40]
        author = r.get("author", "")
        print(f"{i:2}. ❤️{likes:,} 🔄{rts:,} | {name}")
        print(f"    💡 {tip}...")
        print(f"    👤 {author}")
        print()


if __name__ == "__main__":
    main()
