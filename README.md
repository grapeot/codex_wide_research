# Wide Research Orchestrator 项目指南

> 版本日期：2025-10-16

## 1. 背景：Manus 的 Wide Research 有何价值？

2025 年 7 月 31 日，Manus 发布了 Wide Research —— 一项可同时调度上百个通用智能体的并行执行框架。官方案例展示了对 100 款运动鞋的市场分析、几十张海报的同步生成等任务，数分钟即可完成原本需要单个智能体长时间串行处理的工作。citeturn0search2turn0search3turn0search5 该能力最初面向 Pro 订阅用户推出，随后逐步向 Plus、Team 等套餐开放。citeturn0search5turn0search9

Wide Research 的核心优势在于“宽上下文”策略：每个子智能体都是完整的 Manus 实例，运行在独立虚拟机中，不受传统“经理—执行者”式角色约束，可以并行探索并协作汇总结果。citeturn0search3turn0search8 对需要大规模爬取、对比或创作的任务而言，用户无需手动拆分流程，只需以自然语言描述目标，即可获得百倍级的算力放大。citeturn0search10turn0search11

## 2. 技术洞察：宽上下文如何克服 LLM “偷懒”现象？

大型语言模型在上下文接近窗口极限时，常出现输出折损——例如长文翻译中后段漏译、摘要任务后半段自动压缩等。这种“懒惰”不仅发生在单模型，也出现在多模型链式调用中。Wide Research 采取的策略是将大任务拆解为若干小上下文子任务（divide and conquer），再以统一流程聚合结果。每个子任务上下文更短，模型无需为压缩输出而牺牲质量；并行执行还显著缩短总耗时。这是一种“上下文工程”（context engineering）的实践范式：通过编排结构而非盲目扩大窗口，让模型始终工作在高可靠区间。

## 3. 项目概述

本仓库提供了一个可复用的 Wide Research 编排脚手架，包含：

- **主控流程**：在 `wide_research_prompt.md` 中定义了 Orchestrator 的操作规范，确保每轮任务创建独立运行目录、缓存原始数据、聚合输出并进行校验。
- **子任务模板**：`runs/<timestamp>.../child_prompts/` 下的模板可自动注入参数，要求子代理独立抓取、解析、摘要目标网页，并输出一致的 JSON。
- **批量调度脚本**：`run_children.sh` 以并行方式调用 Codex CLI，控制并发度、记录日志，处理失败重试与降级。
- **示例成果**：我们用该框架处理了《现代软件工程》课程 53 位同学的提问博客，生成可验证的深度报告并发布在 [https://yage.ai/software-engineering-report.html](https://yage.ai/software-engineering-report.html)。该案例验证了 Wide Research 在大规模资料整理中的可靠性，相比单智能体流程不会在中后段“偷懒”或截断。

## 4. 环境配置

1. **Codex CLI 设置**
   - 推荐启用网络搜索能力（`codex config set sandbox_workspace_write.network_access true`）。
   - 在实验环境下，可将 `approval_policy` 设为 `never` 以避免频繁人工确认。

2. **可选 MCP Server**
   - 运行 `initial_config.sh` 将 Playwright 与 Chrome DevTools MCP 服务加入 Codex，增强网页自动化与调试能力：
     ```bash
     bash initial_config.sh
     ```

3. **目录约定**
   - 所有临时与产出文件存放在 `runs/` 目录并已加入 `.gitignore`，避免污染仓库。

## 5. 使用步骤

1. **导入主控提示**  
   在会话中引用 `wide_research_prompt.md`，确认 Orchestrator 计划后启动任务。

2. **初始化运行目录**  
   主控按照时间戳创建 `runs/<timestamp>-<task>/`，缓存索引页与参数列表（如 `tmp/student_manifest.json`）。

3. **准备子任务模板**  
   使用 `child_prompts/student_summary.template.md` 生成每个子代理 prompt，并显式要求“禁止调用 plan 工具 / 禁止等待用户输入”，保证子任务一次性完成。

4. **批量执行**  
   在运行目录中执行：
   ```bash
   MAX_JOBS=4 ./run_children.sh
   ```
   - 脚本会跳过已完成子任务，并在失败两次后输出包含 `status: "error"` 的 JSON，便于聚合阶段识别。

5. **聚合与校验**  
   - 调用 `python3 label_stats.py` 输出标签频次并刷新 `tmp/label_frequencies.json`。
   - 使用项目内的聚合脚本生成最终 HTML/Markdown 报告，或根据需要改写。

6. **成果发布**  
   - 最终 artefact（如 `final_report.html`）可直接部署到网站或内部知识库。

## 6. 目录结构示例

```
.
├── .gitignore
├── README.md
├── initial_config.sh
├── wide_research_prompt.md
└── runs/
    └── 20251016-125410-cnblogs-blogs/
        ├── child_outputs/
        ├── child_prompts/
        ├── final_report.html
        ├── label_stats.py
        ├── logs/
        ├── raw/
        └── tmp/
```

## 7. 常见问题

| 问题 | 解决方案 |
| --- | --- |
| 子任务出现 404 或超时 | 模板已要求两次重试，仍失败时会输出 error JSON；在汇总中做好异常说明即可。 |
| 部分子任务未生成问题列表 | 检查原文是否为总结类文章；脚本保留占位提示，保证聚合结构完整。 |
| 并行度设置多少合适？ | 可通过 `MAX_JOBS` 控制；建议根据本地算力与 API 限额调整（默认 4）。 |

---

借助 Wide Research 的编排思路，我们可以在保证质量的前提下，构建可审计、可复现、可扩展的大规模 AI 处理流水线。欢迎在此仓库基础上拓展更多场景。欢迎 Issue / PR 分享你的实践经验。
