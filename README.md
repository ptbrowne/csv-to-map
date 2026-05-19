# csv-to-map

Render georeferenced point maps from a CSV file.

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv add git+https://github.com/ptbrowne/csv-to-map.git
```

## Render a map

Point `csv-to-map` at any CSV with `Latitude` and `Longitude` columns:

```csv
name,Latitude,Longitude
Reykjavík,64.1466,-21.9426
Akureyri,65.6835,-18.1105
```

```bash
csv-to-map render sites.csv
# → sites.png
```

No token needed — uses OpenStreetMap by default.

## Try a different style

```bash
csv-to-map render sites.csv --style Esri.WorldImagery
csv-to-map render sites.csv --style OpenStreetMap.Mapnik
```

Use dot notation to pick any [contextily provider](https://contextily.readthedocs.io/en/latest/providers_deepdive.html). Mapbox styles use the same notation with a free [Mapbox token](https://account.mapbox.com):

```bash
export MAPBOX_TOKEN=pk.eyJ1...
csv-to-map render sites.csv --style Mapbox.outdoors-v12
csv-to-map render sites.csv --style Mapbox.satellite-streets-v12
```

## Set a custom bounding box

By default the map zooms to fit your data. To control the extent:

1. Draw a rectangle at [geojson.io](https://geojson.io) and export it as GeoJSON
2. Pass it with `--bbox`:

```bash
csv-to-map render sites.csv --bbox my-area.json
```

## More configuration

For full control (labels, colors, lat/lon column names) use a config file. Copy the working example to get started:

```bash
csv-to-map init
csv-to-map render example/sites.csv
```

Then edit `example/config.json`. The full reference is in [config.schema.json](./config.schema.json) — copy it locally with `csv-to-map schema` for IDE autocompletion.
