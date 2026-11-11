# IdeaScientist CLI

一个独立的 IdeaScientist 协调器。角色循环由这个程序执行，模型通过本机的 Magpie 网关调用。Claude Code 不充当协调器，也不用当前会话的模型来写提案。

这不是官方发行版，也不复现论文里的分数。文献检索只查 arXiv，没有 Vault，也没有向量索引。许可证是 CC BY-NC 4.0，见 [LICENSE](LICENSE) 和 [NOTICE.md](NOTICE.md)。

## 命令

在本目录下：

```sh
PYTHONPATH=src python -m ideascientist ideate "研究问题" --cutoff 2025-12-31
```

```sh
PYTHONPATH=src python -m ideascientist resume runs/ideascientist/<slug> "补充说明"
```

```sh
PYTHONPATH=src python -m ideascientist check runs/ideascientist/<slug>
```

```sh
PYTHONPATH=src python -m ideascientist evaluate runs/ideascientist/<slug>
```

产物写在当前项目的 `runs/ideascientist/<slug>/`。已有的 run 不会被覆盖。

默认预算是 24 次角色调用、40 次检索、18 次读论文。`--max-role-calls` 只能把角色预算调低。

## Magpie

默认提供方是本机 Magpie Router，地址 `http://127.0.0.1:3425/v1`，使用已经打通的 OpenAI 对话格式。网关没开时命令会退出，不会改连别的主机。

默认模型是 `claude/claude-sonnet-5-5`。`--model` 可换成 Magpie 目录里的其他 id，例如 `claude/claude-opus-5-5` 或 `group/never-stuck-free`。

可用环境变量覆盖：`MAGPIE_BASE_URL`、`MAGPIE_API_KEY`、`MAGPIE_MODEL`、`IDEASCIENTIST_PROVIDER`（`magpie` 或 `openai`）。密钥不会写入 `run.json`。

读 PDF 需要 `pypdf`：

```sh
python -m pip install pypdf
```

## MCP

stdio 服务与本机的 `codex` MCP 同一类。测试通过后注册：

```sh
claude mcp add ideascientist -s user -- "D:\python\python.exe" "D:\AAA Year 2\科研\Ideascientist\ideascientist-cli\mcp_server.py"
```

工具是 `ideascientist` 和 `ideascientist-reply`。一次调用会跑到完成、没有缺口或被挡住为止，期间发送进度。回复时带上返回的 `runId`。`prompt` 为 `evaluate` 时对已完成的报告做评估。

## 不会做的事

不训练，不加载 LoRA，不建嵌入索引。检查器只核对结构和引用回执，不证明一个想法是新的，也不证明盲基线在时间上不可伪造。机制类论断没有全文时，运行会停在 `blocked` 或 `unverified`。
