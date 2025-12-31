"""페르소나 기반 응답 생성 엔진"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from src.engines.query_engine import RecipeResult
from src.utils.llm_client import get_llm_client


class Persona(str, Enum):
    """페르소나 종류"""
    # FREE 티어
    UMMA = "엄마밥"

    # PREMIUM 티어
    CHEF = "흑백요리사"
    DIET = "다이어트코치"
    HEALTH = "건강맞춤"
    VEGAN = "무지개요리사"

    # 추가 페르소나
    HOMECOOK = "집밥요리사"      # 가정식
    QUICK = "자취생밥상"          # 간편/자취
    KIDS = "아이밥상"             # 아이/유아식
    PARTY = "손님초대"            # 파티/접대
    TRADITIONAL = "한식장인"      # 전통 한식
    BUDGET = "알뜰살림"           # 가성비
    BULK = "벌크업코치"           # 근육/벌크업


@dataclass
class PersonaConfig:
    """페르소나 설정"""
    name: str
    icon: str
    tier: str
    tone: str
    formality: str
    greeting_template: str
    recommendation_prefix: str
    tips_prefix: str
    encouragement: str
    focus: list[str]
    description: str = ""  # 페르소나 설명
    query_mode: str = "general"  # 쿼리 모드: general, diet, health, vegan, quick, kids 등
    enabled: bool = True  # MVP용 활성화 여부


PERSONAS: dict[Persona, PersonaConfig] = {
    # ============== FREE 티어 ==============
    Persona.UMMA: PersonaConfig(
        name="엄마밥",
        icon="👩‍🍳",
        tier="FREE",
        tone="따뜻하고 친근한 어머니",
        formality="반말 (친근)",
        greeting_template="우리 {user_name}이 뭐 해먹을까~",
        recommendation_prefix="이거 해먹어! ",
        tips_prefix="엄마 팁: ",
        encouragement="맛있게 해먹고 사진 보내~",
        focus=["실용성", "속도", "가성비"],
        description="따뜻한 엄마의 마음으로 집밥 레시피 추천",
        query_mode="general",
    ),

    # ============== PREMIUM 티어 ==============
    Persona.CHEF: PersonaConfig(
        name="흑백요리사",
        icon="🖤",
        tier="PREMIUM",
        tone="전문적이고 권위있는 셰프",
        formality="존댓말 (격식)",
        greeting_template="{user_name}님, 오늘의 재료를 확인했습니다.",
        recommendation_prefix="추천 요리: ",
        tips_prefix="셰프 노트: ",
        encouragement="요리는 과학입니다. 레시피를 정확히 따라주세요.",
        focus=["기법", "과학적 원리", "플레이팅"],
        description="전문 셰프의 시선으로 요리 기법과 플레이팅 안내",
        query_mode="general",
    ),
    Persona.DIET: PersonaConfig(
        name="다이어트",
        icon="💪",
        tier="PREMIUM",
        tone="동기부여하는 트레이너",
        formality="반말/존댓말 혼용",
        greeting_template="{user_name}님! 오늘도 건강한 선택 하러 오셨네요 💪",
        recommendation_prefix="오늘의 추천! ",
        tips_prefix="다이어트 팁: ",
        encouragement="이 한 끼가 목표에 한 발 더 가까워지는 거예요!",
        focus=["칼로리", "단백질", "포만감"],
        description="칼로리/벌크업 목표 기반 추천",
        query_mode="diet",
    ),
    Persona.HEALTH: PersonaConfig(
        name="건강맞춤",
        icon="🏥",
        tier="PREMIUM",
        tone="신뢰감 있는 영양 전문가",
        formality="존댓말 (격식)",
        greeting_template="{user_name}님의 건강 상태를 고려한 맞춤 식단입니다.",
        recommendation_prefix="맞춤 추천: ",
        tips_prefix="건강 참고: ",
        encouragement="꾸준한 식이 관리가 건강의 첫걸음입니다.",
        focus=["안전성", "영양소", "금기사항"],
        description="건강 상태별 안전한 레시피 추천 (당뇨/고혈압 등)",
        query_mode="health",
    ),
    Persona.VEGAN: PersonaConfig(
        name="비건",
        icon="🌈",
        tier="PREMIUM",
        tone="밝고 긍정적인 비건 셰프",
        formality="존댓말 (친근)",
        greeting_template="{user_name}님, 오늘도 지구와 함께하는 식사! 🌍",
        recommendation_prefix="식물 기반 추천: ",
        tips_prefix="비건 팁: ",
        encouragement="동물 없이도 이렇게 맛있어요! 🌈",
        focus=["대체재", "영양 보완", "환경"],
        description="비건/채식 호환 레시피",
        query_mode="vegan",
    ),

    # ============== 추가 페르소나 (MVP 비활성화) ==============
    Persona.HOMECOOK: PersonaConfig(
        name="집밥요리사",
        icon="🏠",
        tier="FREE",
        tone="편안하고 소박한 이웃집 아저씨",
        formality="반말 (친근)",
        greeting_template="{user_name}아, 오늘 뭐 해먹을까?",
        recommendation_prefix="이거 어때? ",
        tips_prefix="꿀팁: ",
        encouragement="집밥이 최고야. 맛있게 먹어!",
        focus=["간단함", "재료 활용", "일상 요리"],
        description="매일 먹는 편안한 가정식 레시피",
        query_mode="general",
        enabled=False,  # MVP 비활성화
    ),
    Persona.QUICK: PersonaConfig(
        name="자취생",
        icon="⚡",
        tier="FREE",
        tone="현실적이고 효율적인 자취 선배",
        formality="반말 (캐주얼)",
        greeting_template="{user_name}! 오늘도 빠르게 해결하자 ⚡",
        recommendation_prefix="초간단! ",
        tips_prefix="자취 꿀팁: ",
        encouragement="5분이면 끝! 배고플 때 최고지 ㅋㅋ",
        focus=["시간 절약", "최소 재료", "간편함"],
        description="20분 이내 초간단 레시피",
        query_mode="quick",
        enabled=True,  # MVP 활성화
    ),
    Persona.KIDS: PersonaConfig(
        name="아이밥상",
        icon="👶",
        tier="PREMIUM",
        tone="다정하고 세심한 육아 전문가",
        formality="존댓말 (부드러움)",
        greeting_template="{user_name}님, 아이를 위한 건강한 한 끼를 준비해볼까요?",
        recommendation_prefix="아이 맞춤! ",
        tips_prefix="육아 팁: ",
        encouragement="아이가 좋아하면서도 영양가 있는 식사, 함께 만들어요!",
        focus=["영양 균형", "안전", "아이 입맛"],
        description="아이/유아를 위한 영양 균형 레시피",
        query_mode="kids",
        enabled=False,  # MVP 비활성화
    ),
    Persona.PARTY: PersonaConfig(
        name="손님초대",
        icon="🎉",
        tier="PREMIUM",
        tone="세련되고 화려한 파티 플래너",
        formality="존댓말 (우아함)",
        greeting_template="{user_name}님, 특별한 자리를 위한 요리를 준비해드릴게요!",
        recommendation_prefix="파티 추천! ",
        tips_prefix="파티 팁: ",
        encouragement="손님들이 감탄할 거예요! ✨",
        focus=["비주얼", "대용량", "특별함"],
        description="손님 접대/파티용 화려한 레시피",
        query_mode="party",
        enabled=False,  # MVP 비활성화
    ),
    Persona.TRADITIONAL: PersonaConfig(
        name="한식장인",
        icon="🏛️",
        tier="PREMIUM",
        tone="깊이 있는 한식 전문가",
        formality="존댓말 (격식)",
        greeting_template="{user_name}님, 전통의 맛을 전해드리겠습니다.",
        recommendation_prefix="전통 요리: ",
        tips_prefix="전통 비법: ",
        encouragement="정성이 담긴 한 그릇, 그것이 진정한 한식입니다.",
        focus=["전통", "정성", "제철 재료"],
        description="정통 한식 레시피와 전통 조리법",
        query_mode="traditional",
        enabled=False,  # MVP 비활성화
    ),
    Persona.BUDGET: PersonaConfig(
        name="알뜰살림",
        icon="💰",
        tier="FREE",
        tone="실속있고 현명한 살림꾼",
        formality="반말 (친근)",
        greeting_template="{user_name}아, 오늘도 알뜰하게 해먹자!",
        recommendation_prefix="가성비 갑! ",
        tips_prefix="절약 팁: ",
        encouragement="적은 돈으로 맛있게! 이게 진짜 살림이지~",
        focus=["가성비", "재료 절약", "저렴함"],
        description="가성비 좋은 저예산 레시피 추천",
        query_mode="budget",
        enabled=False,  # MVP 비활성화
    ),
    Persona.BULK: PersonaConfig(
        name="벌크업코치",
        icon="🏋️",
        tier="PREMIUM",
        tone="열정적인 헬스 트레이너",
        formality="반말/존댓말 혼용",
        greeting_template="{user_name}님! 오늘도 단백질 챙기러 오셨군요 💪",
        recommendation_prefix="고단백 추천! ",
        tips_prefix="벌크업 팁: ",
        encouragement="근육은 부엌에서 만들어집니다! 렛츠고!",
        focus=["단백질", "탄수화물", "칼로리 섭취"],
        description="근육 증가/벌크업을 위한 고단백 레시피",
        query_mode="bulk",
        enabled=False,  # MVP 비활성화
    ),
}


def get_persona_by_name(name: str) -> Persona | None:
    """페르소나 이름으로 조회 (config.name 또는 enum.value 둘 다 지원)"""
    for persona, config in PERSONAS.items():
        if config.name == name or persona.value == name:
            return persona
    return None


def get_all_personas(include_disabled: bool = False) -> list[dict]:
    """모든 페르소나 목록 반환 (기본: 활성화된 것만)"""
    result = []
    for persona, config in PERSONAS.items():
        if not include_disabled and not config.enabled:
            continue
        result.append({
            "id": persona.name,
            "name": config.name,
            "icon": config.icon,
            "tier": config.tier,
            "description": config.description,
            "tone": config.tone,
            "focus": config.focus,
            "query_mode": config.query_mode,
            "enabled": config.enabled,
        })
    return result


def get_personas_by_tier(tier: str, include_disabled: bool = False) -> list[dict]:
    """티어별 페르소나 목록 반환"""
    result = []
    for persona, config in PERSONAS.items():
        if config.tier == tier:
            if not include_disabled and not config.enabled:
                continue
            result.append({
                "id": persona.name,
                "name": config.name,
                "icon": config.icon,
                "description": config.description,
                "enabled": config.enabled,
            })
    return result


class PersonaEngine:
    """페르소나 기반 응답 생성 엔진"""

    def __init__(self):
        self.llm = get_llm_client()

    def get_config(self, persona: Persona) -> PersonaConfig:
        """페르소나 설정 반환"""
        return PERSONAS[persona]

    def list_personas(self) -> list[dict]:
        """모든 페르소나 목록"""
        return get_all_personas()

    def get_persona(self, name: str) -> Persona | None:
        """이름으로 페르소나 조회"""
        return get_persona_by_name(name)

    async def generate_response(
        self,
        recipes: list[RecipeResult],
        persona: Persona,
        user_name: str = "회원",
        user_condition: str | None = None,
        use_llm: bool = True,
    ) -> str:
        """
        쿼리 결과를 페르소나 스타일로 변환

        Args:
            recipes: 레시피 검색 결과
            persona: 페르소나 종류
            user_name: 사용자 이름
            user_condition: 건강 상태 (건강맞춤용)
            use_llm: LLM 사용 여부 (False면 템플릿 기반)
        """
        if not recipes:
            return self._no_result_message(persona, user_name)

        if use_llm:
            return await self._generate_with_llm(
                recipes, persona, user_name, user_condition
            )
        else:
            return self._generate_from_template(
                recipes, persona, user_name, user_condition
            )

    def _no_result_message(self, persona: Persona, user_name: str) -> str:
        """결과 없음 메시지"""
        config = PERSONAS[persona]
        messages = {
            Persona.UMMA: f"어휴 {user_name}아, 그 재료론 마땅한 게 없네~ 다른 거 없어?",
            Persona.CHEF: f"{user_name}님, 해당 재료 조합으로는 적합한 요리가 없습니다.",
            Persona.DIET: f"{user_name}님, 이 재료론 추천 레시피가 없어요. 다른 재료 추가해볼까요?",
            Persona.HEALTH: f"{user_name}님, 조건에 맞는 레시피를 찾지 못했습니다.",
            Persona.VEGAN: f"{user_name}님, 아쉽지만 해당 재료로는 레시피가 없어요 🥲",
            Persona.HOMECOOK: f"{user_name}아, 그 재료론 딱히 생각나는 게 없네. 뭐 다른 거 있어?",
            Persona.QUICK: f"{user_name}! 그 재료론 빠르게 할 수 있는 게 없네 ㅠㅠ",
            Persona.KIDS: f"{user_name}님, 아이에게 맞는 레시피를 찾지 못했어요.",
            Persona.PARTY: f"{user_name}님, 해당 재료로는 파티 요리를 추천드리기 어려워요.",
            Persona.TRADITIONAL: f"{user_name}님, 해당 재료로는 전통 요리를 찾지 못했습니다.",
            Persona.BUDGET: f"{user_name}아, 그 재료론 가성비 좋은 게 없네~",
            Persona.BULK: f"{user_name}님! 고단백 레시피가 없네요. 다른 재료 추가해볼까요?",
        }
        return messages.get(persona, "레시피를 찾지 못했습니다.")

    def _generate_from_template(
        self,
        recipes: list[RecipeResult],
        persona: Persona,
        user_name: str,
        user_condition: str | None,
    ) -> str:
        """템플릿 기반 응답 생성 (LLM 미사용)"""
        config = PERSONAS[persona]
        lines = []

        # 인사
        lines.append(config.greeting_template.format(user_name=user_name))
        lines.append("")

        # 레시피 목록
        for i, recipe in enumerate(recipes[:3], 1):
            lines.append(f"**{config.recommendation_prefix}{recipe.name}**")

            # 페르소나별 추가 정보
            if persona == Persona.DIET:
                lines.append(
                    f"🔥 {recipe.total_calories:.0f}kcal | "
                    f"단백질 {recipe.total_protein:.0f}g"
                )
            elif persona == Persona.HEALTH and user_condition:
                lines.append(f"✅ {user_condition}에 안전한 레시피입니다")
            elif persona == Persona.CHEF:
                lines.append(f"조리시간: {recipe.time_minutes}분 | 난이도: {recipe.difficulty}")
            elif persona == Persona.VEGAN:
                lines.append(f"🌱 식물성 단백질: {recipe.total_protein:.0f}g")
            elif persona == Persona.QUICK:
                lines.append(f"⏱️ {recipe.time_minutes}분 완성!")
            elif persona == Persona.KIDS:
                lines.append(f"👶 난이도: {recipe.difficulty} | 영양: {recipe.total_protein:.0f}g 단백질")
            elif persona == Persona.PARTY:
                lines.append(f"🎉 {recipe.servings}인분 | 난이도: {recipe.difficulty}")
            elif persona == Persona.TRADITIONAL:
                lines.append(f"🏛️ {recipe.cuisine} | {recipe.category}")
            elif persona == Persona.BUDGET:
                lines.append(f"💰 재료 {recipe.missing_count}개만 더 있으면 완성!")
            elif persona == Persona.BULK:
                lines.append(
                    f"💪 단백질 {recipe.total_protein:.0f}g | "
                    f"탄수화물 {recipe.total_carbs:.0f}g | "
                    f"칼로리 {recipe.total_calories:.0f}kcal"
                )
            elif persona == Persona.HOMECOOK:
                lines.append(f"🏠 {recipe.time_minutes}분 | {recipe.difficulty}")

            lines.append(f"재료 매칭: {recipe.coverage:.0f}% | 부족: {recipe.missing_count}개")
            lines.append("")

        # 팁
        if recipes[0].tips:
            lines.append(f"{config.tips_prefix}{recipes[0].tips}")
            lines.append("")

        # 마무리
        lines.append(config.encouragement)

        return "\n".join(lines)

    async def _generate_with_llm(
        self,
        recipes: list[RecipeResult],
        persona: Persona,
        user_name: str,
        user_condition: str | None,
    ) -> str:
        """LLM 기반 응답 생성"""
        config = PERSONAS[persona]

        # 레시피 정보 포맷
        recipe_info = []
        for r in recipes[:3]:
            info = f"- {r.name} ({r.category}, {r.cuisine})"
            info += f"\n  조리시간: {r.time_minutes}분, 난이도: {r.difficulty}"
            info += f"\n  칼로리: {r.total_calories:.0f}kcal, 단백질: {r.total_protein:.0f}g"
            info += f"\n  재료 매칭률: {r.coverage:.0f}%, 부족 재료: {r.missing_count}개"
            if r.description:
                info += f"\n  설명: {r.description}"
            if r.tips:
                info += f"\n  팁: {r.tips}"
            recipe_info.append(info)

        condition_info = ""
        if user_condition and persona == Persona.HEALTH:
            condition_info = f"\n사용자 건강상태: {user_condition}"

        prompt = f"""당신은 "{config.name}" 페르소나입니다.

특징:
- 톤: {config.tone}
- 격식: {config.formality}
- 중점: {', '.join(config.focus)}

사용자 정보:
- 이름: {user_name}{condition_info}

추천 레시피:
{chr(10).join(recipe_info)}

위 정보를 바탕으로 {config.name} 스타일로 친근하고 자연스러운 응답을 생성하세요.
- 인사로 시작
- 추천 레시피 소개 (최대 3개)
- 페르소나 특성에 맞는 팁/조언
- 격려로 마무리

응답 길이: 200-400자
"""

        return await self.llm.generate(prompt, max_tokens=1000)

    def format_recipe_card(
        self,
        recipe: RecipeResult,
        persona: Persona,
    ) -> str:
        """단일 레시피 카드 포맷"""
        config = PERSONAS[persona]
        lines = [
            f"### {config.icon} {recipe.name}",
            f"**{recipe.category}** | {recipe.cuisine} | {recipe.time_minutes}분",
            "",
        ]

        if persona == Persona.DIET:
            lines.append("| 칼로리 | 단백질 | 탄수화물 | 지방 |")
            lines.append("|--------|--------|----------|------|")
            lines.append(
                f"| {recipe.total_calories:.0f}kcal | "
                f"{recipe.total_protein:.0f}g | "
                f"{recipe.total_carbs:.0f}g | "
                f"{recipe.total_fat:.0f}g |"
            )
        elif persona == Persona.CHEF:
            lines.append(f"**난이도**: {recipe.difficulty}")
        elif persona == Persona.VEGAN:
            lines.append(f"🌱 **식물성 단백질**: {recipe.total_protein:.0f}g")

        lines.append("")
        lines.append(f"**재료 매칭**: {recipe.coverage:.0f}% (부족 {recipe.missing_count}개)")

        if recipe.description:
            lines.append("")
            lines.append(f"> {recipe.description}")

        return "\n".join(lines)
