"""Command line for a standalone IdeaScientist run."""

import argparse
import getpass
import json
import sys

from ideascientist import __version__
from ideascientist.provider import (
    PRESETS,
    ProviderError,
    _mask,
    config_path,
    load_config,
    provider_from_env,
    resolve_settings,
    save_config,
)


def main(argv=None):
    _utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="ideascientist",
        description="Run the IdeaScientist ideation harness against any OpenAI-compatible model.",
    )
    parser.add_argument("--version", action="version", version=f"ideascientist {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("ideate", help="Start a run from a research problem.")
    start.add_argument("problem")
    start.add_argument("--cwd", default=".", help="Project directory; runs go to <cwd>/runs/ideascientist/.")
    start.add_argument("--cutoff", default=None, help="Inclusive YYYY-MM-DD literature cutoff.")
    start.add_argument("--slug", default=None)
    start.add_argument("--model", default=None)
    start.add_argument("--language", default=None)
    start.add_argument("--max-role-calls", type=int, default=None, help="Lower the role-call budget (max 24).")

    cont = sub.add_parser("resume", help="Continue a saved run.")
    cont.add_argument("run_dir")
    cont.add_argument("note", nargs="?", default="")
    cont.add_argument("--model", default=None)

    audit = sub.add_parser("check", help="Validate a run directory offline.")
    audit.add_argument("run_dir")

    graded = sub.add_parser("evaluate", help="Evaluate a completed report.")
    graded.add_argument("run_dir")
    graded.add_argument("--model", default=None)

    wizard = sub.add_parser("setup", help="Choose a provider, model, and key; saves the config file.")
    wizard.add_argument("--provider", choices=sorted(PRESETS), default=None)
    wizard.add_argument("--base-url", default=None)
    wizard.add_argument("--model", default=None)
    wizard.add_argument("--api-key", default=None, help="Stored in the config file. Prefer an env var on shared machines.")
    wizard.add_argument("--non-interactive", action="store_true", help="Do not prompt; use flags and preset defaults.")

    sub.add_parser("status", help="Show the resolved provider configuration.")

    ping = sub.add_parser("doctor", help="Check Python deps, the model endpoint, and arXiv reachability.")
    ping.add_argument("--model", default=None)

    sub.add_parser("mcp", help="Serve the stdio MCP adapter.")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            from ideascientist.loop import check_run

            errors = check_run(args.run_dir)
            if errors:
                print("\n".join(errors))
                return 1
            print("Artifact contracts and evidence receipts pass. Semantic support and chronology require review.")
            return 0
        if args.command == "setup":
            return _setup(args)
        if args.command == "status":
            return _status()
        if args.command == "doctor":
            return _doctor(args.model)
        if args.command == "mcp":
            from ideascientist.mcp import main as serve

            serve()
            return 0
        from ideascientist.loop import evaluate, ideate, resume

        provider = provider_from_env(getattr(args, "model", None))
        if args.command == "ideate":
            result = ideate(
                args.problem,
                cwd=args.cwd,
                provider=provider,
                cutoff=args.cutoff,
                slug=args.slug,
                language=args.language,
                max_role_calls=args.max_role_calls,
                on_progress=_progress,
            )
        elif args.command == "resume":
            result = resume(args.run_dir, args.note, provider=provider, on_progress=_progress)
        else:
            result = evaluate(args.run_dir, provider=provider, on_progress=_progress)
    except (ProviderError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. The run directory keeps its progress; continue with `ideascientist resume`.", file=sys.stderr)
        return 130
    print(result["content"])
    return 0 if result["status"] in ("complete", "no_gap") and not result["errors"] else 2


def _setup(args):
    config = load_config()
    interactive = not args.non_interactive and sys.stdin.isatty()
    names = list(PRESETS)
    provider = args.provider
    if provider is None and interactive:
        print("IdeaScientist setup\n\nChoose a provider (any OpenAI-compatible endpoint works):")
        for index, name in enumerate(names, 1):
            print(f"  {index}. {name:<11} {PRESETS[name]['label']}")
        current = config.get("provider", "openai")
        raw = input(f"Provider [{current}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(names):
            provider = names[int(raw) - 1]
        else:
            provider = raw or current
    provider = provider or config.get("provider") or "openai"
    if provider not in PRESETS:
        print(f"Unknown provider {provider!r}.", file=sys.stderr)
        return 1
    preset = PRESETS[provider]
    keep = config.get("provider") == provider

    def ask(label, flag, default, secret=False):
        if flag is not None:
            return flag
        if not interactive:
            return default
        shown = "(hidden)" if secret and default else (default or "")
        prompt = f"{label} [{shown}]: "
        value = getpass.getpass(prompt) if secret else input(prompt)
        return value.strip() or default

    base_url = ask("Base URL", args.base_url, (config.get("base_url") if keep else None) or preset["base_url"])
    model = ask("Model", args.model, (config.get("model") if keep else None) or preset["model"])
    key_hint = f" (leave empty to read ${preset['key_env']})" if preset["key_env"] else ""
    api_key = ask(f"API key{key_hint}", args.api_key, config.get("api_key") if keep else None, secret=True)
    if not model:
        print("A model id is required for this provider.", file=sys.stderr)
        return 1
    saved = {"provider": provider, "base_url": base_url, "model": model}
    if api_key:
        saved["api_key"] = api_key
    if config.get("timeout"):
        saved["timeout"] = config["timeout"]
    path = save_config(saved)
    print(f"Saved {path}")
    return _status()


def _status():
    settings = resolve_settings()
    shown = dict(settings)
    shown["api_key"] = _mask(settings["api_key"])
    shown["config_file"] = str(config_path()) + ("" if config_path().is_file() else " (not created; run `ideascientist setup`)")
    print(json.dumps(shown, ensure_ascii=False, indent=2))
    return 0


def _doctor(model):
    ok = True
    print(f"python {sys.version.split()[0]}")
    try:
        import pypdf

        print(f"pypdf {pypdf.__version__}")
    except ImportError:
        ok = False
        print("pypdf MISSING: python -m pip install pypdf (needed to read arXiv PDFs)")
    try:
        from ideascientist.sources import search_arxiv

        hits = search_arxiv("credit assignment", max_results=1)
        print(f"arXiv search ok ({len(hits)} hit)")
    except Exception as exc:  # noqa: BLE001 - report any network failure
        ok = False
        print(f"arXiv search FAILED: {exc}")
    try:
        provider = provider_from_env(model)
        print(f"endpoint {provider.base_url}  model {provider.model}")
        reply = provider.complete(role="doctor", messages=[{"role": "user", "content": "Reply with the single word ok."}])
        print(f"model replied: {reply.content.strip()[:60]!r} (served by {reply.upstream['model']})")
    except ProviderError as exc:
        ok = False
        print(f"model FAILED: {exc}")
    return 0 if ok else 1


def _progress(message):
    print(f".. {message}", file=sys.stderr, flush=True)


def _utf8_stdio():
    # Windows consoles default to a legacy code page; run output is often Chinese.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
