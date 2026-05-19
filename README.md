# csv-to-map

Render georeferenced point maps from a CSV file.

Requires [uv](https://docs.astral.sh/uv/) and a free [Mapbox token](https://account.mapbox.com).

```bash
uv add git+https://github.com/ptbrowne/csv-to-map.git
```

This installs the `csv-to-map` command.

## Quick start

```bash
csv-to-map init                            # copy the example project to ./example
csv-to-map render example/config.json     # render the example map
csv-to-map schema                         # copy config.schema.json to current directory
```

## 1. Copy the example

```bash
csv-to-map init
```

This copies a working example (CSV + config) into `./example/`.

## 2. Add your Mapbox token

Create a `.env` file in your working directory:

```
MAPBOX_TOKEN=pk.eyJ1...
```

## 3. Render the example map

```bash
csv-to-map render example/config.json
# → example/output.png
```

Open `output.png` and confirm the map looks right before continuing.

## 4. Use your own CSV

Your CSV needs at minimum a latitude and longitude column:

```csv
name,Latitude,Longitude
Reykjavík,64.1466,-21.9426
Akureyri,65.6835,-18.1105
```

Point the `csv` field in your config at it.

## 5. Edit the config

Open `example/config.json`. The most useful fields to change:

| Field | What it does |
|---|---|
| `mapbox_style` | Map background — try `streets-v12` or `satellite-streets-v12` |
| `label_col` | Which CSV column to use as point labels |
| `color_col` + `color_map` | Color points by a category column |
| `lat_col` / `lon_col` | Column names if yours differ from `Latitude` / `Longitude` |

The full config reference is in [config.schema.json](./config.schema.json). Copy it locally with `csv-to-map schema` for IDE autocompletion.

### Bounding box

By default the map zooms to fit your data points. To control the extent manually:

1. Draw a rectangle at [geojson.io](https://geojson.io)
2. Save it as `bbox.json` next to your CSV (or set the `bbox` field in your config)
