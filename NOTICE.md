# Attribution and adaptation notice

This project is an independent command-line adaptation of **IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation**, by the IdeaScientist authors. It is not an official distribution and does not claim to reproduce the paper's benchmark scores.

Original work: [jiarui-liu/IdeaScientist](https://github.com/jiarui-liu/IdeaScientist), particularly [commit 9613a5e575e4a3f41fcb62609e3c8e80bea819a6](https://github.com/jiarui-liu/IdeaScientist/tree/9613a5e575e4a3f41fcb62609e3c8e80bea819a6). Original copyright: Copyright (c) 2026 The IdeaScientist authors.

The role instructions, evidence contracts, artifact schema and templates, offline checker, arXiv metadata resolver, and arXiv PDF acquirer in `src/ideascientist/vendor/` come from the independent adaptation [junjiezhou1122/ideascientist-claude-code](https://github.com/junjiezhou1122/ideascientist-claude-code), which derives its method and field contracts from the original work. Its adaptation maintainer is `junjiezhou1122`.

Changes here include a Python coordinator, OpenAI-compatible model interface, CLI and MCP adapter. The vendored checker was adjusted to locate its colocated schema and read UTF-8 on Windows; the PDF acquirer also turns worker startup failures into blocked receipts. The CLI and setup experience take inspiration from [ARIS-Code](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/tree/aris-code); this does not imply an official affiliation.

The original work and this adaptation are licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). See [LICENSE](LICENSE) for the license notice.
