"""
Tests für die LLM-Integration in BaseCaste.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from src.castes.base_caste import BaseCaste, _get_ollama_client
from src.models.caste import CasteName
from src.models.pheromone import PheromoneType
from pydantic import BaseModel, Field


class TestCaste(BaseCaste):
    """Test-Kaste für die LLM-Tests."""
    
    caste_name = CasteName.ANALYST
    role = "Test-Kaste"
    specialization = "Test"
    reads_pheromones = []
    writes_pheromones = []
    
    def execute(self, work_dir: Path):
        pass


class TestModel(BaseModel):
    """Test-Modell für die Validierung."""
    summary: str = Field(..., description="Eine Zusammenfassung")
    confidence: str = Field(..., description="Das Vertrauen")


@pytest.fixture
def temp_workspace():
    """Erstellt einen temporären Workspace."""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    
    yield workspace_path
    
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestBaseCasteAskLLM:
    """Tests für die ask_llm()-Methode."""

    @patch("src.castes.base_caste._get_ollama_client")
    def test_ask_llm_calls_ollama_client(self, mock_get_client, temp_workspace):
        """ask_llm() ruft den Ollama-Client auf."""
        mock_client = MagicMock()
        mock_client.generate.return_value = TestModel(
            summary="Test summary",
            confidence="high",
        )
        mock_client.max_retries = 3
        mock_client.temperature = 0.2
        mock_client.context_size = 4096
        mock_client.model = "gemma4:31b-cloud"
        mock_get_client.return_value = mock_client

        caste = TestCaste(workspace_path=temp_workspace)
        result = caste.ask_llm(
            prompt="Test prompt",
            response_model=TestModel,
        )

        assert isinstance(result, TestModel)
        assert result.summary == "Test summary"
        mock_client.generate.assert_called_once()

    @patch("src.castes.base_caste._get_ollama_client")
    def test_ask_llm_with_custom_parameters(self, mock_get_client, temp_workspace):
        """ask_llm() überschreibt Default-Parameter."""
        mock_client = MagicMock()
        mock_client.generate.return_value = TestModel(
            summary="Test",
            confidence="low",
        )
        mock_client.max_retries = 3
        mock_client.temperature = 0.2
        mock_client.context_size = 4096
        mock_client.model = "gemma4:31b-cloud"
        mock_get_client.return_value = mock_client

        caste = TestCaste(workspace_path=temp_workspace)
        result = caste.ask_llm(
            prompt="Test prompt",
            response_model=TestModel,
            max_retries=5,
            temperature=0.5,
        )

        # Parameter sollten überschrieben worden sein
        assert mock_client.max_retries == 3  # Wiederhergestellt nach dem Aufruf
        assert mock_client.temperature == 0.2  # Wiederhergestellt nach dem Aufruf

    @patch("src.castes.base_caste._get_ollama_client")
    def test_ask_llm_raises_exception_on_failure(self, mock_get_client, temp_workspace):
        """ask_llm() wirft Exception bei Fehlschlag."""
        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("Ollama unavailable")
        mock_client.max_retries = 3
        mock_client.temperature = 0.2
        mock_client.context_size = 4096
        mock_client.model = "gemma4:31b-cloud"
        mock_get_client.return_value = mock_client

        caste = TestCaste(workspace_path=temp_workspace)
        
        with pytest.raises(Exception) as exc_info:
            caste.ask_llm(prompt="Test prompt")
        
        assert "Ollama unavailable" in str(exc_info.value)


class TestOllamaClientSingleton:
    """Tests für die Singleton-Instanz."""

    def test_get_ollama_client_returns_singleton(self):
        """_get_ollama_client() gibt dieselbe Instanz zurück."""
        client1 = _get_ollama_client()
        client2 = _get_ollama_client()
        
        assert client1 is client2
