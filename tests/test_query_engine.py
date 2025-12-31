"""쿼리 엔진 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.engines.query_engine import QueryEngine, RecipeResult


@pytest.fixture
def mock_client():
    """Mock Neo4j 클라이언트"""
    client = MagicMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def query_engine(mock_client):
    """쿼리 엔진 인스턴스"""
    return QueryEngine(mock_client)


class TestFindRecipesByIngredients:
    """재료 → 레시피 쿼리 테스트"""

    async def test_returns_recipes(self, query_engine, mock_client):
        """레시피 반환 테스트"""
        mock_client.execute_query.return_value = [
            {
                "name": "김치찌개",
                "category": "찌개",
                "cuisine": "한식",
                "time_minutes": 30,
                "difficulty": "쉬움",
                "total_calories": 450,
                "total_protein": 35,
                "total_carbs": 25,
                "total_fat": 20,
                "tags": ["국물"],
                "description": "맛있는 김치찌개",
                "coverage": 80,
                "missing_count": 1,
            }
        ]

        results = await query_engine.find_recipes_by_ingredients(
            ingredients=["돼지고기", "김치", "두부"],
            min_coverage=60,
        )

        assert len(results) == 1
        assert results[0].name == "김치찌개"
        assert results[0].coverage == 80

    async def test_empty_ingredients(self, query_engine, mock_client):
        """빈 재료 목록 테스트"""
        mock_client.execute_query.return_value = []

        results = await query_engine.find_recipes_by_ingredients(
            ingredients=[],
            min_coverage=60,
        )

        assert len(results) == 0


class TestFindByCalories:
    """칼로리 기반 검색 테스트"""

    async def test_filters_by_max_calories(self, query_engine, mock_client):
        """칼로리 필터링 테스트"""
        mock_client.execute_query.return_value = [
            {
                "name": "닭가슴살 샐러드",
                "category": "무침",
                "cuisine": "양식",
                "time_minutes": 15,
                "difficulty": "쉬움",
                "total_calories": 300,
                "total_protein": 40,
                "total_carbs": 10,
                "total_fat": 8,
                "tags": ["다이어트"],
                "coverage": 90,
                "missing_count": 0,
            }
        ]

        results = await query_engine.find_by_calories(
            ingredients=["닭가슴살", "상추"],
            max_calories=400,
        )

        assert len(results) == 1
        assert results[0].total_calories == 300


class TestGetStats:
    """통계 쿼리 테스트"""

    async def test_returns_stats(self, query_engine, mock_client):
        """통계 반환 테스트"""
        mock_client.execute_query.side_effect = [
            [{"count": 100}],
            [{"count": 50}],
            [{"count": 200}],
        ]

        stats = await query_engine.get_stats()

        assert stats["recipes"] == 100
        assert stats["ingredients"] == 50
        assert stats["relations"] == 200
