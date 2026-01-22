"""LLM Provider abstractions and implementations."""

import os
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, model: str) -> str:
        """Generate a response from the LLM."""
        pass


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
        # Enable web search tool for real-time data access using beta header
        message = self.client.messages.create(
            model=model,
            max_tokens=4096,
            extra_headers={"anthropic-beta": "web-search-2025-03-05"},
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,  # Allow up to 5 searches per request
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response, handling potential tool use blocks
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
        # Use search-enabled model for real-time data access
        # Map standard models to their search variants
        search_models = {
            "gpt-4o": "gpt-4o-search-preview",
            "gpt-4o-mini": "gpt-4o-mini-search-preview",
            "gpt-5": "gpt-5-search-api",
            "gpt-5-mini": "gpt-5-mini-search-api",
            "gpt-5.1": "gpt-5-search-api",
            "gpt-5.2": "gpt-5-search-api",
        }
        actual_model = search_models.get(model, model)

        # Newer models (gpt-5, o1, o3, etc.) use max_completion_tokens instead of max_tokens
        uses_new_token_param = any(
            actual_model.startswith(prefix)
            for prefix in ("gpt-5", "o1", "o3", "o4")
        )

        # Build request parameters
        request_params = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add appropriate token limit parameter
        if uses_new_token_param:
            request_params["max_completion_tokens"] = 4096
        else:
            request_params["max_tokens"] = 4096

        # Enable web search for search-preview models
        if "search" in actual_model:
            request_params["web_search_options"] = {"search_context_size": "medium"}

        response = self.client.chat.completions.create(**request_params)
        return response.choices[0].message.content


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def get_provider(provider_name: str) -> LLMProvider:
        """Get an LLM provider instance by name."""
        if provider_name == "anthropic":
            return AnthropicProvider()
        elif provider_name == "openai":
            return OpenAIProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
