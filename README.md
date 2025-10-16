# Codex Wide Research

这个repo给[Codex CLI](https://github.com/openai/codex/)加上了Wide Research的功能，大幅增强了它的能力（下文有具体示例）。

## 1. 背景：Manus的Wide Research

2025年7月底，Manus 发布了 Wide Research。这个功能可以同时调度上百个通用智能体并行执行任务。官方案例展示了对 100 款运动鞋的市场分析、几十张海报的同步生成等任务。

这个功能从产品业务的角度解决了大规模调研的问题，但从技术上看它的意义可能更大。LLM或者说AI，它一大限制就是当输出的长度到了一定程度，比如说占了max context window 50%，或者有时候甚至20%的时候，它就会开始偷懒。比如说让它翻译一个东西，前面做得还挺认真的，但是到中间就开始跳一句翻一句，到后面干脆就不原样翻译，而是一边做缩略一边做翻译。

而且这是一个所有LLM都有的普遍规律，严重限制了LLM的实用性。具体表现就是不听话，偷懒。更糟糕的是，大多数AI的用户其实没有意识到这个限制。这就导致很多时候LLM的能力在那里，但大多数用户因为识别不出来这个限制，也不知道怎么绕过去，AI的能力被极大浪费了。

Wide Research的核心在于它的“宽上下文”的策略。它用了分而治之的思想，通过把一个问题分解成很多独立的子问题，来把子Agents的上下文窗口分隔开了。这样每个Agent的输出都不会太长。最后再用程序（而不是LLM）把输出合并起来，解决了这个根本性的限制。

我在使用Manus的过程中越来越离不开Wide Research这个功能。而与此同时，我另一个很常用的工具是Codex。相比于其他AI，Codex的AI特别听话、主动、可靠。但即便如此，由于上面所说的output context window的限制，在进行一些类似Wide Research的大规模任务时，它仍然会力不从心。

这是为什么我做了这个 repo，试图给 Codex 一个 prompt 上的指引，从而让它也能实现 Wide Research 的功能。

## 2. 实例展示

我们有一个《现代软件工程》课程，其中的一个作业是希望学生把自己的上课感想和问题写成一篇 blog。一共53个学生交了作业，他们的文章分散在不同的网站上。我们一开始试着用了DeepSeek来[做总结](https://www.cnblogs.com/xinz/p/19139660)，但是发现它的结果大都是幻觉。

如果有一个靠谱的AI可以抓取、理解和概括他们的文章内容，并且在这个基础上做出更抽象、更高层的分析，可以省掉老师很多时间。

我们使用这个repo可以完美完成这个任务。使用这样的prompt：

> https://www.cnblogs.com/xinz/p/19139660
> 
> 我们在上一门软件工程课的时候录制了一个作业，让学生在 blog 里面对软件工程进行提问。这个页面是一个 AI 总结，但是里面基本上全是幻觉，只有 URL 是正确的。我现在就想看下面几件事情：
> 
> 第一，你把里面学生 blog 的姓名和 URL 全部提取出来，但是不要看 AI 总结，那都是幻觉。
> 
> 第二，你用 Wide Research 把每一个 blog 阅读一下，总结一下每个学生分别提了什么问题，用标题加简述的形式进行总结。
> 
> 第三，你再具体看一下这些总结的结果，看看大家有没有什么共同点或者最关注的话题，设计一个 label taxonomy。
> 
> 第四，你再再次调用 Wide Research，针对每篇文章的内容给它们 assign 五个标签。
> 
> 第五，你再写一个程序来统计最常见的几个标签。
> 
> 第六，你再根据上面所有的内容汇总整理成一个单网页的中文的有深度的分析。它的根本目标是让人一看就知道学生最关心的问题是什么，同时还能点进文章进行核实。要着重强调思维深度，给人惊喜感，让人觉得有顿见，又能轻松验证它的正确性。对于从 Wide Research 中间拿到的结果不要进行缩略，直接放到最终报告里。最终结果发布出来。
>
> wide_research_prompt.md

注意最后的md文件，这就是repo里面的prompt文件。

Codex收到这个任务以后首先会做一个计划，让用户确认。确认以后在没有人工干预的情况下忙活了半个多小时，生成了[这样一个网页](https://yage.ai/software-engineering-report.html)。

他有几个特征：  

1. 53个学生的结果全出来了。  
2. 姓名和 URL 之间的对应关系都是对的。  
3. 不论是 URL 还是题的问题，还是做打的标签，都没有幻觉和错误。

这个是非常难得的。事实上，在使用 Wide Research 之前，我们也试了用其他工具来做这个任务。一般的 AI 工具就不说了，出来的质量很差。唯一做得比较好的是两个工具： 

第一是 Deep Research，由于它可以输出十几个学生的正确结果，但是由于类似 context window 长度的限制，后面更多的学生作业它就没有看了，就没有看和输出了。  
第二是 Codex，它用纯手工的方法去做，可以输出二十多个学生的概括。但也是由于同样的原因，这样做一方面很慢，另一方面也漏了很多学生。

唯一成功的是Manus的wide research和我们的Codex wide research。

## 3. 项目概述

本仓库提供了一个可复用的 Wide Research 编排脚手架，包含：

- **主控流程**：在 `wide_research_prompt.md` 中定义了 Wide Research 的操作规范。在Codex中@这个文件即可启用。
- **批量调度脚本**：`scripts/run_children.sh` 是一个barebone示例脚本，帮助Codex规避一些最基础的问题。

## 4. 环境配置

1. **Codex CLI 设置**
   - 在实验环境下，可将 `/approve` 设为 `Full Access` 以避免频繁人工确认。

2. **可选 MCP Server**
   - 可以运行下面的指令安装两个MCP server。这两个server不是硬性依赖（装不上也没事）。但可以增强Codex的能力。
     ```bash
      codex mcp add playright -- npx @playwright/mcp@latest
      codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
     ```
## 5. 使用步骤

在会话中引用 `wide_research_prompt.md` 即可。然后在Prompt里提到Wide Research的时候Codex就会知道怎么并行做了。一个示例prompt见第二节。