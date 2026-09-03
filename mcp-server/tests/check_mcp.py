import asyncio
import json
import os

from mcp import Client


async def main() -> None:
    endpoint = os.getenv("MCP_URL", "http://127.0.0.1:8081/mcp")
    mode = os.getenv("MCP_MODE", "auto")

    async with Client(endpoint, mode=mode) as client:
        listed = await client.list_tools()
        tool_names = [tool.name for tool in listed.tools]
        if tool_names != ["search_vault"]:
            raise RuntimeError(f"Unexpected MCP tools: {tool_names}")

        called = await client.call_tool(
            "search_vault",
            {"query": "containerd snapshotter", "limit": 3},
        )
        if called.is_error:
            raise RuntimeError(f"search_vault failed: {called.content}")

        result = called.structured_content
        if not isinstance(result, dict):
            raise RuntimeError("search_vault did not return structured data")

        expected_fields = {
            "score",
            "source_path",
            "note_name",
            "heading",
            "chunk_index",
            "text",
        }
        for item in result.get("results", []):
            missing = expected_fields.difference(item)
            if missing:
                raise RuntimeError(f"Search result is missing fields: {missing}")

        empty_query = await client.call_tool(
            "search_vault",
            {"query": "   ", "limit": 3},
        )
        invalid_limit = await client.call_tool(
            "search_vault",
            {"query": "containerd", "limit": 21},
        )
        if not empty_query.is_error or not invalid_limit.is_error:
            raise RuntimeError("MCP input validation did not reject invalid data")
        empty_query_message = " ".join(
            block.text
            for block in empty_query.content
            if hasattr(block, "text")
        )
        if "non-empty" not in empty_query_message:
            raise RuntimeError("MCP did not expose the query validation message")

        summary = {
            "endpoint": endpoint,
            "client_mode": mode,
            "protocol_version": client.protocol_version,
            "server_name": (
                client.server_info.name if client.server_info else None
            ),
            "tools": [
                {
                    "name": tool.name,
                    "input_schema": tool.input_schema,
                }
                for tool in listed.tools
            ],
            "call": {
                "is_error": called.is_error,
                "query": result.get("query"),
                "count": result.get("count"),
                "results": [
                    {
                        "score": item.get("score"),
                        "source_path": item.get("source_path"),
                        "note_name": item.get("note_name"),
                        "heading": item.get("heading"),
                        "chunk_index": item.get("chunk_index"),
                        "text_length": len(item.get("text") or ""),
                    }
                    for item in result.get("results", [])
                ],
            },
            "validation": {
                "empty_query_rejected": empty_query.is_error,
                "limit_above_20_rejected": invalid_limit.is_error,
            },
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
