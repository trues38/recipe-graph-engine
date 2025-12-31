# 데이터 파이프라인

## 개요

```
공개 데이터셋 ──┐
               ├──▶ 통합 ──▶ LLM 구조화 ──▶ Neo4j 적재
크롤링 구조 ───┘
```

---

## Phase 1: 데이터 수집

### 1.1 공개 데이터셋

#### 한국 데이터

| 소스 | URL | 내용 | 포맷 |
|------|-----|------|------|
| 농식품부 한식DB | data.mafra.go.kr | 한식 3,000+ | JSON/XML |
| 식약처 영양DB | foodsafetykorea.go.kr | 식품 영양정보 | API |
| 공공데이터포털 | data.go.kr | 조리법, 영양 | CSV |

```python
# 농식품부 API 예시
import requests

def fetch_korean_recipes():
    url = "http://api.data.mafra.go.kr/..."
    params = {
        "serviceKey": API_KEY,
        "type": "json",
        "pageNo": 1,
        "numOfRows": 100
    }
    response = requests.get(url, params=params)
    return response.json()["recipes"]
```

#### 글로벌 데이터

| 소스 | 내용 | 라이선스 |
|------|------|----------|
| Recipe1M+ | 100만+ 레시피 (영문) | MIT |
| Kaggle Food.com | 50만+ 레시피 | CC |
| USDA FoodData | 영양정보 | Public |

```python
# Recipe1M+ 다운로드
# http://pic2recipe.csail.mit.edu/

# Kaggle 다운로드
# kaggle datasets download -d shuyangli94/food-com-recipes-and-user-interactions
```

### 1.2 크롤링 (구조만)

**법적 안전 원칙**: 팩트만 추출, 원문 저장 안 함

```python
def extract_recipe_structure(raw_html):
    """
    저장 O (팩트):
    - 재료 목록: ["돼지고기 300g", "김치 200g"]
    - 조리 시간: 30
    - 난이도: "쉬움"
    - 카테고리: "찌개"
    - 태그: ["한식", "국물요리"]
    
    저장 X (저작권):
    - 레시피 원문
    - 조리 설명 문장
    - 이미지 URL
    """
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    structure = {
        "source": "만개의레시피",  # 출처만 기록
        "source_id": extract_id(soup),
        "ingredients": extract_ingredients(soup),
        "time_minutes": extract_time(soup),
        "difficulty": extract_difficulty(soup),
        "category": classify_category(soup),
        "tags": extract_tags(soup),
        "servings": extract_servings(soup),
    }
    
    # 원문은 저장하지 않음!
    # structure["instructions"] = X
    # structure["description"] = X
    
    return structure


def extract_ingredients(soup):
    """재료 추출 (팩트)"""
    ingredients = []
    for item in soup.select('.ingredient-item'):
        name = item.select_one('.name').text.strip()
        amount = item.select_one('.amount').text.strip()
        ingredients.append(f"{name} {amount}")
    return ingredients


def extract_time(soup):
    """조리 시간 추출 (팩트)"""
    time_el = soup.select_one('.cooking-time')
    if time_el:
        text = time_el.text
        # "30분" -> 30
        return int(re.search(r'\d+', text).group())
    return None
```

### 1.3 크롤링 대상

| 사이트 | 크롤링 | 참고 |
|--------|--------|------|
| 만개의레시피 | 구조만 | robots.txt 확인 |
| 백종원 유튜브 | X | 저작권 |
| 해먹남녀 | 구조만 | robots.txt 확인 |
| 쿠킹엔 | 구조만 | API 있음 |

---

## Phase 2: LLM 구조화

### 2.1 재료 정규화

```python
INGREDIENT_NORMALIZE_PROMPT = """
다음 재료 목록을 정규화해주세요.

입력: {raw_ingredients}

출력 형식 (JSON):
[
  {
    "name": "정규화된 이름",
    "amount": 숫자,
    "unit": "g/ml/개/큰술/작은술/컵",
    "prep": "전처리 방법 (선택)",
    "optional": true/false
  }
]

규칙:
1. 이름은 기본형으로 (삼겹살 → 돼지고기)
2. 단위 통일 (한 줌 → 30g)
3. 선택 재료는 optional: true
4. 전처리는 별도 필드로 (다진 마늘 → name: 마늘, prep: 다진)

예시:
입력: ["삼겹살 300g", "다진 마늘 1큰술", "파 약간"]
출력: [
  {"name": "돼지고기", "amount": 300, "unit": "g"},
  {"name": "마늘", "amount": 1, "unit": "큰술", "prep": "다진"},
  {"name": "대파", "amount": 20, "unit": "g", "optional": true}
]
"""
```

### 2.2 레시피 재생성 (저작권 회피)

```python
RECIPE_GENERATION_PROMPT = """
다음 조건으로 일반적인 조리 방법을 작성해주세요.

재료: {ingredients}
요리 종류: {category}
난이도: {difficulty}
조리 시간: {time}분

규칙:
1. 특정 출처의 문장을 복제하지 마세요
2. 일반적인 조리 상식에 기반해 작성하세요
3. 단계별로 명확하게 작성하세요
4. 팁이 있다면 추가해주세요

출력 형식 (JSON):
{
  "description": "한 줄 설명",
  "steps": ["1단계", "2단계", ...],
  "tips": "조리 팁"
}
"""
```

### 2.3 영양 정보 계산

```python
def calculate_nutrition(ingredients: List[dict]) -> dict:
    """
    재료 목록 → 총 영양 정보 계산
    USDA/식약처 DB 참조
    """
    total = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "fiber": 0,
        "sodium": 0
    }
    
    for ing in ingredients:
        # DB에서 100g당 영양정보 조회
        nutrition = get_nutrition_per_100g(ing["name"])
        if not nutrition:
            continue
            
        # 실제 양으로 계산
        ratio = convert_to_grams(ing["amount"], ing["unit"]) / 100
        
        total["calories"] += nutrition["calories"] * ratio
        total["protein"] += nutrition["protein"] * ratio
        # ...
    
    return total
```

### 2.4 자동 분류

```python
CLASSIFICATION_PROMPT = """
다음 레시피를 분류해주세요.

레시피: {recipe_name}
재료: {ingredients}

출력 형식 (JSON):
{
  "category": "찌개/볶음/구이/찜/튀김/무침/국/밥/면/디저트",
  "cuisine": "한식/양식/중식/일식/동남아/퓨전",
  "tags": ["태그1", "태그2"],
  "spicy_level": 0-3,
  "suitable_for": ["다이어트", "벌크업", ...],
  "avoid_for": ["당뇨", "고혈압", ...]
}
"""
```

---

## Phase 3: 배치 처리

### 3.1 파이프라인 실행

```python
import asyncio
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async def process_recipe(raw_data: dict) -> dict:
    """단일 레시피 처리"""
    
    # 1. 재료 정규화
    ingredients = await normalize_ingredients(raw_data["ingredients"])
    
    # 2. 레시피 재생성
    recipe_content = await generate_recipe(
        ingredients=ingredients,
        category=raw_data["category"],
        difficulty=raw_data["difficulty"],
        time=raw_data["time_minutes"]
    )
    
    # 3. 영양 정보 계산
    nutrition = calculate_nutrition(ingredients)
    
    # 4. 자동 분류
    classification = await classify_recipe(
        raw_data["name"], 
        ingredients
    )
    
    return {
        "name": raw_data["name"],
        "ingredients": ingredients,
        "nutrition": nutrition,
        **recipe_content,
        **classification
    }


async def batch_process(raw_recipes: List[dict], batch_size=10):
    """배치 처리"""
    results = []
    
    for i in range(0, len(raw_recipes), batch_size):
        batch = raw_recipes[i:i+batch_size]
        tasks = [process_recipe(r) for r in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        print(f"Processed {len(results)}/{len(raw_recipes)}")
        await asyncio.sleep(1)  # Rate limiting
    
    return results
```

### 3.2 비용 추정

| 작업 | 토큰/건 | 1만 건 비용 |
|------|---------|-------------|
| 재료 정규화 | ~500 | ~$7.50 |
| 레시피 생성 | ~800 | ~$12.00 |
| 자동 분류 | ~300 | ~$4.50 |
| **총합** | ~1,600 | **~$24** |

---

## Phase 4: 데이터 검증

### 4.1 품질 체크

```python
def validate_recipe(recipe: dict) -> List[str]:
    """레시피 품질 검증"""
    errors = []
    
    # 필수 필드
    required = ["name", "ingredients", "category", "steps"]
    for field in required:
        if not recipe.get(field):
            errors.append(f"Missing: {field}")
    
    # 재료 최소 개수
    if len(recipe.get("ingredients", [])) < 2:
        errors.append("Too few ingredients")
    
    # 영양 정보 범위
    if recipe.get("total_calories", 0) > 3000:
        errors.append("Unrealistic calories")
    
    # 조리 시간 범위
    if not (5 <= recipe.get("time_minutes", 0) <= 480):
        errors.append("Unrealistic time")
    
    return errors
```

### 4.2 중복 제거

```python
def deduplicate_recipes(recipes: List[dict]) -> List[dict]:
    """중복 레시피 제거"""
    seen = set()
    unique = []
    
    for r in recipes:
        # 재료 기반 해시
        ing_key = tuple(sorted([i["name"] for i in r["ingredients"]]))
        key = (r["name"], ing_key)
        
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return unique
```

---

## 출력 형식

### 최종 JSON 스키마

```json
{
  "name": "김치찌개",
  "category": "찌개",
  "cuisine": "한식",
  "time_minutes": 30,
  "difficulty": "쉬움",
  "servings": 2,
  
  "ingredients": [
    {"name": "돼지고기", "amount": 300, "unit": "g"},
    {"name": "김치", "amount": 200, "unit": "g"},
    {"name": "두부", "amount": 150, "unit": "g"},
    {"name": "대파", "amount": 30, "unit": "g"}
  ],
  
  "nutrition": {
    "total_calories": 450,
    "total_protein": 35,
    "total_carbs": 25,
    "total_fat": 20,
    "total_fiber": 5,
    "total_sodium": 1200
  },
  
  "description": "시큼한 김치와 돼지고기가 어우러진 한국 대표 국물 요리",
  "steps": [
    "1. 돼지고기를 한입 크기로 썬다",
    "2. 냄비에 기름을 두르고 돼지고기를 볶는다",
    "3. 김치를 넣고 함께 볶는다",
    "4. 물을 붓고 끓인다",
    "5. 두부를 넣고 5분 더 끓인다",
    "6. 대파를 넣고 마무리한다"
  ],
  "tips": "김치가 시큼할수록 국물 맛이 좋습니다",
  
  "tags": ["국물", "매운맛", "겨울", "집밥"],
  "spicy_level": 2,
  
  "suitable_for": ["일반"],
  "avoid_for": ["저나트륨"]
}
```
