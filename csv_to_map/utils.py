from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import contextily as ctx
import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.lines as mlines
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd
from adjustText import adjust_text
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
from shapely.geometry import Point, box as shapely_box

_FONT = "Helvetica Neue"
_DEFAULT_COLOR = "#e74c3c"


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env(path: str | Path = ".env") -> None:
    """Load variables from a .env file into os.environ (no-op if absent)."""
    env = Path(path)
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a map config JSON file.

    Adds a ``_base`` key with the resolved parent directory so that all
    relative paths in the config can be resolved without knowing the
    caller's working directory.
    """
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    cfg: dict[str, Any] = json.loads(path.read_text())

    if "csv" not in cfg:
        raise ValueError("Config must include a 'csv' field.")

    cfg["_base"] = str(path.parent)
    return cfg


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(cfg: dict[str, Any]) -> tuple[gpd.GeoDataFrame, list[float]]:
    """Return ``(gdf, map_bounds)`` from a loaded config dict.

    ``gdf`` is projected to EPSG:3857.  ``map_bounds`` is
    ``[minx, miny, maxx, maxy]`` in EPSG:3857 metres, derived from the
    bbox GeoJSON file when present, or from the data extent otherwise.
    """
    base = Path(cfg["_base"])
    csv_path = base / cfg["csv"]
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    lat_col = cfg.get("lat_col", "Latitude")
    lon_col = cfg.get("lon_col", "Longitude")

    raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    raw.columns = raw.columns.str.strip()
    raw[lat_col] = pd.to_numeric(raw[lat_col].astype(str).str.rstrip(","), errors="coerce")
    raw[lon_col] = pd.to_numeric(raw[lon_col].astype(str).str.rstrip(","), errors="coerce")
    raw = raw.dropna(subset=[lat_col, lon_col]).reset_index(drop=True)

    gdf = gpd.GeoDataFrame(
        raw,
        geometry=[Point(lon, lat) for lat, lon in zip(raw[lat_col], raw[lon_col])],
        crs="EPSG:4326",
    ).to_crs("EPSG:3857")

    bbox_path = base / cfg.get("bbox", "bbox.json")
    if bbox_path.exists():
        fc = json.loads(bbox_path.read_text())
        coords = fc["features"][0]["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bbox_gdf = gpd.GeoDataFrame(
            geometry=[shapely_box(min(lons), min(lats), max(lons), max(lats))],
            crs="EPSG:4326",
        ).to_crs("EPSG:3857")
        map_bounds = list(bbox_gdf.total_bounds)
    else:
        map_bounds = list(gdf.total_bounds)

    return gdf, map_bounds


# ---------------------------------------------------------------------------
# Map rendering
# ---------------------------------------------------------------------------

def _resolve_source(style: str, token: str | None) -> Any:
    if not style.startswith("Mapbox.") and "." in style:
        provider: Any = ctx.providers
        for part in style.split("."):
            try:
                provider = provider[part]
            except KeyError:
                raise ValueError(
                    f"Unknown tile provider: '{style}'. "
                    f"Check available providers with: python -c \"import contextily as ctx; print(list(ctx.providers.keys()))\""
                )
        return provider

    if not style.startswith("Mapbox.") and style in ctx.providers:
        return ctx.providers[style]

    style_id = style[len("Mapbox."):] if style.startswith("Mapbox.") else style
    if not token:
        raise ValueError(
            f"Mapbox style '{style}' requires a MAPBOX_TOKEN.\n"
            "  Set it in your environment, a .env file, or pass --token.\n"
            "  Or use a free style like 'OpenStreetMap.Mapnik' (no token needed)."
        )
    from xyzservices import TileProvider
    return TileProvider({**ctx.providers.MapBox, "id": f"mapbox/{style_id}", "accessToken": token})


def render_map(
    gdf: gpd.GeoDataFrame,
    map_bounds: list[float],
    cfg: dict[str, Any],
    token: str | None = None,
) -> plt.Figure:
    """Render a point map and return the matplotlib Figure.

    If ``cfg['output']`` is set the figure is also saved as a PNG relative
    to ``cfg['_base']``.
    """
    style = cfg.get("style", "OpenStreetMap.Mapnik")
    source = _resolve_source(style, token)

    font_size = cfg.get("font_size", 8.5)
    circle_size = cfg.get("circle_size", 6)

    label_col = cfg.get("label_col")
    color_col = cfg.get("color_col")
    color_map = cfg.get("color_map", {})
    default_color = color_map.get("__default__", _DEFAULT_COLOR)
    title = cfg.get("title", "")

    def _label(row: pd.Series, idx: int) -> str:
        if label_col and label_col in gdf.columns:
            v = row[label_col]
            return str(v) if pd.notna(v) else str(idx)
        return str(idx)

    def _color(row: pd.Series) -> str:
        if color_col and color_col in gdf.columns:
            v = row[color_col]
            return color_map.get(str(v) if pd.notna(v) else "", default_color)
        return default_color

    x_range = map_bounds[2] - map_bounds[0]
    y_range = map_bounds[3] - map_bounds[1]
    fig_width = 13
    fig_height = fig_width * y_range / x_range
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_aspect("equal")

    for _, row in gdf.iterrows():
        ax.plot(
            row.geometry.x, row.geometry.y,
            "o",
            color=_color(row),
            markersize=circle_size,
            alpha=0.92,
            markeredgecolor="white",
            markeredgewidth=1.2,
            zorder=5,
        )

    texts = []
    for idx, (_, row) in enumerate(gdf.iterrows(), start=1):
        t = ax.text(
            row.geometry.x, row.geometry.y,
            _label(row, idx),
            fontsize=font_size,
            color="#1a1a1a",
            fontfamily=_FONT,
            fontweight=500,
            zorder=6,
        )
        t.set_path_effects([pe.withStroke(linewidth=2.5, foreground="white"), pe.Normal()])
        texts.append(t)

    ax.set_xlim(map_bounds[0], map_bounds[2])
    ax.set_ylim(map_bounds[1], map_bounds[3])
    try:
        ctx.add_basemap(ax, source=source, zoom="auto", zoom_adjust=1)
    except Exception as e:
        ax.set_facecolor("#cce0f0")
        ax.text(
            0.5, 0.5, f"Tile error:\n{e}",
            transform=ax.transAxes, ha="center", va="center",
            color="red", fontsize=8,
        )

    plt.tight_layout(pad=1.2)
    adjust_text(
        texts,
        x=gdf.geometry.x.values,
        y=gdf.geometry.y.values,
        ax=ax,
        arrowprops=dict(arrowstyle="-", color="#999999", lw=0.5),
    )

    if color_col and color_map:
        handles = [
            mlines.Line2D([], [], marker="o", linestyle="none",
                          markerfacecolor=hex_, markeredgecolor="white",
                          markersize=7, label=val)
            for val, hex_ in color_map.items() if val != "__default__"
        ]
        if handles:
            ax.legend(
                handles=handles,
                loc="lower left",
                fontsize=8,
                framealpha=0.75,
                title=color_col,
                title_fontsize=8,
                prop=fm.FontProperties(family=_FONT, size=8),
            )

    scalebar = AnchoredSizeBar(
        ax.transData,
        100_000, "100 km",
        loc="lower right",
        pad=0.5,
        color="#1a1a1a",
        frameon=True,
        size_vertical=1_800,
        sep=4,
        fontproperties=fm.FontProperties(size=7.5, family=_FONT),
        label_top=False,
    )
    scalebar.patch.set(facecolor="white", alpha=0.55, linewidth=0)
    ax.add_artist(scalebar)

    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=10.5, pad=7, fontfamily=_FONT, fontweight=500, color="#1a1a1a")

    if cfg.get("output"):
        out = Path(cfg["_base"]) / cfg["output"]
        fig.savefig(out, dpi=300, bbox_inches="tight")

    return fig
