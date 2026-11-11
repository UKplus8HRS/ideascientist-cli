# IdeaScientist CLI

基于论文 [IdeaScientist: Orchestrating Agents for Grounded Scientific Ideation](https://github.com/jiarui-liu/IdeaScientist) 的独立命令行复现与扩展：输入研究问题，协调器调用模型检索 arXiv、阅读论文、寻找缺口、提出并审查想法，生成附有证据的研究提案。流程受预算、文献可用性和模型输出质量限制，可能以 `blocked` 或 `no_gap` 结束。

本项目不是原作者的官方发行版，也不声称复现论文中的分数。原论文的训练、Svalbard Idea Vault、向量检索和基准评估未在此实现。方法和部分材料的来源、修改以及 CC BY-NC 4.0 许可证详见 [NOTICE.md](NOTICE.md) 和 [LICENSE](LICENSE)。

## 安装

需要 Python 3.10 或更新版本。在仓库根目录执行：

```bash
python -m pip install .
```

开发时可安装 `python -m pip install -e '.[dev]'`；Windows 命令行也可以使用双引号。安装完成后通过 `ideascientist --help` 查看命令。

## 配置模型

参考 ARIS-Code 的交互式设置方式，运行：

```bash
ideascientist setup
```

选择预设，填写服务地址和模型 ID。模型接口使用 OpenAI 兼容的 `/chat/completions`，需要支持工具调用；也可选择 `custom` 接入兼容服务。预设的模型可修改，具体支持情况取决于服务商。`ideascientist status` 显示当前配置（密钥会被遮盖），`ideascientist doctor` 检查依赖、arXiv 检索和一次真实模型请求；这会产生一次 API 调用。

配置优先级：命令行 `--model` > 环境变量 > 配置文件 > 预设。配置文件默认位于 `~/.config/ideascientist/config.json`，也可通过 `IDEASCIENTIST_CONFIG` 指定。交互式输入的密钥会保存在该文件中；使用环境变量可避免写入磁盘。Linux/macOS 上程序尝试将文件权限设为仅所有者可读写；Windows 上请自行管理文件权限。

| 环境变量 | 作用 |
| --- | --- |
| `IDEASCIENTIST_PROVIDER` | 预设名称，如 `openai`、`openrouter`、`custom` |
| `IDEASCIENTIST_BASE_URL` | 服务地址，例如 `https://example.com/v1` |
| `IDEASCIENTIST_MODEL` | 服务端模型 ID |
| `IDEASCIENTIST_API_KEY` | 服务密钥 |
| `IDEASCIENTIST_TIMEOUT` | 请求超时秒数，默认 180 |

OpenAI 等预设也支持各自常用的 API key 环境变量。`custom` 没有默认模型，需要填写模型 ID。

## 运行

```bash
ideascientist ideate "How can agents assign credit over long horizons?" --cutoff 2025-12-31
```

默认输出到当前目录的 `runs/ideascientist/<slug>/`；可用 `--cwd` 指定项目目录。已有 run 不会被覆盖。默认预算为 24 次角色任务、40 次检索、18 次论文读取，`--max-role-calls` 可降低角色预算。模型调用次数可能高于角色任务数，因为每个任务可以多轮调用模型。

```bash
ideascientist resume runs/ideascientist/<slug> "补充说明"
```

```bash
ideascientist check runs/ideascientist/<slug>
```

```bash
ideascientist evaluate runs/ideascientist/<slug>
```

`check` 离线检查结构和证据回执，不能证明文献支持论断、想法具有新颖性或盲基线确实在候选之前产生。`evaluate` 需要已完成的报告，并调用模型；没有人工参考答案时不会伪造参考指标。失败的模型回复可能保存在 run 目录下的 `attempts/`，其中可能包含研究内容，请按需保护。

## MCP

安装后以 `ideascientist mcp` 启动 stdio 服务。MCP 客户端的配置示例：

```json
{
  "mcpServers": {
    "ideascientist": {
      "command": "ideascientist",
      "args": ["mcp"]
    }
  }
}
```

客户端若不能找到可执行文件，请填写安装环境中 `ideascientist` 的完整路径。工具 `ideascientist` 启动运行；`ideascientist-reply` 使用返回的 `runId` 继续运行，输入 `evaluate` 可评估已完成的报告。模型配置来自启动服务进程的环境和上述配置文件。

## 验证与限制

```bash
python -m pytest -q
```

离线测试使用合成数据，不需要模型或网络。真实运行需要 arXiv 网络访问、可下载且可提取文本的论文 PDF，以及支持该工作流的模型。输出是待研究者核验的想法，而非已证实的科学结果；代码不会替你运行实验或训练模型。
