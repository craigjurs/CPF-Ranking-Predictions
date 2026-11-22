"""Call the repo's CFBD MCP server tools from a script.

Why this exists: the project rule is "CFBD data only through the cfbd MCP
tools". An agent chatting in Claude Code calls those tools directly. A *script*
that pulls many seasons needs the same door, so this module starts the same
server (``mcp_servers/cfbd``) over stdio and calls the same tools.

Analogy: instead of walking up to the bank teller yourself each time, you hand
the teller a written list of withdrawals. Same teller, same menu, same vault
rules (allowlist, rate limits, key never visible to us).

This module never sees, reads or sets an API key.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "mcp_servers" / "cfbd"

# A whole FBS season of games is ~900 rows, above the server's default
# 500-row cap. The cap exists to protect an agent's context window; a script
# writing to disk doesn't have one. Raising it lets us pull a season in ONE
# call instead of ~16 weekly calls, which is far kinder to the monthly quota.
BULK_MAX_ITEMS = "5000"


class CFBDToolError(RuntimeError):
    pass


@asynccontextmanager
async def cfbd_session(max_items: str = BULK_MAX_ITEMS):
    """Start the CFBD MCP server and yield a ``call(tool, **args)`` coroutine."""
    from mcp import ClientSession, StdioServerParameters, stdio_client

    env = dict(os.environ)
    env["CFBD_MAX_ITEMS"] = max_items
    params = StdioServerParameters(
        command="uv",
        args=["run", "--quiet", "--project", str(SERVER_DIR), "cfbd-mcp"],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool: str, **args) -> dict:
                args = {k: v for k, v in args.items() if v is not None}
                result = await session.call_tool(tool, args)
                payload = _payload(result)
                if "error" in payload:
                    raise CFBDToolError(f"{tool}({args}): {payload['error']}")
                if payload.get("truncated"):
                    raise CFBDToolError(f"{tool}({args}) was truncated at the row cap; narrow the query")
                return payload

            yield call


def _payload(result) -> dict:
    structured = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and structured:
        return structured.get("result", structured) if "data" not in structured and "error" not in structured else structured
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    raise CFBDToolError("tool returned no content")
