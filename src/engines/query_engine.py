"""레시피 쿼리 엔진 - Cypher 쿼리 실행"""

from dataclasses import dataclass
from src.utils.neo4j_client import Neo4jClient


@dataclass
class RecipeResult:
    """레시피 검색 결과"""
    name: str
    category: str
    cuisine: str
    time_minutes: int
    difficulty: str
    coverage: float  # 재료 매칭율 (%)
    missing_count: int
    total_calories: float = 0
    total_protein: float = 0
    total_carbs: float = 0
    total_fat: float = 0
    tags: list[str] | None = None
    description: str = ""
    steps: list[str] | None = None
    tips: str = ""
    servings: int = 2  # 인분 수


class QueryEngine:
    """레시피 쿼리 엔진"""

    def __init__(self, client: Neo4jClient):
        self.client = client

    # ============== 기본 쿼리 (FREE) ==============

    async def find_recipes_by_ingredients(
        self,
        ingredients: list[str],
        min_coverage: int = 60,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """재료 → 레시피 역방향 쿼리"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r,
             count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             round(matched * 100.0 / total) AS coverage
        WHERE coverage >= $min_coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.tags AS tags,
               r.description AS description,
               r.steps AS steps,
               r.tips AS tips,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.time_minutes ASC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "min_coverage": min_coverage,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def find_missing_ingredients(
        self,
        recipe_name: str,
        my_ingredients: list[str],
    ) -> list[dict]:
        """레시피에 부족한 재료 목록"""
        query = """
        MATCH (r:Recipe {name: $recipe_name})-[req:REQUIRED_FOR]-(i:Ingredient)
        WHERE NOT i.name IN $my_ingredients
        RETURN i.name AS ingredient,
               req.amount AS amount,
               req.unit AS unit,
               i.category AS category,
               req.optional AS optional
        ORDER BY req.optional, i.category
        """
        return await self.client.execute_query(
            query,
            {"recipe_name": recipe_name, "my_ingredients": my_ingredients},
        )

    async def find_by_category(
        self,
        category: str,
        ingredients: list[str],
        limit: int = 10,
    ) -> list[RecipeResult]:
        """카테고리별 레시피 검색"""
        query = """
        MATCH (r:Recipe {category: $category})-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WHERE matched >= 2
        WITH r, matched, total,
             round(matched * 100.0 / total) AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.tags AS tags,
               r.description AS description,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {"category": category, "ingredients": ingredients, "limit": limit},
        )
        return [RecipeResult(**r) for r in results]

    # ============== 다이어트코치 쿼리 (PREMIUM) ==============

    async def find_by_calories(
        self,
        ingredients: list[str],
        max_calories: int,
        min_coverage: int = 0,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """칼로리 제한 + 재료 매칭 (재료 없어도 칼로리 기반 추천)"""
        query = """
        MATCH (r:Recipe)
        WHERE r.total_calories > 0 AND r.total_calories <= $max_calories
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        WHERE coverage >= $min_coverage OR size($ingredients) = 0
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.tags AS tags,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.total_protein DESC, r.total_calories ASC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "max_calories": max_calories,
                "min_coverage": min_coverage,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def find_by_goal(
        self,
        ingredients: list[str],
        goal_name: str,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """목표 기반 추천 (SUITABLE_FOR 관계 또는 속성 기반)"""
        query = """
        MATCH (r:Recipe)
        WHERE $goal_name IN r.suitable_for
           OR exists((r)-[:SUITABLE_FOR]->(:Goal {name: $goal_name}))
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.total_protein DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {"ingredients": ingredients, "goal_name": goal_name, "limit": limit},
        )
        return [RecipeResult(**r) for r in results]

    # ============== 건강맞춤 쿼리 (PREMIUM) ==============

    async def find_safe_for_condition(
        self,
        ingredients: list[str],
        condition_name: str,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """건강 상태 필터링 (위험 제외, 안전 우선)"""
        query = """
        MATCH (r:Recipe)
        WHERE NOT $condition_name IN r.avoid_for
          AND NOT (r)-[:AVOID_FOR]->(:Condition {name: $condition_name})
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.total_calories ASC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "condition_name": condition_name,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def find_for_multiple_conditions(
        self,
        ingredients: list[str],
        conditions: list[str],
        limit: int = 10,
    ) -> list[RecipeResult]:
        """복수 건강 상태 필터링"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        AND NOT EXISTS {
            MATCH (r)-[:AVOID_FOR]->(c:Condition)
            WHERE c.name IN $conditions
        }
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             round(matched * 100.0 / total) AS coverage
        WHERE coverage >= 50
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {"ingredients": ingredients, "conditions": conditions, "limit": limit},
        )
        return [RecipeResult(**r) for r in results]

    # ============== 무지개요리사 쿼리 (PREMIUM) ==============

    async def find_by_diet(
        self,
        ingredients: list[str],
        diet_name: str,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """식단 호환 레시피 검색 (비건/채식 등)"""
        query = """
        MATCH (r:Recipe)-[:COMPATIBLE_WITH]->(d:Diet {name: $diet_name})
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.total_protein DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {"ingredients": ingredients, "diet_name": diet_name, "limit": limit},
        )
        return [RecipeResult(**r) for r in results]

    async def find_substitutable_recipes(
        self,
        ingredients: list[str],
        diet_name: str,
        limit: int = 10,
    ) -> list[dict]:
        """대체재로 변환 가능한 레시피"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(original:Ingredient)
        WHERE NOT original.vegan
        OPTIONAL MATCH (alt:Ingredient)-[rep:CAN_REPLACE]->(original)
        WHERE alt.vegan AND rep.context = $diet_name
        WITH r,
             collect(DISTINCT original.name) AS meat_ingredients,
             collect(DISTINCT alt.name) AS alternatives
        WHERE size(alternatives) > 0
        RETURN r.name AS recipe,
               meat_ingredients,
               alternatives
        LIMIT $limit
        """
        return await self.client.execute_query(
            query,
            {"diet_name": diet_name, "limit": limit},
        )

    # ============== 흑백요리사 쿼리 (PREMIUM) ==============

    async def find_by_technique(
        self,
        ingredients: list[str],
        difficulty_levels: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """테크닉 기반 추천"""
        difficulty_levels = difficulty_levels or ["보통", "어려움"]
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        MATCH (r)-[:USES_TECHNIQUE]->(t:Technique)
        WHERE t.difficulty IN $difficulty_levels
        WITH r, collect(t.name) AS techniques, count(DISTINCT i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, techniques, matched, total,
             round(matched * 100.0 / total) AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.difficulty AS difficulty,
               techniques,
               coverage,
               total - matched AS missing_count
        ORDER BY size(techniques) DESC, coverage DESC
        LIMIT $limit
        """
        return await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "difficulty_levels": difficulty_levels,
                "limit": limit,
            },
        )

    async def find_ingredient_pairings(
        self,
        main_ingredient: str,
        limit: int = 10,
    ) -> list[dict]:
        """재료 페어링 추천 (양방향 관계 검색)"""
        query = """
        MATCH (main:Ingredient {name: $main_ingredient})-[p:PAIRS_WELL]-(pair:Ingredient)
        RETURN pair.name AS ingredient,
               pair.category AS category,
               p.count AS count
        ORDER BY p.count DESC
        LIMIT $limit
        """
        return await self.client.execute_query(
            query,
            {"main_ingredient": main_ingredient, "limit": limit},
        )

    # ============== 유틸리티 쿼리 ==============

    async def find_similar_recipes(
        self,
        recipe_name: str,
        limit: int = 5,
    ) -> list[dict]:
        """유사 레시피 검색 (양방향 관계 검색)"""
        query = """
        MATCH (r1:Recipe {name: $recipe_name})-[s:SIMILAR_TO]-(r2:Recipe)
        RETURN r2.name AS name,
               r2.category AS category,
               r2.difficulty AS difficulty,
               r2.time_minutes AS time_minutes,
               s.score AS similarity,
               s.shared_ingredients AS shared_ingredients
        ORDER BY s.score DESC
        LIMIT $limit
        """
        return await self.client.execute_query(
            query,
            {"recipe_name": recipe_name, "limit": limit},
        )

    async def autocomplete_ingredient(
        self,
        prefix: str,
        limit: int = 10,
    ) -> list[dict]:
        """재료 자동완성"""
        query = """
        MATCH (i:Ingredient)
        WHERE i.name STARTS WITH $prefix
        RETURN i.name AS name, i.category AS category
        LIMIT $limit
        """
        return await self.client.execute_query(
            query,
            {"prefix": prefix, "limit": limit},
        )

    async def find_by_time(
        self,
        ingredients: list[str],
        max_minutes: int = 30,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """시간 기반 필터"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        AND r.time_minutes <= $max_minutes
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             round(matched * 100.0 / total) AS coverage
        WHERE coverage >= 50
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               coverage,
               total - matched AS missing_count
        ORDER BY r.time_minutes ASC, coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "max_minutes": max_minutes,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def get_stats(self) -> dict:
        """전체 통계"""
        queries = {
            "recipes": "MATCH (r:Recipe) RETURN count(r) AS count",
            "ingredients": "MATCH (i:Ingredient) RETURN count(i) AS count",
            "relations": "MATCH ()-[req:REQUIRED_FOR]->() RETURN count(req) AS count",
        }
        stats = {}
        for key, query in queries.items():
            result = await self.client.execute_query(query)
            stats[key] = result[0]["count"] if result else 0
        return stats

    # ============== 모드별 특화 쿼리 ==============

    async def find_quick_recipes(
        self,
        ingredients: list[str],
        max_minutes: int = 20,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """자취생/간편식 - 20분 이내 초간단 레시피"""
        query = """
        MATCH (r:Recipe)
        WHERE r.time_minutes <= $max_minutes
          AND r.difficulty IN ['쉬움', '보통']
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        WHERE coverage >= 30 OR size($ingredients) = 0
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.description AS description,
               r.tips AS tips,
               coverage,
               total - matched AS missing_count
        ORDER BY r.time_minutes ASC, coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "max_minutes": max_minutes,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def find_kids_recipes(
        self,
        ingredients: list[str],
        limit: int = 10,
    ) -> list[RecipeResult]:
        """아이밥상 - 아이/유아용 안전 레시피 (매운맛 제외, 영양 균형)"""
        query = """
        MATCH (r:Recipe)
        WHERE r.spicy_level = 0 OR r.spicy_level IS NULL
          AND r.difficulty IN ['쉬움', '보통']
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.description AS description,
               r.tips AS tips,
               coverage,
               total - matched AS missing_count
        ORDER BY r.total_protein DESC, coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {"ingredients": ingredients, "limit": limit},
        )
        return [RecipeResult(**r) for r in results]

    async def find_bulk_recipes(
        self,
        ingredients: list[str],
        min_protein: float = 20.0,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """벌크업코치 - 고단백 벌크업 레시피"""
        query = """
        MATCH (r:Recipe)
        WHERE r.total_protein >= $min_protein
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.description AS description,
               r.tips AS tips,
               coverage,
               total - matched AS missing_count
        ORDER BY r.total_protein DESC, coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "min_protein": min_protein,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def find_party_recipes(
        self,
        ingredients: list[str],
        min_servings: int = 4,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """손님초대 - 파티/접대용 대용량 레시피"""
        query = """
        MATCH (r:Recipe)
        WHERE r.servings >= $min_servings
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.description AS description,
               r.tips AS tips,
               r.servings AS servings,
               coverage,
               total - matched AS missing_count
        ORDER BY r.servings DESC, coverage DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "min_servings": min_servings,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]

    async def find_traditional_recipes(
        self,
        ingredients: list[str],
        limit: int = 10,
    ) -> list[RecipeResult]:
        """한식장인 - 정통 한식 레시피"""
        query = """
        MATCH (r:Recipe)
        WHERE r.cuisine = '한식'
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched,
             COUNT { (r)-[:REQUIRED_FOR]-() } AS total
        WITH r, matched, total,
             CASE WHEN total > 0 THEN round(matched * 100.0 / total) ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.description AS description,
               r.steps AS steps,
               r.tips AS tips,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.time_minutes ASC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {"ingredients": ingredients, "limit": limit},
        )
        return [RecipeResult(**r) for r in results]

    async def find_budget_recipes(
        self,
        ingredients: list[str],
        max_ingredients: int = 7,
        limit: int = 10,
    ) -> list[RecipeResult]:
        """알뜰살림 - 가성비 레시피 (적은 재료)"""
        query = """
        MATCH (r:Recipe)
        WITH r, COUNT { (r)-[:REQUIRED_FOR]-() } AS total_ingredients
        WHERE total_ingredients <= $max_ingredients
        OPTIONAL MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, total_ingredients, count(i) AS matched
        WITH r, matched, total_ingredients,
             CASE WHEN total_ingredients > 0
                  THEN round(matched * 100.0 / total_ingredients)
                  ELSE 0 END AS coverage
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.total_carbs AS total_carbs,
               r.total_fat AS total_fat,
               r.description AS description,
               r.tips AS tips,
               coverage,
               total_ingredients - matched AS missing_count
        ORDER BY coverage DESC, total_ingredients ASC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query,
            {
                "ingredients": ingredients,
                "max_ingredients": max_ingredients,
                "limit": limit,
            },
        )
        return [RecipeResult(**r) for r in results]
