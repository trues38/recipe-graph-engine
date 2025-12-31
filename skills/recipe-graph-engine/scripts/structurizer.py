#!/usr/bin/env python3
"""
레시피 LLM 구조화 스크립트
크롤링/API 데이터 → 정규화된 JSON
"""

import json
import asyncio
from typing import List, Dict, Any
from anthropic import AsyncAnthropic

client = AsyncAnthropic()
MODEL = "claude-sonnet-4-20250514"


# ============================================================
# 프롬프트 템플릿
# ============================================================

INGREDIENT_NORMALIZE_PROMPT = """
다음 재료 목록을 정규화해주세요.

입력: {raw_ingredients}

출력 형식 (JSON만, 다른 텍스트 없이):
[
  {{
    "name": "정규화된 이름 (기본형)",
    "amount": 숫자,
    "unit": "g/ml/개/큰술/작은술/컵",
    "prep": "전처리 방법 (없으면 null)",
    "optional": false
  }}
]

규칙:
1. 이름은 기본형으로 (삼겹살 → 돼지고기, 청양고추 → 고추)
2. 단위 통일 (한 줌 → 30g, 약간 → 10g)
3. 선택 재료는 optional: true
4. 전처리는 별도 필드로 (다진 마늘 → name: 마늘, prep: 다진)
"""

RECIPE_GENERATION_PROMPT = """
다음 조건으로 일반적인 조리 방법을 작성해주세요.

요리명: {recipe_name}
재료: {ingredients}
카테고리: {category}
난이도: {difficulty}
조리 시간: {time}분

규칙:
1. 특정 출처의 문장을 복제하지 마세요
2. 일반적인 조리 상식에 기반해 작성하세요
3. 단계별로 명확하게 작성하세요

출력 형식 (JSON만, 다른 텍스트 없이):
{{
  "description": "한 줄 설명 (20자 이내)",
  "steps": ["1. ...", "2. ...", "3. ..."],
  "tips": "조리 팁 (한 문장)"
}}
"""

CLASSIFICATION_PROMPT = """
다음 레시피를 분류해주세요.

레시피: {recipe_name}
재료: {ingredients}

출력 형식 (JSON만, 다른 텍스트 없이):
{{
  "category": "찌개/볶음/구이/찜/튀김/무침/국/밥/면/디저트/샐러드/기타",
  "cuisine": "한식/양식/중식/일식/동남아/퓨전",
  "tags": ["태그1", "태그2", "태그3"],
  "spicy_level": 0,
  "suitable_for": ["다이어트/벌크업/일반"],
  "avoid_for": ["당뇨/고혈압/통풍/없음"]
}}

spicy_level: 0=안매움, 1=약간, 2=매움, 3=아주매움
"""


# ============================================================
# LLM 호출 함수
# ============================================================

async def call_llm(prompt: str) -> str:
    """Claude API 호출"""
    response = await client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def parse_json_response(text: str) -> Any:
    """LLM 응답에서 JSON 추출"""
    # ```json ... ``` 제거
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    
    return json.loads(text)


# ============================================================
# 구조화 함수
# ============================================================

async def normalize_ingredients(raw_ingredients: List[str]) -> List[Dict]:
    """재료 정규화"""
    prompt = INGREDIENT_NORMALIZE_PROMPT.format(
        raw_ingredients=json.dumps(raw_ingredients, ensure_ascii=False)
    )
    response = await call_llm(prompt)
    return parse_json_response(response)


async def generate_recipe_content(
    recipe_name: str,
    ingredients: List[Dict],
    category: str,
    difficulty: str,
    time_minutes: int
) -> Dict:
    """레시피 내용 생성"""
    ing_str = ", ".join([f"{i['name']} {i['amount']}{i['unit']}" for i in ingredients])
    
    prompt = RECIPE_GENERATION_PROMPT.format(
        recipe_name=recipe_name,
        ingredients=ing_str,
        category=category,
        difficulty=difficulty,
        time=time_minutes
    )
    response = await call_llm(prompt)
    return parse_json_response(response)


async def classify_recipe(recipe_name: str, ingredients: List[Dict]) -> Dict:
    """레시피 자동 분류"""
    ing_names = [i["name"] for i in ingredients]
    
    prompt = CLASSIFICATION_PROMPT.format(
        recipe_name=recipe_name,
        ingredients=", ".join(ing_names)
    )
    response = await call_llm(prompt)
    return parse_json_response(response)


# ============================================================
# 영양 정보 (USDA/식약처 DB 연동 시 구현)
# ============================================================

# 임시 영양 데이터 (실제로는 DB 조회)
NUTRITION_DB = {
    "돼지고기": {"calories": 250, "protein": 25, "carbs": 0, "fat": 15},
    "김치": {"calories": 15, "protein": 1, "carbs": 2, "fat": 0},
    "두부": {"calories": 80, "protein": 8, "carbs": 2, "fat": 4},
    "대파": {"calories": 25, "protein": 1, "carbs": 5, "fat": 0},
    "마늘": {"calories": 100, "protein": 4, "carbs": 20, "fat": 0},
    "고추": {"calories": 30, "protein": 1, "carbs": 6, "fat": 0},
    "계란": {"calories": 150, "protein": 12, "carbs": 1, "fat": 10},
    "밥": {"calories": 130, "protein": 3, "carbs": 28, "fat": 0},
    "닭가슴살": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},
}


def convert_to_grams(amount: float, unit: str) -> float:
    """단위를 그램으로 변환"""
    conversions = {
        "g": 1,
        "kg": 1000,
        "ml": 1,
        "L": 1000,
        "개": 50,  # 평균
        "큰술": 15,
        "작은술": 5,
        "컵": 200,
    }
    return amount * conversions.get(unit, 1)


def calculate_nutrition(ingredients: List[Dict]) -> Dict:
    """총 영양 정보 계산"""
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    
    for ing in ingredients:
        name = ing["name"]
        if name not in NUTRITION_DB:
            continue
            
        nutrition = NUTRITION_DB[name]
        grams = convert_to_grams(ing["amount"], ing["unit"])
        ratio = grams / 100
        
        total["calories"] += nutrition["calories"] * ratio
        total["protein"] += nutrition["protein"] * ratio
        total["carbs"] += nutrition["carbs"] * ratio
        total["fat"] += nutrition["fat"] * ratio
    
    # 반올림
    return {k: round(v, 1) for k, v in total.items()}


# ============================================================
# 메인 파이프라인
# ============================================================

async def process_single_recipe(raw_data: Dict) -> Dict:
    """단일 레시피 처리"""
    
    # 1. 재료 정규화
    ingredients = await normalize_ingredients(raw_data["ingredients"])
    
    # 2. 영양 정보 계산
    nutrition = calculate_nutrition(ingredients)
    
    # 3. 레시피 내용 생성 (저작권 회피)
    content = await generate_recipe_content(
        recipe_name=raw_data["name"],
        ingredients=ingredients,
        category=raw_data.get("category", "기타"),
        difficulty=raw_data.get("difficulty", "보통"),
        time_minutes=raw_data.get("time_minutes", 30)
    )
    
    # 4. 자동 분류
    classification = await classify_recipe(raw_data["name"], ingredients)
    
    # 5. 통합
    return {
        "name": raw_data["name"],
        "ingredients": ingredients,
        "time_minutes": raw_data.get("time_minutes", 30),
        "difficulty": raw_data.get("difficulty", "보통"),
        "servings": raw_data.get("servings", 2),
        
        "total_calories": nutrition["calories"],
        "total_protein": nutrition["protein"],
        "total_carbs": nutrition["carbs"],
        "total_fat": nutrition["fat"],
        
        **content,  # description, steps, tips
        **classification  # category, cuisine, tags, spicy_level, suitable_for, avoid_for
    }


async def batch_process(
    raw_recipes: List[Dict],
    batch_size: int = 5,
    delay: float = 1.0
) -> List[Dict]:
    """배치 처리"""
    results = []
    errors = []
    
    for i in range(0, len(raw_recipes), batch_size):
        batch = raw_recipes[i:i+batch_size]
        
        tasks = [process_single_recipe(r) for r in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                errors.append({"index": i+j, "error": str(result)})
            else:
                results.append(result)
        
        print(f"✓ Processed {len(results)}/{len(raw_recipes)} (errors: {len(errors)})")
        await asyncio.sleep(delay)
    
    if errors:
        print(f"\n⚠️ {len(errors)} errors occurred")
    
    return results


# ============================================================
# 사용 예시
# ============================================================

if __name__ == "__main__":
    # 샘플 입력 데이터 (크롤링/API에서 가져온 형태)
    sample_raw = [
        {
            "name": "김치찌개",
            "ingredients": ["삼겹살 300g", "묵은지 200g", "두부 반모", "대파 1대", "다진 마늘 1큰술"],
            "time_minutes": 30,
            "difficulty": "쉬움"
        },
        {
            "name": "된장찌개",
            "ingredients": ["된장 2큰술", "두부 반모", "호박 반개", "양파 반개", "청양고추 1개"],
            "time_minutes": 25,
            "difficulty": "쉬움"
        }
    ]
    
    async def main():
        results = await batch_process(sample_raw)
        
        # 결과 저장
        with open("structured_recipes.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Saved {len(results)} recipes to structured_recipes.json")
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    
    asyncio.run(main())
