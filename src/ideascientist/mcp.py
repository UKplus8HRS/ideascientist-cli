"""stdio MCP adapter, shaped like the local codex-exec server."""

import json
import os
import sys
import uuid
from pathlib import Path

from ideascientist import __version__
from ideascientist.loop import evaluate, ideate, resume
from ideascientist.provider import ProviderError, provider_from_env
from ideascientist.store import dump, load_json

PROTOCOL = "2025-06-18"
TOOLS = [
    {
        "name": "ideascientist",
        "description": "Start an IdeaScientist run. The CLI calls Magpie itself and returns when the run completes, blocks, or finds no gap.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Research problem."},
                "cutoff": {"type": "string", "description": "Inclusive YYYY-MM-DD literature cutoff. Omit for live literature."},
                "slug": {"type": "string"},
                "model": {"type": "string", "description": "Magpie model id, for example claude/claude-sonnet-5-5."},
                "cwd": {"type": "string"},
                "language": {"type": "string"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "ideascientist-reply",
        "description": "Continue a saved IdeaScientist run. The run keeps the directory and model it was started with.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Note for the continuation, or 'evaluate' to score a completed report."},
                "runId": {"type": "string"},
            },
            "required": ["prompt", "runId"],
        },
    },
]


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            _write({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        response = handle(message, emit=_write)
        if response is not None:
            _write(response)


def handle(message, *, emit, provider=None, source=None, state_dir=None):
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ideascientist", "version": __version__},
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        return _call(message, emit=emit, provider=provider, source=source, state_dir=state_dir)
    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"unknown method {method}"}}


def _call(message, *, emit, provider, source, state_dir):
    request_id = message.get("id")
    params = message.get("params") or {}
    name = params.get("name")
    args = params.get("arguments") or {}
    token = (params.get("_meta") or {}).get("progressToken")
    progress = {"n": 0}

    def on_progress(text):
        progress["n"] += 1
        if token is None:
            return
        emit({"jsonrpc": "2.0", "method": "notifications/progress", "params": {
            "progressToken": token, "progress": progress["n"], "message": text,
        }})

    try:
        if name == "ideascientist":
            prompt = args.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                return _error(request_id, -32602, "prompt is required")
            chosen = provider or provider_from_env(args.get("model"))
            on_progress("starting run")
            result = ideate(
                prompt,
                cwd=args.get("cwd") or os.getcwd(),
                provider=chosen,
                source=source,
                cutoff=args.get("cutoff"),
                slug=args.get("slug"),
                language=args.get("language"),
                on_progress=on_progress,
            )
            run_id = uuid.uuid4().hex[:16]
            _remember(run_id, {
                "runId": run_id,
                "runDir": result["run_dir"],
                "cwd": str(Path(args.get("cwd") or os.getcwd()).resolve()),
                "model": args.get("model"),
            }, state_dir)
        elif name == "ideascientist-reply":
            prompt = args.get("prompt")
            run_id = args.get("runId")
            if not isinstance(prompt, str) or not run_id:
                return _error(request_id, -32602, "prompt and runId are required")
            saved = _recall(run_id, state_dir)
            if saved is None:
                return _error(request_id, -32602, f"unknown runId {run_id}")
            chosen = provider or provider_from_env(saved.get("model"))
            on_progress("resuming run")
            if prompt.strip().lower() == "evaluate":
                result = evaluate(saved["runDir"], provider=chosen, on_progress=on_progress)
            else:
                result = resume(saved["runDir"], prompt, provider=chosen, source=source, on_progress=on_progress)
        else:
            return _error(request_id, -32601, f"unknown tool {name}")
    except (ProviderError, ValueError, OSError) as exc:
        return _tool_result(request_id, run_id=None, text=str(exc), failed=True)
    return _tool_result(request_id, run_id=run_id, text=result["content"], failed=False, result=result)


def _tool_result(request_id, *, run_id, text, failed, result=None):
    body = {
        "runId": run_id,
        "status": None if result is None else result["status"],
        "stage": None if result is None else result["stage"],
        "runDir": None if result is None else result["run_dir"],
        "content": text,
    }
    payload = {"content": [{"type": "text", "text": text}], "structuredContent": body}
    if failed:
        payload["isError"] = True
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def _remember(run_id, payload, state_dir):
    dump(_state(state_dir) / f"{run_id}.json", payload)


def _recall(run_id, state_dir):
    path = _state(state_dir) / f"{run_id}.json"
    if not path.is_file():
        return None
    return load_json(path)


def _state(state_dir):
    path = Path(state_dir) if state_dir else Path(os.environ.get("IDEASCIENTIST_STATE_DIR", Path.home() / ".ideascientist" / "runs"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _write(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()
