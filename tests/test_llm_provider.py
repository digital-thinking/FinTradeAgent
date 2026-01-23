"""Tests for LLM Provider classes."""

import sys
import pytest
from unittest.mock import MagicMock, patch


class TestLLMProviderFactory:
    """Tests for LLMProviderFactory."""

    def test_raises_for_unknown_provider(self):
        """Test raises ValueError for unknown provider."""
        from fin_trade.services.llm_provider import LLMProviderFactory

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMProviderFactory.get_provider("unknown")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_returns_anthropic_provider(self):
        """Test returns AnthropicProvider for 'anthropic'."""
        # Mock anthropic module before importing
        mock_anthropic = MagicMock()
        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            from fin_trade.services.llm_provider import LLMProviderFactory, AnthropicProvider

            provider = LLMProviderFactory.get_provider("anthropic")
            assert isinstance(provider, AnthropicProvider)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_returns_openai_provider(self):
        """Test returns OpenAIProvider for 'openai'."""
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import LLMProviderFactory, OpenAIProvider

            provider = LLMProviderFactory.get_provider("openai")
            assert isinstance(provider, OpenAIProvider)


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_without_api_key(self):
        """Test raises RuntimeError when API key not set."""
        mock_anthropic = MagicMock()
        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch("fin_trade.services.llm_provider.load_dotenv"):
                from fin_trade.services.llm_provider import AnthropicProvider

                with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
                    AnthropicProvider()

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    def test_initializes_with_api_key(self):
        """Test initializes client with API key from environment."""
        mock_anthropic = MagicMock()
        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            from fin_trade.services.llm_provider import AnthropicProvider

            provider = AnthropicProvider()
            mock_anthropic.Anthropic.assert_called_once_with(api_key="test-api-key")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_generate_calls_api(self):
        """Test generate method calls Anthropic API correctly."""
        mock_anthropic = MagicMock()

        # Setup mock response
        mock_text_block = MagicMock()
        mock_text_block.text = "Generated response"

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            from fin_trade.services.llm_provider import AnthropicProvider

            provider = AnthropicProvider()
            result = provider.generate("Test prompt", "claude-3-sonnet")

            assert result == "Generated response"
            mock_client.messages.create.assert_called_once()

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_generate_handles_multiple_content_blocks(self):
        """Test generate concatenates multiple text blocks."""
        mock_anthropic = MagicMock()

        mock_text_block1 = MagicMock()
        mock_text_block1.text = "Part 1"

        mock_text_block2 = MagicMock()
        mock_text_block2.text = " Part 2"

        mock_tool_block = MagicMock(spec=[])  # No text attribute

        mock_message = MagicMock()
        mock_message.content = [mock_text_block1, mock_tool_block, mock_text_block2]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            from fin_trade.services.llm_provider import AnthropicProvider

            provider = AnthropicProvider()
            result = provider.generate("Test", "claude-3")

            assert result == "Part 1 Part 2"


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_without_api_key(self):
        """Test raises RuntimeError when API key not set."""
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch("fin_trade.services.llm_provider.load_dotenv"):
                from fin_trade.services.llm_provider import OpenAIProvider

                with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
                    OpenAIProvider()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"})
    def test_initializes_with_api_key(self):
        """Test initializes client with API key from environment."""
        mock_openai = MagicMock()
        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import OpenAIProvider

            provider = OpenAIProvider()
            mock_openai.OpenAI.assert_called_once_with(api_key="test-api-key")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_generate_calls_api(self):
        """Test generate method calls OpenAI API correctly."""
        mock_openai = MagicMock()

        mock_message = MagicMock()
        mock_message.content = "Generated response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import OpenAIProvider

            provider = OpenAIProvider()
            result = provider.generate("Test prompt", "gpt-4o")

            assert result == "Generated response"
            mock_client.chat.completions.create.assert_called_once()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_maps_to_search_model(self):
        """Test maps standard models to search variants."""
        mock_openai = MagicMock()

        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import OpenAIProvider

            provider = OpenAIProvider()
            provider.generate("Test", "gpt-4o")

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-search-preview"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_uses_max_completion_tokens_for_new_models(self):
        """Test uses max_completion_tokens for gpt-5 models."""
        mock_openai = MagicMock()

        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import OpenAIProvider

            provider = OpenAIProvider()
            provider.generate("Test", "gpt-5")

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "max_completion_tokens" in call_kwargs
            assert "max_tokens" not in call_kwargs

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_uses_max_tokens_for_older_models(self):
        """Test uses max_tokens for older models."""
        mock_openai = MagicMock()

        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import OpenAIProvider

            provider = OpenAIProvider()
            provider.generate("Test", "gpt-3.5-turbo")

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "max_tokens" in call_kwargs
            assert "max_completion_tokens" not in call_kwargs

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_enables_web_search_for_search_models(self):
        """Test enables web_search_options for search models."""
        mock_openai = MagicMock()

        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            from fin_trade.services.llm_provider import OpenAIProvider

            provider = OpenAIProvider()
            provider.generate("Test", "gpt-4o")

            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "web_search_options" in call_kwargs
