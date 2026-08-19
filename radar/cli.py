from __future__ import annotations

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .collect import collect_workspace
from .doctor import doctor_workspace
from .site import build_site
from .workspace import init_workspace, require_workspace


VERSION = "0.1.0a1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research-radar",
        description="Build a private, self-hosted research radar from people, topics, and sources you follow.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a private Research Radar workspace")
    init_parser.add_argument("workspace", help="Workspace directory to create")

    collect_parser = subparsers.add_parser("collect", help="Collect, deduplicate, and rank research items")
    collect_parser.add_argument("--workspace", required=True, help="Research Radar workspace")
    collect_parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable network access; requires --fixture-set synthetic",
    )
    collect_parser.add_argument(
        "--fixture-set",
        choices=("synthetic",),
        help="Use a deterministic synthetic fixture set instead of network collectors",
    )

    build_parser = subparsers.add_parser("build-site", help="Build the static local research site")
    build_parser.add_argument("--workspace", required=True, help="Research Radar workspace")

    doctor_parser = subparsers.add_parser(
        "doctor", help="Check workspace structure and configuration without network access"
    )
    doctor_parser.add_argument("--workspace", required=True, help="Research Radar workspace")

    serve_parser = subparsers.add_parser("serve", help="Serve the generated site locally")
    serve_parser.add_argument("--workspace", required=True, help="Research Radar workspace")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    return parser


def _serve(workspace_value: str | Path, host: str, port: int) -> int:
    workspace = require_workspace(workspace_value)
    site_dir = workspace / "site"
    if not (site_dir / "index.html").exists():
        build_site(workspace)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer((host, port), handler)
    shown_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print(f"Research Radar: http://{shown_host}:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Research Radar.")
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            workspace, created = init_workspace(args.workspace)
            print(f"Workspace ready: {workspace}")
            if created:
                print("Created: " + ", ".join(created))
            else:
                print("No files overwritten; existing configuration was kept.")
            return 0

        if args.command == "collect":
            result = collect_workspace(
                args.workspace,
                offline=args.offline,
                fixture_set=args.fixture_set,
            )
            print(f"Collected {result.collected} item(s); ranked {result.ranked} item(s).")
            print(f"Data: {result.ranked_path}")
            for error in result.errors:
                print(f"Warning: {error}")
            return 0 if result.ranked or not result.errors else 2

        if args.command == "build-site":
            site_dir = build_site(args.workspace)
            print(f"Site built: {site_dir / 'index.html'}")
            return 0

        if args.command == "doctor":
            report = doctor_workspace(args.workspace)
            for issue in report.issues:
                print(f"[{issue.level.upper()}] {issue.code}: {issue.message}")
            if not report.issues:
                print("Workspace check passed.")
            else:
                print(
                    f"Workspace check found {len(report.errors)} error(s) "
                    f"and {len(report.warnings)} warning(s)."
                )
            return 0 if report.ok else 2

        if args.command == "serve":
            return _serve(args.workspace, args.host, args.port)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
