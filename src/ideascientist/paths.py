"""Locate the vendored checker, schema, and role instructions."""

import importlib.util
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "vendor"


def load_vendor(name):
    path = VENDOR / f"{name}.py"
    # acquire_arxiv downloads in a spawned process. On Windows that process
    # re-imports the worker by module name, so the name must be a real module
    # whose directory is already on sys.path. The child copies this path.
    if name == "acquire_arxiv":
        module_name = "acquire_arxiv"
        vendor_path = str(VENDOR)
        if vendor_path not in sys.path:
            sys.path.append(vendor_path)
    else:
        module_name = f"ideascientist_vendor_{name}"
    cached = sys.modules.get(module_name)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() == path.resolve():
        return cached
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
