"""LLM을 사용한 조리순서 정규화"""

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

INPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_normalized.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "processed" / "recipes_final.json"

# 블로그 스타일 패턴
BLOG_PATTERNS = ['~', '^^', 'ㅎㅎ', 'ㅋㅋ', '요~', '에요', '해요', '네요', '어요', '가요',
                 '해주세요', '넣어주세요', '끓여주세요', '볶아주세요']


def needs_normalization(steps: list) -> bool:
    """조리순서가 정규화가 필요한지 확인"""
    if not steps:
        return False

    for step in steps:
        step_str = str(step)
        # 블로그 스타일 패턴 확인
        if any(p in step_str for p in BLOG_PATTERNS):
            return True
        # 너무 긴 단계 (50자 이상)
        if len(step_str) > 100:
            return True
        # 이모지 포함
        if any(ord(c) > 0x1F600 and ord(c) < 0x1F650 for c in step_str):
            return True

    return False


def rule_based_clean_step(step: str) -> str:
    """규칙 기반 조리순서 정제"""
    # ~요 → ~다 변환
    step = re.sub(r'해요\.?$', '한다.', step)
    step = re.sub(r'해주세요\.?$', '한다.', step)
    step = re.sub(r'넣어요\.?$', '넣는다.', step)
    step = re.sub(r'넣어주세요\.?$', '넣는다.', step)
    step = re.sub(r'끓여요\.?$', '끓인다.', step)
    step = re.sub(r'끓여주세요\.?$', '끓인다.', step)
    step = re.sub(r'볶아요\.?$', '볶는다.', step)
    step = re.sub(r'볶아주세요\.?$', '볶는다.', step)
    step = re.sub(r'굽죠\.?$', '굽는다.', step)
    step = re.sub(r'구워요\.?$', '굽는다.', step)
    step = re.sub(r'으세요\.?$', '는다.', step)
    step = re.sub(r'세요\.?$', '다.', step)

    # 이모지, 특수문자 제거
    step = re.sub(r'[~^ㅎㅋ]+', '', step)
    step = re.sub(r'[!]+', '.', step)

    # 공백 정리
    step = re.sub(r'\s+', ' ', step).strip()

    return step


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


async def normalize_steps_llm(recipe_name: str, steps: list) -> list:
    """LLM으로 조리순서 정규화"""

    steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])

    prompt = f"""다음은 "{recipe_name}" 레시피의 조리순서입니다.
간결하고 명확한 지시문으로 정규화해주세요.

규칙:
1. "~해요", "~해주세요" → "~한다" (명령형/서술형)
2. 이모지, ~, ^^, ㅎㅎ 등 제거
3. 각 단계는 1-2문장으로 간결하게
4. 불필요한 설명/감탄사 제거
5. 핵심 조리 동작만 유지

원본 조리순서:
{steps_text}

정규화된 조리순서를 JSON 배열로 반환:
["1단계 내용", "2단계 내용", ...]

JSON 배열만 반환:"""

    result = await call_llm(prompt)

    try:
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        normalized = json.loads(result.strip())
        if isinstance(normalized, list) and len(normalized) > 0:
            return normalized
    except json.JSONDecodeError:
        pass

    # 파싱 실패시 규칙 기반 정제
    return [rule_based_clean_step(s) for s in steps]


async def main():
    print("=" * 60, flush=True)
    print("조리순서 정규화", flush=True)
    print("=" * 60, flush=True)

    # 데이터 로드
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    print(f"Loaded {len(recipes)} recipes", flush=True)

    # 정규화 필요한 레시피 확인
    needs_norm = [(i, r) for i, r in enumerate(recipes) if needs_normalization(r.get('steps', []))]
    print(f"정규화 필요: {len(needs_norm)}개", flush=True)

    # 1단계: 규칙 기반 전처리
    print("\n[1/2] 규칙 기반 전처리...", flush=True)
    rule_fixed = 0
    for i, recipe in enumerate(recipes):
        steps = recipe.get('steps', [])
        if steps:
            cleaned = [rule_based_clean_step(s) for s in steps]
            if cleaned != steps:
                recipes[i]['steps'] = cleaned
                rule_fixed += 1
    print(f"  규칙 기반 정제: {rule_fixed}개", flush=True)

    # 다시 확인
    still_needs = [(i, r) for i, r in enumerate(recipes) if needs_normalization(r.get('steps', []))]
    print(f"\n[2/2] LLM 정제 필요: {len(still_needs)}개", flush=True)

    # 2단계: LLM으로 나머지 처리 (배치 없이 개별 처리)
    llm_fixed = 0
    for batch_idx, (i, recipe) in enumerate(still_needs):
        if (batch_idx + 1) % 20 == 0:
            print(f"  {batch_idx + 1}/{len(still_needs)} processed...", flush=True)

        steps = recipe.get('steps', [])
        normalized = await normalize_steps_llm(recipe['name'], steps)
        recipes[i]['steps'] = normalized
        llm_fixed += 1

        await asyncio.sleep(0.5)  # API 레이트 리밋

    print(f"\nLLM 정제 완료: {llm_fixed}개", flush=True)

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    # 통계
    print(f"\n" + "=" * 60, flush=True)
    print("완료!", flush=True)
    print(f"총 레시피: {len(recipes)}", flush=True)
    print(f"규칙 기반 정제: {rule_fixed}", flush=True)
    print(f"LLM 정제: {llm_fixed}", flush=True)
    print(f"출력 파일: {OUTPUT_FILE}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
