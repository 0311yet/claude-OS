from .base import VisionProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .zhipu_provider import ZhiPuProvider

def get_provider(name: str, api_key: str, model: str = None) -> VisionProvider:
    providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "zhipu": ZhiPuProvider
    }

    provider_class = providers.get(name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}. Supported providers: {', '.join(providers.keys())}")

    return provider_class(api_key, model)

__all__ = ["VisionProvider", "OpenAIProvider", "GeminiProvider", "ZhiPuProvider", "get_provider"]
