"""stdio MCP entry point for a source checkout. After `pip install`, use `ideascientist mcp` instead."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ideascientist.mcp import main

if __name__ == "__main__":
    main()
