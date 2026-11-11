"""Command line for a standalone IdeaScientist run."""

import argparse
import sys

from ideascientist.loop import check_run, evaluate, ideate, resume
from ideascientist.provider import ProviderError, provider_from_env


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ideascientist", description="Run the IdeaScientist harness without a host agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("ideate", help="Start a run from a research problem.")
    start.add_argument("problem")
    start.add_argument("--cwd", default=".")
    start.add_argument("--cutoff", default=None)
    start.add_argument("--slug", default=None)
    start.add_argument("--model", default=None)
    start.add_argument("--language", default=None)
    start.add_argument("--max-role-calls", type=int, default=None)

    cont = sub.add_parser("resume", help="Continue a saved run.")
    cont.add_argument("run_dir")
    cont.add_argument("note", nargs="?", default="")
    cont.add_argument("--model", default=None)

    audit = sub.add_parser("check", help="Validate a run directory.")
    audit.add_argument("run_dir")

    graded = sub.add_parser("evaluate", help="Evaluate a completed report.")
    graded.add_argument("run_dir")
    graded.add_argument("--model", default=None)

    sub.add_parser("mcp", help="Serve the stdio MCP adapter.")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            errors = check_run(args.run_dir)
            if errors:
                print("\n".join(errors))
                return 1
            print("Artifact contracts and evidence receipts pass. Semantic support and chronology require review.")
            return 0
        if args.command == "mcp":
            from ideascientist.mcp import main as serve
            serve()
            return 0
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
    print(result["content"])
    return 0 if result["status"] in ("complete", "no_gap") and not result["errors"] else 2


def _progress(message):
    print(f".. {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
