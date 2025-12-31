"""Neo4j 스키마 생성 및 초기 데이터 적재 스크립트"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.neo4j_client import get_neo4j_client


# ============== 스키마 생성 쿼리 ==============

SCHEMA_QUERIES = [
    # 제약조건 (Unique)
    """CREATE CONSTRAINT ingredient_name IF NOT EXISTS
       FOR (i:Ingredient) REQUIRE i.name IS UNIQUE""",

    """CREATE CONSTRAINT recipe_name IF NOT EXISTS
       FOR (r:Recipe) REQUIRE r.name IS UNIQUE""",

    """CREATE CONSTRAINT goal_name IF NOT EXISTS
       FOR (g:Goal) REQUIRE g.name IS UNIQUE""",

    """CREATE CONSTRAINT condition_name IF NOT EXISTS
       FOR (c:Condition) REQUIRE c.name IS UNIQUE""",

    """CREATE CONSTRAINT diet_name IF NOT EXISTS
       FOR (d:Diet) REQUIRE d.name IS UNIQUE""",

    """CREATE CONSTRAINT technique_name IF NOT EXISTS
       FOR (t:Technique) REQUIRE t.name IS UNIQUE""",

    # 인덱스
    """CREATE INDEX ingredient_category IF NOT EXISTS
       FOR (i:Ingredient) ON (i.category)""",

    """CREATE INDEX recipe_category IF NOT EXISTS
       FOR (r:Recipe) ON (r.category)""",

    """CREATE INDEX recipe_cuisine IF NOT EXISTS
       FOR (r:Recipe) ON (r.cuisine)""",

    """CREATE INDEX recipe_calories IF NOT EXISTS
       FOR (r:Recipe) ON (r.total_calories)""",

    """CREATE INDEX recipe_time IF NOT EXISTS
       FOR (r:Recipe) ON (r.time_minutes)""",
]


# ============== 기본 데이터 ==============

DEFAULT_GOALS = [
    {
        "name": "다이어트",
        "daily_calories": 1500,
        "protein_ratio": 0.30,
        "carbs_ratio": 0.40,
        "fat_ratio": 0.30,
        "avoid_tags": ["고탄수화물", "튀김", "고칼로리"],
        "prefer_tags": ["저칼로리", "고단백", "식이섬유"],
    },
    {
        "name": "벌크업",
        "daily_calories": 3000,
        "protein_ratio": 0.35,
        "carbs_ratio": 0.45,
        "fat_ratio": 0.20,
        "avoid_tags": ["저칼로리"],
        "prefer_tags": ["고단백", "고칼로리", "탄수화물"],
    },
    {
        "name": "유지",
        "daily_calories": 2000,
        "protein_ratio": 0.25,
        "carbs_ratio": 0.50,
        "fat_ratio": 0.25,
        "avoid_tags": [],
        "prefer_tags": ["균형"],
    },
    {
        "name": "저탄수",
        "daily_calories": 1800,
        "protein_ratio": 0.35,
        "carbs_ratio": 0.15,
        "fat_ratio": 0.50,
        "avoid_tags": ["고탄수화물", "밥", "면", "빵"],
        "prefer_tags": ["저탄수", "고지방", "케토"],
    },
]

DEFAULT_CONDITIONS = [
    {
        "name": "당뇨",
        "avoid_ingredients": ["설탕", "흰쌀", "흰밀가루", "꿀", "물엿"],
        "limit_nutrients": {"carbs": 130},
        "prefer_tags": ["저GI", "식이섬유", "통곡물"],
        "description": "혈당 관리가 필요한 상태",
    },
    {
        "name": "고혈압",
        "avoid_ingredients": ["소금", "간장", "된장", "젓갈"],
        "limit_nutrients": {"sodium": 2000},
        "prefer_tags": ["저나트륨", "칼륨"],
        "description": "나트륨 제한이 필요한 상태",
    },
    {
        "name": "통풍",
        "avoid_ingredients": ["내장", "맥주", "등푸른생선", "새우"],
        "limit_nutrients": {"purine": 400},
        "prefer_tags": ["저퓨린", "채소"],
        "description": "퓨린 섭취 제한이 필요한 상태",
    },
    {
        "name": "신장질환",
        "avoid_ingredients": ["바나나", "감자", "토마토", "견과류"],
        "limit_nutrients": {"protein": 50, "potassium": 2000},
        "prefer_tags": ["저단백", "저칼륨"],
        "description": "단백질과 칼륨 제한이 필요한 상태",
    },
    {
        "name": "고지혈증",
        "avoid_ingredients": ["버터", "라드", "마가린"],
        "limit_nutrients": {"fat": 50, "cholesterol": 200},
        "prefer_tags": ["저지방", "불포화지방", "식이섬유"],
        "description": "지방과 콜레스테롤 제한이 필요한 상태",
    },
]

DEFAULT_DIETS = [
    {
        "name": "비건",
        "exclude_categories": ["육류", "해산물", "유제품", "계란"],
        "exclude_ingredients": ["꿀", "젤라틴", "버터"],
        "description": "동물성 식품 완전 배제",
    },
    {
        "name": "락토",
        "exclude_categories": ["육류", "해산물", "계란"],
        "exclude_ingredients": [],
        "description": "유제품만 허용",
    },
    {
        "name": "오보",
        "exclude_categories": ["육류", "해산물", "유제품"],
        "exclude_ingredients": [],
        "description": "계란만 허용",
    },
    {
        "name": "페스코",
        "exclude_categories": ["육류"],
        "exclude_ingredients": [],
        "description": "해산물만 허용",
    },
    {
        "name": "폴로",
        "exclude_categories": ["적색육", "해산물"],
        "exclude_ingredients": ["돼지고기", "소고기", "양고기"],
        "description": "가금류만 허용",
    },
]

DEFAULT_TECHNIQUES = [
    {
        "name": "수비드",
        "difficulty": "어려움",
        "equipment": ["수비드 머신", "진공포장기"],
        "description": "저온에서 장시간 조리하는 기법",
        "best_for": ["스테이크", "닭가슴살", "연어"],
    },
    {
        "name": "에어프라이어",
        "difficulty": "쉬움",
        "equipment": ["에어프라이어"],
        "description": "뜨거운 공기로 튀기듯 조리",
        "best_for": ["치킨", "감자튀김", "돈까스"],
    },
    {
        "name": "훈연",
        "difficulty": "어려움",
        "equipment": ["훈연기", "우드칩"],
        "description": "연기로 풍미를 입히는 기법",
        "best_for": ["삼겹살", "연어", "치킨"],
    },
    {
        "name": "압력조리",
        "difficulty": "보통",
        "equipment": ["압력솥", "전기압력밥솥"],
        "description": "높은 압력으로 빠르게 조리",
        "best_for": ["갈비찜", "족발", "곰탕"],
    },
]


async def create_schema(client) -> None:
    """Neo4j 스키마 생성"""
    print("Creating schema...")
    for query in SCHEMA_QUERIES:
        try:
            await client.execute_write(query)
            print(f"  ✓ {query[:50]}...")
        except Exception as e:
            print(f"  ✗ {query[:50]}... ({e})")


async def load_goals(client) -> None:
    """Goal 노드 생성"""
    print("\nLoading Goals...")
    query = """
    MERGE (g:Goal {name: $name})
    SET g.daily_calories = $daily_calories,
        g.protein_ratio = $protein_ratio,
        g.carbs_ratio = $carbs_ratio,
        g.fat_ratio = $fat_ratio,
        g.avoid_tags = $avoid_tags,
        g.prefer_tags = $prefer_tags
    """
    for goal in DEFAULT_GOALS:
        await client.execute_write(query, goal)
        print(f"  ✓ {goal['name']}")


async def load_conditions(client) -> None:
    """Condition 노드 생성"""
    print("\nLoading Conditions...")
    query = """
    MERGE (c:Condition {name: $name})
    SET c.avoid_ingredients = $avoid_ingredients,
        c.limit_nutrients = $limit_nutrients,
        c.prefer_tags = $prefer_tags,
        c.description = $description
    """
    for condition in DEFAULT_CONDITIONS:
        params = {
            **condition,
            "limit_nutrients": json.dumps(condition["limit_nutrients"]),
        }
        await client.execute_write(query, params)
        print(f"  ✓ {condition['name']}")


async def load_diets(client) -> None:
    """Diet 노드 생성"""
    print("\nLoading Diets...")
    query = """
    MERGE (d:Diet {name: $name})
    SET d.exclude_categories = $exclude_categories,
        d.exclude_ingredients = $exclude_ingredients,
        d.description = $description
    """
    for diet in DEFAULT_DIETS:
        await client.execute_write(query, diet)
        print(f"  ✓ {diet['name']}")


async def load_techniques(client) -> None:
    """Technique 노드 생성"""
    print("\nLoading Techniques...")
    query = """
    MERGE (t:Technique {name: $name})
    SET t.difficulty = $difficulty,
        t.equipment = $equipment,
        t.description = $description,
        t.best_for = $best_for
    """
    for tech in DEFAULT_TECHNIQUES:
        await client.execute_write(query, tech)
        print(f"  ✓ {tech['name']}")


async def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("Recipe Graph Engine - Neo4j Loader")
    print("=" * 50)

    async with get_neo4j_client() as client:
        await create_schema(client)
        await load_goals(client)
        await load_conditions(client)
        await load_diets(client)
        await load_techniques(client)

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
