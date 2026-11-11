"""Model providers. Magpie is an OpenAI-compatible gateway on this machine."""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "http://127.0.0.1:3425/v1"
DEFAULT_MODEL = "claude/claude-sonnet-5-5"
# Local gateway token Magpie writes into Codex config. Not an upstream account key.
DEFAULT_TOKEN = "magpie"


class ProviderError(RuntimeError):
    pass


@dataclass
class Completion:
    content: str = ""
    tool_calls: list = field(default_factory=list)


class ScriptedProvider:
    """Return canned completions. Tests use this; it never touches the network."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    def complete(self, *, role, messages, tools=None):
        self.calls.append({"role": role, "messages": messages, "tools": tools or []})
        for index, (expected, payload) in enumerate(self.steps):
            if expected == role:
                self.steps.pop(index)
                if isinstance(payload, Completion):
                    return payload
                return Completion(content=json.dumps(payload, ensure_ascii=False))
        raise ProviderError(f"no scripted completion for role {role}")


class MagpieProvider:
    def __init__(self, *, base_url=None, api_key=None, model=None, timeout=180):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or DEFAULT_TOKEN
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout

    def complete(self, *, role, messages, tools=None):
        del role
        body = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "x-openai-actor-authorization": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                provider = response.headers.get("X-Magpie-Provider")
                upstream = response.headers.get("X-Magpie-Model")
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"Magpie gateway is not reachable at {self.base_url}. Start Magpie Router and retry. ({exc})"
            ) from exc
        except TimeoutError as exc:
            raise ProviderError(f"Magpie did not respond within {self.timeout}s.") from exc
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Magpie returned an unexpected chat payload: {payload!r}"[:500]) from exc
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            arguments = function.get("arguments") or "{}"
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"_raw": arguments}
            calls.append({"id": call.get("id") or function.get("name"), "name": function.get("name"), "arguments": arguments})
        completion = Completion(content=message.get("content") or "", tool_calls=calls)
        completion.upstream = {"provider": provider, "model": upstream}
        return completion


def provider_from_env(model=None):
    kind = os.environ.get("IDEASCIENTIST_PROVIDER", "magpie").strip().lower()
    if kind == "openai":
        return MagpieProvider(
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=model or os.environ.get("OPENAI_MODEL", "gpt-4.1"),
        )
    if kind != "magpie":
        raise ProviderError(f"Unknown IDEASCIENTIST_PROVIDER {kind!r}. Use magpie or openai.")
    return MagpieProvider(
        base_url=os.environ.get("MAGPIE_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ.get("MAGPIE_API_KEY", DEFAULT_TOKEN),
        model=model or os.environ.get("MAGPIE_MODEL", DEFAULT_MODEL),
        timeout=int(os.environ.get("MAGPIE_TIMEOUT", "180")),
    )
