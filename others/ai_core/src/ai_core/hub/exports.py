from __future__ import annotations

from ai_core.protocol.metadata import MetadataView


def to_openai_tools(funcs: list[MetadataView]) -> list[dict]:
    """把 MetadataView list 轉換成 OpenAI tools schema 格式（function calling）。

    每個函式對應一個 tool dict，含 name / description / parameters（從 io + examples 推斷）。
    absent=True 的函式仍轉換，description 標「metadata absent，請用 --help 或讀 source」。
    """
    pass


def to_anthropic_tools(funcs: list[MetadataView]) -> list[dict]:
    """把 MetadataView list 轉換成 Anthropic tools schema 格式（§15.3）。"""
    pass


def to_mcp(funcs: list[MetadataView]) -> dict:
    """把 MetadataView list 轉換成 MCP server descriptor 格式（§15.3）。"""
    pass


def to_agent_md(funcs: list[MetadataView]) -> str:
    """產生 AGENTS.md 內容（基於 §15.2 模板）。

    包含：可用 function 清單（呼叫方式）、進入專案後建議流程、行為規範。
    """
    pass


def to_functions_md(funcs: list[MetadataView]) -> str:
    """產生 auto/FUNCTIONS.md 內容（人類 + agent 兩用的函式清單 + 用法）。"""
    pass


def to_claude_skill(func: MetadataView) -> str:
    """產生單一函式的 Claude Code skill SKILL.md 內容（含 frontmatter）。"""
    pass
