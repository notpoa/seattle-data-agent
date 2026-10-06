"""The CLI shares the same contracts as HTTP and future LLM tool calls."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from .models import DatasetId, Query, Schema, Search
from .query import QueryError, compile_query
from .tools import DataUnavailable, PendingSeattleTools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seattle Data Agent tools (live integration pending)")
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Search the official Seattle catalog")
    search.add_argument("text")
    search.add_argument("--limit", type=int, default=10)
    inspect = commands.add_parser("inspect", help="Inspect an official Seattle dataset")
    inspect.add_argument("dataset_id")
    query = commands.add_parser("query", help="Execute a bounded structured query")
    query.add_argument("request_file", type=Path)
    compile_cmd = commands.add_parser("compile", help="Offline validation only; does not retrieve data")
    compile_cmd.add_argument("request_file", type=Path)
    compile_cmd.add_argument("schema_file", type=Path)
    args = parser.parse_args(argv)
    tools = PendingSeattleTools()
    try:
        if args.command == "search":
            output = tools.search(Search(text=args.text, limit=args.limit))
        elif args.command == "inspect":
            dataset_id = TypeAdapter(DatasetId).validate_python(args.dataset_id)
            output = tools.inspect(dataset_id)
        else:
            request = Query.model_validate_json(args.request_file.read_text(encoding="utf-8"))
            if args.command == "compile":
                schema = Schema.model_validate_json(args.schema_file.read_text(encoding="utf-8"))
                output = {"offline_only": True, "parameters": compile_query(request, schema)}
            else:
                output = tools.query(request)
        print(json.dumps(output, indent=2, default=str))
        return 0
    except (ValidationError, QueryError, DataUnavailable, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
