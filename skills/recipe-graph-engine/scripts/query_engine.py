#!/usr/bin/env python3
"""
레시피 쿼리 엔진
Neo4j 그래프에서 레시피 검색/추천
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from neo4j import GraphDatabase


@dataclass
class RecipeResult:
    """검색 결과 레시피"""
    name: str
    category: str
    time_minutes: int
    difficulty: str
    total_calories: float
    total_protein: float
    coverage: float = 0  # 재료 매칭률
    missing_count: int = 0  # 부족한 재료 수
    recommended: bool = False  # 건강 추천 여부


class RecipeQueryEngine:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def _run(self, query: str, params: dict = None) -> List[Dict]:
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]
    
    # ========================================================
    # [FREE] 기본 쿼리
    # ========================================================
    
    def find_by_ingredients(
        self,
        ingredients: List[str],
        min_coverage: int = 60,
        limit: int = 10
    ) -> List[RecipeResult]:
        """
        보유 재료로 만들 수 있는 레시피 검색
        
        Args:
            ingredients: 보유 재료 목록
            min_coverage: 최소 재료 커버리지 (%)
            limit: 결과 개수
        """
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, 
             count(i) AS matched,
             size((r)-[:REQUIRED_FOR]-()) AS total
        WITH r, matched, total,
             round(matched * 100.0 / total) AS coverage
        WHERE coverage >= $min_coverage
        RETURN r.name AS name,
               r.category AS category,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               coverage,
               total - matched AS missing_count
        ORDER BY coverage DESC, r.time_minutes ASC
        LIMIT $limit
        """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "min_coverage": min_coverage,
            "limit": limit
        })
        
        return [RecipeResult(**r) for r in results]
    
    def get_missing_ingredients(
        self,
        recipe_name: str,
        my_ingredients: List[str]
    ) -> List[Dict]:
        """선택한 레시피에 부족한 재료 목록"""
        query = """
        MATCH (r:Recipe {name: $recipe_name})-[req:REQUIRED_FOR]-(i:Ingredient)
        WHERE NOT i.name IN $my_ingredients
        RETURN i.name AS name,
               req.amount AS amount,
               req.unit AS unit,
               i.category AS category
        ORDER BY i.category
        """
        
        return self._run(query, {
            "recipe_name": recipe_name,
            "my_ingredients": my_ingredients
        })
    
    # ========================================================
    # [PREMIUM] 다이어트코치
    # ========================================================
    
    def find_diet_recipes(
        self,
        ingredients: List[str],
        max_calories: int = 500,
        min_protein: int = 20,
        limit: int = 10
    ) -> List[RecipeResult]:
        """칼로리 제한 + 고단백 레시피 검색"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        AND r.total_calories <= $max_calories
        AND r.total_protein >= $min_protein
        WITH r, count(i) AS matched,
             size((r)-[:REQUIRED_FOR]-()) AS total
        WITH r, round(matched * 100.0 / total) AS coverage
        WHERE coverage >= 50
        RETURN r.name AS name,
               r.category AS category,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               coverage,
               0 AS missing_count
        ORDER BY r.total_protein DESC, r.total_calories ASC
        LIMIT $limit
        """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "max_calories": max_calories,
            "min_protein": min_protein,
            "limit": limit
        })
        
        return [RecipeResult(**r) for r in results]
    
    def find_by_goal(
        self,
        ingredients: List[str],
        goal: str,  # "다이어트", "벌크업", etc.
        limit: int = 10
    ) -> List[RecipeResult]:
        """목표 기반 레시피 검색"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        MATCH (r)-[:SUITABLE_FOR]->(g:Goal {name: $goal})
        WITH r, count(i) AS matched
        WHERE matched >= 2
        RETURN r.name AS name,
               r.category AS category,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               0 AS coverage,
               0 AS missing_count
        ORDER BY r.total_protein DESC
        LIMIT $limit
        """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "goal": goal,
            "limit": limit
        })
        
        return [RecipeResult(**r) for r in results]
    
    # ========================================================
    # [PREMIUM] 건강맞춤
    # ========================================================
    
    def find_safe_recipes(
        self,
        ingredients: List[str],
        condition: str,  # "당뇨", "고혈압", etc.
        limit: int = 10
    ) -> List[RecipeResult]:
        """건강 상태에 안전한 레시피 검색"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        // 위험 레시피 제외
        AND NOT (r)-[:AVOID_FOR]->(:Condition {name: $condition})
        WITH r, count(i) AS matched,
             exists((r)-[:SAFE_FOR]->(:Condition {name: $condition})) AS recommended
        WHERE matched >= 2
        RETURN r.name AS name,
               r.category AS category,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               0 AS coverage,
               0 AS missing_count,
               recommended
        ORDER BY recommended DESC, matched DESC
        LIMIT $limit
        """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "condition": condition,
            "limit": limit
        })
        
        return [RecipeResult(**r) for r in results]
    
    def find_safe_for_multiple(
        self,
        ingredients: List[str],
        conditions: List[str],  # ["당뇨", "고혈압"]
        limit: int = 10
    ) -> List[RecipeResult]:
        """복수 건강 상태에 안전한 레시피"""
        query = """
        MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        // 모든 조건에서 안전
        AND NOT EXISTS {
            MATCH (r)-[:AVOID_FOR]->(c:Condition)
            WHERE c.name IN $conditions
        }
        WITH r, count(i) AS matched
        WHERE matched >= 2
        RETURN r.name AS name,
               r.category AS category,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               0 AS coverage,
               0 AS missing_count
        ORDER BY matched DESC
        LIMIT $limit
        """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "conditions": conditions,
            "limit": limit
        })
        
        return [RecipeResult(**r) for r in results]
    
    # ========================================================
    # [PREMIUM] 무지개요리사
    # ========================================================
    
    def find_vegan_recipes(
        self,
        ingredients: List[str],
        diet: str = "비건",
        limit: int = 10
    ) -> List[RecipeResult]:
        """비건/채식 레시피 검색"""
        query = """
        MATCH (r:Recipe)-[:COMPATIBLE_WITH]->(d:Diet {name: $diet})
        MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
        WHERE i.name IN $ingredients
        WITH r, count(i) AS matched
        WHERE matched >= 2
        RETURN r.name AS name,
               r.category AS category,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               0 AS coverage,
               0 AS missing_count
        ORDER BY matched DESC
        LIMIT $limit
        """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "diet": diet,
            "limit": limit
        })
        
        return [RecipeResult(**r) for r in results]
    
    def get_substitutes(self, ingredient: str, context: str = "비건") -> List[Dict]:
        """대체재 조회"""
        query = """
        MATCH (alt:Ingredient)-[r:CAN_REPLACE]->(original:Ingredient {name: $ingredient})
        WHERE r.context = $context
        RETURN alt.name AS alternative,
               original.name AS original,
               r.ratio AS ratio,
               r.notes AS notes
        """
        
        return self._run(query, {
            "ingredient": ingredient,
            "context": context
        })
    
    # ========================================================
    # [PREMIUM] 흑백요리사
    # ========================================================
    
    def find_advanced_recipes(
        self,
        ingredients: List[str],
        techniques: List[str] = None,
        limit: int = 10
    ) -> List[RecipeResult]:
        """고급 테크닉 레시피 검색"""
        if techniques:
            query = """
            MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
            WHERE i.name IN $ingredients
            MATCH (r)-[:USES_TECHNIQUE]->(t:Technique)
            WHERE t.name IN $techniques
            WITH r, collect(DISTINCT t.name) AS techs, count(DISTINCT i) AS matched
            RETURN r.name AS name,
                   r.category AS category,
                   r.time_minutes AS time_minutes,
                   r.difficulty AS difficulty,
                   r.total_calories AS total_calories,
                   r.total_protein AS total_protein,
                   0 AS coverage,
                   0 AS missing_count,
                   techs AS techniques
            ORDER BY size(techs) DESC, matched DESC
            LIMIT $limit
            """
        else:
            query = """
            MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
            WHERE i.name IN $ingredients
            MATCH (r)-[:USES_TECHNIQUE]->(t:Technique)
            WHERE t.difficulty IN ["중", "상"]
            WITH r, collect(DISTINCT t.name) AS techs, count(DISTINCT i) AS matched
            RETURN r.name AS name,
                   r.category AS category,
                   r.time_minutes AS time_minutes,
                   r.difficulty AS difficulty,
                   r.total_calories AS total_calories,
                   r.total_protein AS total_protein,
                   0 AS coverage,
                   0 AS missing_count,
                   techs AS techniques
            ORDER BY size(techs) DESC
            LIMIT $limit
            """
        
        results = self._run(query, {
            "ingredients": ingredients,
            "techniques": techniques or [],
            "limit": limit
        })
        
        return results
    
    def get_pairings(self, ingredient: str) -> List[Dict]:
        """재료 페어링 조회"""
        query = """
        MATCH (main:Ingredient {name: $ingredient})-[:PAIRS_WELL]->(pair:Ingredient)
        RETURN pair.name AS name,
               pair.category AS category
        LIMIT 10
        """
        
        return self._run(query, {"ingredient": ingredient})
    
    # ========================================================
    # 유틸리티
    # ========================================================
    
    def search_ingredients(self, prefix: str, limit: int = 10) -> List[str]:
        """재료 자동완성"""
        query = """
        MATCH (i:Ingredient)
        WHERE i.name STARTS WITH $prefix
        RETURN i.name AS name
        LIMIT $limit
        """
        
        results = self._run(query, {"prefix": prefix, "limit": limit})
        return [r["name"] for r in results]
    
    def get_recipe_detail(self, name: str) -> Optional[Dict]:
        """레시피 상세 정보"""
        query = """
        MATCH (r:Recipe {name: $name})
        OPTIONAL MATCH (r)-[req:REQUIRED_FOR]-(i:Ingredient)
        WITH r, collect({
            name: i.name,
            amount: req.amount,
            unit: req.unit
        }) AS ingredients
        RETURN r.name AS name,
               r.category AS category,
               r.cuisine AS cuisine,
               r.time_minutes AS time_minutes,
               r.difficulty AS difficulty,
               r.servings AS servings,
               r.total_calories AS total_calories,
               r.total_protein AS total_protein,
               r.description AS description,
               r.steps AS steps,
               r.tips AS tips,
               r.tags AS tags,
               ingredients
        """
        
        results = self._run(query, {"name": name})
        return results[0] if results else None


# ============================================================
# 사용 예시
# ============================================================

if __name__ == "__main__":
    engine = RecipeQueryEngine(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="your_password"
    )
    
    try:
        # 테스트 재료
        my_ingredients = ["돼지고기", "김치", "두부", "대파", "마늘"]
        
        # 1. 기본 검색
        print("=== 재료로 검색 ===")
        results = engine.find_by_ingredients(my_ingredients)
        for r in results:
            print(f"  {r.name} ({r.coverage}% 매칭, {r.missing_count}개 부족)")
        
        # 2. 다이어트 검색
        print("\n=== 다이어트 레시피 ===")
        results = engine.find_diet_recipes(my_ingredients, max_calories=400)
        for r in results:
            print(f"  {r.name} ({r.total_calories}kcal, 단백질 {r.total_protein}g)")
        
        # 3. 건강 검색
        print("\n=== 당뇨 안전 레시피 ===")
        results = engine.find_safe_recipes(my_ingredients, condition="당뇨")
        for r in results:
            print(f"  {r.name} (추천: {r.recommended})")
        
    finally:
        engine.close()
