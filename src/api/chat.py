"""채팅 기반 레시피 추천 API"""

import os
import json
import httpx
from pydantic import BaseModel
from neo4j import AsyncGraphDatabase


# ============== 설정 ==============

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://141.164.35.214:7690")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "recipe_vultr_2025")


# ============== 모델 ==============

class ChatRequest(BaseModel):
    message: str
    user_name: str = "회원"


class ChatResponse(BaseModel):
    reply: str
    recipes: list[dict] = []
    ingredients_detected: list[str] = []


# ============== LLM 호출 ==============

async def extract_ingredients_llm(user_message: str) -> list[str]:
    """LLM으로 사용자 메시지에서 재료 추출"""

    prompt = f"""사용자 메시지에서 요리 재료만 추출해주세요.
JSON 배열로만 응답하세요. 다른 설명 없이 배열만 출력하세요.

예시:
- "냉장고에 두부랑 파 있어" → ["두부", "파"]
- "감자랑 양파, 당근으로 뭐 만들지" → ["감자", "양파", "당근"]
- "오늘 저녁 뭐 먹지" → []

사용자 메시지: {user_message}

응답 (JSON 배열만):"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "xiaomi/mimo-v2-flash:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0,
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            print(f"LLM Error: {response.text}")
            return []

        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        # JSON 파싱
        try:
            # ```json ... ``` 형태 처리
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            ingredients = json.loads(content)
            return ingredients if isinstance(ingredients, list) else []
        except:
            return []


async def generate_chat_response(
    user_message: str,
    ingredients: list[str],
    recipes: list[dict],
    user_name: str,
) -> str:
    """LLM으로 자연스러운 채팅 응답 생성"""

    if not recipes:
        recipe_info = "매칭되는 레시피가 없습니다."
    else:
        recipe_info = "\n".join([
            f"- {r['name']} ({r['calories']}kcal, 매칭 {r['matched']}개)"
            for r in recipes[:5]
        ])

    prompt = f"""당신은 친근한 요리 추천 AI입니다.
사용자의 냉장고 재료를 보고 레시피를 추천해주세요.
따뜻하고 자연스러운 한국어로 대화하세요.

사용자: {user_name}
사용자 메시지: {user_message}
감지된 재료: {ingredients}

매칭된 레시피:
{recipe_info}

응답 (2-3문장, 친근하게):"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "xiaomi/mimo-v2-flash:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            return "죄송해요, 잠시 문제가 생겼어요. 다시 시도해주세요!"

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()


# ============== Neo4j 쿼리 ==============

async def query_recipes_by_ingredients(ingredients: list[str], limit: int = 5) -> list[dict]:
    """재료로 레시피 검색 + 영양정보 (커버율 기반 정렬)"""

    if not ingredients:
        return []

    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # 재료 매칭 레시피 검색 (커버율 기반)
            result = await session.run("""
                UNWIND $ingredients AS ing
                MATCH (i:Ingredient)-[:REQUIRED_FOR]->(r:Recipe)
                WHERE toLower(i.name) CONTAINS toLower(ing)
                   OR ing IN r.aliases
                WITH r, collect(DISTINCT i.name) AS matched_ings

                // 레시피의 전체 재료
                MATCH (all_ing:Ingredient)-[:REQUIRED_FOR]->(r)
                WITH r, matched_ings, collect(DISTINCT all_ing.name) AS all_ingredients

                // 부족한 재료 계산 (전체 - 매칭)
                WITH r, matched_ings, all_ingredients,
                     [x IN all_ingredients WHERE NOT x IN matched_ings] AS missing_ings,
                     size(matched_ings) AS matched_count,
                     size(all_ingredients) AS total_count,
                     round(size(matched_ings) * 100.0 / size(all_ingredients)) AS coverage

                // 최소 1개 이상 매칭 & 커버율 20% 이상 & 재료 2개 이상
                WHERE matched_count >= 1 AND coverage >= 20 AND total_count >= 2

                RETURN r.name AS name,
                       r.category AS category,
                       r.cooking_time AS time,
                       r.difficulty AS difficulty,
                       r.calories AS recipe_cal,
                       matched_count AS matched,
                       matched_ings AS matched_ingredients,
                       missing_ings AS missing_ingredients,
                       total_count AS total_ingredients,
                       coverage
                ORDER BY coverage DESC, matched_count DESC
                LIMIT $limit
            """, ingredients=ingredients, limit=limit)

            recipes = []
            async for record in result:
                recipes.append({
                    "name": record["name"],
                    "category": record["category"],
                    "time": record["time"],
                    "difficulty": record["difficulty"],
                    "matched": record["matched"],
                    "matched_ingredients": record["matched_ingredients"],
                    "missing_ingredients": record["missing_ingredients"],
                    "total_ingredients": record["total_ingredients"],
                    "coverage": record["coverage"],
                    "calories": record["recipe_cal"] or 0,
                })

            return recipes
    finally:
        await driver.close()


async def query_basic_recipes(limit: int = 5) -> list[dict]:
    """한국요리 기본 100선 (인기/기본 레시피) - 로직 기반"""
    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # 기본/인기 레시피 쿼리 (예: 재료 수 적절, 난이도 보통 이하 등)
            # 여기서는 간단히 임의의 인기 한식 레시피를 가져오는 것으로 가정
            result = await session.run("""
                MATCH (r:Recipe)
                WHERE r.category IN ['국/찌개', '메인요리', '반찬', '밥']
                RETURN r.name AS name,
                       r.category AS category,
                       r.cooking_time AS time,
                       r.difficulty AS difficulty,
                       r.calories AS recipe_cal,
                       size([(i)-[:REQUIRED_FOR]->(r) | i]) AS total_ingredients
                ORDER BY r.views DESC, r.name ASC  // 뷰 수가 없다면 이름순 등
                LIMIT $limit
            """, limit=limit)

            recipes = []
            async for record in result:
                recipes.append({
                    "name": record["name"],
                    "category": record["category"],
                    "time": record["time"],
                    "difficulty": record["difficulty"],
                    "matched": 0,
                    "matched_ingredients": [],
                    "total_ingredients": record["total_ingredients"],
                    "coverage": 0,
                    "calories": record["recipe_cal"] or 0,
                })

            return recipes
    finally:
        await driver.close()


# ============== 메인 채팅 함수 ==============

async def query_recipe_detail(recipe_name: str) -> dict | None:
    """레시피 상세 정보 조회"""
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            result = await session.run("""
                MATCH (r:Recipe)
                WHERE r.name CONTAINS $name
                OPTIONAL MATCH (i:Ingredient)-[rel:REQUIRED_FOR]->(r)
                RETURN r.name AS name, r.category AS category,
                       r.cooking_time AS time, r.difficulty AS difficulty,
                       r.calories AS calories,
                       collect({name: i.name, amount: rel.amount, unit: rel.unit}) AS ingredients
                LIMIT 1
            """, name=recipe_name)

            record = await result.single()
            if record:
                return {
                    "name": record["name"],
                    "category": record["category"],
                    "time": record["time"],
                    "difficulty": record["difficulty"],
                    "calories": record["calories"],
                    "ingredients": record["ingredients"]
                }
            return None
    finally:
        await driver.close()


async def process_chat(request: ChatRequest) -> ChatResponse:
    """채팅 메시지 처리"""

    msg = request.message.strip()

    # 0-1. 레시피 상세 요청 감지 ("동그랑땡 어떻게", "김치찌개 만드는 법")
    recipe_keywords = ["어떻게", "만드는", "레시피", "만들", "조리법", "알려", "해"]
    if any(kw in msg for kw in recipe_keywords):
        # 메시지에서 레시피 이름 추출 시도 (모든 키워드 제거)
        msg_clean = msg
        for kw in recipe_keywords:
            msg_clean = msg_clean.replace(kw, "")
        msg_clean = msg_clean.replace("?", "").replace("줘", "").replace(" ", "").strip()

        if len(msg_clean) >= 2:
            recipe = await query_recipe_detail(msg_clean)
            if recipe:
                ing_list = ", ".join([i["name"] for i in recipe["ingredients"] if i["name"]])
                reply = f"**{recipe['name']}** 레시피에요!\n\n"
                reply += f"📂 카테고리: {recipe['category']}\n"
                reply += f"⏱️ 조리시간: {recipe['time']}분\n"
                reply += f"🔥 칼로리: {recipe['calories']}kcal\n"
                reply += f"📝 재료: {ing_list}\n\n"
                reply += "자세한 조리법이 필요하시면 말씀해주세요!"

                return ChatResponse(
                    reply=reply,
                    recipes=[recipe],
                    ingredients_detected=[]
                )

    # 0-2. 기본 한국 요리 추천
    if "한국요리 기본" in msg or "기본 요리" in msg:
        recipes = await query_basic_recipes()
        reply = "한국인이 가장 즐겨 먹는 기본 요리 100선 중 인기 레시피를 추천해드릴게요! 어떤게 끌리시나요?"
        return ChatResponse(
            reply=reply,
            recipes=recipes,
            ingredients_detected=[]
        )

    # 1. 재료 추출
    ingredients = await extract_ingredients_llm(request.message)

    # 2. 레시피 검색
    recipes = []
    if ingredients:
        recipes = await query_recipes_by_ingredients(ingredients)

    # 3. 응답 생성
    # 재료가 없는데 기본 추천을 원한 경우 (LLM이 재료 못 찾음) -> 기본 로직 fallback
    if not ingredients and not recipes:
         # LLM에게 그냥 맡기기 보다는, 레시피 추천 의도라면 추천해줌
         pass 

    reply = await generate_chat_response(
        user_message=request.message,
        ingredients=ingredients,
        recipes=recipes,
        user_name=request.user_name,
    )

    return ChatResponse(
        reply=reply,
        recipes=recipes,
        ingredients_detected=ingredients,
    )
