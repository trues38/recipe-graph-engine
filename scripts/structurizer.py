"""LLM 기반 레시피 데이터 구조화 스크립트"""

import asyncio
import json
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.llm_client import get_llm_client

llm = get_llm_client()


# ============== 프롬프트 템플릿 ==============

INGREDIENT_NORMALIZE_PROMPT = """다음 재료 목록을 정규화해주세요.

입력: {raw_ingredients}

출력 형식 (JSON):
[
  {{
    "name": "정규화된 이름",
    "amount": 숫자,
    "unit": "g/ml/개/큰술/작은술/컵",
    "prep": "전처리 방법 (선택)",
    "optional": true/false
  }}
]

규칙:
1. 이름은 기본형으로 (삼겹살 → 돼지고기)
2. 단위 통일 (한 줌 → 30g, 약간 → 5g)
3. 선택 재료는 optional: true
4. 전처리는 별도 필드로 (다진 마늘 → name: 마늘, prep: 다진)

예시:
입력: ["삼겹살 300g", "다진 마늘 1큰술", "파 약간"]
출력: [
  {{"name": "돼지고기", "amount": 300, "unit": "g"}},
  {{"name": "마늘", "amount": 1, "unit": "큰술", "prep": "다진"}},
  {{"name": "대파", "amount": 20, "unit": "g", "optional": true}}
]

JSON만 출력하세요."""


RECIPE_GENERATION_PROMPT = """다음 조건으로 일반적인 조리 방법을 작성해주세요.

재료: {ingredients}
요리 이름: {recipe_name}
카테고리: {category}
난이도: {difficulty}
조리 시간: {time}분

규칙:
1. 특정 출처의 문장을 복제하지 마세요
2. 일반적인 조리 상식에 기반해 작성하세요
3. 단계별로 명확하게 작성하세요

출력 형식 (JSON):
{{
  "description": "한 줄 설명",
  "steps": ["1단계", "2단계", ...],
  "tips": "조리 팁"
}}

JSON만 출력하세요."""


CLASSIFICATION_PROMPT = """다음 레시피를 분류해주세요.

레시피: {recipe_name}
재료: {ingredients}

출력 형식 (JSON):
{{
  "category": "찌개/볶음/구이/찜/튀김/무침/국/밥/면/디저트 중 하나",
  "cuisine": "한식/양식/중식/일식/동남아/퓨전 중 하나",
  "tags": ["태그1", "태그2", ...],
  "spicy_level": 0-3,
  "suitable_for": ["다이어트", "벌크업", "유지", "저탄수" 중 해당하는 것들],
  "avoid_for": ["당뇨", "고혈압", "통풍", "신장질환", "고지혈증" 중 해당하는 것들]
}}

JSON만 출력하세요."""


# ============== 영양 정보 DB (간소화) ==============

NUTRITION_DB = {
    "돼지고기": {"calories": 242, "protein": 27, "carbs": 0, "fat": 14},
    "소고기": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15},
    "닭고기": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},
    "닭가슴살": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},
    "김치": {"calories": 15, "protein": 1.1, "carbs": 2.4, "fat": 0.5},
    "두부": {"calories": 76, "protein": 8, "carbs": 1.9, "fat": 4.8},
    "계란": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11},
    "쌀밥": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3},
    "대파": {"calories": 32, "protein": 1.8, "carbs": 7.3, "fat": 0.2},
    "마늘": {"calories": 149, "protein": 6.4, "carbs": 33, "fat": 0.5},
    "양파": {"calories": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1},
    "고추장": {"calories": 228, "protein": 5.6, "carbs": 45, "fat": 2.8},
    "간장": {"calories": 53, "protein": 5.6, "carbs": 5.6, "fat": 0},
    "된장": {"calories": 199, "protein": 12, "carbs": 26, "fat": 6},
    "참기름": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100},
    "감자": {"calories": 77, "protein": 2, "carbs": 17, "fat": 0.1},
    "당근": {"calories": 41, "protein": 0.9, "carbs": 10, "fat": 0.2},
    "버섯": {"calories": 22, "protein": 3.1, "carbs": 3.3, "fat": 0.3},
    "시금치": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4},
    "콩나물": {"calories": 31, "protein": 4.3, "carbs": 2.1, "fat": 0.8},
}


# ============== 유닛 변환 ==============

UNIT_TO_GRAMS = {
    "g": 1,
    "ml": 1,
    "개": 50,
    "큰술": 15,
    "작은술": 5,
    "컵": 200,
}


def convert_to_grams(amount: float, unit: str) -> float:
    """단위를 그램으로 변환"""
    return amount * UNIT_TO_GRAMS.get(unit, 1)


def calculate_nutrition(ingredients: list[dict]) -> dict:
    """재료 목록에서 총 영양 정보 계산"""
    total = {
        "total_calories": 0,
        "total_protein": 0,
        "total_carbs": 0,
        "total_fat": 0,
    }

    for ing in ingredients:
        name = ing.get("name", "")
        nutrition = NUTRITION_DB.get(name)
        if not nutrition:
            continue

        grams = convert_to_grams(ing.get("amount", 0), ing.get("unit", "g"))
        ratio = grams / 100

        total["total_calories"] += nutrition["calories"] * ratio
        total["total_protein"] += nutrition["protein"] * ratio
        total["total_carbs"] += nutrition["carbs"] * ratio
        total["total_fat"] += nutrition["fat"] * ratio

    return {k: round(v, 1) for k, v in total.items()}


# ============== LLM 호출 ==============

async def call_llm(prompt: str) -> str:
    """OpenRouter API 호출 (폴백 지원)"""
    return await llm.generate(prompt, max_tokens=2000)


def parse_json_response(response: str) -> Any:
    """JSON 응답 파싱"""
    # 코드 블록 제거
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1])
    return json.loads(response)


# ============== 파이프라인 함수 ==============

async def normalize_ingredients(raw_ingredients: list[str]) -> list[dict]:
    """재료 정규화"""
    prompt = INGREDIENT_NORMALIZE_PROMPT.format(
        raw_ingredients=json.dumps(raw_ingredients, ensure_ascii=False)
    )
    response = await call_llm(prompt)
    return parse_json_response(response)


async def generate_recipe_content(
    ingredients: list[dict],
    recipe_name: str,
    category: str,
    difficulty: str,
    time_minutes: int,
) -> dict:
    """레시피 컨텐츠 생성"""
    ing_names = [f"{i['name']} {i['amount']}{i['unit']}" for i in ingredients]
    prompt = RECIPE_GENERATION_PROMPT.format(
        ingredients=", ".join(ing_names),
        recipe_name=recipe_name,
        category=category,
        difficulty=difficulty,
        time=time_minutes,
    )
    response = await call_llm(prompt)
    return parse_json_response(response)


async def classify_recipe(recipe_name: str, ingredients: list[dict]) -> dict:
    """레시피 분류"""
    ing_names = [i["name"] for i in ingredients]
    prompt = CLASSIFICATION_PROMPT.format(
        recipe_name=recipe_name,
        ingredients=", ".join(ing_names),
    )
    response = await call_llm(prompt)
    return parse_json_response(response)


async def process_recipe(raw_data: dict) -> dict:
    """단일 레시피 처리 파이프라인"""
    print(f"Processing: {raw_data['name']}")

    # 1. 재료 정규화
    ingredients = await normalize_ingredients(raw_data["ingredients"])
    print(f"  - Normalized {len(ingredients)} ingredients")

    # 2. 영양 정보 계산
    nutrition = calculate_nutrition(ingredients)
    print(f"  - Calculated nutrition: {nutrition['total_calories']}kcal")

    # 3. 레시피 컨텐츠 생성
    content = await generate_recipe_content(
        ingredients=ingredients,
        recipe_name=raw_data["name"],
        category=raw_data.get("category", "기타"),
        difficulty=raw_data.get("difficulty", "보통"),
        time_minutes=raw_data.get("time_minutes", 30),
    )
    print(f"  - Generated {len(content['steps'])} steps")

    # 4. 분류
    classification = await classify_recipe(raw_data["name"], ingredients)
    print(f"  - Classified as {classification['category']}")

    return {
        "name": raw_data["name"],
        "time_minutes": raw_data.get("time_minutes", 30),
        "difficulty": raw_data.get("difficulty", "보통"),
        "servings": raw_data.get("servings", 2),
        "ingredients": ingredients,
        **nutrition,
        **content,
        **classification,
    }


async def batch_process(raw_recipes: list[dict], batch_size: int = 5) -> list[dict]:
    """배치 처리"""
    results = []

    for i in range(0, len(raw_recipes), batch_size):
        batch = raw_recipes[i : i + batch_size]
        print(f"\n=== Batch {i // batch_size + 1} ===")

        tasks = [process_recipe(r) for r in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in batch_results:
            if isinstance(result, Exception):
                print(f"  Error: {result}")
            else:
                results.append(result)

        print(f"Progress: {len(results)}/{len(raw_recipes)}")
        await asyncio.sleep(1)  # Rate limiting

    return results


def validate_recipe(recipe: dict) -> list[str]:
    """레시피 품질 검증"""
    errors = []

    required = ["name", "ingredients", "category", "steps"]
    for field in required:
        if not recipe.get(field):
            errors.append(f"Missing: {field}")

    if len(recipe.get("ingredients", [])) < 2:
        errors.append("Too few ingredients")

    if recipe.get("total_calories", 0) > 3000:
        errors.append("Unrealistic calories")

    if not (5 <= recipe.get("time_minutes", 0) <= 480):
        errors.append("Unrealistic time")

    return errors


def deduplicate_recipes(recipes: list[dict]) -> list[dict]:
    """중복 레시피 제거"""
    seen = set()
    unique = []

    for r in recipes:
        ing_key = tuple(sorted([i["name"] for i in r.get("ingredients", [])]))
        key = (r["name"], ing_key)

        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


# ============== 메인 ==============

SAMPLE_RECIPES = [
    {
        "name": "김치찌개",
        "ingredients": ["삼겹살 300g", "신김치 200g", "두부 반모", "대파 1대", "다진 마늘 1큰술"],
        "time_minutes": 30,
        "difficulty": "쉬움",
        "servings": 2,
    },
    {
        "name": "된장찌개",
        "ingredients": ["된장 2큰술", "두부 반모", "호박 반개", "양파 반개", "청양고추 1개", "대파 1대"],
        "time_minutes": 25,
        "difficulty": "쉬움",
        "servings": 2,
    },
    {
        "name": "제육볶음",
        "ingredients": ["돼지고기 앞다리 400g", "양파 1개", "대파 1대", "고추장 2큰술", "간장 1큰술", "설탕 1큰술"],
        "time_minutes": 20,
        "difficulty": "쉬움",
        "servings": 2,
    },
]


async def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("Recipe Structurizer")
    print("=" * 50)

    # 샘플 데이터 처리
    results = await batch_process(SAMPLE_RECIPES)

    # 검증
    valid_recipes = []
    for recipe in results:
        errors = validate_recipe(recipe)
        if errors:
            print(f"Validation errors for {recipe['name']}: {errors}")
        else:
            valid_recipes.append(recipe)

    # 중복 제거
    unique_recipes = deduplicate_recipes(valid_recipes)

    # 결과 저장
    output_path = Path(__file__).parent.parent / "data" / "processed" / "recipes.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_recipes, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {len(unique_recipes)} recipes to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
