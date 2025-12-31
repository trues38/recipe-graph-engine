"""Neo4j 노드/엣지 스키마 정의"""

from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


# ============== Enums ==============

class IngredientCategory(str, Enum):
    MEAT = "육류"
    VEGETABLE = "채소"
    SEAFOOD = "해산물"
    DAIRY = "유제품"
    GRAIN = "곡물"
    SEASONING = "양념"
    OTHER = "기타"


class StorageType(str, Enum):
    REFRIGERATED = "냉장"
    FROZEN = "냉동"
    ROOM_TEMP = "실온"


class RecipeCategory(str, Enum):
    STEW = "찌개"
    STIRFRY = "볶음"
    GRILL = "구이"
    STEAM = "찜"
    FRY = "튀김"
    SALAD = "무침"
    SOUP = "국"
    RICE = "밥"
    NOODLE = "면"
    DESSERT = "디저트"


class CuisineType(str, Enum):
    KOREAN = "한식"
    WESTERN = "양식"
    CHINESE = "중식"
    JAPANESE = "일식"
    SOUTHEAST_ASIAN = "동남아"
    FUSION = "퓨전"


class Difficulty(str, Enum):
    EASY = "쉬움"
    MEDIUM = "보통"
    HARD = "어려움"


class Unit(str, Enum):
    GRAM = "g"
    ML = "ml"
    PIECE = "개"
    TABLESPOON = "큰술"
    TEASPOON = "작은술"
    CUP = "컵"


# ============== 노드 모델 ==============

class Ingredient(BaseModel):
    """재료 노드"""
    name: str
    category: IngredientCategory
    storage: StorageType = StorageType.REFRIGERATED
    calories_per_100g: float = 0
    protein_per_100g: float = 0
    carbs_per_100g: float = 0
    fat_per_100g: float = 0
    fiber_per_100g: float = 0
    sodium_per_100g: float = 0
    allergens: list[str] = Field(default_factory=list)
    gi_index: float | None = None
    vegan: bool = False
    kosher: bool = True
    halal: bool = True


class Recipe(BaseModel):
    """레시피 노드"""
    name: str
    category: RecipeCategory
    cuisine: CuisineType = CuisineType.KOREAN
    time_minutes: int
    difficulty: Difficulty = Difficulty.EASY
    servings: int = 2
    total_calories: float = 0
    total_protein: float = 0
    total_carbs: float = 0
    total_fat: float = 0
    tags: list[str] = Field(default_factory=list)
    spicy_level: int = Field(default=0, ge=0, le=3)
    description: str = ""
    steps: list[str] = Field(default_factory=list)
    tips: str = ""


class Goal(BaseModel):
    """목표 노드 (다이어트, 벌크업 등)"""
    name: str
    daily_calories: int = 2000
    protein_ratio: float = 0.30
    carbs_ratio: float = 0.40
    fat_ratio: float = 0.30
    avoid_tags: list[str] = Field(default_factory=list)
    prefer_tags: list[str] = Field(default_factory=list)


class Condition(BaseModel):
    """건강상태 노드 (당뇨, 고혈압 등)"""
    name: str
    avoid_ingredients: list[str] = Field(default_factory=list)
    limit_nutrients: dict[str, float] = Field(default_factory=dict)
    prefer_tags: list[str] = Field(default_factory=list)
    description: str = ""


class Diet(BaseModel):
    """식단 노드 (비건, 락토 등)"""
    name: str
    exclude_categories: list[str] = Field(default_factory=list)
    exclude_ingredients: list[str] = Field(default_factory=list)
    description: str = ""


class Technique(BaseModel):
    """조리 기법 노드 (수비드, 에어프라이어 등)"""
    name: str
    difficulty: Difficulty = Difficulty.MEDIUM
    equipment: list[str] = Field(default_factory=list)
    description: str = ""
    best_for: list[str] = Field(default_factory=list)


# ============== 엣지 모델 ==============

class IngredientRequirement(BaseModel):
    """REQUIRED_FOR 엣지 속성"""
    ingredient_name: str
    recipe_name: str
    amount: float
    unit: Unit
    optional: bool = False
    prep: str = ""


class IngredientSubstitute(BaseModel):
    """CAN_REPLACE 엣지 속성"""
    original: str
    alternative: str
    ratio: float = 1.0
    context: str = ""
    notes: str = ""


class RecipeSuitability(BaseModel):
    """SUITABLE_FOR 엣지 속성"""
    recipe_name: str
    goal_name: str
    score: float = Field(ge=0, le=1)
    reason: str = ""


class RecipeSafety(BaseModel):
    """SAFE_FOR / AVOID_FOR 엣지 속성"""
    recipe_name: str
    condition_name: str
    is_safe: bool
    reason: str = ""
    severity: Literal["high", "medium", "low"] = "medium"
