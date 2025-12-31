"""OpenRouter LLM 클라이언트 (폴백 지원)"""

import httpx
from config.settings import get_settings


class LLMClient:
    """OpenRouter API 클라이언트 with 모델 폴백"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.models = settings.llm_models
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://recipe-graph-engine.local",
            "X-Title": "Recipe Graph Engine",
        }

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """
        LLM 응답 생성 (모델 폴백 지원)

        순서대로 시도:
        1. xiaomi/mimo-v2-flash:free (무료)
        2. x-ai/grok-4.1-fast
        3. openai/gpt-4o-mini
        4. deepseek/deepseek-chat
        """
        last_error = None

        async with httpx.AsyncClient(timeout=60.0) as client:
            for model in self.models:
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]

                    # 모델 에러 시 다음 모델 시도
                    last_error = f"{model}: HTTP {response.status_code}"
                    print(f"[LLM] {last_error}, trying next model...")

                except Exception as e:
                    last_error = f"{model}: {str(e)}"
                    print(f"[LLM] {last_error}, trying next model...")
                    continue

        # 모든 모델 실패
        raise RuntimeError(f"All LLM models failed. Last error: {last_error}")

    async def generate_json(
        self,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """JSON 응답 생성 (파싱은 호출자가 처리)"""
        full_prompt = prompt + "\n\nJSON만 출력하세요. 다른 텍스트는 포함하지 마세요."
        return await self.generate(full_prompt, max_tokens, temperature=0.3)


# 싱글톤 인스턴스
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
