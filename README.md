# Tresbolillo Grid Generator

Tresbolillo Grid Generator is a QGIS plugin that creates staggered point grids inside polygon layers.

## Features

- Creates point grids inside polygon layers.
- Supports horizontal offset (`X`) and vertical offset (`Y`).
- Uses a user-defined spacing in meters.
- Works with projected coordinate reference systems such as UTM.
- Saves the output as an ESRI Shapefile.
- Automatically loads the generated point layer into the current QGIS project.

## Requirements

- QGIS 3.22 or newer.
- Input polygon layer must use a projected CRS in meters.
- No external Python dependencies are required.

## Usage

1. Load a polygon layer into QGIS.
2. Make sure the layer is projected in meters, for example UTM.
3. Open **Vector → Tresbolillo Grid Generator**.
4. Select the polygon layer.
5. Enter the point spacing.
6. Choose the output shapefile path.
7. Select the offset direction:
   - `X`: offsets alternating rows horizontally.
   - `Y`: offsets alternating columns vertically.
8. Click **Generate points**.

## Author

Jorge H Caal Pineda

## License

GPL-2.0-or-later
