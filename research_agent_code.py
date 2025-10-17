#!/usr/bin/env python3
"""Command-line research agent that uses OpenAI and Tavily tools."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

TAVILY_BASE_URL = "https://api.tavily.com"
MAX_TAVILY_RESULTS = 20
RESULT_LOG_LIMIT = 500


class TavilyError(RuntimeError):
    """Raised when Tavily returns an error response."""


@dataclass
class TavilySearchArgs:
    keywords: List[str]
    num_results: int = 6


@dataclass
class TavilyExtractArgs:
    urls: List[str]


class TavilyAsyncClient:
    """Async HTTP client for Tavily search and extract endpoints."""

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=TAVILY_BASE_URL,
            timeout=httpx.Timeout(timeout, connect=timeout),
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, args: TavilySearchArgs) -> Dict[str, Any]:
        if not args.keywords:
            raise TavilyError("search requires at least one keyword")
        if args.num_results < 1 or args.num_results > MAX_TAVILY_RESULTS:
            raise TavilyError(
                f"num_results must be between 1 and {MAX_TAVILY_RESULTS}, got {args.num_results}"
            )

        async def _search_one(keyword: str) -> Dict[str, Any]:
            payload = {
                "query": keyword,
                "include_answer": "advanced",
                "include_raw_content": False,
                "include_images": True,
                "include_image_descriptions": True,
                "search_depth": "advanced",
                "max_results": args.num_results,
            }
            response = await self._client.post("/search", json=payload)
            _ensure_tavily_success(response)
            return response.json()

        tasks = [asyncio.create_task(_search_one(keyword)) for keyword in args.keywords]
        results = []
        for keyword, task in zip(args.keywords, tasks):
            data = await task
            results.append({"keyword": keyword, "response": data})

        combined_answer = "\n".join(
            entry["response"].get("answer", "") for entry in results if entry["response"].get("answer")
        ).strip()

        return {
            "queries": results,
            "combined_answer": combined_answer,
        }

    async def extract(self, args: TavilyExtractArgs) -> Dict[str, Any]:
        if not args.urls:
            raise TavilyError("extract requires at least one URL")

        async def _extract_one(url: str) -> Dict[str, Any]:
            payload = {
                "urls": url,
                "extract_depth": "advanced",
                "format": "markdown",
                "include_images": False,
                "include_favicon": False,
            }
            response = await self._client.post("/extract", json=payload)
            _ensure_tavily_success(response)
            return response.json()

        tasks = [asyncio.create_task(_extract_one(url)) for url in args.urls]
        results = []
        for url, task in zip(args.urls, tasks):
            data = await task
            results.append({"url": url, "response": data})

        return {"extractions": results}


def _ensure_tavily_success(response: httpx.Response) -> None:
    if response.status_code >= 400:
        try:
            detail = response.json()
        except json.JSONDecodeError:
            detail = response.text
        raise TavilyError(f"Tavily request failed ({response.status_code}): {detail}")


def truncate(text: str, limit: int = RESULT_LOG_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def message_content_text(message: Dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                if "text" in part:
                    parts.append(str(part["text"]))
                elif part.get("type") == "text" and "text" in part:
                    parts.append(str(part["text"]))
        return "\n".join(parts)
    return str(content)


def build_tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": (
                    "Use Tavily search to fetch up-to-date web results. "
                    "Keywords should be a list of related terms. Set num_results between 1 and 20."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of search keywords.",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 6).",
                            "default": 6,
                            "minimum": 1,
                            "maximum": MAX_TAVILY_RESULTS,
                        },
                    },
                    "required": ["keywords"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract",
                "description": (
                    "Use Tavily extract to pull cleaned markdown content from URLs returned by search."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string", "format": "uri"},
                            "description": "List of absolute URLs to extract in markdown format.",
                        }
                    },
                    "required": ["urls"],
                },
            },
        },
    ]


SYSTEM_PROMPT = (
    "You are an autonomous research analyst. "
    "Begin each assignment by mapping the high-level angles of the topic, then iterate through targeted evidence gathering with Tavily search and extract. "
    "Refine your queries based on what you learn, optionally collect images, and finish with a concise, well-structured markdown brief (no code fences) containing sections, bullet points, citations, and relevant visuals."
)


def initial_user_prompt(research_prompt: str) -> str:
    return (
        "Approach the research request with a 总分加迭代 workflow: first form a high-level plan, then iterate into specifics.\n\n"
        f"Research request: {research_prompt}\n\n"
        "Principles:\n"
        "1. 先总览后细化：用 1-2 轮 Tavily search 勾勒主要视角、 stakeholders 和时间线，再逐个角度深入。\n"
        "2. 角度驱动迭代：根据前序发现动态调整关键词，必要时调用 extract 深挖高价值链接。\n"
        "3. 富媒体呈现：可在最终 markdown 中嵌入 Tavily 返回的图像（使用 ![alt](url)），并注明来源。\n\n"
        "工具说明：\n"
        "- search(keywords: list[str], num_results: int=6): Tavily 搜索（include_answer='advanced'，带图像与描述）。\n"
        "- extract(urls: list[str]): Tavily Extract（markdown 格式，适合深入阅读关键页面）。\n\n"
        "交付要求：\n"
        "- 结构化 markdown：含亮点总结、关键洞察、风险/不确定性、推荐动作等部分。\n"
        "- 引用：为数据点或引言附上易读参考（例如 [来源1]）。\n"
        "- 仅在完成时输出 markdown 正文，无额外解释。"
    )


async def run_agent(args: argparse.Namespace) -> None:
    load_dotenv()

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise SystemExit("TAVILY_API_KEY is required in the environment or .env file.")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required in the environment or .env file.")

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    client = AsyncOpenAI(api_key=openai_api_key, base_url=args.base_url or None)
    tavily_client = TavilyAsyncClient(api_key=tavily_api_key)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": initial_user_prompt(args.research_prompt)},
    ]
    tools = build_tool_definitions()

    try:
        for current_round in range(1, args.max_rounds + 1):
            allow_tools = True
            if current_round == args.max_rounds:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You have reached the maximum number of rounds. "
                            "Do not request additional tool calls. Return your final markdown summary now."
                        ),
                    }
                )
                allow_tools = False

            logging.info(
                "Round %s - latest message (%s): %s",
                current_round,
                messages[-1]["role"],
                truncate(message_content_text(messages[-1])),
            )

            api_tools = tools if allow_tools else []
            response = await client.chat.completions.create(
                model=args.model,
                messages=messages,
                tools=api_tools,
                tool_choice="auto" if allow_tools else "none",
            )

            choice = response.choices[0]
            message = choice.message
            content = message.content or ""
            logging.info(
                "Round %s - assistant reply: %s",
                current_round,
                truncate(content) if content else "<tool call>",
            )

            message_dict = message.model_dump()
            messages.append(message_dict)

            tool_calls = message.tool_calls or []
            if tool_calls:
                handler_tasks = []
                for tool_call in tool_calls:
                    function = tool_call.function
                    name = function.name
                    try:
                        arguments = json.loads(function.arguments or "{}")
                    except json.JSONDecodeError as exc:
                        raise TavilyError(f"Invalid arguments for tool '{name}': {function.arguments}") from exc

                    logging.info(
                        "Tool call requested: %s with args %s",
                        name,
                        truncate(json.dumps(arguments, ensure_ascii=False)),
                    )

                    if name == "search":
                        task = asyncio.create_task(
                            tavily_client.search(
                                TavilySearchArgs(
                                    keywords=arguments.get("keywords", []),
                                    num_results=arguments.get("num_results", 6),
                                )
                            )
                        )
                    elif name == "extract":
                        task = asyncio.create_task(
                            tavily_client.extract(
                                TavilyExtractArgs(
                                    urls=arguments.get("urls", []),
                                )
                            )
                        )
                    else:
                        raise TavilyError(f"Unknown tool requested: {name}")

                    handler_tasks.append((tool_call.id, name, task))

                for tool_call_id, name, task in handler_tasks:
                    result = await task
                    result_text = json.dumps(result, ensure_ascii=False)
                    logging.info("Tool result (%s): %s", name, truncate(result_text))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": name,
                            "content": result_text,
                        }
                    )
                continue

            # No tool calls, produce final output
            if content.strip():
                sys.stdout.write(content)
                sys.stdout.flush()
                return

        raise SystemExit("Max rounds reached without final markdown output.")
    finally:
        await tavily_client.close()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the research agent.")
    parser.add_argument("research_prompt", help="Research topic or question the agent should investigate.")
    parser.add_argument("--base-url", default="", help="Optional custom OpenAI-compatible base URL.")
    parser.add_argument("--model", default="gpt-5", help="Model name to use (default: gpt-5).")
    parser.add_argument("--max-rounds", type=int, default=15, help="Maximum interaction rounds before forcing completion.")
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO).")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run_agent(args))
    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
    except TavilyError as exc:
        logging.error("Tavily error: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logging.exception("Unexpected error")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
