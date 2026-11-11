"""Model providers.

Every live provider speaks the OpenAI chat-completions format. Configuration is
resolved in this order, first hit wins per field:

1. explicit arguments (``--model`` on the command line, ``model`` in MCP calls)
2. environment variables ``IDEASCIENTIST_BASE_URL`` / ``IDEASCIENTIST_API_KEY`` /
   ``IDEASCIENTIST_MODEL`` / ``IDEASCIENTIST_TIMEOUT``
3. the config file written by ``ideascientist setup``
   (``$IDEASCIENTIST_CONFIG`` or ``~/.config/ideascientist/config.json``)
4. the preset named by ``IDEASCIENTIST_PROVIDER`` or the config's ``provider``

The API key is never written into a run directory.
"""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# Presets only fill in a base URL, a default model, and the environment variable
# that usually holds the key. Any OpenAI-compatible endpoint works via "custom".
PRESETS = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5.5",
        "key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "label": "Anthropic (OpenAI-compatible endpoint)",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-sonnet-5-5",
        "key_env": "ANTHROPIC_API_KEY",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-5.5",
        "key_env": "OPENROUTER_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "zhipu": {
        "label": "Zhipu GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-5",
        "key_env": "ZHIPUAI_API_KEY",
    },
    "minimax": {
        "label": "MiniMax",
        "base_url": "https://api.minimax.io/v1",
        "model": "MiniMax-M2.7",
        "key_env": "MINIMAX_API_KEY",
    },
    "custom": {
        "label": "Custom OpenAI-compatible endpoint (vLLM, Ollama, LiteLLM, a local router, ...)",
        "base_url": "http://127.0.0.1:8000/v1",
        "model": None,
        "key_env": None,
    },
}
DEFAULT_PROVIDER = "openai"
DEFAULT_TIMEOUT = 180


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


class OpenAICompatProvider:
    """POST /chat/completions on any OpenAI-compatible endpoint."""

    def __init__(self, *, base_url, api_key, model, timeout=DEFAULT_TIMEOUT, name="custom"):
        if not base_url:
            raise ProviderError("No base URL configured. Run `ideascientist setup` or set IDEASCIENTIST_BASE_URL.")
        if not model:
            raise ProviderError("No model configured. Pass --model, run `ideascientist setup`, or set IDEASCIENTIST_MODEL.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout
        self.name = name

    def describe(self):
        return {"provider": self.name, "base_url": self.base_url, "model": self.model, "api_key": _mask(self.api_key)}

    def complete(self, *, role, messages, tools=None):
        del role
        body = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise ProviderError(f"{self.base_url} returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Model endpoint {self.base_url} is not reachable. ({exc.reason})") from exc
        except TimeoutError as exc:
            raise ProviderError(f"Model endpoint did not respond within {self.timeout}s.") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Model endpoint returned non-JSON: {exc}") from exc
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected chat payload: {payload!r}"[:500]) from exc
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
        # Record which model actually answered; routers may substitute one.
        completion.upstream = {"provider": self.name, "model": payload.get("model") or self.model}
        return completion


# --- configuration -------------------------------------------------------


def config_path():
    override = os.environ.get("IDEASCIENTIST_CONFIG")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "ideascientist" / "config.json"


def load_config():
    path = config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Cannot read {path}: {exc}") from exc


def save_config(config):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def resolve_settings(model=None):
    """Merge arguments, environment, config file, and preset into one dict."""
    config = load_config()
    name = (os.environ.get("IDEASCIENTIST_PROVIDER") or config.get("provider") or DEFAULT_PROVIDER).strip().lower()
    if name not in PRESETS:
        raise ProviderError(f"Unknown provider {name!r}. Choose one of: {', '.join(PRESETS)}.")
    preset = PRESETS[name]
    # A config written for one provider should not leak its URL/model into another.
    same = config.get("provider", name) == name
    key = os.environ.get("IDEASCIENTIST_API_KEY") or (config.get("api_key") if same else None)
    if not key and preset["key_env"]:
        key = os.environ.get(preset["key_env"])
    timeout = os.environ.get("IDEASCIENTIST_TIMEOUT") or (config.get("timeout") if same else None) or DEFAULT_TIMEOUT
    return {
        "provider": name,
        "base_url": os.environ.get("IDEASCIENTIST_BASE_URL") or (config.get("base_url") if same else None) or preset["base_url"],
        "model": model or os.environ.get("IDEASCIENTIST_MODEL") or (config.get("model") if same else None) or preset["model"],
        "api_key": key or "",
        "timeout": int(timeout),
    }


def provider_from_env(model=None):
    settings = resolve_settings(model)
    return OpenAICompatProvider(
        base_url=settings["base_url"],
        api_key=settings["api_key"],
        model=settings["model"],
        timeout=settings["timeout"],
        name=settings["provider"],
    )


def _mask(key):
    if not key:
        return "(none)"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"
