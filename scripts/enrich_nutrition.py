"""영양정보 연동 (식약처 CSV 기반)"""

import json
import re
import csv
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict

INPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_deduped.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_enriched.json"
NUTRITION_CSV = Path(__file__).parent.parent / "data" / "raw" / "전국통합식품영양성분정보_음식_표준데이터.csv"

# 단위 변환 매핑
UNIT_MAPPING = {
    "큰술": 15,      # 15g
    "T": 15,
    "작은술": 5,     # 5g
    "t": 5,
    "컵": 200,       # 200ml
    "종이컵": 180,
    "한줌": 30,
    "약간": 2,
    "조금": 5,
    "적당량": 10,
    "개": 50,        # 평균 크기
    "쪽": 5,         # 마늘 한 쪽
    "톨": 5,
    "줄기": 10,
    "장": 30,        # 김 한 장
    "봉": 100,       # 라면 한 봉
    "모": 300,       # 두부 한 모
    "근": 600,       # 1근 = 600g
    "대": 100,       # 파 한 대
}


def load_nutrition_db():
    """식약처 CSV에서 영양정보 로드"""
    nutrition_db = {}

    if not NUTRITION_CSV.exists():
        print(f"영양정보 CSV 파일이 없습니다: {NUTRITION_CSV}")
        return nutrition_db

    # EUC-KR 인코딩으로 읽기
    with open(NUTRITION_CSV, "r", encoding="euc-kr", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("식품명", "").strip()
            if not name:
                continue

            try:
                nutrition_db[name] = {
                    "calories": float(row.get("에너지(kcal)", 0) or 0),
                    "protein": float(row.get("단백질(g)", 0) or 0),
                    "fat": float(row.get("지방(g)", 0) or 0),
                    "carbs": float(row.get("탄수화물(g)", 0) or 0),
                    "sugar": float(row.get("당류(g)", 0) or 0),
                    "fiber": float(row.get("식이섬유(g)", 0) or 0),
                    "sodium": float(row.get("나트륨(mg)", 0) or 0),
                    "calcium": float(row.get("칼슘(mg)", 0) or 0),
                    "iron": float(row.get("철(mg)", 0) or 0),
                    "reference_amount": row.get("영양성분함량기준량", "100g"),
                }
            except (ValueError, TypeError):
                continue

    return nutrition_db


def normalize_for_matching(name: str) -> str:
    """매칭을 위한 이름 정규화"""
    # 공백 제거, 소문자화
    name = re.sub(r'\s+', '', name.lower())
    # 특수문자 제거
    name = re.sub(r'[^\w가-힣]', '', name)
    return name


def find_best_match(recipe_name: str, nutrition_db: dict, threshold: float = 0.7) -> tuple:
    """레시피 이름과 가장 유사한 영양정보 찾기"""
    normalized_recipe = normalize_for_matching(recipe_name)

    best_match = None
    best_score = 0

    for db_name in nutrition_db.keys():
        normalized_db = normalize_for_matching(db_name)

        # 정확 매칭
        if normalized_recipe == normalized_db:
            return db_name, 1.0

        # 포함 관계
        if normalized_recipe in normalized_db or normalized_db in normalized_recipe:
            score = 0.9
            if score > best_score:
                best_score = score
                best_match = db_name
                continue

        # 유사도 계산
        score = SequenceMatcher(None, normalized_recipe, normalized_db).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = db_name

    return best_match, best_score


def parse_amount(amount_str: str) -> float:
    """재료 양 문자열을 g으로 변환"""
    if not amount_str:
        return 0

    amount_str = str(amount_str).strip()

    # 숫자만 추출
    numbers = re.findall(r'[\d.]+', amount_str)
    if not numbers:
        # 단위만 있는 경우
        for unit, grams in UNIT_MAPPING.items():
            if unit in amount_str:
                return grams
        return 0

    value = float(numbers[0])

    # 단위 변환
    for unit, grams in UNIT_MAPPING.items():
        if unit in amount_str:
            return value * grams

    # g, ml 등 직접 단위
    if 'g' in amount_str.lower() or 'ml' in amount_str.lower():
        return value
    if 'kg' in amount_str.lower() or 'l' in amount_str.lower():
        return value * 1000

    return value


def calculate_recipe_nutrition(recipe: dict, nutrition_db: dict) -> dict:
    """레시피 영양정보 계산"""
    total_nutrition = {
        "calories": 0,
        "protein": 0,
        "fat": 0,
        "carbs": 0,
        "sodium": 0,
    }

    matched_ingredients = []
    unmatched_ingredients = []

    for ing in recipe.get("ingredients", []):
        ing_name = ing.get("name", "")
        amount_str = ing.get("amount", "")

        # 영양정보 매칭
        match_name, score = find_best_match(ing_name, nutrition_db, threshold=0.6)

        if match_name:
            nutrition = nutrition_db[match_name]
            amount_g = parse_amount(str(amount_str))

            if amount_g > 0:
                # 100g 기준 → 실제 양으로 환산
                ratio = amount_g / 100

                total_nutrition["calories"] += nutrition["calories"] * ratio
                total_nutrition["protein"] += nutrition["protein"] * ratio
                total_nutrition["fat"] += nutrition["fat"] * ratio
                total_nutrition["carbs"] += nutrition["carbs"] * ratio
                total_nutrition["sodium"] += nutrition["sodium"] * ratio

                matched_ingredients.append({
                    "name": ing_name,
                    "matched_to": match_name,
                    "score": round(score, 2),
                    "amount_g": amount_g
                })
        else:
            unmatched_ingredients.append(ing_name)

    # 반올림
    for key in total_nutrition:
        total_nutrition[key] = round(total_nutrition[key], 1)

    return {
        "nutrition": total_nutrition,
        "matched": matched_ingredients,
        "unmatched": unmatched_ingredients
    }


def main():
    print("=" * 60)
    print("영양정보 연동")
    print("=" * 60)

    # 영양정보 DB 로드
    print("\n[1/3] 영양정보 DB 로드 중...")
    nutrition_db = load_nutrition_db()
    print(f"  로드된 식품: {len(nutrition_db)}개")

    if not nutrition_db:
        print("영양정보 DB가 비어있습니다. CSV 파일을 확인하세요.")
        return

    # 레시피 로드
    print("\n[2/3] 레시피 로드 중...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"  레시피 수: {len(recipes)}")

    # 영양정보 매칭
    print("\n[3/3] 영양정보 매칭 중...")
    matched_count = 0
    partial_count = 0

    for i, recipe in enumerate(recipes):
        result = calculate_recipe_nutrition(recipe, nutrition_db)

        # 기존 영양정보가 없거나 0이면 업데이트
        if recipes[i].get("total_calories", 0) == 0:
            recipes[i]["total_calories"] = result["nutrition"]["calories"]
            recipes[i]["total_protein"] = result["nutrition"]["protein"]
            recipes[i]["total_fat"] = result["nutrition"]["fat"]
            recipes[i]["total_carbs"] = result["nutrition"]["carbs"]
            recipes[i]["sodium"] = result["nutrition"]["sodium"]

        # 매칭 통계
        if result["matched"]:
            if not result["unmatched"]:
                matched_count += 1
            else:
                partial_count += 1

        recipes[i]["nutrition_matched"] = len(result["matched"])
        recipes[i]["nutrition_unmatched"] = result["unmatched"]

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(recipes)} processed...")

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    # 통계
    print(f"\n" + "=" * 60)
    print("완료!")
    print(f"전체 레시피: {len(recipes)}")
    print(f"완전 매칭: {matched_count}")
    print(f"부분 매칭: {partial_count}")
    print(f"매칭 실패: {len(recipes) - matched_count - partial_count}")
    print(f"출력 파일: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
