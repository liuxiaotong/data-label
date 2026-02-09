"""LLM 客户端测试 — 全部 mock，不依赖真实 API key。"""

from unittest.mock import MagicMock, patch

import pytest

from datalabel.llm.client import (
    DEFAULT_MODELS,
    ENV_KEYS,
    MOONSHOT_BASE_URL,
    LLMClient,
    LLMConfig,
    LLMResponse,
    LLMUsage,
)


# ============================================================
# LLMConfig tests
# ============================================================


class TestLLMConfig:
    def test_default_provider(self):
        cfg = LLMConfig()
        assert cfg.provider == "moonshot"

    def test_default_model_per_provider(self):
        for provider, expected_model in DEFAULT_MODELS.items():
            cfg = LLMConfig(provider=provider, api_key="test")
            assert cfg.model == expected_model

    def test_custom_model(self):
        cfg = LLMConfig(provider="openai", model="gpt-4o", api_key="test")
        assert cfg.model == "gpt-4o"

    def test_invalid_provider(self):
        with pytest.raises(ValueError, match="不支持的提供商"):
            LLMConfig(provider="invalid")

    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"MOONSHOT_API_KEY": "sk-test-123"}):
            cfg = LLMConfig(provider="moonshot")
            assert cfg.api_key == "sk-test-123"

    def test_api_key_explicit(self):
        cfg = LLMConfig(provider="openai", api_key="my-key")
        assert cfg.api_key == "my-key"

    def test_moonshot_default_base_url(self):
        cfg = LLMConfig(provider="moonshot", api_key="test")
        assert cfg.base_url == MOONSHOT_BASE_URL

    def test_moonshot_custom_base_url(self):
        cfg = LLMConfig(provider="moonshot", api_key="test", base_url="https://custom.api")
        assert cfg.base_url == "https://custom.api"

    def test_openai_no_base_url(self):
        cfg = LLMConfig(provider="openai", api_key="test")
        assert cfg.base_url is None

    def test_env_keys_mapping(self):
        assert ENV_KEYS["openai"] == "OPENAI_API_KEY"
        assert ENV_KEYS["anthropic"] == "ANTHROPIC_API_KEY"
        assert ENV_KEYS["moonshot"] == "MOONSHOT_API_KEY"


# ============================================================
# LLMClient tests
# ============================================================


class TestLLMClient:
    def test_init_with_config(self):
        cfg = LLMConfig(provider="openai", api_key="test")
        client = LLMClient(config=cfg)
        assert client.config.provider == "openai"

    def test_init_with_kwargs(self):
        client = LLMClient(provider="moonshot", api_key="test")
        assert client.config.provider == "moonshot"
        assert client.config.api_key == "test"

    def test_missing_api_key_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            client = LLMClient(provider="openai")
            resp = client.chat([{"role": "user", "content": "hi"}])
            assert not resp.success
            assert "OPENAI_API_KEY" in resp.error

    def test_missing_openai_package(self):
        client = LLMClient(provider="openai", api_key="test")
        with patch.dict("sys.modules", {"openai": None}):
            with patch("builtins.__import__", side_effect=ImportError("no openai")):
                # Reset the client so it tries to init again
                client._client = None
                resp = client.chat([{"role": "user", "content": "hi"}])
                assert not resp.success
                assert "openai" in resp.error.lower()

    @patch("datalabel.llm.client.OpenAI", create=True)
    def test_chat_openai(self, mock_openai_cls):
        """Test OpenAI/Moonshot chat path."""
        # Mock response
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_choice = MagicMock()
        mock_choice.message.content = "Hello!"

        mock_resp = MagicMock()
        mock_resp.usage = mock_usage
        mock_resp.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        client = LLMClient(provider="openai", api_key="test-key")
        # Manually patch import path
        with patch("datalabel.llm.client.OpenAI", mock_openai_cls, create=True):
            # Force re-init
            client._client = None
            # Simulate import success by setting client directly
            client._client = mock_client

        resp = client.chat([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ])

        assert resp.success
        assert resp.content == "Hello!"
        assert resp.usage.prompt_tokens == 10
        assert resp.usage.completion_tokens == 20
        assert resp.usage.total_tokens == 30

    def test_chat_anthropic(self):
        """Test Anthropic chat path — system message separated."""
        mock_usage = MagicMock()
        mock_usage.input_tokens = 15
        mock_usage.output_tokens = 25

        mock_content = MagicMock()
        mock_content.text = "Bonjour!"

        mock_resp = MagicMock()
        mock_resp.usage = mock_usage
        mock_resp.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        client = LLMClient(provider="anthropic", api_key="test-key")
        client._client = mock_client

        resp = client.chat([
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Hello"},
        ])

        assert resp.success
        assert resp.content == "Bonjour!"
        assert resp.usage.prompt_tokens == 15
        assert resp.usage.completion_tokens == 25
        assert resp.usage.total_tokens == 40

        # Verify system message was separated
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "Be brief."
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    def test_chat_exception_handling(self):
        """API 异常应返回 error response 而非抛出异常。"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        client = LLMClient(provider="openai", api_key="test")
        client._client = mock_client

        resp = client.chat([{"role": "user", "content": "hi"}])
        assert not resp.success
        assert "API down" in resp.error


# ============================================================
# chat_json tests
# ============================================================


class TestChatJson:
    def _make_client_with_response(self, content: str) -> LLMClient:
        """Helper: create client that returns given content."""
        mock_client = MagicMock()
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_choice = MagicMock()
        mock_choice.message.content = content

        mock_resp = MagicMock()
        mock_resp.usage = mock_usage
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp

        client = LLMClient(provider="openai", api_key="test")
        client._client = mock_client
        return client

    def test_plain_json(self):
        client = self._make_client_with_response('{"key": "value"}')
        parsed, resp = client.chat_json([{"role": "user", "content": "test"}])
        assert resp.success
        assert parsed == {"key": "value"}

    def test_json_with_code_fence(self):
        content = '```json\n{"key": "value"}\n```'
        client = self._make_client_with_response(content)
        parsed, resp = client.chat_json([{"role": "user", "content": "test"}])
        assert resp.success
        assert parsed == {"key": "value"}

    def test_json_with_bare_code_fence(self):
        content = '```\n[1, 2, 3]\n```'
        client = self._make_client_with_response(content)
        parsed, resp = client.chat_json([{"role": "user", "content": "test"}])
        assert resp.success
        assert parsed == [1, 2, 3]

    def test_invalid_json(self):
        client = self._make_client_with_response("not json at all")
        parsed, resp = client.chat_json([{"role": "user", "content": "test"}])
        assert parsed is None
        assert not resp.success
        assert "JSON 解析失败" in resp.error

    def test_chat_json_propagates_chat_error(self):
        """chat 失败时 chat_json 也返回失败。"""
        client = LLMClient(provider="openai")  # No API key
        with patch.dict("os.environ", {}, clear=True):
            client.config.api_key = None
            parsed, resp = client.chat_json([{"role": "user", "content": "test"}])
            assert parsed is None
            assert not resp.success


# ============================================================
# LLMUsage / LLMResponse dataclass tests
# ============================================================


class TestDataclasses:
    def test_usage_defaults(self):
        u = LLMUsage()
        assert u.prompt_tokens == 0
        assert u.completion_tokens == 0
        assert u.total_tokens == 0

    def test_response_defaults(self):
        r = LLMResponse()
        assert r.content == ""
        assert r.success is True
        assert r.error is None

    def test_response_error(self):
        r = LLMResponse(success=False, error="oops")
        assert not r.success
        assert r.error == "oops"
