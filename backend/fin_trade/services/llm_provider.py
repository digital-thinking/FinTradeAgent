"""LLM Provider abstractions and implementations."""

import os
from abc import ABC, abstractmethod

import requests
from dotenv import load_dotenv

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, model: str) -> str:
        """Generate a response from the LLM."""
        pass

    @property
    def supports_web_search(self) -> bool:
        """Whether this provider supports built-in web search."""
        return True


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider implementation."""

    def __init__(self):
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed")

        load_dotenv()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, prompt: str, model: str) -> str:
        """Invoke Anthropic's API with web search enabled."""
        message = self.client.messages.create(
            model=model,
            max_tokens=4096,
            extra_headers={"anthropic-beta": "web-search-2025-03-05"},
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                result_text += block.text

        return result_text


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation."""

    def __init__(self):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed")

        load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Add it to your .env file.")

        self.client = openai.OpenAI(api_key=api_key)

    def generate(self, prompt: str, model: str) -> str:
        """Invoke OpenAI's API with web search enabled for search models."""
        search_models = {
            "gpt-4o": "gpt-4o-search-preview",
            "gpt-4o-mini": "gpt-4o-mini-search-preview",
            "gpt-5": "gpt-5-search-api",
            "gpt-5-mini": "gpt-5-mini-search-api",
            "gpt-5.1": "gpt-5-search-api",
            "gpt-5.2": "gpt-5-search-api",
        }
        actual_model = search_models.get(model, model)

        uses_new_token_param = any(
            actual_model.startswith(prefix)
            for prefix in ("gpt-5", "o1", "o3", "o4")
        )

        request_params = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
        }

        if uses_new_token_param:
            request_params["max_completion_tokens"] = 4096
        else:
            request_params["max_tokens"] = 4096

        if "search" in actual_model:
            request_params["web_search_options"] = {"search_context_size": "medium"}

        response = self.client.chat.completions.create(**request_params)
        return response.choices[0].message.content


class OllamaProvider(LLMProvider):
    """Ollama provider using OpenAI-compatible local API."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
    ):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed")

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = openai.OpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="ollama",
        )

    @property
    def supports_web_search(self) -> bool:
        """Ollama models do not support built-in web search."""
        return False

    def generate(self, prompt: str, model: str | None = None) -> str:
        """Invoke Ollama's OpenAI-compatible API."""
        effective_model = model or self.model
        if not effective_model:
            raise ValueError("Ollama model is required")

        try:
            response = self.client.chat.completions.create(
                model=effective_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running and model '{effective_model}' is installed."
            ) from e

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Ollama returned an empty response")
        return content


def check_ollama_status(base_url: str = DEFAULT_OLLAMA_BASE_URL) -> dict:
    """Check Ollama health and return available local models."""
    normalized_url = base_url.rstrip("/")

    try:
        response = requests.get(f"{normalized_url}/api/tags", timeout=3)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"status": "error", "models": [], "error": str(e)}

    try:
        payload = response.json()
    except ValueError as e:
        return {"status": "error", "models": [], "error": f"Invalid JSON response: {e}"}

    models = []
    for model in payload.get("models", []):
        if isinstance(model, dict) and model.get("name"):
            models.append(model["name"])

    return {"status": "ok", "models": models, "error": ""}


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def get_provider(
        provider_name: str,
        model: str | None = None,
        **kwargs,
    ) -> LLMProvider:
        """Get an LLM provider instance by name."""
        if provider_name == "anthropic":
            return AnthropicProvider()
        if provider_name == "openai":
            return OpenAIProvider()
        if provider_name == "ollama":
            base_url = kwargs.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL)
            return OllamaProvider(model=model, base_url=base_url)
        raise ValueError(f"Unknown LLM provider: {provider_name}")
