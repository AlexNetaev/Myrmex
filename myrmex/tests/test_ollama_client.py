"""
Tests für den Ollama-Client.
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from src.llm.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaResponseError,
)
from pydantic import BaseModel, Field


class TestModel(BaseModel):
    """Test-Modell für die Validierung."""
    summary: str = Field(..., description="Eine Zusammenfassung")
    confidence: str = Field(..., description="Das Vertrauen")


class TestOllamaClientInit:
    """Tests für die Initialisierung."""

    def test_default_configuration(self):
        """Standard-Konfiguration wird verwendet."""
        client = OllamaClient()
        assert client.host == "http://localhost:11434"
        assert client.model == "gemma4:31b-cloud"
        assert client.temperature == 0.2
        assert client.max_retries == 3
        assert client.timeout_s == 120
        assert client.context_size == 4096

    def test_custom_configuration(self):
        """Benutzerdefinierte Konfiguration wird verwendet."""
        client = OllamaClient(
            host="http://custom-host:11434",
            model="custom-model",
            temperature=0.5,
            max_retries=5,
            timeout_s=60,
            context_size=2048,
        )
        assert client.host == "http://custom-host:11434"
        assert client.model == "custom-model"
        assert client.temperature == 0.5
        assert client.max_retries == 5
        assert client.timeout_s == 60
        assert client.context_size == 2048


class TestOllamaClientGenerate:
    """Tests für die generate()-Methode."""

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_generate_without_response_model(self, mock_urlopen):
        """generate() gibt rohe Antwort zurück, wenn kein response_model angegeben ist."""
        # Mock-Antwort
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "This is a test response.",
        }).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OllamaClient()
        result = client.generate(prompt="Test prompt")

        assert result == "This is a test response."

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_generate_with_response_model(self, mock_urlopen):
        """generate() validiert Antwort mit response_model."""
        # Mock-Antwort
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": json.dumps({
                "summary": "Test summary",
                "confidence": "high",
            }),
        }).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OllamaClient()
        result = client.generate(
            prompt="Test prompt",
            response_model=TestModel,
        )

        assert isinstance(result, TestModel)
        assert result.summary == "Test summary"
        assert result.confidence == "high"

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_generate_with_markdown_code_block(self, mock_urlopen):
        """generate() entfernt Markdown-Codeblöcke."""
        # Mock-Antwort mit Markdown-Codeblock
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "response": "```json\n{\"summary\": \"Test\", \"confidence\": \"low\"}\n```",
        }).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OllamaClient()
        result = client.generate(
            prompt="Test prompt",
            response_model=TestModel,
        )

        assert isinstance(result, TestModel)
        assert result.summary == "Test"

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_connection_error(self, mock_urlopen):
        """OllamaConnectionError wird geworfen, wenn der Server nicht erreichbar ist."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        client = OllamaClient(max_retries=1)
        
        with pytest.raises(OllamaResponseError) as exc_info:
            client.generate(prompt="Test prompt")
        
        assert "All 1 attempts failed" in str(exc_info.value)

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_retry_logic(self, mock_urlopen):
        """Retry-Logik funktioniert."""
        import urllib.error
        
        # Erster Versuch schlägt fehl, zweiter succeeds
        mock_response_success = MagicMock()
        mock_response_success.read.return_value = json.dumps({
            "response": "Success after retry",
        }).encode("utf-8")
        mock_response_success.status = 200
        
        mock_urlopen.side_effect = [
            urllib.error.URLError("Connection refused"),
            MagicMock(__enter__=MagicMock(return_value=mock_response_success)),
        ]

        client = OllamaClient(max_retries=2)
        result = client.generate(prompt="Test prompt")

        assert result == "Success after retry"
        assert mock_urlopen.call_count == 2


class TestOllamaClientIsAvailable:
    """Tests für die is_available()-Methode."""

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_is_available_true(self, mock_urlopen):
        """is_available() gibt True zurück, wenn der Server erreichbar ist."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = OllamaClient()
        assert client.is_available() is True

    @patch("src.llm.ollama_client.urllib.request.urlopen")
    def test_is_available_false(self, mock_urlopen):
        """is_available() gibt False zurück, wenn der Server nicht erreichbar ist."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        client = OllamaClient()
        assert client.is_available() is False
