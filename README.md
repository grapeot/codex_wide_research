# Codex Wide Research

## 中文版

这个 repo 提供一个实验性的 Wide Research 工作流，核心是保持以往的中文说明，但将调研执行交给已经写好的 Python 代码。和 `master` 分支相比，`code_based` 分支最大的不同在于：

- 不再依赖 Codex 的多轮 Prompt 来完成调研，而是调用仓库内的 `research_agent_code.py`，它集成了 Tavily 搜索、内容抽取与 OpenAI API。
- 所有相关的提示文件已经重命名/替换为代码导向版本，只保留了中文版 `wide_research_code_prompt_cn.md`，英文版暂时移除。

### 主要文件

- `research_agent_code.py`：基于 Tavily 与 OpenAI 异步 API 的调研代理实现。
- `wide_research_code_prompt_cn.md`：针对上述代码流程的协调提示，保持原有中文内容主体不变。
- `requirements.txt`：运行该代理所需的依赖列表，可通过 `uv pip install -r requirements.txt` 安装。

### 当前状态

该分支仍在实验阶段，欢迎在本地跑通后反馈使用体验。

### 使用方式（示例）

1. 确保本地激活 `uv` 创建的虚拟环境，例如：
   ```bash
   uv venv venv
   source venv/bin/activate
   uv pip install -r requirements.txt
   ```
2. 使用 CLI 运行调研代理：
   ```bash
   python research_agent_code.py --help
   ```
3. 在 Codex CLI 中提及 `wide_research_code_prompt_cn.md`即可启用新的编排提示。

> 注意：该实验版本主要针对中文调研场景，英文 Wide Research Prompt 已移除。
