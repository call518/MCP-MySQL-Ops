"""Check that server instructions replace the old MCP prompt template."""

from fastmcp import Client

from mcp_mysql_ops.mcp_main import SERVER_INSTRUCTIONS, mcp

# Claude Code truncates server instructions after this many characters.
CLAUDE_CODE_INSTRUCTIONS_LIMIT = 4096


def test_instructions_are_present_and_short():
    assert SERVER_INSTRUCTIONS.strip()
    assert len(SERVER_INSTRUCTIONS) <= CLAUDE_CODE_INSTRUCTIONS_LIMIT


async def test_client_receives_instructions_and_no_prompts():
    async with Client(mcp) as client:
        assert client.initialize_result.instructions == SERVER_INSTRUCTIONS
        assert await client.list_prompts() == []
