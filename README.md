# Codex Wide Research

- [English Version](#english-version)

--------------------------------------------------------------------------------

## 中文版

这个 repo 给 [Codex CLI](https://github.com/openai/codex/) 加上了 Wide Research 的能力，大幅增强它在大规模资料整理中的可靠性（下文有场景示例）。

### 1. 背景：Manus 的 Wide Research

2025 年 7 月底 Manus 发布 Wide Research，允许同时调度上百个通用智能体并行执行任务。官方案例展示了对 100 款运动鞋的市场分析、几十张海报的同步生成等场景。

从产品层面，它解决了大规模调研的效率问题；从技术角度看意义更大。LLM 在输出接近 context window 阈值时普遍出现“偷懒”：长文翻译漏译、长列表总结越写越短、甚至随手压缩。多数用户难以察觉这一限制，使得模型潜力被浪费。

Wide Research 的核心是“宽上下文”策略：把大任务拆成多个子任务，让每个子 Agent 的上下文足够短，再用程序而非 LLM 合并结果，根本上规避了长上下文退化。

我在 Manus 中几乎离不开 Wide Research；与此同时，我常用的 Codex 也非常听话、主动、可控。但如果不加额外编排，Codex 面对海量子任务仍然容易卡在同样的上下文瓶颈。这正是我为 Codex 设计这套 Wide Research Prompt 的原因：让它也能以脚本化方式完成“宽上下文”任务。

### 2. 实例展示

《现代软件工程》课程要求 53 名学生分别写博客提问题，文章散落在多个网站。我们起初用 DeepSeek [尝试总结](https://www.cnblogs.com/xinz/p/19139660)，结果几乎全是幻觉。

如果有一个靠谱的 AI 能抓取、理解、概括所有文章，并继续做聚合分析，就能显著节省教师时间。我们使用本 repo 给出的 prompt 完成了该任务：

> https://www.cnblogs.com/xinz/p/19139660  
> ……  
> wide_research_prompt_cn.md

Codex 会先给出计划，用户确认后无需人工干预就能跑完整个流程，最终生成 [软件工程课程分析网页](https://yage.ai/software-engineering-report.html)。

结果亮点：

1. 53 名学生全部覆盖。  
2. 姓名与 URL 配对准确。  
3. URL、问题摘要、标签等内容均无幻觉。

对比其他方案：

- Deep Research 能给出十几篇有效结果，但后续受上下文限制中断。
- 纯手工使用 Codex 能处理二十多篇，速度慢且易遗漏。
- Manus Wide Research 与本仓库编排的 Codex Wide Research 是目前唯二成功“全覆盖”的方案。

### 3. 项目概述

本仓库提供可复用的 Wide Research 编排脚手架，包含：

- **主控流程**：`wide_research_prompt_cn.md` 定义了操作规范，在 Codex 中 @ 该文件即可启用。
- **批量调度脚本**：`scripts/run_children.sh` 为最小示例，帮助 Codex 避免常见陷阱。

### 4. 环境配置

1. **Codex CLI 设置**  
   - 在实验环境可将 `/approve` 设为 `Full Access`，减少人工确认。

2. **可选 MCP Server**  
   - 运行以下命令可安装两个 MCP server（非必需但能增强能力）：
     ```bash
     codex mcp add playright -- npx @playwright/mcp@latest
     codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
     ```

### 5. 使用步骤

在会话中引用 `wide_research_prompt_cn.md`，并在 prompt 描述 Wide Research 任务，Codex 即会按照分治策略完成并行流程。示例 prompt 见前文。

--------------------------------------------------------------------------------

## English Version

This repository equips the [Codex CLI](https://github.com/openai/codex/) with Wide Research style orchestration, greatly boosting its reliability on large-scale information synthesis tasks.

### 1. Background: Manus Wide Research

In late July 2025, Manus launched Wide Research, a feature that can dispatch hundreds of general-purpose agents in parallel. Official demos include market research for 100 sneakers and concurrent design of dozens of posters.

From a product perspective, it accelerates large-scale research. Technically, it solves a classic LLM failure mode: when the generated output approaches the context-window limit (often 20–50% of the window), most LLMs start “cutting corners”—skipping sentences in translations or aggressively shortening long lists. Many users do not notice this degradation, so model capacity is underused.

Wide Research embraces a “wide context” strategy: break the big request into smaller subtasks, keep each agent’s context short, and merge the answers with deterministic code instead of another LLM. This eliminates the long-context decay problem.

I rely heavily on Wide Research inside Manus. Codex remains my go-to assistant because it is obedient, proactive, and dependable. However, without additional orchestration Codex still struggles with dozens of sub-requests due to the same context ceiling. That is why this repository provides a dedicated Wide Research prompt so Codex can execute the divide-and-conquer workflow programmatically.

### 2. Case Study

In a “Modern Software Engineering” class, 53 students wrote blog posts to raise questions about the course, scattered across multiple sites. Our early attempt with DeepSeek to [summarize the posts](https://www.cnblogs.com/xinz/p/19139660) produced hallucinations.

We needed an assistant that could fetch, read, summarize, and aggregate every article reliably. Using the prompt shipped in this repo:

> https://www.cnblogs.com/xinz/p/19139660  
> …  
> wide_research_prompt_en.md

Codex proposed a plan, received approval, and autonomously generated the [software engineering report](https://yage.ai/software-engineering-report.html) with no additional intervention.

Highlights:

1. All 53 students are covered.  
2. Names and URLs are correctly mapped.  
3. Summaries, labels, and links contain no hallucinations.

Alternative attempts:

- Deep Research handled a dozen posts before stalling because of context limits.  
- Running Codex manually covered twenty-something posts but was slow and missed entries.  
- Manus Wide Research and this Codex Wide Research pipeline are the only workflows that completed the full set.

### 3. Project Overview

The repository offers reusable scaffolding:

- **Orchestrator Prompt**: `wide_research_prompt_en.md` defines the workflow—mention the file inside Codex to activate it.
- **Batch Runner**: `scripts/run_children.sh` is a minimal example showing how Codex can avoid common pitfalls.

### 4. Environment Setup

1. **Codex CLI**  
   - For experiments, set `/approve` to `Full Access` to skip manual approvals.

2. **Optional MCP Servers**  
   - Install two optional servers (not required but handy):
     ```bash
     codex mcp add playright -- npx @playwright/mcp@latest
     codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
     ```

### 5. Usage

Mention `wide_research_prompt_en.md` in your dialogue and describe the task as a Wide Research job; Codex will run the parallel divide-and-conquer flow. A real-world example is provided in Section 2.
