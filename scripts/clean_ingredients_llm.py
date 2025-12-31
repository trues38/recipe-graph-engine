"""LLM을 사용한 재료 데이터 정제"""

import asyncio
import json
import os
from pathlib import Path
import httpx

# OpenRouter 설정 (무료 모델)
OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "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"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DATA_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_cleaned.json"
MAPPING_FILE = Path(__file__).parent.parent / "data" / "processed" / "ingredient_mapping.json"


async def call_llm(prompt: str, model: str = "xiaomi/mimo-v2-flash:free") -> str:
    """LLM API 호출 (OpenRouter 무료 모델)"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM error: {e}", flush=True)
            return ""


async def clean_ingredients_batch(ingredients: list[str]) -> dict[str, str]:
    """재료 목록을 LLM으로 정제 (배치 처리)"""

    prompt = f"""다음은 요리 레시피에서 추출한 재료 목록입니다.
각 재료에서 **순수한 재료 이름만** 추출해주세요.

규칙:
1. "(반죽재료)", "(양념)", "(소스)" 같은 접두어 제거
2. "1T", "2큰술", "300ml", "적당량" 같은 용량/단위 제거
3. "다진", "채썬", "썰어" 같은 조리법 제거
4. "끓인다", "넣는다" 같은 동작 설명이 포함된 것은 빈 문자열로
5. 너무 긴 문장(조리법 설명)은 빈 문자열로
6. 재료가 아닌 것(조리 도구, 설명)은 빈 문자열로

입력 재료:
{json.dumps(ingredients, ensure_ascii=False, indent=2)}

JSON 형식으로 응답해주세요 (원본 → 정제된 이름):
{{"원본재료명": "정제된재료명", ...}}

예시:
- "(양념)고추장 2T" → "고추장"
- "돼지고기 300g" → "돼지고기"
- "끓인다. 물 500ml" → ""
- "다진 마늘" → "마늘"

JSON만 반환:"""

    result = await call_llm(prompt)

    # JSON 파싱
    try:
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        print(f"JSON parse error: {result[:200]}")
        return {}


async def main():
    print("=" * 60, flush=True)
    print("LLM 기반 재료 데이터 정제", flush=True)
    print("=" * 60, flush=True)

    # 원본 데이터 로드
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes", flush=True)

    # 모든 고유 재료 추출
    all_ingredients = set()
    for recipe in recipes:
        for ing in recipe.get("ingredients", []):
            all_ingredients.add(ing["name"])

    ingredients_list = sorted(all_ingredients)
    print(f"Found {len(ingredients_list)} unique ingredients", flush=True)

    # 기존 매핑 로드 (있으면)
    mapping = {}
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        print(f"Loaded {len(mapping)} existing mappings")

    # LLM으로 배치 처리 (50개씩)
    batch_size = 50
    new_mappings = 0
    to_process = [ing for ing in ingredients_list if ing not in mapping]

    print(f"Processing {len(to_process)} new ingredients...")

    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i + batch_size]
        print(f"\nBatch {i // batch_size + 1}/{(len(to_process) + batch_size - 1) // batch_size}...")

        batch_result = await clean_ingredients_batch(batch)

        for orig, cleaned in batch_result.items():
            if orig not in mapping:
                mapping[orig] = cleaned
                new_mappings += 1

        # 중간 저장
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        print(f"  Processed: {len(batch)}, New mappings: {new_mappings}")

        # API 레이트 리밋 방지
        await asyncio.sleep(1)

    print(f"\n총 {new_mappings}개 새 매핑 생성됨")
    print(f"총 매핑 수: {len(mapping)}")

    # 정제된 레시피 생성
    print("\n정제된 레시피 생성 중...")
    cleaned_recipes = []

    for recipe in recipes:
        cleaned_recipe = {**recipe}
        cleaned_ingredients = []

        for ing in recipe.get("ingredients", []):
            orig_name = ing["name"]
            cleaned_name = mapping.get(orig_name, orig_name)

            # 유효한 재료만 추가
            if cleaned_name and len(cleaned_name) >= 2 and len(cleaned_name) <= 15:
                cleaned_ing = {**ing, "name": cleaned_name}
                cleaned_ingredients.append(cleaned_ing)

        cleaned_recipe["ingredients"] = cleaned_ingredients
        cleaned_recipes.append(cleaned_recipe)

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_recipes, f, ensure_ascii=False, indent=2)

    # 통계
    orig_ing_count = sum(len(r.get("ingredients", [])) for r in recipes)
    clean_ing_count = sum(len(r.get("ingredients", [])) for r in cleaned_recipes)

    print(f"\n" + "=" * 60)
    print("완료!")
    print(f"원본 재료 수: {orig_ing_count}")
    print(f"정제 후 재료 수: {clean_ing_count}")
    print(f"제거된 재료: {orig_ing_count - clean_ing_count}")
    print(f"출력 파일: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
