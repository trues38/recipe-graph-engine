"""페르소나 엔진 테스트"""

import pytest
from unittest.mock import AsyncMock, patch

from src.engines.persona_engine import PersonaEngine, Persona, PERSONAS
from src.engines.query_engine import RecipeResult


@pytest.fixture
def persona_engine():
    """페르소나 엔진 인스턴스"""
    with patch("src.engines.persona_engine.get_settings") as mock_settings:
        mock_settings.return_value.anthropic_api_key = "test-key"
        return PersonaEngine()


@pytest.fixture
def sample_recipes():
    """샘플 레시피 결과"""
    return [
        RecipeResult(
            name="김치찌개",
            category="찌개",
            cuisine="한식",
            time_minutes=30,
            difficulty="쉬움",
            coverage=80,
            missing_count=1,
            total_calories=450,
            total_protein=35,
            total_carbs=25,
            total_fat=20,
            description="맛있는 김치찌개",
            tips="김치가 시큼할수록 맛있어요",
        )
    ]


class TestPersonaConfig:
    """페르소나 설정 테스트"""

    def test_all_personas_defined(self):
        """모든 페르소나 정의 확인"""
        assert Persona.UMMA in PERSONAS
        assert Persona.CHEF in PERSONAS
        assert Persona.DIET in PERSONAS
        assert Persona.HEALTH in PERSONAS
        assert Persona.VEGAN in PERSONAS

    def test_persona_has_required_fields(self):
        """필수 필드 확인"""
        for persona, config in PERSONAS.items():
            assert config.name
            assert config.icon
            assert config.tier in ["FREE", "PREMIUM"]
            assert config.greeting_template
            assert config.recommendation_prefix


class TestGenerateResponse:
    """응답 생성 테스트"""

    async def test_no_recipes_returns_message(self, persona_engine):
        """레시피 없을 때 메시지 반환"""
        response = await persona_engine.generate_response(
            recipes=[],
            persona=Persona.UMMA,
            user_name="민지",
            use_llm=False,
        )

        assert "민지" in response
        assert len(response) > 0

    async def test_template_response_for_umma(self, persona_engine, sample_recipes):
        """엄마밥 템플릿 응답 테스트"""
        response = await persona_engine.generate_response(
            recipes=sample_recipes,
            persona=Persona.UMMA,
            user_name="민지",
            use_llm=False,
        )

        assert "민지" in response
        assert "김치찌개" in response
        assert "엄마 팁" in response

    async def test_template_response_for_diet(self, persona_engine, sample_recipes):
        """다이어트코치 템플릿 응답 테스트"""
        response = await persona_engine.generate_response(
            recipes=sample_recipes,
            persona=Persona.DIET,
            user_name="철수",
            use_llm=False,
        )

        assert "철수" in response
        assert "450" in response  # 칼로리
        assert "kcal" in response

    async def test_template_response_for_health(self, persona_engine, sample_recipes):
        """건강맞춤 템플릿 응답 테스트"""
        response = await persona_engine.generate_response(
            recipes=sample_recipes,
            persona=Persona.HEALTH,
            user_name="영희",
            user_condition="당뇨",
            use_llm=False,
        )

        assert "영희" in response
        assert "당뇨" in response
        assert "안전" in response


class TestFormatRecipeCard:
    """레시피 카드 포맷 테스트"""

    def test_diet_card_shows_macros(self, persona_engine, sample_recipes):
        """다이어트 카드 매크로 표시"""
        card = persona_engine.format_recipe_card(
            recipe=sample_recipes[0],
            persona=Persona.DIET,
        )

        assert "칼로리" in card
        assert "단백질" in card
        assert "탄수화물" in card
        assert "지방" in card

    def test_chef_card_shows_difficulty(self, persona_engine, sample_recipes):
        """셰프 카드 난이도 표시"""
        card = persona_engine.format_recipe_card(
            recipe=sample_recipes[0],
            persona=Persona.CHEF,
        )

        assert "난이도" in card
        assert "쉬움" in card
