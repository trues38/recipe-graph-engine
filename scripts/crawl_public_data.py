"""공공데이터포털 한식 레시피 크롤링 스크립트

사용 API:
- 식품의약품안전처: 조리식품의 레시피 DB (COOKRCP01)
"""

import asyncio
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from config.settings import get_settings

settings = get_settings()

# API 설정
API_KEY = settings.data_go_kr_api_key
BASE_URL = "http://openapi.foodsafetykorea.go.kr/api"

# 출력 경로
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_recipes(start: int = 1, end: int = 100) -> dict:
    """
    식약처 조리식품 레시피 API 호출

    API: COOKRCP01 (조리식품의 레시피 DB)
    """
    url = f"{BASE_URL}/{API_KEY}/COOKRCP01/json/{start}/{end}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def parse_ingredients(ing_str: str) -> list[dict]:
    """
    재료 문자열 파싱

    예: "돼지고기 300g, 김치 200g, 두부 1/2모"
    """
    if not ing_str:
        return []

    ingredients = []
    # 쉼표 또는 줄바꿈으로 분리
    parts = re.split(r"[,\n]", ing_str)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 숫자와 단위 추출 시도
        match = re.match(r"(.+?)\s*([\d./]+)?\s*(g|ml|개|큰술|작은술|컵|모|장|줌|약간)?$", part)
        if match:
            name = match.group(1).strip()
            amount = match.group(2) or "1"
            unit = match.group(3) or "개"

            # 분수 처리 (1/2 -> 0.5)
            if "/" in amount:
                nums = amount.split("/")
                amount = float(nums[0]) / float(nums[1])
            else:
                try:
                    amount = float(amount)
                except ValueError:
                    amount = 1

            ingredients.append({
                "name": name,
                "amount": amount,
                "unit": unit,
            })
        else:
            # 파싱 실패 시 이름만 저장
            ingredients.append({
                "name": part,
                "amount": 1,
                "unit": "개",
            })

    return ingredients


def parse_steps(recipe: dict) -> list[str]:
    """조리 단계 파싱 (MANUAL01 ~ MANUAL20)"""
    steps = []
    for i in range(1, 21):
        key = f"MANUAL{i:02d}"
        step = recipe.get(key, "").strip()
        if step:
            # 숫자 접두사 제거 (예: "1. 고기를 썬다" -> "고기를 썬다")
            step = re.sub(r"^\d+\.\s*", "", step)
            steps.append(step)
    return steps


def estimate_difficulty(time_minutes: int, steps_count: int) -> str:
    """난이도 추정"""
    if time_minutes <= 20 and steps_count <= 5:
        return "쉬움"
    elif time_minutes <= 40 and steps_count <= 10:
        return "보통"
    else:
        return "어려움"


def estimate_category(name: str, recipe_type: str) -> str:
    """카테고리 추정"""
    name_lower = name.lower()

    if any(k in name_lower for k in ["찌개", "전골"]):
        return "찌개"
    elif any(k in name_lower for k in ["국", "탕", "육수"]):
        return "국"
    elif any(k in name_lower for k in ["볶음", "볶은"]):
        return "볶음"
    elif any(k in name_lower for k in ["구이", "굽", "스테이크"]):
        return "구이"
    elif any(k in name_lower for k in ["찜", "조림"]):
        return "찜"
    elif any(k in name_lower for k in ["튀김", "까스", "커틀릿"]):
        return "튀김"
    elif any(k in name_lower for k in ["무침", "샐러드", "절임"]):
        return "무침"
    elif any(k in name_lower for k in ["밥", "덮밥", "비빔밥", "볶음밥"]):
        return "밥"
    elif any(k in name_lower for k in ["면", "국수", "파스타", "라면"]):
        return "면"
    elif any(k in name_lower for k in ["떡", "디저트", "케이크", "과자"]):
        return "디저트"
    else:
        return "기타"


def transform_recipe(raw: dict) -> dict | None:
    """API 응답을 내부 형식으로 변환"""
    name = raw.get("RCP_NM", "").strip()
    if not name:
        return None

    # 재료 파싱
    ingredients = parse_ingredients(raw.get("RCP_PARTS_DTLS", ""))
    if len(ingredients) < 2:
        return None  # 재료가 너무 적으면 스킵

    # 조리 단계
    steps = parse_steps(raw)
    if not steps:
        return None  # 조리법이 없으면 스킵

    # 영양 정보
    calories = float(raw.get("INFO_ENG", 0) or 0)
    protein = float(raw.get("INFO_PRO", 0) or 0)
    fat = float(raw.get("INFO_FAT", 0) or 0)
    carbs = float(raw.get("INFO_CAR", 0) or 0)
    sodium = float(raw.get("INFO_NA", 0) or 0)

    # 카테고리
    recipe_type = raw.get("RCP_PAT2", "")
    category = estimate_category(name, recipe_type)

    # 조리 시간 추정 (단계 수 * 5분)
    time_minutes = len(steps) * 5
    difficulty = estimate_difficulty(time_minutes, len(steps))

    # 태그 생성
    tags = []
    if recipe_type:
        tags.append(recipe_type)
    if calories < 300:
        tags.append("저칼로리")
    if protein > 20:
        tags.append("고단백")
    if sodium > 1000:
        tags.append("고나트륨")

    # 건강 분류
    suitable_for = []
    avoid_for = []

    if calories < 400 and protein > 15:
        suitable_for.append("다이어트")
    if protein > 30:
        suitable_for.append("벌크업")
    if not suitable_for:
        suitable_for.append("유지")

    if sodium > 1500:
        avoid_for.append("고혈압")
    if carbs > 50:
        avoid_for.append("당뇨")
        avoid_for.append("저탄수")

    return {
        "name": name,
        "category": category,
        "cuisine": "한식",
        "time_minutes": time_minutes,
        "difficulty": difficulty,
        "servings": 2,
        "ingredients": ingredients,
        "total_calories": calories,
        "total_protein": protein,
        "total_carbs": carbs,
        "total_fat": fat,
        "total_sodium": sodium,
        "description": raw.get("RCP_NA_TIP", "")[:200] if raw.get("RCP_NA_TIP") else "",
        "steps": steps,
        "tips": raw.get("RCP_NA_TIP", "")[:100] if raw.get("RCP_NA_TIP") else "",
        "tags": tags,
        "spicy_level": 1 if "고추" in str(ingredients) or "매운" in name else 0,
        "suitable_for": suitable_for,
        "avoid_for": avoid_for,
        "source": "식약처",
        "source_id": raw.get("RCP_SEQ", ""),
    }


async def crawl_all_recipes(batch_size: int = 100, max_recipes: int = 1000) -> list[dict]:
    """전체 레시피 크롤링"""
    all_recipes = []
    start = 1

    print(f"크롤링 시작 (최대 {max_recipes}개)...")

    while start <= max_recipes:
        end = min(start + batch_size - 1, max_recipes)
        print(f"  Fetching {start} - {end}...")

        try:
            data = await fetch_recipes(start, end)

            # API 응답 구조 확인
            if "COOKRCP01" not in data:
                print(f"    API 오류: {data}")
                break

            result = data["COOKRCP01"]

            # 결과 코드 확인
            if result.get("RESULT", {}).get("CODE") != "INFO-000":
                print(f"    결과 없음: {result.get('RESULT')}")
                break

            rows = result.get("row", [])
            if not rows:
                print("    더 이상 데이터 없음")
                break

            # 변환
            for raw in rows:
                recipe = transform_recipe(raw)
                if recipe:
                    all_recipes.append(recipe)

            print(f"    변환된 레시피: {len(rows)}개 → 유효: {len([r for r in rows if transform_recipe(r)])}개")

            start += batch_size
            await asyncio.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"    오류: {e}")
            break

    return all_recipes


def deduplicate(recipes: list[dict]) -> list[dict]:
    """중복 제거"""
    seen = set()
    unique = []

    for r in recipes:
        key = r["name"]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


async def main():
    """메인 실행"""
    print("=" * 50)
    print("공공데이터 한식 레시피 크롤러")
    print("=" * 50)

    if not API_KEY:
        print("오류: DATA_GO_KR_API_KEY가 설정되지 않았습니다.")
        print(".env 파일에 API 키를 추가하세요.")
        return

    # 크롤링
    recipes = await crawl_all_recipes(batch_size=100, max_recipes=1000)
    print(f"\n총 수집: {len(recipes)}개")

    # 중복 제거
    recipes = deduplicate(recipes)
    print(f"중복 제거 후: {len(recipes)}개")

    # 저장 (raw)
    raw_path = OUTPUT_DIR / "public_recipes_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Raw 데이터 저장: {raw_path}")

    # processed 폴더에도 저장 (기존 데이터와 병합)
    processed_path = Path(__file__).parent.parent / "data" / "processed" / "recipes.json"

    existing = []
    if processed_path.exists():
        with open(processed_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"  기존 레시피: {len(existing)}개")

    # 병합 (중복 제거)
    existing_names = {r["name"] for r in existing}
    new_recipes = [r for r in recipes if r["name"] not in existing_names]
    merged = existing + new_recipes

    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"✓ 병합 저장: {processed_path} ({len(existing)} + {len(new_recipes)} = {len(merged)}개)")

    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)
    print(f"\n다음 단계: python scripts/recipe_loader.py")


if __name__ == "__main__":
    asyncio.run(main())
