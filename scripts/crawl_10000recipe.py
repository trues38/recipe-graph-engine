"""만개의레시피 크롤링 스크립트

robots.txt 확인 결과: /admin/, /app/, /static/ 만 차단
일반적인 레시피 페이지 크롤링 허용

주의: 과도한 요청을 피하기 위해 rate limiting 적용
"""

import asyncio
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from bs4 import BeautifulSoup

# 출력 경로
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.10000recipe.com"


@dataclass
class Recipe:
    """크롤링된 레시피 데이터"""
    source_id: str
    name: str
    category: str
    cuisine: str
    time_minutes: int
    difficulty: str
    servings: int
    ingredients: list[dict]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_sodium: float
    description: str
    steps: list[str]
    tips: str
    tags: list[str]
    spicy_level: int
    suitable_for: list[str]
    avoid_for: list[str]
    source: str = "만개의레시피"


def parse_time(time_str: str) -> int:
    """시간 문자열 파싱 (예: '60분 이내' -> 60)"""
    if not time_str:
        return 30

    match = re.search(r"(\d+)", time_str)
    if match:
        return int(match.group(1))
    return 30


def parse_servings(servings_str: str) -> int:
    """인분 파싱 (예: '4인분' -> 4)"""
    if not servings_str:
        return 2

    match = re.search(r"(\d+)", servings_str)
    if match:
        return int(match.group(1))
    return 2


def parse_difficulty(diff_str: str) -> str:
    """난이도 파싱"""
    if not diff_str:
        return "보통"

    if "아무나" in diff_str or "쉬움" in diff_str:
        return "쉬움"
    elif "어려움" in diff_str or "고급" in diff_str:
        return "어려움"
    return "보통"


def parse_ingredients(soup: BeautifulSoup) -> list[dict]:
    """재료 파싱"""
    ingredients = []

    # 재료 영역 찾기
    material_area = soup.find("div", class_="ready_ingre3")
    if not material_area:
        material_area = soup.find("div", id="divConfirmedMaterialArea")

    if not material_area:
        return ingredients

    # 재료 항목 파싱
    items = material_area.find_all("li")
    for item in items:
        name_tag = item.find("div", class_="ingre_list_name")
        amount_tag = item.find("span", class_="ingre_list_ea")

        if not name_tag:
            # 다른 구조 시도
            text = item.get_text(strip=True)
            if not text:
                continue

            # "재료명 양" 형태 파싱
            parts = text.rsplit(" ", 1)
            if len(parts) == 2:
                name, amount_str = parts
            else:
                name = text
                amount_str = "적당량"
        else:
            name = name_tag.get_text(strip=True)
            amount_str = amount_tag.get_text(strip=True) if amount_tag else "적당량"

        # 양과 단위 분리
        amount, unit = parse_amount(amount_str)

        ingredients.append({
            "name": clean_ingredient_name(name),
            "amount": amount,
            "unit": unit,
        })

    return ingredients


def clean_ingredient_name(name: str) -> str:
    """재료명 정제"""
    # 괄호 내용 제거
    name = re.sub(r"\([^)]*\)", "", name)
    # 특수문자 제거
    name = re.sub(r"[●○◎▶▷]", "", name)
    return name.strip()


def parse_amount(amount_str: str) -> tuple[float, str]:
    """양과 단위 파싱"""
    if not amount_str or amount_str in ["적당량", "약간", "조금"]:
        return 1, "적당량"

    # 숫자 추출
    match = re.match(r"([0-9/.]+)\s*(.+)?", amount_str)
    if match:
        amount_raw = match.group(1)
        unit = match.group(2) or "개"

        # 분수 처리
        if "/" in amount_raw:
            parts = amount_raw.split("/")
            try:
                amount = float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                amount = 1
        else:
            try:
                amount = float(amount_raw)
            except ValueError:
                amount = 1

        return amount, unit.strip()

    return 1, amount_str


def parse_steps(soup: BeautifulSoup) -> list[str]:
    """조리 단계 파싱"""
    steps = []

    step_area = soup.find("div", class_="view_step_cont")
    if not step_area:
        step_area = soup.find("div", id="stepdescr")

    if not step_area:
        return steps

    # 단계별 설명 추출
    step_divs = step_area.find_all("div", class_="media-body")
    for div in step_divs:
        text = div.get_text(strip=True)
        if text:
            # 숫자 접두사 제거
            text = re.sub(r"^\d+\.\s*", "", text)
            steps.append(text)

    return steps


def parse_category(soup: BeautifulSoup) -> str:
    """카테고리 파싱"""
    # 메타 태그에서 카테고리 추출
    breadcrumb = soup.find("div", class_="view_cate")
    if breadcrumb:
        links = breadcrumb.find_all("a")
        for link in links:
            text = link.get_text(strip=True)
            if text in ["찌개", "국", "볶음", "구이", "찜", "튀김", "무침", "밥", "면", "디저트"]:
                return text

    return "기타"


def estimate_category_from_name(name: str) -> str:
    """이름에서 카테고리 추정"""
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
    return "기타"


def parse_tags(soup: BeautifulSoup, name: str, ingredients: list[dict]) -> list[str]:
    """태그 추출"""
    tags = []

    # 해시태그 영역
    tag_area = soup.find("div", class_="view_tag")
    if tag_area:
        tag_links = tag_area.find_all("a")
        for link in tag_links:
            tag = link.get_text(strip=True).replace("#", "")
            if tag:
                tags.append(tag)

    return tags[:10]  # 최대 10개


def estimate_spicy_level(ingredients: list[dict], name: str) -> int:
    """매운맛 레벨 추정"""
    spicy_keywords = ["고추", "고춧가루", "청양", "매운", "핫", "불닭"]
    ingredient_text = " ".join([i["name"] for i in ingredients])
    combined = ingredient_text + " " + name

    count = sum(1 for k in spicy_keywords if k in combined)
    if count >= 2:
        return 3
    elif count == 1:
        return 2
    return 0


def estimate_health_info(
    ingredients: list[dict],
    calories: float,
    protein: float,
    carbs: float,
    sodium: float,
) -> tuple[list[str], list[str]]:
    """건강 분류 추정"""
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

    return suitable_for, avoid_for


async def fetch_recipe(client: httpx.AsyncClient, recipe_id: str) -> Recipe | None:
    """단일 레시피 크롤링"""
    url = f"{BASE_URL}/recipe/{recipe_id}"

    try:
        response = await client.get(url)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # 제목
        title_tag = soup.find("div", class_="view2_summary")
        if not title_tag:
            return None

        name_tag = title_tag.find("h3")
        name = name_tag.get_text(strip=True) if name_tag else ""
        if not name:
            return None

        # 메타 정보
        info_tag = soup.find("div", class_="view2_summary_info")
        time_minutes = 30
        servings = 2
        difficulty = "보통"

        if info_tag:
            spans = info_tag.find_all("span")
            for span in spans:
                text = span.get_text(strip=True)
                if "분" in text:
                    time_minutes = parse_time(text)
                elif "인분" in text:
                    servings = parse_servings(text)
                elif any(k in text for k in ["아무나", "초급", "중급", "고급"]):
                    difficulty = parse_difficulty(text)

        # 재료
        ingredients = parse_ingredients(soup)
        if len(ingredients) < 2:
            return None

        # 조리 단계
        steps = parse_steps(soup)
        if not steps:
            return None

        # 카테고리
        category = parse_category(soup)
        if category == "기타":
            category = estimate_category_from_name(name)

        # 태그
        tags = parse_tags(soup, name, ingredients)

        # 설명
        desc_tag = soup.find("div", class_="view2_summary_in")
        description = ""
        if desc_tag:
            p_tag = desc_tag.find("p")
            if p_tag:
                description = p_tag.get_text(strip=True)[:200]

        # 영양 정보 (대략적 추정)
        calories = len(ingredients) * 50  # 임시 추정
        protein = len([i for i in ingredients if any(k in i["name"] for k in ["고기", "닭", "소고기", "돼지", "계란", "두부"])]) * 15
        carbs = len([i for i in ingredients if any(k in i["name"] for k in ["밥", "면", "감자", "당근"])]) * 20
        fat = len([i for i in ingredients if any(k in i["name"] for k in ["기름", "버터", "마요네즈"])]) * 10
        sodium = len([i for i in ingredients if any(k in i["name"] for k in ["간장", "소금", "된장", "고추장"])]) * 300

        # 매운맛
        spicy_level = estimate_spicy_level(ingredients, name)

        # 건강 분류
        suitable_for, avoid_for = estimate_health_info(ingredients, calories, protein, carbs, sodium)

        return Recipe(
            source_id=recipe_id,
            name=name,
            category=category,
            cuisine="한식",
            time_minutes=time_minutes,
            difficulty=difficulty,
            servings=servings,
            ingredients=ingredients,
            total_calories=float(calories),
            total_protein=float(protein),
            total_carbs=float(carbs),
            total_fat=float(fat),
            total_sodium=float(sodium),
            description=description,
            steps=steps,
            tips="",
            tags=tags,
            spicy_level=spicy_level,
            suitable_for=suitable_for,
            avoid_for=avoid_for,
        )

    except Exception as e:
        print(f"  Error fetching {recipe_id}: {e}")
        return None


async def fetch_recipe_ids_from_list(
    client: httpx.AsyncClient,
    page: int = 1,
    category: str = "",
) -> list[str]:
    """레시피 목록에서 ID 추출"""
    url = f"{BASE_URL}/recipe/list.html"
    params = {"page": page}
    if category:
        params["cat4"] = category

    try:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # 레시피 링크 추출
        recipe_ids = []
        links = soup.find_all("a", href=re.compile(r"/recipe/\d+"))
        for link in links:
            match = re.search(r"/recipe/(\d+)", link.get("href", ""))
            if match:
                recipe_ids.append(match.group(1))

        return list(set(recipe_ids))  # 중복 제거

    except Exception as e:
        print(f"  Error fetching list page {page}: {e}")
        return []


async def crawl_recipes(
    max_recipes: int = 500,
    batch_size: int = 10,
) -> list[dict]:
    """레시피 크롤링"""
    all_recipes = []
    seen_ids = set()

    print(f"만개의레시피 크롤링 시작 (목표: {max_recipes}개)")

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={
            "User-Agent": "RecipeGraphEngine/1.0 (Educational Project)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko-KR,ko;q=0.9",
        },
        follow_redirects=True,
    ) as client:
        page = 1

        while len(all_recipes) < max_recipes:
            print(f"\n페이지 {page} 처리 중...")

            # 목록에서 ID 수집
            recipe_ids = await fetch_recipe_ids_from_list(client, page)

            if not recipe_ids:
                print("  더 이상 레시피 없음")
                break

            # 새로운 ID만 필터링
            new_ids = [rid for rid in recipe_ids if rid not in seen_ids]
            seen_ids.update(new_ids)

            if not new_ids:
                page += 1
                continue

            print(f"  {len(new_ids)}개 레시피 발견")

            # 배치 처리
            for i in range(0, len(new_ids), batch_size):
                if len(all_recipes) >= max_recipes:
                    break

                batch = new_ids[i:i + batch_size]
                tasks = [fetch_recipe(client, rid) for rid in batch]
                results = await asyncio.gather(*tasks)

                for recipe in results:
                    if recipe and len(all_recipes) < max_recipes:
                        all_recipes.append(asdict(recipe))
                        print(f"  ✓ {len(all_recipes)}/{max_recipes}: {recipe.name}")

                # Rate limiting
                await asyncio.sleep(1.0)

            page += 1
            await asyncio.sleep(0.5)

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
    print("만개의레시피 크롤러")
    print("=" * 50)

    # 크롤링
    recipes = await crawl_recipes(max_recipes=500)
    print(f"\n총 수집: {len(recipes)}개")

    # 중복 제거
    recipes = deduplicate(recipes)
    print(f"중복 제거 후: {len(recipes)}개")

    # 저장 (raw)
    raw_path = OUTPUT_DIR / "10000recipe_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {raw_path}")

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
    print(f"\n다음 단계: python scripts/recipe_loader.py")


if __name__ == "__main__":
    asyncio.run(main())
