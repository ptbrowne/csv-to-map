from __future__ import annotations

import argparse
import os
import sys
from importlib.resources import files
from pathlib import Path

import matplotlib.pyplot as plt

from csv_to_map.utils import load_config, load_data, load_env, render_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _info(msg: str) -> None:
    print(f"  {msg}")

def _warn(msg: str) -> None:
    print(f"  ⚠  {msg}", file=sys.stderr)

def _error(msg: str) -> None:
    print(f"\n  ✖  {msg}\n", file=sys.stderr)

def _die(msg: str, hint: str | None = None) -> None:
    _error(msg)
    if hint:
        print(f"  → {hint}\n", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _cmd_render(args: argparse.Namespace) -> None:
    print()

    load_env()

    token = args.token or os.environ.get("MAPBOX_TOKEN", "")
    if not token:
        _die(
            "No Mapbox access token found.",
            "Set MAPBOX_TOKEN in your environment or in a .env file next to the config,\n"
            "  or pass it directly with --token pk.eyJ1...\n"
            "  Get a free token at https://account.mapbox.com",
        )

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        _die(
            f"Config file not found: '{args.config}'",
            "Check the path and try again.",
        )
    except ValueError as e:
        _die(str(e))

    if args.output:
        cfg["output"] = args.output

    if not cfg.get("output"):
        _die(
            "No output file specified.",
            "Add an 'output' field to your config (e.g. \"output\": \"map.png\")\n"
            "  or pass --output map.png on the command line.",
        )

    _info(f"Config:  {Path(args.config).resolve()}")

    base = Path(cfg["_base"])
    csv_path = base / cfg["csv"]
    if not csv_path.exists():
        _die(
            f"CSV file not found: '{csv_path}'",
            f"Check that 'csv' in your config points to the right file.\n"
            f"  Current value: \"{cfg['csv']}\"",
        )

    bbox_path = base / cfg.get("bbox", "bbox.json")
    if not bbox_path.exists():
        _warn(
            f"Bounding box file not found: '{bbox_path}'\n"
            "     Falling back to the data extent.\n"
            "     To set a custom bounding box, draw a rectangle at https://geojson.io,\n"
            "     export it as GeoJSON, and save it as 'bbox.json' next to your CSV\n"
            "     (or point to it with the 'bbox' key in your config)."
        )

    _info(f"CSV:     {csv_path}")

    try:
        gdf, map_bounds = load_data(cfg)
    except Exception as e:
        _die(f"Failed to load data: {e}")

    _info(f"Points:  {len(gdf)} loaded")
    _info("Rendering map …")

    try:
        fig = render_map(gdf, map_bounds, cfg, token)
        plt.close(fig)
    except Exception as e:
        _die(f"Rendering failed: {e}")

    out = Path(cfg["_base"]) / cfg["output"]
    print(f"\n  ✔  Saved to {out.resolve()}\n")


def _cmd_init(args: argparse.Namespace) -> None:
    print()
    dest = Path.cwd() / args.directory
    example_pkg = files("csv_to_map").joinpath("example")

    if dest.exists() and not args.force:
        _die(
            f"Directory '{dest}' already exists.",
            "Run with --force to overwrite, or choose a different name:\n"
            "  csv-to-map init my-project",
        )

    dest.mkdir(exist_ok=True)
    for item in example_pkg.iterdir():
        if item.name.endswith(".png"):
            continue
        (dest / item.name).write_bytes(item.read_bytes())

    print(f"\n  ✔  Example copied to {dest.resolve()}/\n")
    _info("Next steps:")
    _info(f"  1. Set your Mapbox token: export MAPBOX_TOKEN=pk.eyJ1...")
    _info(f"  2. Render the example map:")
    _info(f"       csv-to-map render {dest.relative_to(Path.cwd())}/config.json")
    _info(f"  3. Edit config.json and sites.csv to use your own data.\n")


def _cmd_schema(args: argparse.Namespace) -> None:
    print()
    dest = Path.cwd() / "config.schema.json"

    # Use importlib.resources so this works regardless of how/where the
    # package is installed (wheel, editable, zipapp, …).
    schema_text = files("csv_to_map").joinpath("config.schema.json").read_text(encoding="utf-8")

    if dest.exists() and not args.force:
        _die(
            f"config.schema.json already exists in {Path.cwd()}",
            "Run with --force to overwrite it.",
        )

    dest.write_text(schema_text, encoding="utf-8")
    print(f"\n  ✔  config.schema.json written to {dest}\n")
    _info('Point your config\'s "$schema" field at it for IDE autocompletion:')
    _info('  { "$schema": "./config.schema.json", "csv": "sites.csv", … }\n')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="csv-to-map",
        description="Render georeferenced point maps from a CSV file.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # -- render ---------------------------------------------------------------
    render_p = sub.add_parser(
        "render",
        help="Render a map from a config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  csv-to-map render config.json
  csv-to-map render config.json --output map.png
  csv-to-map render config.json --token pk.eyJ1...
        """,
    )
    render_p.add_argument("config", help="Path to the JSON config file.")
    render_p.add_argument(
        "--token",
        metavar="TOKEN",
        help="Mapbox access token. Overrides the MAPBOX_TOKEN env variable.",
    )
    render_p.add_argument(
        "--output",
        metavar="FILE",
        help="Output PNG path. Overrides the 'output' field in the config.",
    )

    # -- init -----------------------------------------------------------------
    init_p = sub.add_parser(
        "init",
        help="Copy the example project into a local directory.",
        description=(
            "Copies the bundled example (CSV, bbox GeoJSON, and config) into a local\n"
            "directory so you have a working starting point to build from."
        ),
    )
    init_p.add_argument(
        "directory",
        nargs="?",
        default="example",
        help="Destination directory (default: ./example).",
    )
    init_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the destination directory if it already exists.",
    )

    # -- schema ---------------------------------------------------------------
    schema_p = sub.add_parser(
        "schema",
        help="Copy config.schema.json into the current directory.",
        description=(
            "Copies the JSON schema for config files into the current working directory.\n"
            "Point your editor at it via the \"$schema\" key for autocompletion and validation."
        ),
    )
    schema_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite config.schema.json if it already exists.",
    )

    args = parser.parse_args()

    if args.command == "render":
        _cmd_render(args)
    elif args.command == "init":
        _cmd_init(args)
    elif args.command == "schema":
        _cmd_schema(args)
