from .server import serve


def main():
    """MCP Memex - Memory extension for MCP"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Memory extension for MCP"
    )
    parser.add_argument("--index", type=str, help="Memex index directory")
    parser.add_argument("--workspace", type=str, help="Workspace directory")

    args = parser.parse_args()
    asyncio.run(serve(args.index, args.workspace))


if __name__ == "__main__":
    main()
