"""stdio entry point. Claude Code launches this file with the local Python."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ideascientist.mcp import main

if __name__ == "__main__":
    main()
