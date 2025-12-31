"""
X(트위터) 레시피 데이터 수집 - xAI Grok API 사용
실시간 X 검색 기능 활용
"""

import os
import json
import httpx
import pandas as pd
from datetime import datetime

# xAI API 설정
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_API_URL = "https://api.x.ai/v1/chat/completions"

# 출력 경로
OUTPUT_DIR = "/Users/js/Documents/recipe/x_recipes"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 검색 쿼리 목록
QUERIES = [
    "한국 레시피 추천",
    "자취 요리 레시피",
    "찌개 만드는 법",
    "볶음밥 만들기",
    "반찬 레시피",
    "약과 만들기",
    "탕후루 레시피",
    "간단 요리",
    "김치찌개 레시피",
    "제육볶음 만들기",
]


def search_recipes_with_grok(query: str, limit: int = 20) -> list:
    """Grok API로 X에서 레시피 검색"""

    prompt = f"""X(트위터)에서 "{query}" 관련 인기 게시물을 검색해서 레시피 정보를 추출해줘.

다음 형식으로 JSON 배열로 반환해줘:
[
  {{
    "text": "트윗 본문 (레시피 내용 포함)",
    "author": "작성자 @아이디",
    "likes": 좋아요 수 (숫자),
    "recipe_name": "요리명",
    "ingredients": ["재료1", "재료2", ...],
    "steps": ["단계1", "단계2", ...]
  }}
]

최대 {limit}개의 레시피를 찾아줘. 실제 X 게시물 데이터 기반으로 응답해줘.
JSON만 반환하고 다른 설명은 하지 마."""

    try:
        response = httpx.post(
            XAI_API_URL,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-2-latest",  # grok-4.1-fast 대신 grok-2-latest 사용
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
            timeout=60.0,
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # JSON 파싱 시도
        try:
            # JSON 블록 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            recipes = json.loads(content.strip())
            for r in recipes:
                r["query"] = query
                r["collected_at"] = datetime.now().isoformat()
            return recipes
        except json.JSONDecodeError as e:
            print(f"  JSON 파싱 실패: {e}")
            print(f"  응답: {content[:200]}...")
            return []

    except Exception as e:
        print(f"❌ API 호출 실패 [{query}]: {e}")
        return []


def main():
    print("=" * 50)
    print("X(트위터) 레시피 수집 - Grok API")
    print(f"쿼리 수: {len(QUERIES)}")
    print("=" * 50)

    all_recipes = []

    for i, query in enumerate(QUERIES, 1):
        print(f"\n[{i}/{len(QUERIES)}] 검색 중: {query}")
        recipes = search_recipes_with_grok(query, limit=20)
        print(f"  → {len(recipes)}개 수집됨")
        all_recipes.extend(recipes)

    print(f"\n총 수집: {len(all_recipes)}개")

    if not all_recipes:
        print("수집된 레시피가 없습니다.")
        return

    # JSON 저장
    json_path = os.path.join(OUTPUT_DIR, "x_recipes_grok.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_recipes, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON 저장: {json_path}")

    # CSV 저장 (평탄화)
    csv_data = []
    for r in all_recipes:
        csv_data.append({
            "recipe_name": r.get("recipe_name", ""),
            "text": r.get("text", ""),
            "author": r.get("author", ""),
            "likes": r.get("likes", 0),
            "ingredients": ", ".join(r.get("ingredients", [])),
            "steps": " | ".join(r.get("steps", [])),
            "query": r.get("query", ""),
            "collected_at": r.get("collected_at", ""),
        })

    csv_path = os.path.join(OUTPUT_DIR, "x_recipes_grok.csv")
    df = pd.DataFrame(csv_data)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"✓ CSV 저장: {csv_path}")

    # 통계 출력
    print("\n" + "=" * 50)
    print("수집 완료!")
    print(f"- 총 레시피: {len(all_recipes)}개")
    print(f"- 쿼리별 분포:")
    for q in QUERIES:
        cnt = len([r for r in all_recipes if r.get("query") == q])
        print(f"    {q}: {cnt}개")
    print("=" * 50)


if __name__ == "__main__":
    main()
