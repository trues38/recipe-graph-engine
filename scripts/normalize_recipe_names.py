"""LLM을 사용한 레시피 이름 정규화"""

import asyncio
import json
import os
import re
from pathlib import Path
import httpx

# OpenRouter 설정
OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "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"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DATA_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_cleaned.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_normalized.json"
MAPPING_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipe_name_mapping.json"


def rule_based_clean(name: str) -> str:
    """규칙 기반 전처리 (LLM 호출 전)"""
    original = name

    # 1. HTML 태그 형식 제거: <다이어트>, <건강식> 등
    name = re.sub(r'<[^>]+>', '', name)

    # 2. 대괄호 태그 제거: [다이어트], [초간단] 등
    name = re.sub(r'\[[^\]]+\]', '', name)

    # 3. 앞쪽 번호 제거: 189., #12, No.5 등
    name = re.sub(r'^[\d#]+[.\s]+', '', name)
    name = re.sub(r'^No\.?\s*\d+\s*', '', name, flags=re.IGNORECASE)

    # 4. 날짜 제거: (2025.11.26), 20241231 등
    name = re.sub(r'\(\d{4}[.\-/]?\d{1,2}[.\-/]?\d{1,2}\)', '', name)
    name = re.sub(r'\d{8}$', '', name)  # 끝에 붙은 8자리 날짜

    # 5. 괄호 안 불필요한 정보 제거
    name = re.sub(r'\([^)]*레시피[^)]*\)', '', name)
    name = re.sub(r'\([^)]*만들기[^)]*\)', '', name)

    # 6. 블로그 스타일 접미사 제거
    suffixes = ['만들기', '레시피', '하는법', '하는 법', '만드는법', '만드는 법', '황금레시피']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # 7. 특수문자 정리
    name = re.sub(r'[~!@#$%^&*]+', '', name)
    name = re.sub(r'\s+', ' ', name)

    return name.strip()


def is_clean_name(name: str) -> bool:
    """이름이 이미 깨끗한지 확인"""
    # 태그, 번호, 날짜 등이 없으면 깨끗함
    patterns = [
        r'<[^>]+>',           # HTML 태그
        r'\[[^\]]+\]',        # 대괄호
        r'^\d+[.\s]',         # 앞쪽 번호
        r'\(\d{4}',           # 연도가 포함된 괄호
        r'만들기$',           # 블로그 스타일
        r'레시피$',
        r'하는\s?법$',
    ]
    for pattern in patterns:
        if re.search(pattern, name):
            return False
    return len(name) <= 20  # 너무 긴 이름도 정제 필요


async def call_llm(prompt: str, model: str = "xiaomi/mimo-v2-flash:free") -> str:
    """LLM API 호출"""
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


async def normalize_names_batch(names: list[str]) -> dict[str, str]:
    """레시피 이름 배치 정규화"""

    prompt = f"""다음은 요리 레시피 이름 목록입니다.
각 이름에서 **순수한 요리 이름만** 추출해주세요.

규칙:
1. 태그 제거: <다이어트>, [건강식], (초간단) 등
2. 번호 제거: 189., #12, No.5 등
3. 날짜 제거: (2025.11.26), 20241231 등
4. 블로그 스타일 제거: "~만들기", "~레시피", "~하는법" 등
5. 수식어는 유지: "매콤", "시원한", "엄마표" 등은 요리 특성이므로 유지
6. 결과는 2-15자 사이의 간결한 요리명

입력 레시피명:
{json.dumps(names, ensure_ascii=False, indent=2)}

JSON 형식으로 응답 (원본 → 정제된 이름):
{{"원본레시피명": "정제된이름", ...}}

예시:
- "<다이어트 건강식>초간단 순두부 계란찜" → "순두부 계란찜"
- "189.새송이버섯조림(2025.11.26)" → "새송이버섯조림"
- "[자취요리] 간단 계란볶음밥 만들기" → "계란볶음밥"
- "엄마표 된장찌개" → "엄마표 된장찌개"

JSON만 반환:"""

    result = await call_llm(prompt)

    try:
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        print(f"JSON parse error: {result[:200]}", flush=True)
        return {}


async def main():
    print("=" * 60, flush=True)
    print("레시피 이름 정규화", flush=True)
    print("=" * 60, flush=True)

    # 데이터 로드
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes", flush=True)

    # 모든 레시피 이름 추출
    all_names = [r["name"] for r in recipes]
    print(f"Total recipe names: {len(all_names)}", flush=True)

    # 기존 매핑 로드
    mapping = {}
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        print(f"Loaded {len(mapping)} existing mappings", flush=True)

    # 1단계: 규칙 기반 전처리
    print("\n[1/2] 규칙 기반 전처리...", flush=True)
    rule_cleaned = 0
    for name in all_names:
        if name not in mapping:
            cleaned = rule_based_clean(name)
            if is_clean_name(cleaned) and cleaned != name:
                mapping[name] = cleaned
                rule_cleaned += 1
    print(f"  규칙 기반 정제: {rule_cleaned}개", flush=True)

    # 2단계: LLM으로 나머지 처리
    to_process = [name for name in all_names if name not in mapping]
    print(f"\n[2/2] LLM 정제 필요: {len(to_process)}개", flush=True)

    if to_process:
        batch_size = 50
        llm_cleaned = 0

        for i in range(0, len(to_process), batch_size):
            batch = to_process[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(to_process) + batch_size - 1) // batch_size
            print(f"\nBatch {batch_num}/{total_batches}...", flush=True)

            batch_result = await normalize_names_batch(batch)

            for orig, cleaned in batch_result.items():
                if orig not in mapping and cleaned:
                    mapping[orig] = cleaned
                    llm_cleaned += 1

            # 중간 저장
            with open(MAPPING_FILE, "w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

            print(f"  Processed: {len(batch)}, New: {llm_cleaned}", flush=True)
            await asyncio.sleep(1)

        print(f"\nLLM 정제 완료: {llm_cleaned}개", flush=True)

    # 정규화된 레시피 생성
    print("\n정규화된 레시피 생성 중...", flush=True)
    normalized_recipes = []

    for recipe in recipes:
        normalized = {**recipe}
        orig_name = recipe["name"]

        # 매핑된 이름 사용, 없으면 규칙 기반 정제
        if orig_name in mapping:
            normalized["name"] = mapping[orig_name]
        else:
            normalized["name"] = rule_based_clean(orig_name)

        # 원본 이름 보존
        normalized["original_name"] = orig_name
        normalized_recipes.append(normalized)

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized_recipes, f, ensure_ascii=False, indent=2)

    # 통계
    changed = sum(1 for r in normalized_recipes if r["name"] != r["original_name"])

    print(f"\n" + "=" * 60, flush=True)
    print("완료!", flush=True)
    print(f"총 레시피: {len(normalized_recipes)}", flush=True)
    print(f"이름 변경됨: {changed}", flush=True)
    print(f"매핑 수: {len(mapping)}", flush=True)
    print(f"출력 파일: {OUTPUT_FILE}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
