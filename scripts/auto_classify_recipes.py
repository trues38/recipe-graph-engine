"""레시피 다차원 자동 분류 (Cuisine/Category/Persona)"""

import json
import re
from pathlib import Path
from collections import Counter

INPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_final.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_classified.json"


# === Cuisine (요리종류) 분류 ===
CUISINE_KEYWORDS = {
    "한식": {
        "ingredients": ["김치", "된장", "고추장", "참기름", "들기름", "젓갈", "고춧가루", "간장", "멸치", "다시마", "깻잎", "부추", "미나리", "쑥갓", "콩나물", "무", "배추"],
        "name_patterns": ["비빔", "찌개", "전골", "국", "탕", "볶음", "조림", "무침", "나물", "김치", "쌈", "죽"],
        "weight": 1.0
    },
    "중식": {
        "ingredients": ["굴소스", "두반장", "화자오", "팔각", "오향", "청경채", "숙주", "목이버섯", "죽순", "샤오싱주"],
        "name_patterns": ["짜장", "짬뽕", "탕수", "마파", "깐풍", "유린", "팔보", "양장피", "깐쇼"],
        "weight": 1.2
    },
    "일식": {
        "ingredients": ["미소", "미린", "가쓰오", "와사비", "다시", "청주", "폰즈", "가츠오부시", "매실청", "유자"],
        "name_patterns": ["돈부리", "우동", "라멘", "초밥", "회", "덮밥", "가츠", "야키", "나베", "데리야끼"],
        "weight": 1.2
    },
    "양식": {
        "ingredients": ["올리브오일", "버터", "크림", "파스타", "치즈", "토마토소스", "바질", "오레가노", "파마산", "베이컨", "소시지"],
        "name_patterns": ["파스타", "스테이크", "수프", "샐러드", "그라탕", "리조또", "피자", "샌드위치", "오믈렛"],
        "weight": 1.1
    },
    "동남아": {
        "ingredients": ["피시소스", "코코넛", "라임", "고수", "칠리", "레몬그라스", "타마린드", "커리", "강황", "갈랑갈"],
        "name_patterns": ["팟타이", "쌀국수", "분짜", "커리", "똠양", "나시", "사테", "분보", "반미"],
        "weight": 1.3
    },
}

# === Category (카테고리) 분류 ===
CATEGORY_RULES = {
    "국/찌개": {
        "name_suffix": ["찌개", "국", "탕", "전골", "수프", "나베"],
        "keywords": ["끓인다", "육수"],
        "priority": 1
    },
    "메인요리": {
        "name_suffix": ["볶음", "구이", "찜", "튀김", "스테이크", "로스트", "커틀릿"],
        "keywords": ["굽는다", "튀긴다", "찐다"],
        "min_time": 20,
        "priority": 2
    },
    "면/밥": {
        "name_suffix": ["면", "국수", "라면", "파스타", "밥", "덮밥", "비빔밥", "볶음밥", "리조또", "죽"],
        "keywords": ["삶는다"],
        "priority": 1
    },
    "반찬": {
        "name_suffix": ["무침", "조림", "나물", "샐러드", "전", "적"],
        "keywords": ["무친다", "조린다"],
        "max_time": 20,
        "priority": 3
    },
    "밑반찬": {
        "name_suffix": ["장아찌", "젓갈", "김치", "절임", "장류", "피클"],
        "keywords": [],
        "priority": 1
    },
    "간식/디저트": {
        "name_suffix": ["디저트", "간식", "떡", "빵", "케이크", "쿠키", "음료", "스무디", "푸딩"],
        "keywords": [],
        "priority": 2
    },
}

# === Persona 태깅 규칙 ===
PERSONA_RULES = {
    "자취생": {
        "conditions": {
            "max_time": 20,
            "max_ingredients": 7,
            "max_steps": 5,
            "difficulty": ["쉬움"],
        },
        "description": "빠르고 간단한 요리"
    },
    "다이어트": {
        "conditions": {
            "max_calories": 500,
            "exclude_ingredients": ["설탕", "버터", "크림", "마요네즈"],
            "prefer_ingredients": ["닭가슴살", "두부", "야채", "샐러드"],
        },
        "description": "저칼로리 건강식"
    },
    "흑백요리사": {
        "conditions": {
            "min_steps": 8,
            "min_time": 40,
            "difficulty": ["어려움", "보통"],
        },
        "description": "본격적인 요리"
    },
    "엄마밥": {
        "conditions": {
            "prefer_categories": ["국/찌개", "밑반찬", "반찬"],
            "prefer_cuisine": ["한식"],
        },
        "description": "정성 가득 한식"
    },
    "건강맞춤": {
        "conditions": {
            "has_nutrition": True,
            "balanced": True,
        },
        "description": "영양 균형식"
    },
    "비건": {
        "conditions": {
            "exclude_ingredients": ["고기", "돼지", "소", "닭", "오리", "생선", "새우", "조개", "계란", "우유", "치즈", "버터", "크림"],
        },
        "description": "채식 요리"
    },
}


def classify_cuisine(recipe: dict) -> str:
    """요리종류 분류"""
    name = recipe.get("name", "")
    ingredients = [ing.get("name", "") for ing in recipe.get("ingredients", [])]
    ingredients_text = " ".join(ingredients)

    scores = {}

    for cuisine, rules in CUISINE_KEYWORDS.items():
        score = 0

        # 재료 매칭
        for kw in rules["ingredients"]:
            if kw in ingredients_text:
                score += 2 * rules["weight"]

        # 이름 패턴 매칭
        for pattern in rules["name_patterns"]:
            if pattern in name:
                score += 3 * rules["weight"]

        scores[cuisine] = score

    # 최고 점수 선택 (기본값: 한식)
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "한식"


def classify_category(recipe: dict) -> str:
    """카테고리 분류"""
    name = recipe.get("name", "")
    time_minutes = recipe.get("time_minutes", 30)
    steps_text = " ".join(recipe.get("steps", []))

    # 우선순위별 확인
    matches = []

    for category, rules in CATEGORY_RULES.items():
        score = 0

        # 이름 접미사 확인
        for suffix in rules.get("name_suffix", []):
            if name.endswith(suffix) or suffix in name:
                score += 10

        # 키워드 확인
        for kw in rules.get("keywords", []):
            if kw in steps_text:
                score += 2

        # 시간 조건
        if "min_time" in rules and time_minutes < rules["min_time"]:
            score -= 5
        if "max_time" in rules and time_minutes > rules["max_time"]:
            score -= 5

        if score > 0:
            matches.append((category, score, rules.get("priority", 5)))

    if matches:
        # 점수 높은 것, 우선순위 낮은 것 선택
        matches.sort(key=lambda x: (-x[1], x[2]))
        return matches[0][0]

    return "메인요리"


def classify_personas(recipe: dict) -> list[str]:
    """페르소나 태깅"""
    name = recipe.get("name", "")
    time_minutes = recipe.get("time_minutes", 30)
    ingredients = [ing.get("name", "") for ing in recipe.get("ingredients", [])]
    ingredients_text = " ".join(ingredients)
    steps = recipe.get("steps", [])
    calories = recipe.get("total_calories", 0)
    difficulty = recipe.get("difficulty", "보통")
    cuisine = recipe.get("cuisine", "한식")
    category = recipe.get("category_group", "메인요리")

    matched_personas = []

    for persona, rules in PERSONA_RULES.items():
        cond = rules["conditions"]
        match = True

        # 시간 조건
        if "max_time" in cond and time_minutes > cond["max_time"]:
            match = False
        if "min_time" in cond and time_minutes < cond["min_time"]:
            match = False

        # 재료 수 조건
        if "max_ingredients" in cond and len(ingredients) > cond["max_ingredients"]:
            match = False

        # 단계 수 조건
        if "max_steps" in cond and len(steps) > cond["max_steps"]:
            match = False
        if "min_steps" in cond and len(steps) < cond["min_steps"]:
            match = False

        # 난이도 조건
        if "difficulty" in cond and difficulty not in cond["difficulty"]:
            match = False

        # 칼로리 조건
        if "max_calories" in cond and calories > 0 and calories > cond["max_calories"]:
            match = False

        # 제외 재료 확인
        if "exclude_ingredients" in cond:
            for excl in cond["exclude_ingredients"]:
                if excl in ingredients_text:
                    match = False
                    break

        # 선호 재료 확인 (보너스)
        if "prefer_ingredients" in cond:
            for pref in cond["prefer_ingredients"]:
                if pref in ingredients_text:
                    match = True  # 하나라도 있으면 매칭

        # 선호 카테고리
        if "prefer_categories" in cond:
            if category in cond["prefer_categories"]:
                match = True

        # 선호 요리종류
        if "prefer_cuisine" in cond:
            if cuisine in cond["prefer_cuisine"]:
                match = True

        if match:
            matched_personas.append(persona)

    return matched_personas if matched_personas else ["일반"]


def main():
    print("=" * 60)
    print("레시피 다차원 자동 분류")
    print("=" * 60)

    # 데이터 로드
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes")

    # 분류 수행
    print("\n분류 진행 중...")
    cuisine_counts = Counter()
    category_counts = Counter()
    persona_counts = Counter()

    for i, recipe in enumerate(recipes):
        # Cuisine 분류
        cuisine = classify_cuisine(recipe)
        recipes[i]["cuisine"] = cuisine
        cuisine_counts[cuisine] += 1

        # Category 분류
        category = classify_category(recipe)
        recipes[i]["category_group"] = category
        category_counts[category] += 1

        # Persona 태깅
        personas = classify_personas(recipe)
        recipes[i]["personas"] = personas
        for p in personas:
            persona_counts[p] += 1

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(recipes)} processed...")

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    # 통계 출력
    print(f"\n" + "=" * 60)
    print("분류 완료!")
    print(f"\n=== Cuisine 분포 ===")
    for cuisine, count in cuisine_counts.most_common():
        print(f"  {cuisine}: {count}")

    print(f"\n=== Category 분포 ===")
    for category, count in category_counts.most_common():
        print(f"  {category}: {count}")

    print(f"\n=== Persona 분포 ===")
    for persona, count in persona_counts.most_common():
        print(f"  {persona}: {count}")

    print(f"\n출력 파일: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
