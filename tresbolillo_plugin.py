# -*- coding: utf-8 -*-
"""
Tresbolillo Grid Generator
Author: Jorge H Caal Pineda
License: GPL-2.0-or-later
"""

import os
import traceback

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QFileDialog, QLineEdit,
    QCheckBox, QMessageBox, QGroupBox, QFrame
)

from qgis.core import (
    Qgis, QgsProject, QgsWkbTypes, QgsVectorLayer, QgsFeature, QgsField,
    QgsFields, QgsGeometry, QgsPointXY, QgsVectorFileWriter
)


class TresbolilloDialog(QDialog):
    """Main plugin dialog."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.layers = []
        self.setWindowTitle("Tresbolillo Grid Generator")
        self.setMinimumWidth(610)
        self._build_ui()
        self.refresh_layers()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Tresbolillo Grid Generator")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Create staggered point grids inside polygon layers.")
        subtitle.setStyleSheet("color: #555; margin-bottom: 6px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        group = QGroupBox("Input parameters")
        grid = QGridLayout(group)

        self.layer_combo = QComboBox()
        self.layer_combo.setMinimumWidth(330)
        self.refresh_button = QPushButton("Refresh layers")
        self.refresh_button.clicked.connect(self.refresh_layers)

        layer_box = QHBoxLayout()
        layer_box.addWidget(self.layer_combo)
        layer_box.addWidget(self.refresh_button)

        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setDecimals(3)
        self.distance_spin.setMinimum(0.001)
        self.distance_spin.setMaximum(1000000.0)
        self.distance_spin.setValue(9.0)
        self.distance_spin.setSuffix(" m")

        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["X - horizontal offset", "Y - vertical offset"])

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Example: C:/GIS/outputs/staggered_grid_9m")
        self.output_button = QPushButton("Browse")
        self.output_button.clicked.connect(self.choose_output)

        output_box = QHBoxLayout()
        output_box.addWidget(self.output_edit)
        output_box.addWidget(self.output_button)

        self.selected_only = QCheckBox("Use selected polygon features only")
        self.selected_only.setChecked(False)

        grid.addWidget(QLabel("Input polygon layer:"), 0, 0)
        grid.addLayout(layer_box, 0, 1)
        grid.addWidget(QLabel("Point spacing:"), 1, 0)
        grid.addWidget(self.distance_spin, 1, 1)
        grid.addWidget(QLabel("Output shapefile:"), 2, 0)
        grid.addLayout(output_box, 2, 1)
        grid.addWidget(QLabel("Offset direction:"), 3, 0)
        grid.addWidget(self.direction_combo, 3, 1)
        grid.addWidget(QLabel("Options:"), 4, 0)
        grid.addWidget(self.selected_only, 4, 1)

        layout.addWidget(group)

        note = QLabel(
            "Important: the input layer must use a projected coordinate reference system in meters, "
            "for example UTM. Geographic CRS layers such as WGS84 degrees are not supported."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666;")
        layout.addWidget(note)

        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.HLine)
        layout.addWidget(footer_line)

        buttons = QHBoxLayout()
        author = QLabel("by Jorge H Caal Pineda")
        author.setStyleSheet("color: #777; font-style: italic;")
        buttons.addWidget(author)
        buttons.addStretch()

        self.run_button = QPushButton("Generate points")
        self.run_button.setStyleSheet("font-weight: 600; padding: 6px 14px;")
        self.run_button.clicked.connect(self.run)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        buttons.addWidget(self.run_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def refresh_layers(self):
        self.layer_combo.clear()
        self.layers = []

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                if QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PolygonGeometry:
                    self.layers.append(layer)
                    self.layer_combo.addItem(layer.name())

        if not self.layers:
            self.layer_combo.addItem("No polygon layers loaded")

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save output point layer", "", "Shapefile (*.shp)")
        if path:
            if not path.lower().endswith(".shp"):
                path += ".shp"
            self.output_edit.setText(path)

    def _validate_inputs(self):
        if not self.layers:
            raise ValueError("No polygon layers are loaded in the current QGIS project.")

        layer = self.layers[self.layer_combo.currentIndex()]
        if not layer.isValid():
            raise ValueError("The selected input layer is not valid.")

        crs = layer.crs()
        if not crs.isValid():
            raise ValueError("The input layer does not have a valid coordinate reference system.")

        if crs.isGeographic():
            raise ValueError("The input layer uses a geographic CRS. Reproject it to UTM or another projected CRS in meters.")

        distance = float(self.distance_spin.value())
        if distance <= 0:
            raise ValueError("Point spacing must be greater than zero.")

        output = self.output_edit.text().strip()
        if not output:
            raise ValueError("Please choose an output path and name.")

        if not output.lower().endswith(".shp"):
            output += ".shp"

        output_folder = os.path.dirname(output)
        if output_folder and not os.path.isdir(output_folder):
            raise ValueError("The output folder does not exist.")

        direction = "X" if self.direction_combo.currentIndex() == 0 else "Y"
        return layer, distance, output, direction

    def _collect_polygon_geometry(self, layer):
        if self.selected_only.isChecked() and layer.selectedFeatureCount() > 0:
            features = layer.selectedFeatures()
        else:
            features = layer.getFeatures()

        union_geometry = None
        feature_count = 0

        for feature in features:
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue

            if union_geometry is None:
                union_geometry = QgsGeometry(geometry)
            else:
                union_geometry = union_geometry.combine(geometry)

            feature_count += 1

        if union_geometry is None or union_geometry.isEmpty():
            raise ValueError("No valid polygon geometry was found.")

        return union_geometry, feature_count

    def _delete_existing_shapefile(self, output):
        if os.path.exists(output):
            removed = QgsVectorFileWriter.deleteShapeFile(output)
            if not removed:
                raise ValueError("The output shapefile already exists and could not be replaced. Close the layer or choose another name.")

    def _write_output(self, output, crs, records):
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        fields.append(QgsField("Row", QVariant.Int))
        fields.append(QgsField("Column", QVariant.Int))

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        writer = QgsVectorFileWriter.create(output, fields, QgsWkbTypes.Point, crs, QgsProject.instance().transformContext(), options)

        if writer.hasError() != QgsVectorFileWriter.NoError:
            raise ValueError("Could not create output: {}".format(writer.errorMessage()))

        for point_id, row, column, x_coord, y_coord in records:
            feature = QgsFeature(fields)
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x_coord, y_coord)))
            feature.setAttributes([point_id, row, column])
            writer.addFeature(feature)

        del writer

    def run(self):
        try:
            layer, distance, output, direction = self._validate_inputs()
            self._delete_existing_shapefile(output)

            polygon_geometry, polygon_count = self._collect_polygon_geometry(layer)
            extent = polygon_geometry.boundingBox()

            xmin, xmax = extent.xMinimum(), extent.xMaximum()
            ymin, ymax = extent.yMinimum(), extent.yMaximum()
            offset = distance / 2.0

            records = []
            total_evaluated = 0
            point_id = 1
            row = 0
            y_coord = ymin

            while y_coord <= ymax:
                column = 0
                x_coord = xmin

                while x_coord <= xmax:
                    if direction == "X":
                        px = x_coord + (offset if row % 2 == 1 else 0)
                        py = y_coord
                    else:
                        px = x_coord
                        py = y_coord + (offset if column % 2 == 1 else 0)

                    total_evaluated += 1
                    point_geometry = QgsGeometry.fromPointXY(QgsPointXY(px, py))

                    if polygon_geometry.intersects(point_geometry):
                        records.append((point_id, row, column, px, py))
                        point_id += 1

                    x_coord += distance
                    column += 1

                y_coord += distance
                row += 1

            if not records:
                raise ValueError("No points were generated inside the polygon. Check the spacing, CRS, and polygon extent.")

            self._write_output(output, layer.crs(), records)

            result_layer = QgsVectorLayer(output, os.path.splitext(os.path.basename(output))[0], "ogr")
            if result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)

            self.iface.messageBar().pushMessage(
                "Tresbolillo Grid Generator",
                "Completed. Points saved: {}. by Jorge H Caal Pineda".format(len(records)),
                level=Qgis.Success,
                duration=7
            )

            QMessageBox.information(
                self,
                "Process completed",
                "Points generated successfully.\n\n"
                "Processed polygon features: {}\n"
                "Evaluated candidate points: {}\n"
                "Saved points: {}\n"
                "Output: {}\n\n"
                "by Jorge H Caal Pineda".format(polygon_count, total_evaluated, len(records), output)
            )

        except Exception as error:
            self.iface.messageBar().pushMessage(
                "Tresbolillo Grid Generator",
                str(error),
                level=Qgis.Critical,
                duration=8
            )
            QMessageBox.critical(self, "Error", "{}\n\nTechnical details:\n{}".format(str(error), traceback.format_exc()))


class TresbolilloGridGeneratorPlugin:
    """QGIS plugin entry point."""

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.plugin_dir = os.path.dirname(__file__)

    def tr(self, message):
        return QCoreApplication.translate("TresbolilloGridGenerator", message)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        self.action = QAction(QIcon(icon_path), "Tresbolillo Grid Generator", self.iface.mainWindow())
        self.action.setToolTip("Create staggered point grids inside polygons")
        self.action.triggered.connect(self.open_dialog)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("Tresbolillo Grid Generator", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginVectorMenu("Tresbolillo Grid Generator", self.action)
            self.iface.removeToolBarIcon(self.action)

    def open_dialog(self):
        self.dialog = TresbolilloDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
