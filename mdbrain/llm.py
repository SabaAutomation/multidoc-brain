"""Ollama client (local, free) and a mock for self-tests."""
import requests


class OllamaLLM:
    def __init__(self, model="qwen2.5-coder:7b", host="http://localhost:11434", timeout=600, num_ctx=4096):
        self.model, self.host, self.timeout, self.num_ctx = model, host.rstrip("/"), timeout, num_ctx

    def check(self):
        try:
            r = requests.get(self.host + "/api/tags", timeout=10)
            r.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Cannot reach Ollama at {self.host}. Is it running? ({e})")
        names = [m.get("name", "") for m in r.json().get("models", [])]
        if not any(n == self.model or n.split(":")[0] == self.model.split(":")[0] and ":" not in self.model for n in names):
            raise RuntimeError(f"Model '{self.model}' not found. Installed: {names}. Run: ollama pull {self.model}")

    def chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0, "num_ctx": self.num_ctx},
        }
        r = requests.post(self.host + "/api/chat", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"]


class MockLLM:
    """For self-tests only. mode='echo' returns the prompt; otherwise returns a fixed string."""

    def __init__(self, fixed=None):
        self.fixed = fixed

    def chat(self, system: str, user: str) -> str:
        return user if self.fixed is None else self.fixed
