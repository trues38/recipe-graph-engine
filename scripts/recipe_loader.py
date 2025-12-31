"""처리된 레시피 데이터를 Neo4j에 적재하는 스크립트"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.neo4j_client import get_neo4j_client


async def load_ingredient(client, ingredient: dict) -> None:
    """재료 노드 생성"""
    query = """
    MERGE (i:Ingredient {name: $name})
    ON CREATE SET
        i.category = $category,
        i.vegan = $vegan
    """
    # 기본 카테고리 추론
    name = ingredient["name"]
    category = "기타"
    vegan = True

    meat_keywords = ["고기", "돼지", "소", "닭", "오리", "양"]
    seafood_keywords = ["새우", "생선", "조개", "오징어", "멸치"]
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

    await client.execute_write(
        query,
        {"name": name, "category": category, "vegan": vegan},
    )


async def load_recipe(client, recipe: dict) -> None:
    """레시피 노드 생성"""
    query = """
    MERGE (r:Recipe {name: $name})
    SET r.category = $category,
        r.cuisine = $cuisine,
        r.time_minutes = $time_minutes,
        r.difficulty = $difficulty,
        r.servings = $servings,
        r.total_calories = $total_calories,
        r.total_protein = $total_protein,
        r.total_carbs = $total_carbs,
        r.total_fat = $total_fat,
        r.tags = $tags,
        r.spicy_level = $spicy_level,
        r.description = $description,
        r.steps = $steps,
        r.tips = $tips,
        r.suitable_for = $suitable_for,
        r.avoid_for = $avoid_for
    """
    await client.execute_write(
        query,
        {
            "name": recipe["name"],
            "category": recipe.get("category", "기타"),
            "cuisine": recipe.get("cuisine", "한식"),
            "time_minutes": recipe.get("time_minutes", 30),
            "difficulty": recipe.get("difficulty", "보통"),
            "servings": recipe.get("servings", 2),
            "total_calories": recipe.get("total_calories", 0),
            "total_protein": recipe.get("total_protein", 0),
            "total_carbs": recipe.get("total_carbs", 0),
            "total_fat": recipe.get("total_fat", 0),
            "tags": recipe.get("tags", []),
            "spicy_level": recipe.get("spicy_level", 0),
            "description": recipe.get("description", ""),
            "steps": recipe.get("steps", []),
            "tips": recipe.get("tips", ""),
            "suitable_for": recipe.get("suitable_for", []),
            "avoid_for": recipe.get("avoid_for", []),
        },
    )


async def create_required_for_edge(
    client,
    recipe_name: str,
    ingredient: dict,
) -> None:
    """REQUIRED_FOR 엣지 생성"""
    query = """
    MATCH (i:Ingredient {name: $ingredient_name})
    MATCH (r:Recipe {name: $recipe_name})
    MERGE (i)-[req:REQUIRED_FOR]->(r)
    SET req.amount = $amount,
        req.unit = $unit,
        req.optional = $optional,
        req.prep = $prep
    """
    await client.execute_write(
        query,
        {
            "ingredient_name": ingredient["name"],
            "recipe_name": recipe_name,
            "amount": ingredient.get("amount", 0),
            "unit": ingredient.get("unit", "g"),
            "optional": ingredient.get("optional", False),
            "prep": ingredient.get("prep", ""),
        },
    )


async def create_goal_edges(client, recipe: dict) -> None:
    """SUITABLE_FOR 엣지 생성"""
    suitable_for = recipe.get("suitable_for", [])
    for goal_name in suitable_for:
        query = """
        MATCH (r:Recipe {name: $recipe_name})
        MATCH (g:Goal {name: $goal_name})
        MERGE (r)-[s:SUITABLE_FOR]->(g)
        SET s.score = 0.8
        """
        await client.execute_write(
            query,
            {"recipe_name": recipe["name"], "goal_name": goal_name},
        )


async def create_condition_edges(client, recipe: dict) -> None:
    """AVOID_FOR 엣지 생성"""
    avoid_for = recipe.get("avoid_for", [])
    for condition_name in avoid_for:
        query = """
        MATCH (r:Recipe {name: $recipe_name})
        MATCH (c:Condition {name: $condition_name})
        MERGE (r)-[a:AVOID_FOR]->(c)
        SET a.severity = 'medium'
        """
        await client.execute_write(
            query,
            {"recipe_name": recipe["name"], "condition_name": condition_name},
        )


async def create_reference_nodes(client) -> None:
    """Goal, Condition, Diet 참조 노드 생성"""
    # Goal 노드들
    goals = ["다이어트", "벌크업", "유지", "저탄수", "고단백"]
    for name in goals:
        await client.execute_write(
            "MERGE (g:Goal {name: $name})",
            {"name": name},
        )

    # Condition 노드들
    conditions = ["당뇨", "고혈압", "통풍", "신장질환", "고지혈증", "저탄수"]
    for name in conditions:
        await client.execute_write(
            "MERGE (c:Condition {name: $name})",
            {"name": name},
        )

    # Diet 노드들
    diets = ["비건", "채식", "페스코", "락토", "오보"]
    for name in diets:
        await client.execute_write(
            "MERGE (d:Diet {name: $name})",
            {"name": name},
        )


def classify_diet_compatibility(recipe: dict) -> list[str]:
    """레시피의 식단 호환성 분류"""
    ingredients = recipe.get("ingredients", [])
    ing_names = " ".join([i["name"].lower() for i in ingredients])

    # 키워드 기반 분류
    meat_keywords = ["고기", "돼지", "소고기", "닭", "오리", "양", "베이컨", "햄", "소시지", "갈비"]
    seafood_keywords = ["새우", "생선", "조개", "오징어", "멸치", "굴", "게", "참치", "연어", "문어"]
    dairy_keywords = ["우유", "치즈", "버터", "크림", "요거트", "요구르트"]
    egg_keywords = ["계란", "달걀", "노른자", "흰자"]

    has_meat = any(kw in ing_names for kw in meat_keywords)
    has_seafood = any(kw in ing_names for kw in seafood_keywords)
    has_dairy = any(kw in ing_names for kw in dairy_keywords)
    has_egg = any(kw in ing_names for kw in egg_keywords)

    compatible = []

    # 비건: 동물성 재료 없음
    if not has_meat and not has_seafood and not has_dairy and not has_egg:
        compatible.extend(["비건", "채식", "락토", "오보", "페스코"])
    # 락토: 유제품만 허용
    elif not has_meat and not has_seafood and not has_egg and has_dairy:
        compatible.extend(["락토", "채식"])
    # 오보: 달걀만 허용
    elif not has_meat and not has_seafood and not has_dairy and has_egg:
        compatible.extend(["오보", "채식"])
    # 페스코: 해산물 허용
    elif not has_meat and has_seafood:
        compatible.append("페스코")

    return compatible


async def create_diet_edges(client, recipe: dict) -> None:
    """COMPATIBLE_WITH 엣지 생성"""
    compatible_diets = classify_diet_compatibility(recipe)
    for diet_name in compatible_diets:
        query = """
        MATCH (r:Recipe {name: $recipe_name})
        MATCH (d:Diet {name: $diet_name})
        MERGE (r)-[:COMPATIBLE_WITH]->(d)
        """
        await client.execute_write(
            query,
            {"recipe_name": recipe["name"], "diet_name": diet_name},
        )


async def load_recipes_from_file(file_path: Path) -> None:
    """JSON 파일에서 레시피 로드"""
    print("=" * 50)
    print("Recipe Loader - Neo4j")
    print("=" * 50)

    with open(file_path, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    print(f"Loaded {len(recipes)} recipes from {file_path}")

    async with get_neo4j_client() as client:
        # 0. 참조 노드 생성 (Goal, Condition, Diet)
        print("\n[0/5] Creating reference nodes (Goal, Condition, Diet)...")
        await create_reference_nodes(client)
        print("  ✓ Created Goal, Condition, Diet nodes")
        # 1. 모든 재료 노드 생성
        print("\n[1/4] Creating ingredient nodes...")
        all_ingredients = set()
        for recipe in recipes:
            for ing in recipe.get("ingredients", []):
                all_ingredients.add(ing["name"])

        for name in all_ingredients:
            await load_ingredient(client, {"name": name})
            print(f"  ✓ {name}")

        # 2. 레시피 노드 생성
        print("\n[2/4] Creating recipe nodes...")
        for recipe in recipes:
            await load_recipe(client, recipe)
            print(f"  ✓ {recipe['name']}")

        # 3. REQUIRED_FOR 엣지 생성
        print("\n[3/4] Creating REQUIRED_FOR edges...")
        for recipe in recipes:
            for ing in recipe.get("ingredients", []):
                await create_required_for_edge(client, recipe["name"], ing)
            print(f"  ✓ {recipe['name']} - {len(recipe.get('ingredients', []))} ingredients")

        # 4. Goal/Condition 엣지 생성
        print("\n[4/5] Creating Goal/Condition edges...")
        for recipe in recipes:
            await create_goal_edges(client, recipe)
            await create_condition_edges(client, recipe)
            suitable = len(recipe.get("suitable_for", []))
            avoid = len(recipe.get("avoid_for", []))
            if suitable > 0 or avoid > 0:
                print(f"  ✓ {recipe['name']} - SUITABLE:{suitable}, AVOID:{avoid}")

        # 5. Diet 호환성 엣지 생성
        print("\n[5/7] Creating Diet compatibility edges...")
        diet_count = 0
        for recipe in recipes:
            await create_diet_edges(client, recipe)
            diets = classify_diet_compatibility(recipe)
            if diets:
                diet_count += 1
        print(f"  ✓ {diet_count} recipes with diet compatibility")

        # 6. SIMILAR_TO 관계 생성 (재료 공유 기반)
        print("\n[6/7] Creating SIMILAR_TO edges (this may take a while)...")
        similar_query = """
        MATCH (r1:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)-[:REQUIRED_FOR]-(r2:Recipe)
        WHERE r1.name < r2.name
        WITH r1, r2, count(DISTINCT i) AS shared,
             COUNT { (r1)-[:REQUIRED_FOR]-() } AS total1,
             COUNT { (r2)-[:REQUIRED_FOR]-() } AS total2
        WHERE shared >= 3
        WITH r1, r2, shared,
             shared * 1.0 / (total1 + total2 - shared) AS jaccard
        WHERE jaccard >= 0.2
        MERGE (r1)-[s:SIMILAR_TO]->(r2)
        SET s.score = jaccard,
            s.shared_ingredients = shared
        RETURN count(*) AS created
        """
        result = await client.execute_query(similar_query)
        similar_count = result[0]["created"] if result else 0
        print(f"  ✓ Created {similar_count} SIMILAR_TO relationships")

        # 7. PAIRS_WELL 관계 생성 (함께 자주 사용되는 재료)
        print("\n[7/7] Creating PAIRS_WELL edges...")
        pairing_query = """
        MATCH (i1:Ingredient)-[:REQUIRED_FOR]->(r:Recipe)<-[:REQUIRED_FOR]-(i2:Ingredient)
        WHERE i1.name < i2.name
        WITH i1, i2, count(DISTINCT r) AS co_occurrence
        WHERE co_occurrence >= 10
        MERGE (i1)-[p:PAIRS_WELL]->(i2)
        SET p.count = co_occurrence
        RETURN count(*) AS created
        """
        result = await client.execute_query(pairing_query)
        pairing_count = result[0]["created"] if result else 0
        print(f"  ✓ Created {pairing_count} PAIRS_WELL relationships")

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


async def main():
    """메인 실행 함수"""
    file_path = Path(__file__).parent.parent / "data" / "processed" / "recipes.json"

    if not file_path.exists():
        print(f"Error: {file_path} not found")
        print("Run 'python scripts/structurizer.py' first to generate recipe data")
        return

    await load_recipes_from_file(file_path)


if __name__ == "__main__":
    asyncio.run(main())
