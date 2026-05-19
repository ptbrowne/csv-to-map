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

    token = args.token or os.environ.get("MAPBOX_TOKEN") or None

    input_path = Path(args.input).resolve()

    if input_path.suffix.lower() == ".csv":
        if not input_path.exists():
            _die(
                f"CSV file not found: '{input_path}'",
                "Check the path and try again.",
            )
        cfg: dict = {
            "_base": str(input_path.parent),
            "csv": input_path.name,
            "output": input_path.stem + ".png",
        }
    else:
        try:
            cfg = load_config(input_path)
        except FileNotFoundError:
            _die(
                f"Config file not found: '{input_path}'",
                "Check the path and try again.",
            )
        except ValueError as e:
            _die(str(e))
        _info(f"Config:  {input_path}")

    if args.style:
        cfg["style"] = args.style
    if args.bbox:
        cfg["bbox"] = str(Path(args.bbox).resolve())
    if args.output:
        cfg["output"] = args.output

    if not cfg.get("output"):
        _die(
            "No output file specified.",
            "Add an 'output' field to your config (e.g. \"output\": \"map.png\")\n"
            "  or pass --output map.png on the command line.",
        )

    base = Path(cfg["_base"])
    csv_path = base / cfg["csv"]
    if not csv_path.exists():
        _die(
            f"CSV file not found: '{csv_path}'",
            f"Check that 'csv' in your config points to the right file.\n"
            f"  Current value: \"{cfg['csv']}\"",
        )

    bbox_key = cfg.get("bbox", "bbox.json")
    bbox_path = Path(bbox_key) if Path(bbox_key).is_absolute() else base / bbox_key
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
        data = item.read_bytes()
        if item.name == "config.json":
            data = data.replace(b'"../config.schema.json"', b'"./config.schema.json"')
        (dest / item.name).write_bytes(data)

    schema_text = files("csv_to_map").joinpath("config.schema.json").read_bytes()
    (dest / "config.schema.json").write_bytes(schema_text)

    csv_rel = dest.relative_to(Path.cwd()) / "sites.csv"
    print(f"\n  ✔  Example copied to {dest.resolve()}/\n")
    _info("Next steps:")
    _info(f"  1. Set your Mapbox token: export MAPBOX_TOKEN=pk.eyJ1...")
    _info(f"  2. Render the example map:")
    _info(f"       csv-to-map render {csv_rel}")
    _info(f"  3. Try a different style:")
    _info(f"       csv-to-map render {csv_rel} --style satellite-streets-v12")
    _info(f"  4. Replace sites.csv with your own data.\n")


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
        help="Render a map from a CSV file or a config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  csv-to-map render sites.csv
  csv-to-map render sites.csv --style satellite-streets-v12
  csv-to-map render sites.csv --bbox my-area.json
  csv-to-map render config.json
        """,
    )
    render_p.add_argument(
        "input",
        help="Path to a CSV file or a JSON config file.",
    )
    render_p.add_argument(
        "--style",
        metavar="STYLE",
        help="Mapbox style ID (e.g. satellite-streets-v12, streets-v12). Overrides the config.",
    )
    render_p.add_argument(
        "--bbox",
        metavar="FILE",
        help="Path to a GeoJSON bounding-box file. Overrides the config.",
    )
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
