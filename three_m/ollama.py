"""Tiny Ollama HTTP client with no third-party dependencies."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, model: str = "qwen3.6", host: str = "http://localhost:11434", timeout: int = 300):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        # Qwen reasoning models may otherwise place the entire structured answer
        # in Ollama's `thinking` field and leave `response` empty.
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }
        if json_mode:
            payload["format"] = "json"
        request = Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise OllamaError(
                f"Could not call Ollama at {self.host}: {exc}. "
                f"Start Ollama and ensure model '{self.model}' is installed."
            ) from exc
        if "response" not in body:
            raise OllamaError(f"Unexpected Ollama response: {body}")
        return body["response"]
