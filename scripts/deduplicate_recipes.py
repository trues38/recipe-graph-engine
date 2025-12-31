"""레시피 중복 제거 (Deduplication)"""

import json
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

INPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_classified.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_deduped.json"
DUPLICATES_LOG = Path(__file__).parent.parent / "data" / "processed" / "duplicates_log.json"


def normalize_name(name: str) -> str:
    """이름 정규화 (비교용)"""
    # 공백, 특수문자 제거
    name = re.sub(r'[^\w가-힣]', '', name.lower())
    return name


def levenshtein_ratio(s1: str, s2: str) -> float:
    """Levenshtein 유사도 계산"""
    return SequenceMatcher(None, s1, s2).ratio()


def jaccard_similarity(set1: set, set2: set) -> float:
    """Jaccard 유사도 계산"""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def get_ingredient_set(recipe: dict) -> set:
    """레시피의 재료 이름 집합"""
    return set(ing.get("name", "") for ing in recipe.get("ingredients", []))


def recipe_completeness(recipe: dict) -> int:
    """레시피 완전성 점수 (높을수록 좋음)"""
    score = 0

    # 필드별 점수
    if recipe.get("steps") and len(recipe["steps"]) > 0:
        score += 20
    if recipe.get("ingredients") and len(recipe["ingredients"]) > 0:
        score += 20
    if recipe.get("total_calories", 0) > 0:
        score += 15
    if recipe.get("description"):
        score += 10
    if recipe.get("tips"):
        score += 5
    if recipe.get("time_minutes", 0) > 0:
        score += 10
    if recipe.get("difficulty"):
        score += 5
    if recipe.get("servings", 0) > 0:
        score += 5
    if recipe.get("cuisine"):
        score += 5
    if recipe.get("category_group"):
        score += 5

    return score


def is_duplicate(recipe1: dict, recipe2: dict, threshold: float = 0.85) -> bool:
    """두 레시피가 중복인지 확인"""
    name1 = normalize_name(recipe1.get("name", ""))
    name2 = normalize_name(recipe2.get("name", ""))

    # Level 1: 정확히 같은 이름
    if name1 == name2:
        return True

    # Level 2: 이름 유사도
    name_sim = levenshtein_ratio(name1, name2)
    if name_sim >= threshold:
        return True

    # Level 3: 재료 유사도 (이름이 80% 이상 유사할 때만)
    if name_sim >= 0.7:
        ing1 = get_ingredient_set(recipe1)
        ing2 = get_ingredient_set(recipe2)
        ing_sim = jaccard_similarity(ing1, ing2)
        if ing_sim >= 0.8:
            return True

    return False


def merge_recipes(recipes: list[dict]) -> dict:
    """중복 레시피들을 병합 (가장 완전한 것 기준)"""
    if len(recipes) == 1:
        return recipes[0]

    # 완전성 점수로 정렬
    sorted_recipes = sorted(recipes, key=recipe_completeness, reverse=True)
    best = sorted_recipes[0].copy()

    # 다른 레시피에서 누락된 정보 보완
    for recipe in sorted_recipes[1:]:
        if not best.get("description") and recipe.get("description"):
            best["description"] = recipe["description"]
        if not best.get("tips") and recipe.get("tips"):
            best["tips"] = recipe["tips"]
        if best.get("total_calories", 0) == 0 and recipe.get("total_calories", 0) > 0:
            best["total_calories"] = recipe["total_calories"]
            best["total_protein"] = recipe.get("total_protein", 0)
            best["total_carbs"] = recipe.get("total_carbs", 0)
            best["total_fat"] = recipe.get("total_fat", 0)

    # 병합된 소스 기록
    best["merged_from"] = [r.get("original_name", r.get("name")) for r in recipes]

    return best


def find_duplicates(recipes: list[dict]) -> list[list[int]]:
    """모든 중복 그룹 찾기"""
    n = len(recipes)
    visited = [False] * n
    duplicate_groups = []

    # 이름 기반 빠른 그룹핑
    name_groups = defaultdict(list)
    for i, recipe in enumerate(recipes):
        normalized = normalize_name(recipe.get("name", ""))
        name_groups[normalized].append(i)

    # 정확히 같은 이름 그룹
    for indices in name_groups.values():
        if len(indices) > 1:
            duplicate_groups.append(indices)
            for i in indices:
                visited[i] = True

    # 유사한 이름 찾기 (O(n^2) 주의)
    print("  유사도 검사 중...")
    for i in range(n):
        if visited[i]:
            continue

        group = [i]
        for j in range(i + 1, n):
            if visited[j]:
                continue

            if is_duplicate(recipes[i], recipes[j]):
                group.append(j)
                visited[j] = True

        if len(group) > 1:
            duplicate_groups.append(group)

        visited[i] = True

    return duplicate_groups


def main():
    print("=" * 60)
    print("레시피 중복 제거")
    print("=" * 60)

    # 데이터 로드
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes")

    # 중복 그룹 찾기
    print("\n[1/2] 중복 그룹 탐색 중...")
    duplicate_groups = find_duplicates(recipes)
    print(f"  발견된 중복 그룹: {len(duplicate_groups)}")

    # 중복 로그 저장
    duplicates_log = []
    for group in duplicate_groups:
        names = [recipes[i].get("name") for i in group]
        duplicates_log.append({
            "indices": group,
            "names": names,
            "count": len(group)
        })

    with open(DUPLICATES_LOG, "w", encoding="utf-8") as f:
        json.dump(duplicates_log, f, ensure_ascii=False, indent=2)

    # 중복 병합
    print("\n[2/2] 중복 병합 중...")
    duplicate_indices = set()
    merged_recipes = []

    for group in duplicate_groups:
        group_recipes = [recipes[i] for i in group]
        merged = merge_recipes(group_recipes)
        merged_recipes.append(merged)
        duplicate_indices.update(group)

    # 중복이 아닌 레시피 추가
    unique_recipes = [r for i, r in enumerate(recipes) if i not in duplicate_indices]
    final_recipes = unique_recipes + merged_recipes

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_recipes, f, ensure_ascii=False, indent=2)

    # 통계
    removed = len(recipes) - len(final_recipes)
    print(f"\n" + "=" * 60)
    print("완료!")
    print(f"원본 레시피: {len(recipes)}")
    print(f"중복 그룹: {len(duplicate_groups)}")
    print(f"제거된 중복: {removed}")
    print(f"최종 레시피: {len(final_recipes)}")
    print(f"중복 로그: {DUPLICATES_LOG}")
    print(f"출력 파일: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
