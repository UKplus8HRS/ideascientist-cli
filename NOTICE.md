# Notice

This program is an independent command-line adaptation of the IdeaScientist method.
It is not an official distribution and does not reproduce the paper's benchmark scores.

The artifact schema, role instructions, evidence contracts, offline checker, arXiv
metadata resolver, and arXiv PDF acquirer under `vendor/` come from
`junjiezhou1122/ideascientist-claude-code`, which adapts
`jiarui-liu/IdeaScientist` at commit `9613a5e575e4a3f41fcb62609e3c8e80bea819a6`.

Original copyright remains Copyright (c) 2026 The IdeaScientist authors.
The adaptation maintainer of the vendored material is `junjiezhou1122`.

`vendor/check_artifacts.py` changes the schema path so the file sits next to the
script, and reads artifacts as UTF-8. On Windows the default locale encoding is
not UTF-8, so Chinese run files otherwise fail the checker. The checks themselves
are unchanged.

`vendor/acquire_arxiv.py` is unchanged. The coordinator loads it as the importable
module `acquire_arxiv`, with `vendor/` on `sys.path`, because its download worker
runs in a spawned process. A synthetic module name cannot be re-imported by that
process on Windows.

All of the above, and the new coordinator, are licensed under
CC BY-NC 4.0. See `LICENSE`.
