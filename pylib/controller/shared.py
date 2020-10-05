#!/usr/bin/python3
#
# Polychromatic is licensed under the GPLv3.
# Copyright (C) 2020 Luke Horwell <code@horwell.me>
#
"""
This module contains widgets shared across the Controller GUI.
"""

from .. import common
from .. import locales
from .. import preferences as pref

import os
from PyQt5 import uic
from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont, QFontDatabase, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, \
                            QWidget, QMessageBox, QGridLayout, \
                            QLabel, QPushButton, QToolButton, QGroupBox, \
                            QListWidget, QHBoxLayout, QVBoxLayout, QFormLayout, \
                            QSizePolicy, QSpacerItem, QDialog, QColorDialog, \
                            QDialogButtonBox, QTreeWidget, QTreeWidgetItem, \
                            QLineEdit

def load_qt_theme(app, qapp, window):
    """
    Apply the Polychromatic Qt theme for the main window if enabled by the user.

    Params:
        app             ApplicationData() object
        qapp            QApplication() object
        window          QMainWindow() or QDialog() object
    """
    if app.system_qt_theme:
        return

    # Load "Play" font
    QFontDatabase.addApplicationFont(os.path.join(app.data_path, "qt", "fonts", "Play_regular.ttf"))
    font = QFont("Play", 10, 1)
    qapp.setFont(font)

    menu_bar = window.findChild(QMenuBar, "menuBar")
    if menu_bar:
        menu_bar.setFont(font)

    custom_tabs = window.findChild(QWidget, "MainTabCustom")
    if custom_tabs:
        custom_tabs.setFont(font)

    # Load basic colour palettes
    ui_palette = QPalette()
    black = QColor(0, 0, 0)
    white = QColor(255, 255, 255)
    primary = QColor(0, 255, 0)
    secondary = QColor(0, 128, 0)
    ui_palette.setColor(QPalette.Window, QColor(0, 0, 0))
    ui_palette.setColor(QPalette.WindowText, white)
    ui_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    ui_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    ui_palette.setColor(QPalette.ToolTipBase, white)
    ui_palette.setColor(QPalette.ToolTipText, white)
    ui_palette.setColor(QPalette.Text, white)
    ui_palette.setColor(QPalette.Button, QColor(50, 50, 50)) #323232
    ui_palette.setColor(QPalette.ButtonText, white)
    ui_palette.setColor(QPalette.Link, primary)
    ui_palette.setColor(QPalette.Highlight, secondary)
    ui_palette.setColor(QPalette.HighlightedText, white)
    window.setPalette(ui_palette)

    # Load QSS (essentially CSS) with Polychromatic's design
    with open(os.path.join(app.data_path, "qt", "style.qss"), "r") as f:
        window.setStyleSheet(f.read().replace("[data]", app.data_path))


def get_ui_widget(appdata, name, q_toplevel=QWidget):
    """
    Returns a QWidget object for the specified .ui file.

    Params:
        appdata         ApplicationData() object
        name            Name of UI file (in ui/ folder) without .ui extension
        q_toplevel      Top-level object class, e.g. QWidget() or QDialog()
    """
    ui_file = os.path.join(appdata.data_path, "qt", name + ".ui")
    if not os.path.exists(ui_file):
        print("Missing UI file: " + ui_file)
        return None

    widget = uic.loadUi(ui_file, q_toplevel())

    # TODO: Process i18n strings

    # If a dialog, apply the styles
    if q_toplevel == QDialog:
        load_qt_theme(appdata, appdata.main_app, widget)

    return widget


def clear_layout(layout):
    """
    Removes all Qt elements inside a layout.
    """
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


class PolychromaticWidgets(object):
    """
    Code for building some of the common UI elements of the Controller application.
    """
    def __init__(self, appdata):
        """
        Stores the ApplicationData() object for reference later.
        """
        self.appdata = appdata

        # Dialogues types
        self.dialog_generic = QMessageBox.Information
        self.dialog_error = QMessageBox.Critical
        self.dialog_warning = QMessageBox.Warning

    def create_summary_widget(self, icon_path, title, indicators=[], buttons=[]):
        """
        Returns a summary widget presenting an overview of the selected device,
        effect or preset.

        Params:
            icon_path           (str)   Absolute path to the icon to use.
            icon_path_fallback  (str)   Absolute path when icon cannot be found.
            title               (str)   Summary title, e.g. device or effect name
            indicators          (list)  See indicators below.
            buttons             (list)  See buttons below.

        Indicators list:
        [
            {
                "icon": (str)       (Absolute path)
                "label": (str)
            },
            {..}
        ]

        Buttons list:
        [
            {
                "id": (str)
                "icon": (str)
                "label": (str)
                "disabled": (bool)
                "action": (obj)     (Function to run when clicked)
            },
            {..}
        ]

        Returns: QWidget()
        """
        summary = get_ui_widget(self.appdata, "widget-summary")
        image_widget = summary.findChild(QLabel, "SummaryImage")
        title_widget = summary.findChild(QLabel, "SummaryTitle")
        indicators_widget = summary.findChild(QWidget, "SummaryIcons")
        buttons_widget = summary.findChild(QWidget, "SummaryButtons")

        title_widget.setText(title)
        title_widget.setStyleSheet("QLabel { color: lime; font-size: 17px; }")

        # Populate Image
        if os.path.exists(icon_path):
            # Make sure it fits dimensions
            pixmap_src = QPixmap(icon_path)
            pixmap = pixmap_src.scaled(115, 115, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_widget.setPixmap(pixmap)
            #image_widget.resize(pixmap.width(), pixmap.height())
        else:
            image_widget.deleteLater()

        # Populate Indicators
        for indicator in indicators:
            widget = QWidget()
            widget.setLayout(QHBoxLayout())
            layout = widget.layout()
            layout.setContentsMargins(0,0,10,0)

            # Create image
            if indicator["icon"]:
                label = QLabel()
                pixmap_src = QPixmap(indicator["icon"])
                pixmap = pixmap_src.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(pixmap)
                label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
                layout.addWidget(label)

            # Create text
            label = QLabel()
            label.setText(indicator["label"])
            layout.addWidget(label)

            indicators_widget.layout().addWidget(widget)
        indicators_widget.layout().addStretch()

        # Populate Buttons
        for btn in buttons:
            button = QPushButton()
            button.setObjectName(btn["id"])
            if btn["icon"] and os.path.exists(btn["icon"]):
                button.setIcon(btn["icon"])
            button.setText(btn["label"])

            if btn["disabled"]:
                button.setDisabled(True)

            button.clicked.connect(btn["action"])
            buttons_widget.layout().addWidget(button)
        buttons_widget.layout().addStretch()

        return summary

    def create_group_widget(self, title):
        """
        Returns a group widget containing controls for a specific device zone.

        Params:
            title           (str)   Group title

        Returns: QGroupBox()
        """
        group = QGroupBox()
        group.setTitle(title)
        #group.setFont(QFont("Play", 11))
        group.setLayout(QGridLayout())
        group.layout().setAlignment(Qt.AlignTop)
        return group

    def create_row_widget(self, label_text, widgets=[], vertical=False):
        """
        Returns a widget for use when presenting controls for a particular option.

        Params:
            label_text      (str)   Human readable control label
            widgets         (list)  List of widgets to display
            vertical        (bool)  Use a vertical layout instead of horizontal

        Returns: QWidget()
        """
        widget = QWidget()
        widget.setLayout(QFormLayout())
        layout = widget.layout()
        layout.setRowWrapPolicy(QFormLayout.WrapLongRows)
        layout.setContentsMargins(QMargins(30, 5, 30, 5))

        # Left - Add label
        label = QLabel()
        label.setText(label_text)
        label.setMinimumWidth(150)

        # Right - Add controls
        inner_widget = QWidget()
        inner_widget.setLayout(QVBoxLayout() if vertical else QHBoxLayout())
        for w in widgets:
            inner_widget.layout().addWidget(w)

        layout.addRow(label, inner_widget)

        return widget

    def populate_empty_state(self, layout, icon_path, title, subtitle, buttons=[]):
        """
        Creates a 'watermark' like background when a page or section is empty.
        For example, this may be used when the device list is empty.

        Params:
            layout          QWidget     QWidget() to apply the layout on. Should be empty.
            icon_path       (str)       Path to the background graphic. Should be 750x500.
            title           (str)       Larger text to display.
            subtitle        (str)       Smaller text to display.
            buttons         (list)      (Optional) In format: [{icon, label, action}, {..}]

        Returns nothing - the layout is directly applied.
        """
        # Center graphic
        image = QLabel()
        pixmap_src = QPixmap(icon_path)
        pixmap = pixmap_src.scaled(750 / 2, 500 / 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image.setPixmap(pixmap)
        image.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        image.setAlignment(Qt.AlignCenter)

        # Text & buttons
        text1 = QLabel()
        text1.setFont(QFont("Play", 14))
        text1.setAlignment(Qt.AlignCenter)
        text1.setText(title)
        text1.setMargin(10)

        text2 = QLabel()
        text2.setFont(QFont("Play", 11))
        text2.setAlignment(Qt.AlignCenter)
        text2.setText(subtitle)
        text2.setMargin(10)
        text2.setWordWrap(True)

        button_container = None
        if buttons:
            button_container = QWidget()
            button_container.setLayout(QHBoxLayout())
            button_container.layout().addStretch()
            for spec in buttons:
                button = QPushButton()
                button.setText(spec["label"])
                button.setIcon(QIcon(spec["icon"]))
                button.clicked.connect(spec["action"])
                button_container.layout().addWidget(button)
            button_container.layout().addStretch()

        # Putting it together
        layout.addStretch()
        for widget in [image, text1, text2, button_container]:
            if widget:
                layout.addWidget(widget)
        layout.addStretch()

    def create_colour_control(self, current_hex, callback_fn, title):
        """
        Create a colour picker control for the user to set a colour. Setting
        the colour will open a dialog.

        When a colour is saved, the callback_fn will be executed passing the new
        hex colour as a parameter.

        Params:
            current_hex     String of the current hex value in use.
            callback_fn     Function to run after saving changes
        """
        container = QWidget()
        container.setLayout(QHBoxLayout())
        preview = QWidget()
        preview.setMinimumHeight(28)
        preview.setMaximumHeight(28)
        preview.setMinimumWidth(80)
        preview.setMaximumWidth(80)
        preview.setStyleSheet("QWidget {{ background-color: {0} }}".format(current_hex))

        def _clicked_change_colour():
            picker = ColourPicker(self.appdata, callback_fn, current_hex, title)

        btn = QPushButton()
        btn.setText(self.appdata._("Change..."))
        btn.clicked.connect(_clicked_change_colour)

        container.layout().addWidget(preview)
        container.layout().addWidget(btn)
        return container

    def create_icon_picker_control(self, callback_fn):
        """
        Create an icon picker control for the user to choose an icon from a list
        of built-in icons, user-imported icons ("custom icons") or an application
        installed on the file system.

        When an icon is saved, the callback_fn will be executed returning the
        relative path (for a built-in icon) or an absolute path (for custom images)
        as a parameter for the function that will process the new selection.

        Params:
            callback_fn     Function to run after saving changes
        """
        print("stub:create_icon_picker_control")

    def open_dialog(self, dialog_type, title, text, info_text="", traceback="", buttons=[], default_button=None, actions={}):
        """
        Opens a modal dialogue box to inform of a situation.

        If no functions are passed to the 'ok', 'cancel', etc functions, then the
        dialog will just show a message and then close with no further action.

        Params:
            dialog_type     (str)   One of self.dialog_* variable above.
            title           (str)   Window title
            text            (str)   Description of what happened.
            info_text       (str)   (Optional) Informative text of next steps.
            traceback       (str)   (Optional) More details of the problem
            buttons         (list)  (Optional) QMessageBox.* buttons to display
            default_button  (obj)   (Optional) QMessageBox.* button to default to.
            actions         (dict)  (Optional) Functions to run after dismissing.
                                    E.g. {QMessageBox.Ok = name_of_function, ...}
        """
        msgbox = QMessageBox()
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
        msgbox.setIcon(dialog_type)
        load_qt_theme(self.appdata, self.appdata.main_app, msgbox)

        if info_text:
            msgbox.setInformativeText(info_text);

        for button in buttons:
            msgbox.addButton(button)

        if default_button:
            msgbox.setDefaultButton(default_button)

        if not buttons:
            msgbox.addButton(QMessageBox.Ok)
            msgbox.setDefaultButton(QMessageBox.Ok)

        if traceback:
            msgbox.setDetailedText(traceback)
            msgbox.setStyleSheet("QTextEdit { font-family: monospace; }");

        def _dialog_closed(result):
            for action in actions.keys():
                if result == action:
                    actions[action]()

        msgbox.finished.connect(_dialog_closed)
        msgbox.exec()


class ColourPicker(object):
    """
    The colour picker dialog allows the user to quickly choose a colour or
    hand over to the system's colour picker (which on Linux, would be Qt's native picker)
    """
    def __init__(self, appdata, callback_fn, current_hex, title):
        self.appdata = appdata
        self.current_hex = current_hex
        self.current_name = ""
        self.callback_fn = callback_fn
        self.title = title
        self.saved_colours = pref.load_file(pref.path.colours)

        # UI Controls
        self.dialog = get_ui_widget(appdata, "colour-picker", q_toplevel=QDialog)
        self.dialog_btns = self.dialog.findChild(QDialogButtonBox, "buttonBox")
        self.change_btn = self.dialog.findChild(QPushButton, "OpenPicker")
        self.list_save_btn = self.dialog.findChild(QPushButton, "SaveToList")
        self.list_del_btn = self.dialog.findChild(QPushButton, "DeleteFromList")
        self.list_text_input = self.dialog.findChild(QLineEdit, "ColourName")
        self.save_widget = self.dialog.findChild(QWidget, "SaveWidget")
        self.save_widget.setHidden(True)
        self.open_save_widget = self.dialog.findChild(QPushButton, "OpenSaveWidget")
        self.close_save_widget = self.dialog.findChild(QPushButton, "CloseSaveWidget")
        self.saved_tree = self.dialog.findChild(QTreeWidget, "SavedColours")
        self.current_preview = self.dialog.findChild(QWidget, "CurrentPreview")
        self.current_label = self.dialog.findChild(QLabel, "CurrentLabel")

        # Connect signals when interacting with UI controls
        self.dialog_btns.accepted.connect(self._apply_colour)
        self.change_btn.clicked.connect(self._open_system_picker)
        self.open_save_widget.clicked.connect(self._open_save_widget)
        self.close_save_widget.clicked.connect(self._close_save_widget)
        self.list_text_input.textEdited.connect(self._on_save_input_change)
        self.list_text_input.returnPressed.connect(self._save_to_list)
        self.list_save_btn.clicked.connect(self._save_to_list)
        self.list_del_btn.clicked.connect(self._delete_from_list)
        self.saved_tree.itemSelectionChanged.connect(self._switch_colour)

        # Refresh UI data and open dialog
        self._build_saved_colour_list()
        self._refresh_selected_colour(current_hex)
        self.saved_tree.setColumnWidth(0, 140)
        self.dialog.setWindowTitle(title)
        self.dialog.exec()

    def _switch_colour(self):
        """
        User selects a colour from their selected colour list.
        """
        items = self.saved_tree.selectedItems()
        if items:
            self._refresh_selected_colour(items[0].colour_hex)

    def _add_to_tree(self, name, value):
        """
        Appends an item to the tree.
        """
        item = QTreeWidgetItem()
        item.setText(0, name)
        item.setText(1, value.upper())
        item.setIcon(0, QIcon(common.generate_colour_bitmap(self.appdata.dbg, pref.path, value, "16x16")))
        item.colour_name = name
        item.colour_hex = value.upper()
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        self.saved_tree.addTopLevelItem(item)
        return item

    def _get_tree_objects(self):
        root = self.saved_tree.invisibleRootItem()
        items = []
        for i in range(root.childCount()):
            items.append(root.child(i))
        return items

    def _refresh_selected_colour(self, new_hex):
        """
        Refresh the UI to show the newly chosen colour.
        """
        self.current_hex = new_hex
        self.current_preview.setStyleSheet("QWidget {{ background-color: {0} }}".format(new_hex))
        self.current_label.setText("{0}\n({1})".format(new_hex.upper(), ", ".join(map(str, common.hex_to_rgb(new_hex)))))

        self.list_text_input.setText("")
        self.open_save_widget.setDisabled(False)
        self.list_del_btn.setDisabled(True)

        for widget in self._get_tree_objects():
            if widget.colour_hex == new_hex:
                widget.setSelected(True)
                self.current_name = widget.colour_name
                self.save_widget.setHidden(True)
                self.open_save_widget.setDisabled(True)
                self.list_del_btn.setDisabled(False)
                return

        self.saved_tree.clearSelection()

    def _apply_colour(self):
        """
        User applies their newly chosen colour. Saves the colour list to file if
        there are new colours or the order was modified.
        """
        dbg = self.appdata.dbg
        self._save_colour_list_to_file()
        dbg.stdout("Colour set to: " + self.current_hex, dbg.success, 1)
        self.callback_fn(self.current_hex)

    def _save_colour_list_to_file(self):
        """
        Saves the colour list to file.
        """
        # TODO: Optimisation: Only save if there are changes (add/remove/reorder)
        dbg = self.appdata.dbg
        dbg.stdout("Saving colour list...", dbg.action, 1)
        colour_list = []
        for item in self._get_tree_objects():
            colour_list.append({
                "name": item.colour_name,
                "hex": item.colour_hex
            })
            pref.save_file(pref.Paths().colours, colour_list)

    def _open_system_picker(self):
        """
        User uses the system's colour picker to pick any colour, which could
        include the ability to choose a pixel on the screen (dependent on OS)
        """
        output = QColorDialog.getColor(title=self.title, initial=QColor(self.current_hex))
        if not output.isValid():
            return
        new_hex = output.name()
        self._refresh_selected_colour(new_hex)

    def _open_save_widget(self):
        self.save_widget.setHidden(False)
        self.open_save_widget.setDisabled(True)

    def _close_save_widget(self):
        self.save_widget.setHidden(True)
        self.open_save_widget.setDisabled(False)

    def _on_save_input_change(self, text):
        self.list_save_btn.setEnabled(True if len(text) > 0 else False)

    def _save_to_list(self):
        """
        Save the colour to their Saved Colour list.
        """
        new_name = self.list_text_input.text()
        new_hex = self.current_hex
        item = self._add_to_tree(new_name, new_hex)
        item.setSelected(True)
        self._close_save_widget()

    def _delete_from_list(self):
        """
        Delete the selected item from the Saved Colour list.
        """
        item = self.saved_tree.selectedItems()[0]
        self.saved_tree.invisibleRootItem().removeChild(item)

    def _build_saved_colour_list(self):
        """
        Builds the initial saved colour list.
        """
        self.saved_tree.invisibleRootItem().takeChildren()

        for index, colour in enumerate(self.saved_colours):
            item = self._add_to_tree(colour["name"], colour["hex"])
            if self.current_hex == item.colour_hex:
                item.setSelected(True)
                if index > 5:
                    self.saved_tree.scrollToItem(item)

