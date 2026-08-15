"""
src/llm/ollama_client.py
Ollama-Client für LLM-Aufrufe.

Dieser Client kommuniziert mit dem Ollama-Server über die HTTP-API
und gibt strukturierte JSON-Antworten zurück, die mit Pydantic-Modellen
validiert werden.
"""
from __future__ import annotations
import json
import logging
import time
from typing import Type, TypeVar, Any
import urllib.request
import urllib.error

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("llm.ollama_client")

T = TypeVar("T", bound=BaseModel)


class OllamaConnectionError(Exception):
    """Wird geworfen, wenn der Ollama-Server nicht erreichbar ist."""
    pass


class OllamaResponseError(Exception):
    """Wird geworfen, wenn die Antwort des Ollama-Servers ungültig ist."""
    pass


class OllamaClient:
    """
    Client für die Ollama-HTTP-API.
    
    Verwendet den /api/generate-Endpoint mit JSON-Mode, um strukturierte
    Antworten zu erhalten, die mit Pydantic-Modellen validiert werden können.
    """
    
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "gemma4:31b-cloud",
        temperature: float = 0.2,
        max_retries: int = 3,
        timeout_s: int = 120,
        context_size: int = 4096,
    ):
        """
        Initialisiert den Ollama-Client.
        
        Args:
            host: Die URL des Ollama-Servers.
            model: Das zu verwendende Modell.
            temperature: Die Temperatur für die Generierung.
            max_retries: Maximale Anzahl der Versuche.
            timeout_s: Timeout pro Anfrage in Sekunden.
            context_size: Die Context-Size für das Modell.
        """
        self.host = host.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.context_size = context_size
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        response_model: Type[T] | None = None,
    ) -> T | str:
        """
        Sendet eine Anfrage an den Ollama-Server und gibt die Antwort zurück.
        
        Args:
            prompt: Der User-Prompt.
            system_prompt: Der System-Prompt.
            response_model: Das Pydantic-Modell für die Validierung.
                           Wenn None, wird die rohe Antwort als String zurückgegeben.
        
        Returns:
            Eine Instanz von response_model (falls angegeben) oder die rohe Antwort.
        
        Raises:
            OllamaConnectionError: Wenn der Server nicht erreichbar ist.
            OllamaResponseError: Wenn die Antwort ungültig ist.
            ValidationError: Wenn die Antwort nicht zum Modell passt.
        """
        # Vollständigen Prompt erstellen
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # JSON-Mode aktivieren, wenn ein response_model angegeben ist
        format_mode = "json" if response_model is not None else None
        
        # Request-Body erstellen
        request_body = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.context_size,
            },
        }
        if format_mode:
            request_body["format"] = format_mode
        
        # Retry-Logik
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "Ollama request (attempt %d/%d): model=%s, prompt_length=%d",
                    attempt, self.max_retries, self.model, len(full_prompt),
                )
                
                response_text = self._send_request(request_body)
                
                # Antwort parsen
                if response_model is not None:
                    return self._parse_json_response(response_text, response_model)
                else:
                    return response_text
                    
            except (OllamaConnectionError, OllamaResponseError, ValidationError) as e:
                last_error = e
                logger.warning(
                    "Ollama request failed (attempt %d/%d): %s",
                    attempt, self.max_retries, e,
                )
                if attempt < self.max_retries:
                    # Exponentieller Backoff
                    wait_time = 2 ** attempt
                    logger.info("Retrying in %d seconds...", wait_time)
                    time.sleep(wait_time)
        
        # Alle Versuche fehlgeschlagen
        raise OllamaResponseError(
            f"All {self.max_retries} attempts failed. Last error: {last_error}"
        )
    
    def _send_request(self, request_body: dict) -> str:
        """
        Sendet eine HTTP-Anfrage an den Ollama-Server.
        
        Args:
            request_body: Der Request-Body als dict.
        
        Returns:
            Die rohe Antwort des Servers.
        
        Raises:
            OllamaConnectionError: Wenn der Server nicht erreichbar ist.
        """
        url = f"{self.host}/api/generate"
        data = json.dumps(request_body).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                
                # Ollama gibt die Antwort im "response"-Feld zurück
                if "response" not in response_data:
                    raise OllamaResponseError(
                        f"Ollama response missing 'response' field: {response_data}"
                    )
                
                return response_data["response"]
                
        except urllib.error.URLError as e:
            raise OllamaConnectionError(
                f"Could not connect to Ollama at {self.host}: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise OllamaResponseError(
                f"Invalid JSON response from Ollama: {e}"
            ) from e
    
    def _parse_json_response(self, response_text: str, response_model: Type[T]) -> T:
        """
        Parst eine JSON-Antwort und validiert sie mit einem Pydantic-Modell.
        
        Args:
            response_text: Die rohe JSON-Antwort.
            response_model: Das Pydantic-Modell für die Validierung.
        
        Returns:
            Eine Instanz von response_model.
        
        Raises:
            OllamaResponseError: Wenn die Antwort kein gültiges JSON ist.
            ValidationError: Wenn die Antwort nicht zum Modell passt.
        """
        # JSON extrahieren (manchmal ist es in Markdown-Codeblöcken verpackt)
        json_text = response_text.strip()
        
        # Markdown-Codeblöcke entfernen
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            # Erste und letzte Zeile entfernen (```json und ```)
            json_text = "\n".join(lines[1:-1])
        
        # WICHTIG: Fallback-Parser für Markdown-Format
        if not json_text.startswith("{"):
            # Versuche, JSON aus Markdown zu extrahieren
            json_text = self._extract_json_from_markdown(response_text)
        
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise OllamaResponseError(
                f"Could not parse JSON from Ollama response: {e}\n"
                f"Response: {response_text[:500]}..."
            ) from e
        
        # Mit Pydantic validieren
        try:
            return response_model.model_validate(data)
        except ValidationError as e:
            raise OllamaResponseError(
                f"Ollama response does not match {response_model.__name__}: {e}"
            ) from e

    def _extract_json_from_markdown(self, markdown_text: str) -> str:
        """
        Extrahiert JSON aus Markdown-Format.
        Dies ist ein Fallback für Modelle, die trotz JSON-Mode Markdown ausgeben.
        
        Unterstützt Formate wie:
        - **Key:** Value
        - Key: Value
        """
        import re
        
        # Mapping von Markdown-Keys zu JSON-Keys
        key_mapping = {
            "strategy": "strategy",
            "parameter_to_change": "parameter_to_change",
            "new_value": "new_value",
            "reasoning": "reasoning",
            "expected_outcome": "expected_outcome",
            "confidence": "confidence",
            "summary": "summary",
            "root_cause_analysis": "root_cause_analysis",
            "proposed_adjustment": "proposed_adjustment",
            "testable_prediction": "testable_prediction",
            "scientific_interpretation": "scientific_interpretation",
            "recommended_next_steps": "recommended_next_steps",
            "key_findings": "key_findings",
            "new_knowledge": "new_knowledge",
            "contradictions_resolved": "contradictions_resolved",
            "deprecated_knowledge": "deprecated_knowledge",
        }
        
        # Zuerst alle ** entfernen, um die Verarbeitung zu vereinfachen
        cleaned_text = markdown_text.replace("**", "")
        
        # Muster 1: Key: Value (nachdem ** entfernt wurden)
        pattern1 = re.compile(r"^([^:]+):\s*(.+)$", re.MULTILINE)
        matches1 = pattern1.findall(cleaned_text)
        
        if matches1:
            data = {}
            for key, value in matches1:
                # Key normalisieren
                normalized_key = key.strip().lower().replace(" ", "_")
                
                # Key-Mapping anwenden
                if normalized_key in key_mapping:
                    normalized_key = key_mapping[normalized_key]
                
                # Value bereinigen
                value = value.strip().strip('"').strip("'")
                # Neue Zeilen entfernen
                value = value.replace("\n", " ")
                
                # Versuche, numerische Werte zu konvertieren
                try:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
                
                data[normalized_key] = value
            
            return json.dumps(data)
        
        # Wenn kein Muster passt, leeres JSON zurückgeben
        return "{}"
    
    def is_available(self) -> bool:
        """
        Prüft, ob der Ollama-Server erreichbar ist.
        
        Returns:
            True wenn der Server erreichbar ist, sonst False.
        """
        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
