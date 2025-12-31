#!/usr/bin/env python3
"""
Neo4j 그래프 적재 스크립트
구조화된 JSON → Neo4j 그래프
"""

import json
from typing import List, Dict, Any
from neo4j import GraphDatabase


# ============================================================
# Neo4j 연결
# ============================================================

class RecipeGraphLoader:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def run_query(self, query: str, params: dict = None):
        with self.driver.session() as session:
            return session.run(query, params or {})
    
    # ========================================================
    # 스키마 초기화
    # ========================================================
    
    def init_schema(self):
        """인덱스 및 제약조건 생성"""
        constraints = [
            "CREATE CONSTRAINT ingredient_name IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT recipe_name IF NOT EXISTS FOR (r:Recipe) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT goal_name IF NOT EXISTS FOR (g:Goal) REQUIRE g.name IS UNIQUE",
            "CREATE CONSTRAINT condition_name IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT diet_name IF NOT EXISTS FOR (d:Diet) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT technique_name IF NOT EXISTS FOR (t:Technique) REQUIRE t.name IS UNIQUE",
        ]
        
        indexes = [
            "CREATE INDEX ingredient_category IF NOT EXISTS FOR (i:Ingredient) ON (i.category)",
            "CREATE INDEX recipe_category IF NOT EXISTS FOR (r:Recipe) ON (r.category)",
            "CREATE INDEX recipe_calories IF NOT EXISTS FOR (r:Recipe) ON (r.total_calories)",
        ]
        
        for q in constraints + indexes:
            try:
                self.run_query(q)
            except Exception as e:
                print(f"  (skip) {e}")
        
        print("✓ Schema initialized")
    
    def init_base_nodes(self):
        """기본 Goal/Condition/Diet/Technique 노드 생성"""
        
        # Goals
        goals = [
            {"name": "다이어트", "daily_calories": 1500, "protein_ratio": 0.3},
            {"name": "벌크업", "daily_calories": 3000, "protein_ratio": 0.35},
            {"name": "유지", "daily_calories": 2000, "protein_ratio": 0.25},
            {"name": "저탄수", "daily_calories": 1800, "carbs_ratio": 0.1},
        ]
        for g in goals:
            self.run_query("""
                MERGE (g:Goal {name: $name})
                SET g.daily_calories = $daily_calories,
                    g.protein_ratio = $protein_ratio
            """, g)
        
        # Conditions
        conditions = [
            {"name": "당뇨", "avoid": ["설탕", "흰쌀", "흰밀가루"]},
            {"name": "고혈압", "avoid": ["소금", "젓갈", "장아찌"]},
            {"name": "통풍", "avoid": ["내장", "맥주", "등푸른생선"]},
            {"name": "신장질환", "avoid": ["단백질과다", "칼륨과다"]},
            {"name": "고지혈증", "avoid": ["포화지방", "콜레스테롤"]},
        ]
        for c in conditions:
            self.run_query("""
                MERGE (c:Condition {name: $name})
                SET c.avoid_ingredients = $avoid
            """, c)
        
        # Diets
        diets = [
            {"name": "비건", "exclude": ["육류", "해산물", "유제품", "계란", "꿀"]},
            {"name": "락토", "exclude": ["육류", "해산물", "계란"]},
            {"name": "오보", "exclude": ["육류", "해산물", "유제품"]},
            {"name": "페스코", "exclude": ["육류"]},
        ]
        for d in diets:
            self.run_query("""
                MERGE (d:Diet {name: $name})
                SET d.exclude_categories = $exclude
            """, d)
        
        # Techniques
        techniques = [
            {"name": "수비드", "difficulty": "상", "equipment": ["수비드머신"]},
            {"name": "에어프라이어", "difficulty": "하", "equipment": ["에어프라이어"]},
            {"name": "압력솥", "difficulty": "중", "equipment": ["압력솥"]},
            {"name": "훈연", "difficulty": "상", "equipment": ["훈연기"]},
        ]
        for t in techniques:
            self.run_query("""
                MERGE (t:Technique {name: $name})
                SET t.difficulty = $difficulty,
                    t.equipment = $equipment
            """, t)
        
        print("✓ Base nodes created")
    
    # ========================================================
    # 재료 노드
    # ========================================================
    
    def load_ingredient(self, ingredient: Dict):
        """단일 재료 노드 생성/업데이트"""
        self.run_query("""
            MERGE (i:Ingredient {name: $name})
            SET i.category = $category,
                i.calories_per_100g = $calories,
                i.protein_per_100g = $protein,
                i.vegan = $vegan
        """, {
            "name": ingredient["name"],
            "category": ingredient.get("category", "기타"),
            "calories": ingredient.get("calories_per_100g", 0),
            "protein": ingredient.get("protein_per_100g", 0),
            "vegan": ingredient.get("vegan", False),
        })
    
    def load_ingredients_from_recipe(self, recipe: Dict):
        """레시피의 재료들을 노드로 생성"""
        for ing in recipe.get("ingredients", []):
            self.run_query("""
                MERGE (i:Ingredient {name: $name})
            """, {"name": ing["name"]})
    
    # ========================================================
    # 레시피 노드
    # ========================================================
    
    def load_recipe(self, recipe: Dict):
        """레시피 노드 생성 및 재료 연결"""
        
        # 1. 레시피 노드 생성
        self.run_query("""
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
                r.tips = $tips
        """, {
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
        })
        
        # 2. 재료 연결 (REQUIRED_FOR)
        for ing in recipe.get("ingredients", []):
            self.run_query("""
                MATCH (r:Recipe {name: $recipe_name})
                MERGE (i:Ingredient {name: $ing_name})
                MERGE (i)-[req:REQUIRED_FOR]->(r)
                SET req.amount = $amount,
                    req.unit = $unit,
                    req.optional = $optional
            """, {
                "recipe_name": recipe["name"],
                "ing_name": ing["name"],
                "amount": ing.get("amount", 0),
                "unit": ing.get("unit", "g"),
                "optional": ing.get("optional", False),
            })
        
        # 3. 목표 연결 (SUITABLE_FOR)
        for goal in recipe.get("suitable_for", []):
            if goal and goal != "일반":
                self.run_query("""
                    MATCH (r:Recipe {name: $recipe_name})
                    MATCH (g:Goal {name: $goal_name})
                    MERGE (r)-[:SUITABLE_FOR]->(g)
                """, {"recipe_name": recipe["name"], "goal_name": goal})
        
        # 4. 건강 상태 연결 (AVOID_FOR)
        for condition in recipe.get("avoid_for", []):
            if condition and condition != "없음":
                self.run_query("""
                    MATCH (r:Recipe {name: $recipe_name})
                    MATCH (c:Condition {name: $condition_name})
                    MERGE (r)-[:AVOID_FOR]->(c)
                """, {"recipe_name": recipe["name"], "condition_name": condition})
    
    # ========================================================
    # 배치 적재
    # ========================================================
    
    def load_recipes_batch(self, recipes: List[Dict]):
        """레시피 배치 적재"""
        total = len(recipes)
        
        for i, recipe in enumerate(recipes):
            try:
                self.load_recipe(recipe)
                if (i + 1) % 100 == 0:
                    print(f"  Loaded {i+1}/{total} recipes")
            except Exception as e:
                print(f"  ✗ Error loading {recipe.get('name')}: {e}")
        
        print(f"✓ Loaded {total} recipes")
    
    # ========================================================
    # 통계
    # ========================================================
    
    def get_stats(self) -> Dict:
        """그래프 통계"""
        stats = {}
        
        result = self.run_query("MATCH (r:Recipe) RETURN count(r) AS count")
        stats["recipes"] = result.single()["count"]
        
        result = self.run_query("MATCH (i:Ingredient) RETURN count(i) AS count")
        stats["ingredients"] = result.single()["count"]
        
        result = self.run_query("MATCH ()-[r:REQUIRED_FOR]->() RETURN count(r) AS count")
        stats["required_for_edges"] = result.single()["count"]
        
        return stats


# ============================================================
# 사용 예시
# ============================================================

if __name__ == "__main__":
    # Neo4j 연결 (환경에 맞게 수정)
    loader = RecipeGraphLoader(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="your_password"
    )
    
    try:
        # 1. 스키마 초기화
        loader.init_schema()
        
        # 2. 기본 노드 생성
        loader.init_base_nodes()
        
        # 3. 구조화된 레시피 로드
        with open("structured_recipes.json", "r", encoding="utf-8") as f:
            recipes = json.load(f)
        
        # 4. 배치 적재
        loader.load_recipes_batch(recipes)
        
        # 5. 통계 확인
        stats = loader.get_stats()
        print(f"\n📊 Graph Stats:")
        print(f"   Recipes: {stats['recipes']}")
        print(f"   Ingredients: {stats['ingredients']}")
        print(f"   REQUIRED_FOR edges: {stats['required_for_edges']}")
        
    finally:
        loader.close()
