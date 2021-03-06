#!/usr/bin/python3
#
# Polychromatic is licensed under the GPLv3.
# Copyright (C) 2020 Luke Horwell <code@horwell.me>
#
"""
This module controls the visual editor shared between layered and scripted effects.
"""

from .. import common
from .. import effects
from .. import locales
from .. import preferences as pref
from . import shared
from . import effects as controller_effects

import json
import os

from PyQt5.QtCore import Qt, QRect, QItemSelectionModel, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtWidgets import QWidget, QPushButton, QToolButton, QMessageBox, \
                            QListWidget, QTreeWidget, QLabel, QComboBox, \
                            QTreeWidgetItem, QMenu, QDialog, QDialogButtonBox, \
                            QButtonGroup, QLineEdit, QTextEdit, QCheckBox, \
                            QGroupBox, QRadioButton, QMainWindow, QAction, \
                            QDockWidget, QMenuBar, QToolBar, QStatusBar, \
                            QTableWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Visual mode within the WebView editor
VISUAL_MODE_ADD = 1
VISUAL_MODE_DEL = 2
VISUAL_MODE_PICK = 3


class VisualEffectEditor(shared.TabData):
    """
    Editor for modifying layered or animated effects. The GUI is shared between
    a "Layered" and "Sequence" type of effect.
    """
    def __init__(self, appdata, fileman, save_path):
        """
        Load the effect from file for editing and show the editor window. The
        file is expected to have been initialized (via EffectMetadataEditor) first.

        Params:
            appdata         ApplicationData() object
            fileman         fileman.FlatFileManagement() based object
            effect_path     Path to save data
        """
        super().__init__(appdata)

        self.fileman = fileman
        self.save_path = save_path
        self.data = fileman.get_item(save_path)
        self.effect_type = self.data["type"]
        self.modified = False
        self.alive = True
        self.current_colour = "#00FF00"
        self.current_tool = VISUAL_MODE_ADD
        self.layer_labels = self._get_layer_labels()
        self.webview_zoom_level = 1.0

        # Fail if the file moved, or was deleted
        if type(self.data) != dict:
            self._show_file_error()
            return

        # Layered Effects Only
        self.current_layer = 0

        # Sequence Effects Only
        self.current_frame = 0

        # Load window
        self.window = shared.get_ui_widget(appdata, "editor", QMainWindow)
        self.window.closeEvent = self.closeEvent
        self.menubar = self.window.findChild(QMenuBar, "MenuBar")
        self.statusbar = self.window.findChild(QStatusBar, "StatusBar")
        self.toolbar = self.window.findChild(QToolBar, "MainToolbar")

        # Visual Editor ("webview")
        self.webview = self.window.findChild(QWebEngineView, "MatrixWebView")
        self.action_info_graphic = self.window.findChild(QAction, "MapGraphic")
        self.action_info_grid_x = self.window.findChild(QAction, "MapDimensionX")
        self.action_info_grid_y = self.window.findChild(QAction, "MapDimensionY")

        # -- DeviceRender() is assigned to this variable in init_controls()
        self.device_renderer = None

        # Device (live preview)
        self.live_preview = self.appdata.preferences["editor"]["live_preview"]
        self.device = None
        self.device_object = None
        self.init_device_preview()

        # Assign widgets to variables
        # -- Menu Bar/Toolbar - File
        self.action_save_apply = self.window.findChild(QAction, "actionSaveApply")
        self.action_save = self.window.findChild(QAction, "actionSave")
        self.action_revert = self.window.findChild(QAction, "actionRevert")
        self.action_exit = self.window.findChild(QAction, "actionExit")

        # -- Menu Bar/Toolbar - Edit
        # -- -- Layer only
        self.action_new_layer = self.window.findChild(QAction, "actionNew_Layer")
        self.action_delete_layer = self.window.findChild(QAction, "actionDelete_Layer")
        self.action_duplicate_layer = self.window.findChild(QAction, "actionDuplicate_Layer")
        self.action_layer_up = self.window.findChild(QAction, "actionMove_Layer_Up")
        self.action_layer_down = self.window.findChild(QAction, "actionMove_Layer_Down")

        # -- -- Frame only
        self.action_new_frame = self.window.findChild(QAction, "actionNew_Frame")
        self.action_delete_frame = self.window.findChild(QAction, "actionDelete_Frame")
        self.action_clone_frame = self.window.findChild(QAction, "actionClone_Frame")
        self.action_frame_left = self.window.findChild(QAction, "actionMove_Frame_Left")
        self.action_frame_right = self.window.findChild(QAction, "actionMove_Frame_Right")

        self.action_shift_left = self.window.findChild(QAction, "actionShift_Left")
        self.action_shift_right = self.window.findChild(QAction, "actionShift_Right")
        self.action_shift_up = self.window.findChild(QAction, "actionShift_Up")
        self.action_shift_down = self.window.findChild(QAction, "actionShift_Down")
        self.action_edit_metadata = self.window.findChild(QAction, "actionEditMetadata")
        self.action_edit_triggers = self.window.findChild(QAction, "actionEditTriggers")

        # -- Menu Bar/Toolbar - View
        self.action_view_device_graphic = self.window.findChild(QAction, "actionShow_as_Device_Graphic")
        self.action_view_grid = self.window.findChild(QAction, "actionShow_as_Grid")
        self.action_zoom_in = self.window.findChild(QAction, "actionZoomIn")
        self.action_zoom_out = self.window.findChild(QAction, "actionZoomOut")
        self.action_zoom_reset = self.window.findChild(QAction, "actionZoomReset")
        self.action_dock_reset = self.window.findChild(QAction, "actionResetDocks")

        # -- Menu Bar/Toolbar - Tools
        self.tool_draw = self.window.findChild(QAction, "actionDraw")
        self.tool_eraser = self.window.findChild(QAction, "actionEraser")
        self.tool_picker = self.window.findChild(QAction, "actionColourPicker")

        # -- Menu Bar - Help
        self.action_help_online = self.window.findChild(QAction, "actionOnlineHelp")
        self.action_help_website = self.window.findChild(QAction, "actionWebsite")
        self.action_help_relnotes = self.window.findChild(QAction, "actionReleaseNotes")
        self.action_help_report_bug = self.window.findChild(QAction, "actionReportBug")
        self.action_help_donate = self.window.findChild(QAction, "actionDonate")
        self.action_help_about = self.window.findChild(QAction, "actionAbout")

        # -- Docks
        self.dock_layers = self.window.findChild(QDockWidget, "LayersDock")
        self.dock_properties = self.window.findChild(QDockWidget, "LayerPropertiesDock")
        self.dock_colours = self.window.findChild(QDockWidget, "ColoursDock")
        self.dock_frames = self.window.findChild(QDockWidget, "FramesDock")

        # -- Layer Widgets
        self.layer_tree = self.window.findChild(QTreeWidget, "LayerTree")
        self.btn_layer_delete = self.window.findChild(QToolButton, "LayerDelete")
        self.btn_layer_duplicate = self.window.findChild(QToolButton, "LayerDuplicate")
        self.btn_layer_move_down = self.window.findChild(QToolButton, "LayerMoveDown")
        self.btn_layer_move_up = self.window.findChild(QToolButton, "LayerMoveUp")
        self.btn_layer_new = self.window.findChild(QToolButton, "LayerNew")

        # -- Frame Widgets
        self.frame_table = self.window.findChild(QTableWidget, "FramesTable")
        self.btn_frame_new = self.window.findChild(QToolButton, "NewFrame")
        self.btn_frame_delete = self.window.findChild(QToolButton, "DeleteFrame")
        self.btn_frame_clone = self.window.findChild(QToolButton, "CloneFrame")
        self.btn_frame_move_left = self.window.findChild(QToolButton, "MoveFrameLeft")
        self.btn_frame_move_right = self.window.findChild(QToolButton, "MoveFrameRight")

        # Font should be applied to dock widgets
        self.docks = [self.dock_layers, self.dock_properties, self.dock_colours, self.dock_frames]
        if self.appdata.system_qt_theme:
            for dock in self.docks:
                font = QFont("Play", 10, 0)
                dock.setFont(font)

        # Connect buttons/actions
        # -- File
        self.action_save_apply.triggered.connect(self.save_and_close)
        self.action_save.triggered.connect(self.save_now)
        self.action_revert.triggered.connect(self.reload_from_file)
        self.action_exit.triggered.connect(self.closeEvent)

        # -- Edit (Layered)
        self.action_new_layer.triggered.connect(self.new_layer)
        self.action_delete_layer.triggered.connect(self.delete_layer)
        self.action_duplicate_layer.triggered.connect(self.duplicate_layer)
        self.action_layer_up.triggered.connect(self.raise_layer)
        self.action_layer_down.triggered.connect(self.lower_layer)

        self.btn_layer_new.triggered.connect(self.new_layer)
        self.btn_layer_delete.triggered.connect(self.delete_layer)
        self.btn_layer_duplicate.triggered.connect(self.duplicate_layer)
        self.btn_layer_move_up.triggered.connect(self.raise_layer)
        self.btn_layer_move_down.triggered.connect(self.lower_layer)

        # -- Edit (Sequence)
        self.action_new_frame.triggered.connect(self.new_frame)
        self.action_delete_frame.triggered.connect(self.delete_frame)
        self.action_clone_frame.triggered.connect(self.clone_frame)
        self.action_frame_left.triggered.connect(self.shift_frame_left)
        self.action_frame_right.triggered.connect(self.shift_frame_right)

        self.btn_frame_new.triggered.connect(self.new_frame)
        self.btn_frame_delete.triggered.connect(self.delete_frame)
        self.btn_frame_clone.triggered.connect(self.clone_frame)
        self.btn_frame_move_left.triggered.connect(self.shift_frame_left)
        self.btn_frame_move_right.triggered.connect(self.shift_frame_right)

        # -- Edit (Shared)
        self.action_shift_left.triggered.connect(self.shift_all_left)
        self.action_shift_right.triggered.connect(self.shift_all_right)
        self.action_shift_up.triggered.connect(self.shift_all_up)
        self.action_shift_down.triggered.connect(self.shift_all_down)
        self.action_edit_metadata.triggered.connect(self.edit_metadata)
        self.action_edit_triggers.triggered.connect(self.edit_triggers)

        # -- View
        self.action_view_device_graphic.triggered.connect(self.view_device_graphic)
        self.action_view_grid.triggered.connect(self.view_device_grid)
        self.action_zoom_in.triggered.connect(self.zoom_in)
        self.action_zoom_out.triggered.connect(self.zoom_out)
        self.action_zoom_reset.triggered.connect(self.zoom_reset)
        self.action_dock_reset.triggered.connect(self.dock_reset)

        # -- Tools
        self.tool_draw.triggered.connect(self.select_mode_draw)
        self.tool_eraser.triggered.connect(self.select_mode_eraser)
        self.tool_picker.triggered.connect(self.select_mode_picker)

        # -- Help
        menubar = self.appdata.menubar
        self.action_help_online.triggered.connect(menubar.online_help)
        self.action_help_website.triggered.connect(menubar.polychromatic_website)
        self.action_help_relnotes.triggered.connect(menubar.polychromatic_release_notes)
        self.action_help_report_bug.triggered.connect(menubar.polychromatic_report_bug)
        self.action_help_donate.triggered.connect(menubar.polychromatic_donate)
        self.action_help_about.triggered.connect(menubar.about_polychromatic)

        # Widgets
        self.frame_table.itemSelectionChanged.connect(self.open_frame)

        # Menu Bar Icons
        if not appdata.system_qt_theme:
            print("stub:menu bar icons")

        # Showtime!
        self._init_window()
        self.init_controls()

    def _init_window(self):
        """
        Prepare the window for the type of effect that'll be edited.

        Layered Effects use these docks/interface elements:
            - Layers
            - Properties

        Sequence Effects use:
            - Colours
            - Frames
        """
        layered_effect = self.data["type"] == effects.TYPE_LAYERED
        sequence_effect = self.data["type"] == effects.TYPE_SEQUENCE

        if layered_effect:
            # Remove frame-specific options
            self.tool_picker.deleteLater()
            self.action_new_frame.deleteLater()
            self.action_delete_frame.deleteLater()
            self.action_clone_frame.deleteLater()
            self.action_frame_left.deleteLater()
            self.action_frame_right.deleteLater()

        elif sequence_effect:
            # Remove layer-specific options
            self.action_new_layer.deleteLater()
            self.action_delete_layer.deleteLater()
            self.action_duplicate_layer.deleteLater()
            self.action_layer_up.deleteLater()
            self.action_layer_down.deleteLater()
            self.dock_layers.deleteLater()
            self.dock_properties.deleteLater()

        # Adjust docks for optimum space
        if layered_effect:
            self.dock_layers.adjustSize()
            self.dock_properties.adjustSize()
        elif sequence_effect:
            self.dock_colours.adjustSize()
            self.dock_frames.adjustSize()

    def init_controls(self):
        """
        Populate the controls for the effect being loaded.
        """
        # Reset session variables
        self.modified = False
        self.current_layer = 0
        self.current_frame = 0

        # Prepare visual editor
        rows = self.data["map_rows"]
        cols = self.data["map_cols"]
        graphic_filename = self.data["map_graphic"]
        self.device_renderer = DeviceRenderer(self.appdata, self, self.webview, self.init_editor, graphic_filename, rows, cols)
        self.select_mode_draw()
        graphic_name = self.device_renderer.graphic_name

        self.action_info_graphic.setText(graphic_name)
        self.action_info_grid_x.setText(self._("Columns: []").replace("[]", str(rows)))
        self.action_info_grid_y.setText(self._("Rows: []").replace("[]", str(cols)))

    def init_editor(self):
        """
        Populate the visual editor (grid/graphic) when the webpage is ready.
        """
        layered_effect = self.data["type"] == effects.TYPE_LAYERED
        sequence_effect = self.data["type"] == effects.TYPE_SEQUENCE

        self.dbg.stdout("Reading data...", self.dbg.action, 1)

        if layered_effect:
            # Populate layer dock
            self.load_layers()

            # Open the first layer and populate properties dock
            self.open_layer()

        elif sequence_effect:
            # Populate colours dock
            self.load_colours()

            # Populate frame dock
            self.load_frames()
            self.open_frame()

        self.dbg.stdout("Load complete.", self.dbg.success, 1)
        self.window.show()

    def init_device_preview(self):
        """
        Initalize the objects for previewing the device on physical hardware.
        """
        if not self.live_preview:
            return

        device_name = self.data["map_device"]
        self.dbg.stdout("Preparing live preview on '{0}'...".format(device_name), self.dbg.action, 1)
        self.device = self.middleman.get_device_by_name(device_name)

        # Inform the user if attempting to load non-existent device
        if not self.device:
            self.dbg.stdout("Device not found! No preview.", self.dbg.error, 1)
            self.widgets.open_dialog(self.widgets.dialog_warning,
                                        self._("Missing Device"),
                                        self._("The device '[]' is assigned to this effect, but was not detected on this system.").replace("[]", device_name),
                                        self._("Live preview has been disabled for this session."))
            return

        self.device_object = self.middleman.get_device_object(self.device["backend"], self.device["uid"])

        # Inform the user if attempting to use an unsupported device
        if self.device_object == None:
            self.dbg.stdout("Device not supported! No preview.", self.dbg.error, 1)
            self.widgets.open_dialog(self.widgets.dialog_error,
                                     self._("File Error"),
                                     self._("The device '[]' is assigned to this effect, but does not support individual addressable LEDs.").replace("[]", device_name),
                                     self._("Live preview has been disabled for this session."))
            self.device = None
            return

        # Inform user if there's a problem initalizing the device object
        if type(self.device_object) == str:
            self.dbg.stdout("Device error! No preview.", self.dbg.error, 1)
            self.widgets.open_dialog(self.widgets.dialog_error,
                                     self._("Backend Error"),
                                     self._("An error occurred while initalizing '[]' for live preview.").replace("[]", device_name),
                                     self._("Live preview has been disabled for this session."),
                                     self.device_object)
            self.device = None
            self.device_object = None
            return

        self.dbg.stdout("Previewing effect '{0}' on device '{1}'.".format(self.data["name"], device_name), self.dbg.success, 1)

    def closeEvent(self, event=None):
        """
        Before closing the editor, make sure any unsaved changes are saved.
        """
        if self.modified:
            def _do_not_save():
                self.modified = False
                return self.closeEvent()

            def _do_save():
                return self.save_and_close()

            self.widgets.open_dialog(self.widgets.dialog_warning,
                                     self._("Unsaved Changes"),
                                     self._("This effect was modified. Would you like to save these changes?"),
                                     None, None,
                                     [QMessageBox.Save, QMessageBox.Discard, QMessageBox.Cancel],
                                     QMessageBox.Save,
                                     {
                                        QMessageBox.Save: _do_save,
                                        QMessageBox.Discard: _do_not_save
                                     })
            if event:
                event.ignore()
            return

        # If live preview was active, restore original state
        if self.live_preview and self.device:
            self.dbg.stdout("Restoring original device state...", self.dbg.action, 1)
            for zone in self.device["zones"]:
                self.middleman.replay_active_effect(self.device["backend"], self.device["uid"], zone)

        # Close window and allow another editor to open again
        self.alive = False
        if event:
            event.accept()
        else:
            self.window.deleteLater()

    def _get_layer_labels(self):
        """
        Return a dictionary of human readable labels for layered effects.
        """
        return {
            effects.LAYER_STATIC: self._("Static"),
            effects.LAYER_GRADIENT: self._("Gradient"),
            effects.LAYER_PULSING: self._("Pulsing"),
            effects.LAYER_WAVE: self._("Wave"),
            effects.LAYER_SPECTRUM: self._("Spectrum"),
            effects.LAYER_CYCLE: self._("Cycling"),
            effects.LAYER_SCRIPT: self._("Run Scripted Effect")
        }

    def _show_file_error(self):
        """
        Alias to the _show_file_error() function from the Effects tab.
        """
        self.appdata.tab_effects._show_file_error()
        self.closeEvent()

    def save_and_close(self):
        """
        Saves the data in memory to disk, then closes the editor.
        """
        success = self.save_now()

        if success:
            self.closeEvent()

    def save_now(self):
        """
        Saves the data in memory to disk.
        """
        self.dbg.stdout("Saving Effect: " + self.save_path, self.dbg.action, 1)
        success, save_path = self.fileman.save_item(self.data, self.save_path)

        if not success:
            self.widgets.open_dialog(self.widgets.dialog_error,
                                     self._("Save Error"),
                                     self._("Save failed. Please check the permissions and try again."))
            return False

        self.modified = False
        self.save_path = save_path
        self.statusbar.showMessage(self._("Saved to: []").replace("[]", save_path))
        return True

    def reload_from_file(self):
        """
        Prompts the user if they're happy to dispose of the data in memory in
        favour of the data stored on disk.
        """
        def _do_reload():
            """
            Hot reload the editor from the beginning via the effects class.
            """
            self.dbg.stdout("Reloading effect from disk...", self.dbg.action, 1)
            self.modified = False
            self.alive = False
            self.appdata.tab_effects.open_file(self.save_path)
            self.appdata.tab_effects.edit_file()
            self.closeEvent()

        buttons = [QMessageBox.Yes, QMessageBox.No]
        actions = {
            QMessageBox.Yes: _do_reload
        }
        self.widgets.open_dialog(self.widgets.dialog_warning,
                                 self._("Revert"),
                                 self._("Reload the effect from disk? Any unsaved data will be lost!"),
                                 None, None, buttons, QMessageBox.Yes, actions)

    # ----------------------------
    # Common
    # ----------------------------
    def _redraw_editor(self):
        """
        Alias to redraw the effect on the editor, based on the effect type.
        """
        aliases = {
            effects.TYPE_LAYERED: self.open_layer,
            effects.TYPE_SEQUENCE: self.open_frame
        }
        aliases[self.effect_type]()

    def shift_all_left(self):
        """
        Move all the LEDs by -1 on the X-axis.
        """
        if effects.TYPE_LAYERED:
            pass
        elif effects.TYPE_SEQUENCE:
            pass

    def shift_all_right(self):
        """
        Move all the LEDs by +1 on the X-axis.
        """
        if effects.TYPE_LAYERED:
            pass
        elif effects.TYPE_SEQUENCE:
            pass

    def shift_all_up(self):
        """
        Move all the LEDs by +1 on the Y-axis.
        """
        if effects.TYPE_LAYERED:
            pass
        elif effects.TYPE_SEQUENCE:
            pass

    def shift_all_down(self):
        """
        Move all the LEDs by -1 on the Y-axis.
        """
        if effects.TYPE_LAYERED:
            pass
        elif effects.TYPE_SEQUENCE:
            pass

    def edit_metadata(self):
        """
        Opens a modal metadata window and reloads the effect upon accepting the
        changes.
        """
        def _metadata_changed(newdata):
            self.dbg.stdout("Metadata changed, reloading device...")
            self.data = newdata

        def _metadata_closed(result):
            self.window.setEnabled(True)

        self.window.setEnabled(False)
        self.metadata_editor = controller_effects.EffectMetadataEditor(self.appdata, self.data, _metadata_changed)
        self.metadata_editor.dialog.finished.connect(_metadata_closed)

    def edit_triggers(self):
        """
        Opens a window to quickly create, modify or delete a trigger that
        uses this effect.
        """
        pass

    def dock_reset(self):
        """
        Reset the docks to their original positions.
        """
        pass

    def _live_preview_failed(self, e):
        """
        Inform the user the live preview failed.

        Params:
            e       Raw exception
        """
        self.dbg.stdout("Failed to preview on device! Exception: ", self.dbg.error)
        self.dbg.stdout(common.get_exception_as_string(e) + "\n", self.dbg.error)

        # Disable live preview for session
        self.device = None
        self.device_object = None
        self.widgets.open_dialog(self.widgets.dialog_error,
                                 self._("Backend Error"),
                                 self._("An error occurred while sending the frame to the hardware."),
                                 self._("Live preview has been disabled for this session."),
                                 common.get_exception_as_string(e))

    # ----------------------------
    # Tools
    # ----------------------------
    def _select_mode_common(self):
        self.tool_draw.setChecked(False)
        self.tool_eraser.setChecked(False)
        self.tool_picker.setChecked(False)

    def select_mode_draw(self):
        """
        Select tool 1 for the visual editor.

            Layered     Assign LEDs/keys to the current layer
            Sequence    Draw colours on LEDs/keys
        """
        self.current_tool = VISUAL_MODE_ADD
        self.device_renderer.set_mode(VISUAL_MODE_ADD)
        self._select_mode_common()
        self.tool_draw.setChecked(True)

    def select_mode_eraser(self):
        """
        Select tool 2 for the visual editor.

            Layered     Unassign LEDs/keys from the current layer
            Sequence    Clear colour on LEDs/keys
        """
        self.current_tool = VISUAL_MODE_DEL
        self.device_renderer.set_mode(VISUAL_MODE_DEL)
        self._select_mode_common()
        self.tool_eraser.setChecked(True)

    def select_mode_picker(self):
        """
        Select tool 3 for the visual editor.

            Layered     n/a - Unused
            Sequence    Grab the colour on an LED/key
        """
        self.current_tool = VISUAL_MODE_PICK
        self.device_renderer.set_mode(VISUAL_MODE_PICK)
        self._select_mode_common()
        self.tool_picker.setChecked(True)

    # ----------------------------
    # Visual Editor (WebView)
    # ----------------------------
    def _update_zoom_controls(self):
        """
        Enable/disable the zoom controls accordingly, to avoid going under or
        over the min/max zoom levels
        """
        self.webview.setZoomFactor(self.webview_zoom_level)
        min_zoom = 0.25
        max_zoom = 3

        self.action_zoom_in.setEnabled(True)
        self.action_zoom_out.setEnabled(True)

        if self.webview_zoom_level <= min_zoom:
            self.action_zoom_out.setEnabled(False)

        if self.webview_zoom_level >= max_zoom:
            self.action_zoom_in.setEnabled(False)

    def zoom_in(self):
        """
        Increase the zoom of the visual editor viewport.
        """
        self.webview_zoom_level += 0.25
        self._update_zoom_controls()

    def zoom_out(self):
        """
        Decrease the zoom of the visual editor viewport.
        """
        self.webview_zoom_level -= 0.25
        self._update_zoom_controls()

    def zoom_reset(self):
        """
        Reset the zoom of the visual editor viewport.
        """
        self.webview_zoom_level = 1.0
        self._update_zoom_controls()

    def view_device_graphic(self):
        """
        Temporarily switch the visual editor graphic to the hardware graphic,
        if available.
        """
        if not self.data["map_graphic"]:
            self.action_view_device_graphic.setChecked(False)
            self.widgets.open_dialog(self.widgets.dialog_generic,
                                     self.action_view_device_graphic.text(),
                                     self._("There is no graphic assigned to this device: []").replace("[]", self.device["name"]),
                                     self._("Specify a graphic by editing the metadata, and then this option will be available."))
            return

        self.device_renderer = DeviceRenderer(self.appdata, self, self.webview, self.init_editor, self.data["map_graphic"], self.data["map_rows"], self.data["map_cols"])
        self.select_mode_draw()
        self.statusbar.showMessage(self._("Temporarily changed the graphic. To make permanent, edit the metadata."), 5000)

    def view_device_grid(self):
        """
        Temporarily switch the visual editor graphic to a grid, which allows
        drawing on any device.
        """
        self.device_renderer = DeviceRenderer(self.appdata, self, self.webview, self.init_editor, "", self.data["map_rows"], self.data["map_cols"])
        self.select_mode_draw()
        self.statusbar.showMessage(self._("Temporarily changed the graphic. To make permanent, edit the metadata."), 5000)

    # ----------------------------
    # Specific to Layered Effects
    # ----------------------------
    def load_layers(self):
        """
        Clears and populates layers on the dock controls.
        """
        pass

    def open_layer(self):
        """
        Draw the selected layer for editing, and update the properties dock.

        This will redraw the colours in the visual editor and physical device
        (if preview is enabled) based on the currently selected layer.
        """
        pass

    def new_layer(self):
        """
        Create a new layer using default values and loads it.
        """
        pass

    def delete_layer(self):
        """
        Prompts for confirmation before deleting a layer.
        """
        pass

    def duplicate_layer(self):
        """
        Creates a new layer inheriting the data for the currently selected one
        and loads it.
        """
        pass

    def raise_layer(self):
        """
        Moves the layer up by one and refreshes the visual editor.
        """
        pass

    def lower_layer(self):
        """
        Moves the layer down by one and refreshes the visual editor.
        """
        pass

    def assign_key_to_layer(self, x, y):
        """
        User clicks on a key/LED in the visual editor. Add this to the layer
        and update the device preview.
        """
        pass

    def unassign_key_to_layer(self, x, y):
        """
        User clicks on a key/LED in the visual editor. Remove this from the
        layer and update the device preview.
        """
        pass

    # ----------------------------
    # Specific to Sequence Effects
    # ----------------------------
    def load_frames(self):
        """
        Clears and populates frames on the dock controls.
        """
        table = self.frame_table
        frame_count = len(self.data["frames"])

        table.setColumnCount(frame_count)
        for frame in range(0, frame_count):
            table.setColumnWidth(frame, 64)

        # Make sure there is one frame
        if frame_count == 0:
            table.insertColumn(0)
            self.data["frames"] = [{}]

        # Select first frame if deselected
        if len(table.selectedIndexes()) == 0:
            table.setSelection(QRect(0, 0, 1, 1), QItemSelectionModel.Select)

    def open_frame(self):
        """
        Open the selected frame for editing.

        This will redraw the colours in the visual editor and physical device
        (if preview is enabled) based on the currently selected frame.
        """
        fx = self.device_object
        self.device_renderer.clear()

        if fx:
            fx.clear()

        index = self.frame_table.selectedIndexes()[0].column()
        self.current_frame = index
        total_X = self.data["map_cols"]
        total_Y = self.data["map_rows"]

        # Make sure the frame dictionary keys have parent (x-axis) keys
        for x in range(0, total_X):
            try:
                self.data["frames"][index][str(x)]
            except KeyError:
                self.data["frames"][index][str(x)] = {}

        frame = self.data["frames"][index]

        # Draw frame on editor (and optionally physical hardware)
        for x in frame.keys():
            for y in frame[x].keys():
                try:
                    hex_value = frame[str(x)][str(y)]
                    self.device_renderer.set_pos(x, y, hex_value)
                except KeyError:
                    # Expected, no data stored for this position
                    continue

                if fx:
                    try:
                        rgb = fx.hex_to_rgb(hex_value)
                        fx.set(int(x), int(y), rgb[0], rgb[1], rgb[2])
                    except Exception as e:
                        self._live_preview_failed(e)

        if fx:
            fx.draw()

    def load_colours(self):
        """
        Populate the colour dock and functions associated for quickly setting
        the brush (draw) colour.
        """
        pass

    def new_frame(self):
        """
        Creates a blank frame after the current frame, and loads it.
        """
        pass

    def delete_frame(self):
        """
        Prompts for confirmation before deleting a frame.
        """
        pass

    def clone_frame(self):
        """
        Creates a new frame inheriting the data for the currently selected one
        and loads it.
        """
        pass

    def shift_frame_left(self):
        """
        Moves the frame to the left by one and refreshes the visual editor.
        """
        pass

    def shift_frame_right(self):
        """
        Moves the frame to the right by one and refreshes the visual editor.
        """
        pass

    def draw_LED_to_frame(self, x, y):
        """
        User draws a new position on the current frame.
        """
        self.data["frames"][self.current_frame][str(x)][str(y)] = self.current_colour

        if self.device_object:
            try:
                rgb = self.device_object.hex_to_rgb(self.current_colour)
                self.device_object.set(int(x), int(y), rgb[0], rgb[1], rgb[2])
                self.device_object.draw()
            except Exception as e:
                self._live_preview_failed(e)

        self.modified = True
        self.dbg.stdout("Set LED ({0},{1}) to {2}".format(x, y, self.current_colour), self.dbg.debug, 1)

    def erase_LED_from_frame(self, x, y):
        """
        User erases a position on the current frame.
        """
        try:
            del(self.data["frames"][self.current_frame][str(x)][str(y)])
        except KeyError:
            self.statusbar.showMessage(self._("This LED is empty - nothing to erase here!"), 5000)
            return

        if self.device_object:
            try:
                self.device_object.set(int(x), int(y), 0, 0, 0)
                self.device_object.draw()
            except Exception as e:
                self._live_preview_failed(e)

        self.modified = True
        self.dbg.stdout("Erase LED ({0},{1})".format(x, y), self.dbg.debug, 1)

    def pick_LED_colour_from_frame(self, x, y):
        """
        User picks a colour from the current frame.
        """
        try:
            self.current_colour = self.data["frames"][self.current_frame][str(x)][str(y)]
            self.statusbar.showMessage(self._("Current colour set to '[]'").replace("[]", self.current_colour), 5000)
            self.select_mode_draw()
        except KeyError:
            self.statusbar.showMessage(self._("This LED is empty - no colour to pick here!"), 5000)
            return

        self.dbg.stdout("Pick LED ({0},{1}). Current colour changed to {2}".format(x, y, self.current_colour), self.dbg.debug, 1)


class DeviceRenderer(shared.TabData):
    """
    Responsible for the input/output of the device graphic or grid layout.
    """
    def __init__(self, appdata, editor, webview, ready_fn, map_graphic, map_rows, map_cols):
        """
        Params:
            appdata         ApplicationData() object
            editor          VisualEffectEditor() object
            webview         QWebEngineView object
            ready_fn        Run this function as soon as the editor has loaded
            map_graphic     Filename of graphic to use. Blank string indicates to use grid.
            map_rows        Number of rows for device
            map_cols        Number of cols for device
        """
        self.appdata = appdata
        super().__init__(appdata)
        self.editor = editor
        self.webview = webview
        self.loaded = False
        self.ready_fn = ready_fn
        self.use_native_cursor = appdata.preferences["editor"]["system_cursors"]

        self.device_map = effects.DeviceMapGraphics(appdata)
        self.map_path = os.path.join(common.paths.data_dir, "devicemaps")
        self.graphic_filename = map_graphic
        self.graphic_name = self.device_map.get_graphic_name_from_filename(map_graphic)
        self.rows = map_rows
        self.cols = map_cols

        # Wait until the webview has fully loaded, then load the graphic.
        self.webview.loadFinished.connect(self.ready)
        url = QUrl("file://" + os.path.join(common.paths.data_dir, "qt", "editor.html"))

        # Reload if web view previously initalized
        if self.webview.page().url() == url:
            self.webview.reload()
        else:
            # First time opening this editor session
            self.webview.load(url)

        # Connect signals
        self.webview.titleChanged.connect(self._cb_title_changed)

    def ready(self, ok=True):
        """
        As soon as the WebView has fully loaded, load the graphic ready for
        editing, as well as the ready_fn.
        """
        self.loaded = True
        if not ok:
            self.widgets.open_dialog(self.widgets.dialog_error,
                                     self._("Controller Error"),
                                     self._("Failed to load the Qt Web Engine. Unfortunately, editing won't be possible."),
                                     self._("Make sure the application (and its dependencies) are installed and configured correctly."))
            self.editor.window.close()

        # Load the SVG into the viewport
        name = self.graphic_name.replace("'", "&quot;")
        svg = self._get_graphic_svg().replace("'", "&quot;")
        self.webview.page().runJavaScript("loadSVG('{0}', '{1}'); clearLED()".format(name, svg))

        # Set mode
        self.set_mode(VISUAL_MODE_ADD)

        # Run ready function
        if self.ready_fn:
            self.ready_fn()

    def _get_graphic_svg(self):
        """
        Returns the SVG of the device's matrix represented as a 'pretty' graphic.
        """
        if not self.graphic_filename:
            return self._generate_grid_svg()

        # Update UI elements
        self.editor.action_view_device_graphic.setChecked(True)
        self.editor.action_view_grid.setChecked(False)

        # Verify the device map exists, then load it!
        graphic_path = os.path.join(self.map_path, self.graphic_filename)

        if not os.path.exists(graphic_path):
            self.dbg.stdout("Graphic does not exist: '{0}'. Using grid as fallback!".format(graphic_path), self.dbg.error)
            self.widgets.open_dialog(self.widgets.dialog_warning,
                                     self._("Missing File"),
                                     self._("This effect was mapped with a graphic named '[]' which wasn't found on this system.".replace("[]", self.graphic_filename)),
                                     self._("The grid will be used instead. A different graphic can be chosen by editing the metadata."))
            return self._generate_grid_svg()

        with open(os.path.join(self.map_path, self.graphic_filename)) as f:
            return str(f.readlines()).replace("\n", "")

    def _generate_grid_svg(self):
        """
        Returns an SVG of the device's matrix grid.
        """
        self.editor.action_view_device_graphic.setChecked(False)
        self.editor.action_view_grid.setChecked(True)
        svg = []

        # How large is each grid?
        square_px = 50
        margin_px = 1
        fill_colour = "#00007f"
        stroke_colour = "#0000ff"
        stroke_width = 1
        total_X_blocks = self.cols
        total_Y_blocks = self.rows

        svg.append('<svg width="{width}px" height="{height}px"> version="1.1" viewBox="0px 0px {width}px {height}px" xmlns="http://www.w3.org/2000/svg">'.format(
            width = total_X_blocks * square_px + (margin_px * total_X_blocks),
            height = total_Y_blocks * square_px + (margin_px * total_X_blocks)
        ))

        for x in range(0, total_X_blocks):
            for y in range(0, total_Y_blocks):
                x_pos = x * square_px + (x * margin_px + 1)
                y_pos = y * square_px + (y * margin_px + 1)
                svg.append('<g id="x{x}-y{y}" class="LED"><rect x="{x_pos}px" y="{y_pos}px" width="{square_px}px" height="{square_px}px" style="fill:{fill_colour};paint-order:markers fill stroke;stroke-linecap:round;stroke-width:{stroke_width};stroke:{stroke_colour}"/></g>'.format(
                    x = x,
                    y = y,
                    x_pos = x_pos,
                    y_pos = y_pos,
                    square_px = square_px,
                    fill_colour = fill_colour,
                    stroke_colour = stroke_colour,
                    stroke_width = stroke_width
                ))

        svg.append("</svg>")
        return "".join(svg)

    def _cb_title_changed(self, title):
        """
        JavaScript sends string messages to us (Python) by changing the title.
        This will run when the title changes.
        """
        pieces = title.split(";")
        if pieces[0] == "click":
            x = int(pieces[1])
            y = int(pieces[2])
            callbacks = {
                effects.TYPE_SEQUENCE: {
                    VISUAL_MODE_ADD: self.editor.draw_LED_to_frame,
                    VISUAL_MODE_DEL: self.editor.erase_LED_from_frame,
                    VISUAL_MODE_PICK: self.editor.pick_LED_colour_from_frame
                },
                effects.TYPE_LAYERED: {
                    VISUAL_MODE_ADD: self.editor.assign_key_to_layer,
                    VISUAL_MODE_DEL: self.editor.unassign_key_to_layer
                }
            }
            callbacks[self.editor.effect_type][self.editor.current_tool](x, y)

    def set_mode(self, mode):
        """
        Update the cursor/behaviour inside the visual editor, but only when
        the editor is ready.
        """
        if not self.loaded:
            return

        self.webview.page().runJavaScript("setMode({0}, {1})".format(mode, str(self.use_native_cursor).lower()))

    def clear(self):
        """
        Clear all the keys.
        """
        if self.loaded:
            self.webview.page().runJavaScript("clearLED()")

    def set_pos(self, x, y, hex_value):
        """
        Set the colour of a specific key.
        """
        self.webview.page().runJavaScript("setLED({0}, {1}, false, '{2}')".format(x, y, hex_value))
