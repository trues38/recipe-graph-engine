"""FastAPI 메인 앱"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.utils.neo4j_client import Neo4jClient
from src.engines.query_engine import QueryEngine
from src.engines.persona_engine import (
    PersonaEngine, Persona, PERSONAS,
    get_all_personas, get_persona_by_name, get_personas_by_tier
)


# ============== 앱 상태 ==============

class AppState:
    neo4j_client: Neo4jClient | None = None
    query_engine: QueryEngine | None = None
    persona_engine: PersonaEngine | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클 관리"""
    # Startup
    state.neo4j_client = Neo4jClient()
    await state.neo4j_client.connect()
    state.query_engine = QueryEngine(state.neo4j_client)
    state.persona_engine = PersonaEngine()
    print("✓ Connected to Neo4j")

    yield

    # Shutdown
    if state.neo4j_client:
        await state.neo4j_client.close()
    print("✓ Disconnected from Neo4j")


# ============== FastAPI 앱 ==============

app = FastAPI(
    title="Recipe Graph Engine",
    description="Neo4j 기반 레시피 추천 엔진 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Request/Response 모델 ==============

class RecommendRequest(BaseModel):
    """레시피 추천 요청"""
    ingredients: list[str]
    persona: str = "엄마밥"
    user_name: str = "회원"
    min_coverage: int = 60
    limit: int = 5


class RecommendResponse(BaseModel):
    """레시피 추천 응답"""
    recipes: list[dict]
    message: str


class HealthRecommendRequest(BaseModel):
    """건강 맞춤 추천 요청"""
    ingredients: list[str]
    condition: str
    user_name: str = "회원"
    limit: int = 5


class DietRecommendRequest(BaseModel):
    """다이어트 추천 요청"""
    ingredients: list[str]
    max_calories: int = 500
    goal: str | None = None
    user_name: str = "회원"
    limit: int = 5


class VeganRecommendRequest(BaseModel):
    """비건 추천 요청"""
    ingredients: list[str]
    diet_type: str = "비건"
    user_name: str = "회원"
    limit: int = 5


class ModeRecommendRequest(BaseModel):
    """통합 모드 추천 요청"""
    ingredients: list[str]
    mode: str  # 페르소나 이름 (엄마밥, 다이어트코치, 자취생밥상 등)
    user_name: str = "회원"
    limit: int = 5
    # 모드별 추가 옵션
    max_calories: int | None = None  # 다이어트
    goal: str | None = None  # 다이어트 목표
    condition: str | None = None  # 건강 상태
    diet_type: str | None = None  # 비건/채식 유형
    max_minutes: int | None = None  # 간편식 시간


class CategoryRecommendRequest(BaseModel):
    """카테고리 기반 추천 요청 (신규)"""
    category: str  # 국/찌개, 메인요리, 반찬, 밑반찬, 간식
    ingredients: list[str] = []  # 선택, 빈 배열 가능
    persona: str = "엄마밥"
    user_name: str = "회원"
    limit: int = 10


# ============== 엔드포인트 ==============

@app.get("/")
async def root():
    """API 상태 확인"""
    return {"status": "ok", "message": "Recipe Graph Engine API"}


@app.get("/stats")
async def get_stats():
    """데이터베이스 통계"""
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")
    stats = await state.query_engine.get_stats()
    return {"stats": stats}


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """
    기본 레시피 추천 (엄마밥 - FREE)

    재료 목록을 입력받아 매칭되는 레시피 추천
    """
    if not state.query_engine or not state.persona_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    # 쿼리 실행
    recipes = await state.query_engine.find_recipes_by_ingredients(
        ingredients=request.ingredients,
        min_coverage=request.min_coverage,
        limit=request.limit,
    )

    # 페르소나 매핑
    try:
        persona = Persona(request.persona)
    except ValueError:
        persona = Persona.UMMA

    # 응답 생성
    message = await state.persona_engine.generate_response(
        recipes=recipes,
        persona=persona,
        user_name=request.user_name,
        use_llm=False,  # 템플릿 기반 (빠름)
    )

    return RecommendResponse(
        recipes=[
            {
                "name": r.name,
                "category": r.category,
                "cuisine": r.cuisine,
                "time_minutes": r.time_minutes,
                "difficulty": r.difficulty,
                "coverage": r.coverage,
                "missing_count": r.missing_count,
                "calories": r.total_calories,
                "protein": r.total_protein,
            }
            for r in recipes
        ],
        message=message,
    )


@app.get("/categories")
async def get_categories():
    """
    사용 가능한 카테고리 목록

    - 국/찌개: 찌개, 국, 탕, 전골
    - 메인요리: 볶음, 구이, 찜, 튀김, 면, 덮밥, 비빔밥
    - 반찬: 무침, 조림, 나물, 샐러드, 전
    - 밑반찬: 장아찌, 젓갈, 김치, 절임, 장류
    - 간식: 디저트, 간식, 떡, 빵, 음료
    """
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    categories = await state.query_engine.get_categories()
    return {"categories": categories}


@app.post("/recommend/category")
async def recommend_by_category(request: CategoryRecommendRequest):
    """
    카테고리 기반 레시피 추천 (신규 로직)

    - 카테고리 먼저 선택 (필수)
    - 재료 입력할수록 좁혀지는 방식
    - 매칭 수로 정렬 (커버리지 최소값 없음)
    - 재료 없어도 해당 카테고리 레시피 반환
    - 항상 결과 있음
    """
    if not state.query_engine or not state.persona_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    # 카테고리 기반 쿼리 실행 (페르소나 필터 적용)
    recipes = await state.query_engine.find_by_category_v2(
        category_group=request.category,
        ingredients=request.ingredients,
        persona=request.persona,
        limit=request.limit,
    )

    # 페르소나별 메시지 생성
    persona_greetings = {
        "엄마밥": f"얘야, {request.category} 맛있는 거 골라봤어~",
        "자취생": f"20분 안에 뚝딱! {request.category} 간단 레시피야",
        "다이어트": f"저칼로리 {request.category} 추천이에요!",
        "흑백요리사": f"오늘의 {request.category} 시그니처 메뉴입니다",
        "건강맞춤": f"건강에 좋은 {request.category} 레시피에요",
        "비건": f"채식 {request.category} 레시피입니다",
    }

    if recipes:
        trending_count = len([r for r in recipes if r.get("trending")])
        if request.ingredients:
            top_match = recipes[0].get("matched_count", 0)
            if top_match > 0:
                message = f"{persona_greetings.get(request.persona, f'{request.category} 레시피에요!')} 재료 {top_match}개 매칭!"
            else:
                message = persona_greetings.get(request.persona, f"{request.category} 레시피들이에요!")
        else:
            base_msg = persona_greetings.get(request.persona, f"{request.category} 인기 레시피들이에요!")
            if trending_count > 0:
                message = f"{base_msg} 🔥 SNS 인기 {trending_count}개 포함"
            else:
                message = base_msg
    else:
        message = f"{request.category} 카테고리에 레시피가 없네요."

    return {
        "recipes": [
            {
                "name": r.get("name"),
                "category": r.get("category"),
                "cooking_time": r.get("cooking_time"),
                "difficulty": r.get("difficulty"),
                "calories": r.get("calories"),
                "matched_count": r.get("matched_count", 0),
                "matched_ingredients": r.get("matched_ingredients", []),
                "missing_ingredients": r.get("missing_ingredients", [])[:5],
                "total_ingredients": r.get("total_ingredients", 0),
                "trending": r.get("trending", False),
                "x_likes": r.get("x_likes", 0),
                "x_tip": r.get("x_tip"),
            }
            for r in recipes
        ],
        "message": message,
        "category": request.category,
        "input_ingredients": request.ingredients,
        "persona": request.persona,
    }


@app.post("/recommend/health", response_model=RecommendResponse)
async def recommend_health(request: HealthRecommendRequest):
    """
    건강맞춤 레시피 추천 (PREMIUM)

    건강 상태를 고려한 안전한 레시피 추천
    """
    if not state.query_engine or not state.persona_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    recipes = await state.query_engine.find_safe_for_condition(
        ingredients=request.ingredients,
        condition_name=request.condition,
        limit=request.limit,
    )

    message = await state.persona_engine.generate_response(
        recipes=recipes,
        persona=Persona.HEALTH,
        user_name=request.user_name,
        user_condition=request.condition,
        use_llm=False,
    )

    return RecommendResponse(
        recipes=[
            {
                "name": r.name,
                "category": r.category,
                "coverage": r.coverage,
                "calories": r.total_calories,
                "safe": True,
            }
            for r in recipes
        ],
        message=message,
    )


@app.post("/recommend/diet", response_model=RecommendResponse)
async def recommend_diet(request: DietRecommendRequest):
    """
    다이어트코치 레시피 추천 (PREMIUM)

    칼로리/목표 기반 레시피 추천
    """
    if not state.query_engine or not state.persona_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    if request.goal:
        recipes = await state.query_engine.find_by_goal(
            ingredients=request.ingredients,
            goal_name=request.goal,
            limit=request.limit,
        )
    else:
        recipes = await state.query_engine.find_by_calories(
            ingredients=request.ingredients,
            max_calories=request.max_calories,
            limit=request.limit,
        )

    message = await state.persona_engine.generate_response(
        recipes=recipes,
        persona=Persona.DIET,
        user_name=request.user_name,
        use_llm=False,
    )

    return RecommendResponse(
        recipes=[
            {
                "name": r.name,
                "category": r.category,
                "calories": r.total_calories,
                "protein": r.total_protein,
                "carbs": r.total_carbs,
                "fat": r.total_fat,
                "coverage": r.coverage,
            }
            for r in recipes
        ],
        message=message,
    )


@app.post("/recommend/vegan", response_model=RecommendResponse)
async def recommend_vegan(request: VeganRecommendRequest):
    """
    무지개요리사 레시피 추천 (PREMIUM)

    비건/채식 호환 레시피 추천
    """
    if not state.query_engine or not state.persona_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    recipes = await state.query_engine.find_by_diet(
        ingredients=request.ingredients,
        diet_name=request.diet_type,
        limit=request.limit,
    )

    message = await state.persona_engine.generate_response(
        recipes=recipes,
        persona=Persona.VEGAN,
        user_name=request.user_name,
        use_llm=False,
    )

    return RecommendResponse(
        recipes=[
            {
                "name": r.name,
                "category": r.category,
                "protein": r.total_protein,
                "coverage": r.coverage,
            }
            for r in recipes
        ],
        message=message,
    )


@app.get("/ingredients/autocomplete")
async def autocomplete_ingredients(
    prefix: str = Query(..., min_length=1),
    limit: int = Query(default=10, le=50),
):
    """재료 자동완성"""
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    results = await state.query_engine.autocomplete_ingredient(
        prefix=prefix,
        limit=limit,
    )
    return {"ingredients": results}


@app.get("/recipes/{recipe_name}")
async def get_recipe_detail(recipe_name: str):
    """레시피 상세 정보 조회"""
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    detail = await state.query_engine.get_recipe_detail(recipe_name)
    if not detail:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return detail


@app.get("/recipes/{recipe_name}/missing")
async def get_missing_ingredients(
    recipe_name: str,
    my_ingredients: list[str] = Query(...),
):
    """레시피에 부족한 재료 조회"""
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    missing = await state.query_engine.find_missing_ingredients(
        recipe_name=recipe_name,
        my_ingredients=my_ingredients,
    )
    return {"recipe": recipe_name, "missing": missing}


@app.get("/recipes/{recipe_name}/similar")
async def get_similar_recipes(
    recipe_name: str,
    limit: int = Query(default=5, le=20),
):
    """유사 레시피 조회"""
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    similar = await state.query_engine.find_similar_recipes(
        recipe_name=recipe_name,
        limit=limit,
    )
    return {"recipe": recipe_name, "similar": similar}


@app.get("/ingredients/{ingredient_name}/pairings")
async def get_ingredient_pairings(
    ingredient_name: str,
    limit: int = Query(default=10, le=30),
):
    """재료 페어링 추천"""
    if not state.query_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    pairings = await state.query_engine.find_ingredient_pairings(
        main_ingredient=ingredient_name,
        limit=limit,
    )
    return {"ingredient": ingredient_name, "pairings": pairings}


# ============== 페르소나 모드 API ==============

@app.get("/modes")
async def list_modes():
    """
    사용 가능한 모든 페르소나 모드 목록

    각 모드별 특성과 티어 정보 반환
    - enabled=True: 현재 사용 가능
    - enabled=False: Coming Soon (추후 업데이트 예정)
    """
    # 모든 페르소나 반환 (비활성화 포함)
    all_personas = get_all_personas(include_disabled=True)
    enabled_personas = get_all_personas(include_disabled=False)

    return {
        "modes": all_personas,
        "total": len(all_personas),
        "enabled_count": len(enabled_personas),
        "tiers": {
            "FREE": get_personas_by_tier("FREE", include_disabled=True),
            "PREMIUM": get_personas_by_tier("PREMIUM", include_disabled=True),
        }
    }


@app.get("/modes/{mode_name}")
async def get_mode_detail(mode_name: str):
    """페르소나 모드 상세 정보"""
    persona = get_persona_by_name(mode_name)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Mode '{mode_name}' not found")

    config = PERSONAS[persona]
    return {
        "id": persona.name,
        "name": config.name,
        "icon": config.icon,
        "tier": config.tier,
        "description": config.description,
        "tone": config.tone,
        "formality": config.formality,
        "focus": config.focus,
        "query_mode": config.query_mode,
        "greeting_template": config.greeting_template,
        "encouragement": config.encouragement,
    }


@app.post("/recommend/mode", response_model=RecommendResponse)
async def recommend_by_mode(request: ModeRecommendRequest):
    """
    통합 모드 기반 레시피 추천

    모드에 따라 적합한 쿼리와 페르소나 응답 생성

    사용 가능한 모드:
    - 엄마밥: 기본 가정식 추천
    - 집밥요리사: 편안한 가정식
    - 자취생밥상: 20분 이내 간편식
    - 알뜰살림: 가성비 레시피
    - 다이어트코치: 칼로리/목표 기반
    - 벌크업코치: 고단백 레시피
    - 건강맞춤: 건강 상태별 추천
    - 무지개요리사: 비건/채식
    - 아이밥상: 아이/유아용
    - 손님초대: 파티/접대용
    - 한식장인: 정통 한식
    - 흑백요리사: 전문 셰프 스타일
    """
    if not state.query_engine or not state.persona_engine:
        raise HTTPException(status_code=503, detail="Service not ready")

    # 페르소나 조회
    persona = get_persona_by_name(request.mode)
    if not persona:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mode: {request.mode}. Use /modes to see available modes."
        )

    config = PERSONAS[persona]

    # 비활성화된 모드 체크
    if not config.enabled:
        raise HTTPException(
            status_code=400,
            detail=f"'{config.name}' 모드는 준비 중입니다. Coming Soon!"
        )

    query_mode = config.query_mode

    # 모드별 쿼리 실행
    recipes = []

    if query_mode == "general":
        recipes = await state.query_engine.find_recipes_by_ingredients(
            ingredients=request.ingredients,
            min_coverage=40,
            limit=request.limit,
        )
    elif query_mode == "diet":
        if request.goal:
            recipes = await state.query_engine.find_by_goal(
                ingredients=request.ingredients,
                goal_name=request.goal,
                limit=request.limit,
            )
        else:
            max_cal = request.max_calories or 500
            recipes = await state.query_engine.find_by_calories(
                ingredients=request.ingredients,
                max_calories=max_cal,
                limit=request.limit,
            )
    elif query_mode == "health":
        condition = request.condition or "당뇨"
        recipes = await state.query_engine.find_safe_for_condition(
            ingredients=request.ingredients,
            condition_name=condition,
            limit=request.limit,
        )
    elif query_mode == "vegan":
        diet_type = request.diet_type or "비건"
        recipes = await state.query_engine.find_by_diet(
            ingredients=request.ingredients,
            diet_name=diet_type,
            limit=request.limit,
        )
    elif query_mode == "quick":
        max_min = request.max_minutes or 20
        recipes = await state.query_engine.find_quick_recipes(
            ingredients=request.ingredients,
            max_minutes=max_min,
            limit=request.limit,
        )
    elif query_mode == "kids":
        recipes = await state.query_engine.find_kids_recipes(
            ingredients=request.ingredients,
            limit=request.limit,
        )
    elif query_mode == "bulk":
        recipes = await state.query_engine.find_bulk_recipes(
            ingredients=request.ingredients,
            limit=request.limit,
        )
    elif query_mode == "party":
        recipes = await state.query_engine.find_party_recipes(
            ingredients=request.ingredients,
            limit=request.limit,
        )
    elif query_mode == "traditional":
        recipes = await state.query_engine.find_traditional_recipes(
            ingredients=request.ingredients,
            limit=request.limit,
        )
    elif query_mode == "budget":
        recipes = await state.query_engine.find_budget_recipes(
            ingredients=request.ingredients,
            limit=request.limit,
        )
    else:
        # 기본 쿼리
        recipes = await state.query_engine.find_recipes_by_ingredients(
            ingredients=request.ingredients,
            min_coverage=40,
            limit=request.limit,
        )

    # 페르소나 응답 생성
    message = await state.persona_engine.generate_response(
        recipes=recipes,
        persona=persona,
        user_name=request.user_name,
        user_condition=request.condition,
        use_llm=False,
    )

    return RecommendResponse(
        recipes=[
            {
                "name": r.name,
                "category": r.category,
                "cuisine": r.cuisine,
                "time_minutes": r.time_minutes,
                "difficulty": r.difficulty,
                "coverage": r.coverage,
                "missing_count": r.missing_count,
                "calories": r.total_calories,
                "protein": r.total_protein,
                "carbs": r.total_carbs,
                "fat": r.total_fat,
            }
            for r in recipes
        ],
        message=message,
    )
