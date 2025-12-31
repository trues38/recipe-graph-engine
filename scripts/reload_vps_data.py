"""VPS Neo4j에 깨끗한 레시피 데이터 재로드"""

import asyncio
import json
from pathlib import Path
from neo4j import AsyncGraphDatabase


# VPS Neo4j 연결 정보
VPS_NEO4J_URI = "bolt://141.164.35.214:7690"
VPS_NEO4J_USER = "neo4j"
VPS_NEO4J_PASSWORD = "recipe_vultr_2025"

# 최종 정규화된 데이터 사용 (파이프라인 결과물)
DATA_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_enriched.json"
# 폴백: 중간 단계 파일
FALLBACK_FILES = [
    Path(__file__).parent.parent / "data" / "processed" / "recipes_deduped.json",
    Path(__file__).parent.parent / "data" / "processed" / "recipes_classified.json",
    Path(__file__).parent.parent / "data" / "processed" / "recipes_final.json",
    Path(__file__).parent.parent / "data" / "processed" / "recipes_normalized.json",
    Path(__file__).parent.parent / "data" / "processed" / "recipes_cleaned.json",
]

import re

def clean_ingredient_name(name: str) -> str:
    """재료 이름 정제"""
    # 괄호 접두어 제거: (반죽재료), (양념), (소스) 등
    name = re.sub(r'^\([^)]+\)\s*', '', name)

    # 숫자+단위 패턴 제거: 1T, 2큰술, 300ml 등
    name = re.sub(r'\s*\d+[TtL㎖㎏g큰술작은술개인분컵ml]*\s*$', '', name)
    name = re.sub(r'\s*\d+~?\d*[TtL㎖㎏g큰술작은술개인분컵ml]*\s*$', '', name)

    # 조리법 텍스트 제거 (마침표, ||, 숫자) 포함 문장)
    if '||' in name or ') ' in name:
        # || 이전 부분만 추출
        name = name.split('||')[0].strip()
        name = name.split(') ')[-1].strip() if ') ' in name else name

    # 조리 설명 제거 (끓인다, 넣는다, 썰어 등)
    if any(word in name for word in ['끓인다', '넣는다', '썰어', '볶는다', '얹는다', '담', '두께']):
        return ""

    # 너무 긴 재료명 제거 (대부분 조리법)
    if len(name) > 15:
        return ""

    # 숫자로 시작하면 제거
    if name and name[0].isdigit():
        return ""

    return name.strip()


def is_valid_ingredient(name: str) -> bool:
    """유효한 재료 이름인지 확인"""
    if not name or len(name) < 2:
        return False
    # 숫자만 있으면 무효
    if name.replace(' ', '').isdigit():
        return False
    # 특수문자가 너무 많으면 무효
    if sum(1 for c in name if not c.isalnum() and c != ' ') > 2:
        return False
    return True


async def clear_database(driver):
    """기존 데이터 삭제"""
    print("Clearing existing data...")
    async with driver.session() as session:
        # 모든 관계 삭제
        await session.run("MATCH ()-[r]->() DELETE r")
        # 모든 노드 삭제
        await session.run("MATCH (n) DELETE n")
    print("  ✓ Database cleared")


async def load_ingredient(session, name: str):
    """재료 노드 생성"""
    category = "기타"
    vegan = True

    meat_keywords = ["고기", "돼지", "소", "닭", "오리", "양", "갈비", "삼겹"]
    seafood_keywords = ["새우", "생선", "조개", "오징어", "멸치", "굴", "게"]
    dairy_keywords = ["우유", "치즈", "버터", "크림"]

    for kw in meat_keywords:
        if kw in name:
            category = "육류"
            vegan = False
            break
    for kw in seafood_keywords:
        if kw in name:
            category = "해산물"
            vegan = False
            break
    for kw in dairy_keywords:
        if kw in name:
            category = "유제품"
            vegan = False
            break

    if "계란" in name or "달걀" in name:
        category = "계란"
        vegan = False

    await session.run(
        """
        MERGE (i:Ingredient {name: $name})
        ON CREATE SET i.category = $category, i.vegan = $vegan
        """,
        {"name": name, "category": category, "vegan": vegan},
    )


async def load_recipe(session, recipe: dict):
    """레시피 노드 생성 (정규화된 필드 포함)"""
    await session.run(
        """
        MERGE (r:Recipe {name: $name})
        SET r.category = $category,
            r.category_group = $category_group,
            r.cuisine = $cuisine,
            r.personas = $personas,
            r.time_minutes = $time_minutes,
            r.cooking_time = $time_minutes,
            r.difficulty = $difficulty,
            r.servings = $servings,
            r.total_calories = $total_calories,
            r.calories = $total_calories,
            r.total_protein = $total_protein,
            r.total_carbs = $total_carbs,
            r.total_fat = $total_fat,
            r.sodium = $sodium,
            r.tags = $tags,
            r.spicy_level = $spicy_level,
            r.description = $description,
            r.steps = $steps,
            r.tips = $tips,
            r.suitable_for = $suitable_for,
            r.avoid_for = $avoid_for,
            r.original_name = $original_name,
            r.trending = false
        """,
        {
            "name": recipe["name"],
            "category": recipe.get("category", "기타"),
            "category_group": recipe.get("category_group", "메인요리"),
            "cuisine": recipe.get("cuisine", "한식"),
            "personas": recipe.get("personas", []),
            "time_minutes": recipe.get("time_minutes", 30),
            "difficulty": recipe.get("difficulty", "보통"),
            "servings": recipe.get("servings", 2),
            "total_calories": recipe.get("total_calories", 0),
            "total_protein": recipe.get("total_protein", 0),
            "total_carbs": recipe.get("total_carbs", 0),
            "total_fat": recipe.get("total_fat", 0),
            "sodium": recipe.get("sodium", 0),
            "tags": recipe.get("tags", []),
            "spicy_level": recipe.get("spicy_level", 0),
            "description": recipe.get("description", ""),
            "steps": recipe.get("steps", []),
            "tips": recipe.get("tips", ""),
            "suitable_for": recipe.get("suitable_for", []),
            "avoid_for": recipe.get("avoid_for", []),
            "original_name": recipe.get("original_name", recipe["name"]),
        },
    )


async def create_edge(session, recipe_name: str, ingredient: dict):
    """REQUIRED_FOR 엣지 생성"""
    await session.run(
        """
        MATCH (i:Ingredient {name: $ingredient_name})
        MATCH (r:Recipe {name: $recipe_name})
        MERGE (i)-[req:REQUIRED_FOR]->(r)
        SET req.amount = $amount,
            req.unit = $unit,
            req.optional = $optional
        """,
        {
            "ingredient_name": ingredient["name"],
            "recipe_name": recipe_name,
            "amount": ingredient.get("amount", 0),
            "unit": ingredient.get("unit", "g"),
            "optional": ingredient.get("optional", False),
        },
    )


async def create_reference_nodes(session):
    """참조 노드 생성"""
    # Goal 노드
    for name in ["다이어트", "벌크업", "유지", "저탄수", "고단백"]:
        await session.run("MERGE (g:Goal {name: $name})", {"name": name})

    # Condition 노드
    for name in ["당뇨", "고혈압", "통풍", "신장질환", "고지혈증", "저탄수"]:
        await session.run("MERGE (c:Condition {name: $name})", {"name": name})

    # Diet 노드
    for name in ["비건", "채식", "페스코", "락토", "오보"]:
        await session.run("MERGE (d:Diet {name: $name})", {"name": name})


async def create_indexes(driver):
    """인덱스 생성"""
    print("Creating indexes...")
    async with driver.session() as session:
        await session.run("CREATE INDEX IF NOT EXISTS FOR (r:Recipe) ON (r.name)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (i:Ingredient) ON (i.name)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (r:Recipe) ON (r.category)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (r:Recipe) ON (r.category_group)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (r:Recipe) ON (r.cuisine)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (r:Recipe) ON (r.trending)")
    print("  ✓ Indexes created")


async def main():
    print("=" * 60)
    print("VPS Neo4j Data Reload")
    print("=" * 60)

    # 데이터 로드 (폴백 지원)
    data_file = None
    if DATA_FILE.exists():
        data_file = DATA_FILE
    else:
        for fallback in FALLBACK_FILES:
            if fallback.exists():
                data_file = fallback
                break

    if not data_file:
        print("ERROR: No data file found!")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes from {data_file.name}")

    # Neo4j 연결
    driver = AsyncGraphDatabase.driver(
        VPS_NEO4J_URI,
        auth=(VPS_NEO4J_USER, VPS_NEO4J_PASSWORD),
    )

    try:
        await driver.verify_connectivity()
        print("Connected to VPS Neo4j")

        # 1. 기존 데이터 삭제
        await clear_database(driver)

        # 2. 인덱스 생성
        await create_indexes(driver)

        # 3. 참조 노드 생성
        print("\n[1/4] Creating reference nodes...")
        async with driver.session() as session:
            await create_reference_nodes(session)
        print("  ✓ Reference nodes created")

        # 4. 재료 노드 생성 (정제 후)
        print("\n[2/4] Creating ingredient nodes (cleaned)...")
        all_ingredients = set()
        for recipe in recipes:
            for ing in recipe.get("ingredients", []):
                cleaned_name = clean_ingredient_name(ing["name"])
                if is_valid_ingredient(cleaned_name):
                    all_ingredients.add(cleaned_name)

        async with driver.session() as session:
            for i, name in enumerate(sorted(all_ingredients)):
                await load_ingredient(session, name)
                if (i + 1) % 100 == 0:
                    print(f"  {i + 1}/{len(all_ingredients)} ingredients...")
        print(f"  ✓ {len(all_ingredients)} ingredients created (cleaned)")

        # 5. 레시피 노드 생성
        print("\n[3/4] Creating recipe nodes...")
        async with driver.session() as session:
            for i, recipe in enumerate(recipes):
                await load_recipe(session, recipe)
                if (i + 1) % 100 == 0:
                    print(f"  {i + 1}/{len(recipes)} recipes...")
        print(f"  ✓ {len(recipes)} recipes created")

        # 6. 관계 생성 (정제된 재료명 사용)
        print("\n[4/4] Creating relationships (cleaned)...")
        edge_count = 0
        skipped = 0
        async with driver.session() as session:
            for i, recipe in enumerate(recipes):
                for ing in recipe.get("ingredients", []):
                    cleaned_name = clean_ingredient_name(ing["name"])
                    if is_valid_ingredient(cleaned_name):
                        cleaned_ing = {**ing, "name": cleaned_name}
                        await create_edge(session, recipe["name"], cleaned_ing)
                        edge_count += 1
                    else:
                        skipped += 1
                if (i + 1) % 100 == 0:
                    print(f"  {i + 1}/{len(recipes)} recipes processed...")
        print(f"  ✓ {edge_count} relationships created (skipped {skipped} invalid)")

        # 7. 통계 출력
        print("\n" + "=" * 60)
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Recipe) WITH count(r) AS recipes
                MATCH (i:Ingredient) WITH recipes, count(i) AS ingredients
                MATCH ()-[rel:REQUIRED_FOR]->() WITH recipes, ingredients, count(rel) AS relations
                RETURN recipes, ingredients, relations
                """
            )
            stats = await result.single()
            print(f"Final stats:")
            print(f"  - Recipes: {stats['recipes']}")
            print(f"  - Ingredients: {stats['ingredients']}")
            print(f"  - Relations: {stats['relations']}")
        print("=" * 60)
        print("Done!")

    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
