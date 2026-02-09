"""MCP 服务器创建与启动."""

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


def create_server() -> "Server":
    """创建 MCP 服务器实例."""
    if not HAS_MCP:
        raise ImportError("MCP 未安装。请运行: pip install datalabel[mcp]")

    server = Server("datalabel")

    from datalabel.mcp_server._prompts import register_prompts
    from datalabel.mcp_server._resources import register_resources
    from datalabel.mcp_server._tools import register_tools

    register_tools(server)
    register_resources(server)
    register_prompts(server)

    return server


async def serve():
    """启动 MCP 服务器."""
    if not HAS_MCP:
        raise ImportError("MCP 未安装。请运行: pip install datalabel[mcp]")

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


def main():
    """主入口."""
    import asyncio

    asyncio.run(serve())


if __name__ == "__main__":
    main()
