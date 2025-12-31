"""Kaggle What's Cooking 데이터셋에서 한식 레시피 추출

데이터셋: https://www.kaggle.com/c/whats-cooking/data
- 39,774개 레시피, 20개 cuisine 중 Korean 포함
- 재료 목록만 포함 (조리법 없음)
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# 출력 경로
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_kaggle_data():
    """Kaggle 데이터 다운로드 시도"""
    try:
        import kaggle
        kaggle.api.competition_download_files(
            "whats-cooking",
            path=str(OUTPUT_DIR),
        )
        return True
    except Exception as e:
        print(f"Kaggle API 오류: {e}")
        print("대안: GitHub 미러에서 다운로드 시도...")
        return False


def download_from_github():
    """GitHub 미러에서 다운로드"""
    import httpx

    # 알려진 GitHub 미러들
    mirrors = [
        "https://raw.githubusercontent.com/philipp-gaspar/whats-cooking/master/data/train.json",
        "https://raw.githubusercontent.com/Arcaici/whatcooking/main/data/train.json",
    ]

    for url in mirrors:
        try:
            print(f"다운로드 시도: {url}")
            response = httpx.get(url, timeout=60.0, follow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                print(f"  성공! {len(data)}개 레시피 로드")
                return data
        except Exception as e:
            print(f"  실패: {e}")
            continue

    return None


def create_sample_korean_recipes():
    """Kaggle 데이터 없을 경우 샘플 한식 레시피 생성"""
    print("샘플 한식 레시피 생성 중...")

    # What's Cooking 스타일의 한식 재료 데이터
    korean_ingredients = [
        {
            "name": "불고기",
            "ingredients": ["beef", "soy sauce", "sesame oil", "garlic", "sugar", "green onions", "sesame seeds", "pear", "black pepper"],
        },
        {
            "name": "비빔밥",
            "ingredients": ["rice", "beef", "spinach", "bean sprouts", "carrots", "zucchini", "egg", "gochujang", "sesame oil", "garlic"],
        },
        {
            "name": "김치찌개",
            "ingredients": ["kimchi", "pork belly", "tofu", "green onions", "garlic", "gochugaru", "sesame oil", "water"],
        },
        {
            "name": "된장찌개",
            "ingredients": ["doenjang", "tofu", "zucchini", "onion", "green chili", "red chili", "garlic", "anchovy stock"],
        },
        {
            "name": "잡채",
            "ingredients": ["sweet potato noodles", "beef", "spinach", "carrots", "onion", "mushrooms", "soy sauce", "sesame oil", "sugar", "garlic"],
        },
        {
            "name": "삼겹살",
            "ingredients": ["pork belly", "lettuce", "perilla leaves", "garlic", "green chili", "ssamjang", "sesame oil"],
        },
        {
            "name": "떡볶이",
            "ingredients": ["rice cakes", "fish cakes", "cabbage", "green onions", "gochujang", "gochugaru", "sugar", "soy sauce", "garlic"],
        },
        {
            "name": "순두부찌개",
            "ingredients": ["soft tofu", "pork", "clams", "egg", "green onions", "gochugaru", "garlic", "sesame oil", "anchovy stock"],
        },
        {
            "name": "갈비찜",
            "ingredients": ["beef short ribs", "radish", "carrots", "chestnuts", "jujubes", "soy sauce", "sugar", "garlic", "sesame oil", "ginger"],
        },
        {
            "name": "닭갈비",
            "ingredients": ["chicken", "cabbage", "sweet potato", "perilla leaves", "rice cakes", "gochujang", "gochugaru", "soy sauce", "sugar", "garlic"],
        },
        {
            "name": "냉면",
            "ingredients": ["buckwheat noodles", "beef brisket", "cucumber", "radish", "egg", "asian pear", "beef broth", "vinegar", "mustard"],
        },
        {
            "name": "김밥",
            "ingredients": ["rice", "seaweed", "pickled radish", "spinach", "carrots", "egg", "ham", "cucumber", "sesame oil", "salt"],
        },
        {
            "name": "해물파전",
            "ingredients": ["flour", "eggs", "squid", "shrimp", "green onions", "salt", "vegetable oil", "water"],
        },
        {
            "name": "감자탕",
            "ingredients": ["pork spine", "potatoes", "perilla leaves", "green onions", "garlic", "gochugaru", "doenjang", "perilla seeds"],
        },
        {
            "name": "보쌈",
            "ingredients": ["pork belly", "doenjang", "garlic", "ginger", "green onions", "rice wine", "black peppercorns"],
        },
        {
            "name": "제육볶음",
            "ingredients": ["pork", "onion", "green onions", "gochujang", "gochugaru", "soy sauce", "sugar", "garlic", "sesame oil", "black pepper"],
        },
        {
            "name": "오이소박이",
            "ingredients": ["cucumber", "chives", "garlic", "gochugaru", "fish sauce", "sugar", "salt"],
        },
        {
            "name": "깍두기",
            "ingredients": ["radish", "green onions", "garlic", "ginger", "gochugaru", "fish sauce", "sugar", "salt"],
        },
        {
            "name": "부대찌개",
            "ingredients": ["spam", "hot dogs", "kimchi", "tofu", "ramen noodles", "baked beans", "green onions", "gochugaru", "garlic"],
        },
        {
            "name": "갈비탕",
            "ingredients": ["beef short ribs", "radish", "green onions", "garlic", "salt", "black pepper", "water"],
        },
    ]

    return korean_ingredients


def estimate_category(name: str, ingredients: list[str]) -> str:
    """카테고리 추정"""
    name_lower = name.lower()
    ing_str = " ".join(ingredients).lower()

    if any(k in name_lower for k in ["찌개", "탕"]):
        return "찌개"
    elif any(k in name_lower for k in ["국"]):
        return "국"
    elif any(k in name_lower for k in ["볶음", "볶"]):
        return "볶음"
    elif any(k in name_lower for k in ["구이", "삼겹살"]):
        return "구이"
    elif any(k in name_lower for k in ["찜", "조림"]):
        return "찜"
    elif any(k in name_lower for k in ["전", "튀김"]):
        return "튀김"
    elif any(k in name_lower for k in ["무침", "소박이", "깍두기"]):
        return "무침"
    elif any(k in name_lower for k in ["밥", "김밥"]):
        return "밥"
    elif any(k in name_lower for k in ["면", "냉면"]):
        return "면"
    return "기타"


def translate_ingredient(eng: str) -> dict:
    """영어 재료를 한글로 변환"""
    translations = {
        "beef": "소고기",
        "pork": "돼지고기",
        "pork belly": "삼겹살",
        "chicken": "닭고기",
        "soy sauce": "간장",
        "sesame oil": "참기름",
        "garlic": "마늘",
        "sugar": "설탕",
        "green onions": "대파",
        "sesame seeds": "깨",
        "pear": "배",
        "black pepper": "후추",
        "rice": "쌀밥",
        "spinach": "시금치",
        "bean sprouts": "콩나물",
        "carrots": "당근",
        "zucchini": "애호박",
        "egg": "계란",
        "gochujang": "고추장",
        "kimchi": "김치",
        "tofu": "두부",
        "gochugaru": "고춧가루",
        "water": "물",
        "doenjang": "된장",
        "onion": "양파",
        "green chili": "청양고추",
        "red chili": "홍고추",
        "anchovy stock": "멸치육수",
        "sweet potato noodles": "당면",
        "mushrooms": "버섯",
        "lettuce": "상추",
        "perilla leaves": "깻잎",
        "ssamjang": "쌈장",
        "rice cakes": "떡",
        "fish cakes": "어묵",
        "cabbage": "배추",
        "soft tofu": "순두부",
        "clams": "조개",
        "beef short ribs": "소갈비",
        "radish": "무",
        "chestnuts": "밤",
        "jujubes": "대추",
        "ginger": "생강",
        "sweet potato": "고구마",
        "buckwheat noodles": "메밀면",
        "beef brisket": "차돌박이",
        "cucumber": "오이",
        "asian pear": "배",
        "beef broth": "소고기육수",
        "vinegar": "식초",
        "mustard": "겨자",
        "seaweed": "김",
        "pickled radish": "단무지",
        "ham": "햄",
        "salt": "소금",
        "flour": "밀가루",
        "squid": "오징어",
        "shrimp": "새우",
        "vegetable oil": "식용유",
        "pork spine": "돼지등뼈",
        "perilla seeds": "들깨",
        "rice wine": "맛술",
        "black peppercorns": "통후추",
        "chives": "부추",
        "fish sauce": "액젓",
        "spam": "스팸",
        "hot dogs": "소시지",
        "ramen noodles": "라면",
        "baked beans": "콩",
    }

    name = translations.get(eng.lower(), eng)
    return {
        "name": name,
        "amount": 1,
        "unit": "적당량",
    }


def transform_to_recipe(item: dict) -> dict:
    """Kaggle 형식을 내부 형식으로 변환"""
    name = item.get("name", "한식 요리")
    raw_ingredients = item.get("ingredients", [])

    ingredients = [translate_ingredient(ing) for ing in raw_ingredients]
    category = estimate_category(name, raw_ingredients)

    # 매운맛 레벨
    spicy_keywords = ["gochujang", "gochugaru", "kimchi", "chili"]
    ing_str = " ".join(raw_ingredients).lower()
    spicy_level = sum(1 for k in spicy_keywords if k in ing_str)
    spicy_level = min(spicy_level, 3)

    # 건강 분류
    protein_keywords = ["beef", "pork", "chicken", "tofu", "egg", "shrimp"]
    has_protein = any(k in ing_str for k in protein_keywords)

    suitable_for = []
    if has_protein:
        suitable_for.append("벌크업")
    suitable_for.append("유지")

    avoid_for = []
    if "spam" in ing_str or "hot dogs" in ing_str:
        avoid_for.append("고혈압")

    return {
        "name": name,
        "category": category,
        "cuisine": "한식",
        "time_minutes": 30,  # 기본값
        "difficulty": "보통",
        "servings": 2,
        "ingredients": ingredients,
        "total_calories": len(ingredients) * 50,  # 대략적 추정
        "total_protein": 20.0 if has_protein else 5.0,
        "total_carbs": 30.0,
        "total_fat": 10.0,
        "total_sodium": 500.0,
        "description": f"{name} - 한국 전통 요리",
        "steps": [f"{name} 조리법을 참고하세요."],  # 조리법 없음
        "tips": "",
        "tags": ["한식", category],
        "spicy_level": spicy_level,
        "suitable_for": suitable_for,
        "avoid_for": avoid_for,
        "source": "Kaggle-Whats-Cooking",
        "source_id": name,
    }


def extract_korean_from_kaggle(data: list[dict]) -> list[dict]:
    """Kaggle 데이터에서 한식만 추출"""
    korean_recipes = [
        item for item in data
        if item.get("cuisine", "").lower() == "korean"
    ]
    print(f"한식 레시피 추출: {len(korean_recipes)}개")

    results = []
    for item in korean_recipes:
        # Kaggle 형식: {"id": 123, "cuisine": "korean", "ingredients": [...]}
        recipe = {
            "name": f"Korean Recipe {item.get('id', 0)}",
            "ingredients": item.get("ingredients", []),
        }
        results.append(transform_to_recipe(recipe))

    return results


def main():
    """메인 실행"""
    print("=" * 50)
    print("Kaggle What's Cooking 한식 데이터 추출")
    print("=" * 50)

    # 1. Kaggle 데이터 다운로드 시도
    kaggle_data = download_from_github()

    if kaggle_data:
        # Kaggle 데이터에서 한식 추출
        recipes = extract_korean_from_kaggle(kaggle_data)
    else:
        # 샘플 데이터 사용
        print("\n온라인 데이터를 찾을 수 없습니다.")
        print("내장된 한식 샘플 레시피를 사용합니다.")
        sample_data = create_sample_korean_recipes()
        recipes = [transform_to_recipe(item) for item in sample_data]

    print(f"\n총 {len(recipes)}개 한식 레시피 준비됨")

    # 저장
    raw_path = OUTPUT_DIR / "kaggle_korean_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print(f"저장: {raw_path}")

    # processed 폴더에 병합
    processed_path = Path(__file__).parent.parent / "data" / "processed" / "recipes.json"

    existing = []
    if processed_path.exists():
        with open(processed_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"기존 레시피: {len(existing)}개")

    # 병합
    existing_names = {r["name"] for r in existing}
    new_recipes = [r for r in recipes if r["name"] not in existing_names]
    merged = existing + new_recipes

    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"병합 저장: {len(existing)} + {len(new_recipes)} = {len(merged)}개")

    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
