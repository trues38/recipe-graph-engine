"""
X 트렌드 레시피를 Neo4j에 적재
"""

import json
import asyncio
from neo4j import AsyncGraphDatabase

NEO4J_URI = "bolt://141.164.35.214:7690"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "recipe_vultr_2025"

INPUT_FILE = "/Users/js/Documents/recipe/x_recipes/x_recipes_wide.json"
MIN_LIKES = 500  # 500+ 좋아요만


async def load_trends():
    # 데이터 로드
    with open(INPUT_FILE, 'r') as f:
        all_recipes = json.load(f)

    # 500+ 좋아요 필터링 & 중복 제거
    seen_names = set()
    trending = []
    for r in sorted(all_recipes, key=lambda x: x.get('likes', 0), reverse=True):
        name = r.get('recipe_name', '').strip()
        if not name or name in seen_names:
            continue
        if r.get('likes', 0) >= MIN_LIKES:
            seen_names.add(name)
            trending.append(r)

    print(f"트렌드 레시피: {len(trending)}개 (좋아요 {MIN_LIKES}+)")

    # Neo4j 연결
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    async with driver.session() as session:
        # 기존 트렌드 태그 제거 (재실행 대비)
        await session.run("MATCH (r:Recipe) REMOVE r.trending, r.x_likes, r.x_tip")
        print("✓ 기존 트렌드 태그 제거")

        added = 0
        updated = 0

        for r in trending:
            name = r.get('recipe_name', '')
            likes = r.get('likes', 0)
            tip = r.get('key_tip', '')
            ingredients = r.get('ingredients', [])

            # 기존 레시피 있으면 업데이트, 없으면 생성
            result = await session.run("""
                MATCH (r:Recipe {name: $name})
                SET r.trending = true,
                    r.x_likes = $likes,
                    r.x_tip = $tip
                RETURN r.name
            """, name=name, likes=likes, tip=tip)

            record = await result.single()
            if record:
                updated += 1
                print(f"  ✓ 업데이트: {name} (❤️{likes})")
            else:
                # 새 레시피 생성
                # 카테고리 추정
                category = "기타"
                if any(k in name for k in ['볶음', '볶음밥']): category = "볶음"
                elif any(k in name for k in ['찌개', '국', '탕']): category = "국"
                elif any(k in name for k in ['파스타', '면', '라면']): category = "면"
                elif any(k in name for k in ['밥', '김밥', '덮밥']): category = "밥"
                elif any(k in name for k in ['떡볶이']): category = "떡볶이"
                elif any(k in name for k in ['샐러드']): category = "샐러드"
                elif any(k in name for k in ['토스트', '빵', '케이크']): category = "빵/간식"

                await session.run("""
                    CREATE (r:Recipe {
                        name: $name,
                        category: $category,
                        difficulty: '쉬움',
                        trending: true,
                        x_likes: $likes,
                        x_tip: $tip,
                        source: 'x_trend'
                    })
                """, name=name, category=category, likes=likes, tip=tip)

                # 재료 연결
                for ing in ingredients:
                    ing = ing.strip()
                    if not ing:
                        continue
                    await session.run("""
                        MERGE (i:Ingredient {name: $ing})
                        WITH i
                        MATCH (r:Recipe {name: $recipe_name})
                        MERGE (r)-[:REQUIRED_FOR]->(i)
                    """, ing=ing, recipe_name=name)

                added += 1
                print(f"  + 신규: {name} (❤️{likes}, 재료 {len(ingredients)}개)")

    await driver.close()

    print("\n" + "=" * 50)
    print(f"✅ 완료!")
    print(f"  - 업데이트: {updated}개")
    print(f"  - 신규 추가: {added}개")
    print(f"  - 총 트렌드: {updated + added}개")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(load_trends())
