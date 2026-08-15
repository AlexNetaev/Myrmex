"""
src/llm_wrapper.py
LLM-Wrapper für Ollama-Integration.

Dieser Wrapper stellt die Verbindung zu Ollama her und ruft das LLM auf.
Er validiert die Antwort gegen ein Pydantic-Modell und retryt bei Fehlern.
"""
from __future__ import annotations
import logging
import json
from typing import Any, Type

logger = logging.getLogger("llm_wrapper")


def ask_llm_with_validation(
    prompt: str,
    system_prompt: str = "",
    response_model: Type | None = None,
    max_retries: int = 3,
    model: str = "gemma4:31b-cloud",
    temperature: float = 0.2,
    context_size: int = 4096,
) -> Any:
    """
    Ruft das LLM auf und gibt das validierte Ergebnis zurück.
    
    Args:
        prompt: Der User-Prompt.
        system_prompt: Der System-Prompt.
        response_model: Das Pydantic-Modell für die Validierung.
        max_retries: Maximale Anzahl der Versuche.
        model: Das zu verwendende Modell.
        temperature: Die Temperatur für die Generierung.
        context_size: Die Context-Size für das LLM.
    
    Returns:
        Das validierte Ergebnis (Instanz von response_model).
    
    Raises:
        Exception: Wenn das LLM nicht verfügbar ist oder keine gültige
                   Antwort gibt nach allen Retry-Versuchen.
    """
    # Hinweis: In dieser Phase wird nur ein Mock zurückgegeben, da
    # Ollama noch nicht verfügbar ist. Die echte Implementierung
    # würde hier den HTTP-Request an Ollama senden.
    
    logger.info(
        f"[LLM] Calling {model} with temperature={temperature}, "
        f"context_size={context_size}, max_retries={max_retries}"
    )
    
    # Simuliere einen LLM-Aufruf (Mock für Tests)
    # In der echten Implementierung würde hier der HTTP-Request stehen:
    # import requests
    # response = requests.post(
    #     "http://localhost:11434/api/generate",
    #     json={
    #         "model": model,
    #         "prompt": prompt,
    #         "system": system_prompt,
    #         "options": {"temperature": temperature, "num_ctx": context_size}
    #     }
    # )
    # raw_response = response.json()["response"]
    
    # Für jetzt: Exception werfen, um das Fallback zu testen
    # In einer späteren Phase wird hier der echte Ollama-Aufruf implementiert
    raise NotImplementedError(
        f"LLM call to {model} not yet implemented. "
        "This is a placeholder for the real Ollama integration."
    )
