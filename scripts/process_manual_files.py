"""수동 크롤링 파일 처리 스크립트

처리 대상:
1. 전북특별자치도_음식만드는법_20191219..csv (875개) - 완전한 레시피
2. 농림수산식품교육문화정보원_고수요리법_20190926.csv (705개) - HTML 파싱 필요
"""

import json
import re
from pathlib import Path
from html.parser import HTMLParser
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class HTMLTextExtractor(HTMLParser):
    """HTML에서 텍스트 추출"""
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data.strip())

    def get_text(self):
        return ' '.join(filter(None, self.text_parts))


def strip_html(html_str: str) -> str:
    """HTML 태그 제거"""
    if not html_str or pd.isna(html_str):
        return ""
    parser = HTMLTextExtractor()
    try:
        parser.feed(str(html_str))
        return parser.get_text()
    except:
        # 간단한 정규식 폴백
        return re.sub(r'<[^>]+>', ' ', str(html_str)).strip()


def parse_ingredients(ing_str: str) -> list[dict]:
    """재료 문자열 파싱"""
    if not ing_str or pd.isna(ing_str):
        return []

    ingredients = []
    # 다양한 구분자로 분리
    parts = re.split(r'[,\n·•]', str(ing_str))

    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue

        # 숫자와 단위 추출
        match = re.match(r'(.+?)\s*([\d./]+)?\s*(g|ml|개|큰술|작은술|컵|모|장|줌|약간|조금)?$', part)
        if match:
            name = match.group(1).strip()
            amount = match.group(2) or "1"
            unit = match.group(3) or "적당량"

            # 분수 처리
            if "/" in amount:
                nums = amount.split("/")
                try:
                    amount = float(nums[0]) / float(nums[1])
                except:
                    amount = 1
            else:
                try:
                    amount = float(amount)
                except:
                    amount = 1

            ingredients.append({
                "name": name[:20],  # 이름 길이 제한
                "amount": amount,
                "unit": unit,
            })
        else:
            ingredients.append({
                "name": part[:20],
                "amount": 1,
                "unit": "적당량",
            })

    return ingredients[:30]  # 최대 30개


def parse_steps(content: str) -> list[str]:
    """조리 단계 파싱"""
    if not content or pd.isna(content):
        return []

    content = strip_html(str(content))

    # 숫자로 시작하는 단계 분리
    steps = re.split(r'(?:\d+[.)\s]|\n)', content)
    steps = [s.strip() for s in steps if s and len(s.strip()) > 5]

    if not steps:
        # 문장 단위로 분리
        steps = [s.strip() for s in content.split('.') if len(s.strip()) > 10]

    return steps[:20]  # 최대 20단계


def estimate_category(name: str) -> str:
    """카테고리 추정"""
    name = str(name).lower()

    if any(k in name for k in ["찌개", "전골"]):
        return "찌개"
    elif any(k in name for k in ["국", "탕", "육수"]):
        return "국"
    elif any(k in name for k in ["볶음", "볶"]):
        return "볶음"
    elif any(k in name for k in ["구이", "굽"]):
        return "구이"
    elif any(k in name for k in ["찜", "조림"]):
        return "찜"
    elif any(k in name for k in ["전", "튀김", "부침"]):
        return "튀김"
    elif any(k in name for k in ["무침", "샐러드", "절임", "김치"]):
        return "무침"
    elif any(k in name for k in ["밥", "덮밥", "비빔밥"]):
        return "밥"
    elif any(k in name for k in ["면", "국수", "냉면"]):
        return "면"
    elif any(k in name for k in ["떡", "한과", "약과"]):
        return "디저트"
    return "기타"


def estimate_difficulty(steps_count: int, ing_count: int) -> str:
    """난이도 추정"""
    if steps_count <= 5 and ing_count <= 5:
        return "쉬움"
    elif steps_count <= 10 and ing_count <= 10:
        return "보통"
    return "어려움"


def process_jeonbuk(df: pd.DataFrame) -> list[dict]:
    """전북특별자치도_음식만드는법 처리"""
    recipes = []

    for _, row in df.iterrows():
        name = str(row.get("음식명", "")).strip()
        if not name or len(name) < 2:
            continue

        # 재료 파싱
        ingredients = parse_ingredients(row.get("재료", ""))
        if len(ingredients) < 2:
            continue

        # 조리 단계
        steps = parse_steps(row.get("내용", ""))
        if not steps:
            continue

        # 칼로리
        calories = 0
        cal_str = str(row.get("칼로리", ""))
        cal_match = re.search(r'(\d+)', cal_str)
        if cal_match:
            calories = int(cal_match.group(1))

        category = estimate_category(name)
        difficulty = estimate_difficulty(len(steps), len(ingredients))

        # 매운맛 추정
        ing_str = " ".join([i["name"] for i in ingredients])
        spicy_level = 0
        if any(k in ing_str for k in ["고추", "고춧가루", "청양"]):
            spicy_level = 2
        elif any(k in ing_str for k in ["고추장", "매운"]):
            spicy_level = 1

        recipe = {
            "name": name,
            "category": category,
            "cuisine": "한식",
            "time_minutes": len(steps) * 5,
            "difficulty": difficulty,
            "servings": 4,
            "ingredients": ingredients,
            "total_calories": calories if calories else len(ingredients) * 50,
            "total_protein": 15.0,
            "total_carbs": 30.0,
            "total_fat": 10.0,
            "total_sodium": 500.0,
            "description": str(row.get("관련이야기", ""))[:200] if pd.notna(row.get("관련이야기")) else "",
            "steps": steps,
            "tips": str(row.get("팁", ""))[:100] if pd.notna(row.get("팁")) else "",
            "tags": ["한식", "전북", category],
            "spicy_level": spicy_level,
            "suitable_for": ["유지"],
            "avoid_for": [],
            "source": "전북특별자치도",
            "source_id": f"jeonbuk_{row.get('연번', '')}",
        }
        recipes.append(recipe)

    return recipes


def process_gosu(df: pd.DataFrame) -> list[dict]:
    """농림수산식품교육문화정보원_고수요리법 처리"""
    recipes = []

    for _, row in df.iterrows():
        name = str(row.get("제목", row.get("메뉴명", ""))).strip()
        if not name or len(name) < 2:
            continue

        # HTML 내용에서 재료와 단계 추출
        content = str(row.get("내용", ""))
        text_content = strip_html(content)

        if len(text_content) < 50:
            continue

        # 재료 추출 시도 (패턴: "재료:" 또는 "재료 :" 다음 내용)
        ing_match = re.search(r'재료[:\s]+(.+?)(?:만드는\s*법|조리법|방법|①|1\.|$)', text_content, re.DOTALL)
        if ing_match:
            ingredients = parse_ingredients(ing_match.group(1))
        else:
            # 전체 텍스트에서 추출 시도
            ingredients = parse_ingredients(text_content[:500])

        if len(ingredients) < 2:
            # 최소 재료 추가
            ingredients = [{"name": "재료", "amount": 1, "unit": "적당량"}]

        # 조리법 추출
        steps_match = re.search(r'(?:만드는\s*법|조리법|방법)[:\s]*(.+)', text_content, re.DOTALL)
        if steps_match:
            steps = parse_steps(steps_match.group(1))
        else:
            steps = parse_steps(text_content)

        if not steps:
            continue

        category = estimate_category(name)
        difficulty = estimate_difficulty(len(steps), len(ingredients))

        recipe = {
            "name": name,
            "category": category,
            "cuisine": "한식",
            "time_minutes": len(steps) * 5,
            "difficulty": difficulty,
            "servings": 2,
            "ingredients": ingredients,
            "total_calories": len(ingredients) * 50,
            "total_protein": 15.0,
            "total_carbs": 30.0,
            "total_fat": 10.0,
            "total_sodium": 500.0,
            "description": text_content[:200],
            "steps": steps,
            "tips": "",
            "tags": ["한식", "고수요리", category],
            "spicy_level": 1,
            "suitable_for": ["유지"],
            "avoid_for": [],
            "source": "농림수산식품교육문화정보원",
            "source_id": f"gosu_{_}",
        }
        recipes.append(recipe)

    return recipes


def deduplicate(recipes: list[dict], existing_names: set) -> list[dict]:
    """중복 제거"""
    seen = set(existing_names)
    unique = []

    for r in recipes:
        name = r["name"]
        if name not in seen:
            seen.add(name)
            unique.append(r)

    return unique


def main():
    print("=" * 50)
    print("수동 크롤링 파일 처리")
    print("=" * 50)

    all_recipes = []

    # 1. 전북특별자치도_음식만드는법
    jeonbuk_path = DATA_DIR / "전북특별자치도_음식만드는법_20191219..csv"
    if jeonbuk_path.exists():
        print(f"\n[1] 전북특별자치도 파일 처리 중...")
        df = pd.read_csv(jeonbuk_path, encoding='cp949')
        recipes = process_jeonbuk(df)
        print(f"    → {len(recipes)}개 레시피 추출")
        all_recipes.extend(recipes)

    # 2. 농림수산식품교육문화정보원_고수요리법
    gosu_path = DATA_DIR / "농림수산식품교육문화정보원_고수요리법_20190926.csv"
    if gosu_path.exists():
        print(f"\n[2] 고수요리법 파일 처리 중...")
        df = pd.read_csv(gosu_path, encoding='cp949')
        recipes = process_gosu(df)
        print(f"    → {len(recipes)}개 레시피 추출")
        all_recipes.extend(recipes)

    print(f"\n총 추출: {len(all_recipes)}개")

    # 기존 데이터 로드
    processed_path = OUTPUT_DIR / "recipes.json"
    existing = []
    if processed_path.exists():
        with open(processed_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"기존 레시피: {len(existing)}개")

    # 중복 제거
    existing_names = {r["name"] for r in existing}
    new_recipes = deduplicate(all_recipes, existing_names)
    print(f"신규 레시피: {len(new_recipes)}개")

    # 병합 저장
    merged = existing + new_recipes
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n병합 저장: {len(existing)} + {len(new_recipes)} = {len(merged)}개")
    print(f"→ {processed_path}")

    # Raw 저장
    raw_path = DATA_DIR / "manual_processed.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_recipes, f, ensure_ascii=False, indent=2)
    print(f"→ {raw_path}")

    print("\n" + "=" * 50)
    print("완료!")
    print("=" * 50)
    print(f"\n다음 단계: python scripts/recipe_loader.py")


if __name__ == "__main__":
    main()
