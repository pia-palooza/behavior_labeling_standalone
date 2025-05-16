# === START FILE: scripts/behavior_labeling/annotation_window.py ===
# === START FILE: scripts/behavior_annotator/annotation_window.py ===
# annotation_window.py
"""
AnnotationWindow class for the Behavior Annotator GUI.
Handles the main UI layout, annotation management, and interaction logic.
"""
import logging
import os
import sys
import traceback
from pathlib import Path
# *** MODIFICATION START ***
# Import 'random' for shuffling
import random
# *** MODIFICATION END ***
from typing import Any, Dict, List, Optional, Tuple # Added Tuple

import pandas as pd
# *** MODIFICATION START ***
# Added QCheckBox
from PyQt5.QtCore import QCoreApplication, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, # Added QCheckBox
                             QComboBox, QDoubleSpinBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QSizePolicy, QSlider,
                             QSpacerItem, QSpinBox, QStatusBar, QStyle,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)
# *** MODIFICATION END ***


# Local imports
from config import (COL_BEHAVIOR, COL_DURATION, COL_END_FRAME,
                    COL_START_FRAME, DEFAULT_BEHAVIOR_IDENTITIES,
                    DEFAULT_PLAYBACK_SPEED, PROCEED_CANCEL, PROCEED_DISCARD,
                    PROCEED_SAVE, STATE_PAUSED, STATE_PLAYING, STATE_STOPPED, PROJECT_DIR)
from utils import format_timestamp # Import from utils
from video_player import VideoPlayer # Import VideoPlayer

class AnnotationWindow(QWidget):
    """
    PyQt5 window for manually annotating behavior bouts in videos. Uses VideoPlayer for video handling.
    """
    # Constants for table columns are now imported from config

    def __init__(self, parent=None):
        super().__init__(parent)
        # --- Data Holders ---
        self.selected_folder_path: Optional[Path] = None
        self.video_files_in_folder: List[Path] = []
        # *** MODIFICATION START ***
        # Store mapping for blind mode: displayed_name -> actual_path
        self._blind_mode_mapping: Dict[str, Path] = {}
        # Store checkmark status: actual_path -> bool
        self._video_annotation_status: Dict[Path, bool] = {}
        # *** MODIFICATION END ***
        self.current_video_path: Optional[Path] = None
        # Video properties managed by VideoPlayer now
        self.current_start_frame: Optional[int] = None
        self.current_end_frame: Optional[int] = None
        self.annotations: List[Dict[str, Any]] = []
        self._is_updating_table = False
        self.behavior_identities: List[str] = DEFAULT_BEHAVIOR_IDENTITIES.copy()
        self._slider_is_pressed = False # Flag to prevent player seeking during playback update
        self.unsaved_changes: bool = False # Flag for unsaved annotations

        # --- Video Player Instance ---
        self.video_player = VideoPlayer()
        self._video_frame_count = 0 # Keep local copy for convenience
        self._video_fps = 0.0       # Keep local copy

        # --- UI Elements ---
        # Layouts
        self.main_layout = QVBoxLayout(self)
        self.folder_video_layout = QHBoxLayout()
        self.controls_layout = QHBoxLayout() # Main area: Video | Annotation Controls
        self.video_area_layout = QVBoxLayout()
        self.annotation_controls_panel = QVBoxLayout() # New panel on the right
        self.player_controls_layout = QHBoxLayout()
        self.annotation_table_area_layout = QVBoxLayout()
        self.table_controls_layout = QHBoxLayout()

        # Folder/Video Selection
        self.browse_folder_button = QPushButton("Browse Folder...")
        self.selected_folder_label = QLabel("Folder: None")
        self.selected_folder_label.setWordWrap(True)
        self.video_select_label = QLabel("Select Video:")
        self.video_select_combo = QComboBox()
        # *** MODIFICATION START ***
        self.blind_mode_checkbox = QCheckBox("Blind Mode")
        # *** MODIFICATION END ***

        # Video Player Elements (UI Only)
        self.video_display_label = QLabel("Video Not Loaded")
        self.video_slider = QSlider(Qt.Horizontal)
        self.play_pause_button = QPushButton()
        self.prev_frame_button = QPushButton("<< Frame")
        self.next_frame_button = QPushButton("Frame >>")
        self.skip_backward_button = QPushButton("<< Skip")
        self.skip_forward_button = QPushButton("Skip >>")
        self.skip_amount_label = QLabel("Skip Amount:")
        self.skip_amount_spinbox = QSpinBox()
        self.reverse_button = QPushButton("< Reverse") # Functionality might change
        self.speed_label = QLabel("Speed:")
        self.speed_spinbox = QDoubleSpinBox()
        self.current_frame_label = QLabel("Frame: - / -")
        self.current_time_label = QLabel("Time: --:--:--.---")

        # Annotation Control UI Elements
        self.annot_ctrl_title_label = QLabel("Annotation Controls")
        self.mark_start_button = QPushButton("Mark Start")
        self.mark_end_button = QPushButton("Mark End")
        self.start_frame_display = QLabel("Start: -")
        self.end_frame_display = QLabel("End: -")
        self.behavior_label = QLabel("Behavior:")
        self.behavior_combo = QComboBox()
        self.add_annotation_button = QPushButton("Add Annotation")

        # Annotation Table
        self.annotation_table = QTableWidget()
        self.remove_annotation_button = QPushButton("Remove Selected Annotation")
        self.export_annotations_button = QPushButton("Export Annotations for Video")

        # Status Bar
        self.status_bar = QStatusBar()

        # Icons
        self._play_icon: Optional[QIcon] = None
        self._pause_icon: Optional[QIcon] = None

        # Go To Frame elements
        self.goto_frame_label = QLabel("Go To:")
        self.goto_frame_spinbox = QSpinBox()
        self.goto_frame_button = QPushButton("Go")

        # --- Initialize UI and Connections ---
        self._init_ui()
        self._connect_signals()
        self._select_folder(Path(PROJECT_DIR)) # Default to project folder

    def _init_ui(self):
        """ Set up the user interface layout and widgets. """
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setGeometry(100, 100, 1200, 750)

        try:
            self._play_icon = self.style().standardIcon(QStyle.SP_MediaPlay)
            self._pause_icon = self.style().standardIcon(QStyle.SP_MediaPause)
            self.play_pause_button.setIcon(self._play_icon)
        except Exception as e:
            logging.warning(f"Could not load standard media icons: {e}")
            self.play_pause_button.setText("Play") # Fallback text

        # --- Top Bar: Folder and Video Selection ---
        self.folder_video_layout.addWidget(self.browse_folder_button)
        self.folder_video_layout.addWidget(self.selected_folder_label, 1)
        self.folder_video_layout.addSpacing(20)
        self.folder_video_layout.addWidget(self.video_select_label)
        self.video_select_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.folder_video_layout.addWidget(self.video_select_combo, 2)
        # *** MODIFICATION START ***
        self.blind_mode_checkbox.setToolTip("Randomize video order and hide names")
        self.folder_video_layout.addWidget(self.blind_mode_checkbox)
        # *** MODIFICATION END ***
        self.main_layout.addLayout(self.folder_video_layout)

        # --- Main Area: Annotation Controls | Video Player ---
        self.main_layout.addLayout(self.controls_layout, 2) # Add the main horizontal layout

        # Configure Annotation Controls Panel (Left Side - NEW)
        annot_panel_widget = QWidget() # Container widget for the panel
        annot_panel_widget.setLayout(self.annotation_controls_panel) # Apply the QVBoxLayout
        annot_panel_widget.setMaximumWidth(280) # Maintain fixed width for controls

        title_font = self.annot_ctrl_title_label.font()
        title_font.setPointSize(12); title_font.setBold(True)
        self.annot_ctrl_title_label.setFont(title_font)
        self.annot_ctrl_title_label.setAlignment(Qt.AlignCenter)
        self.annotation_controls_panel.addWidget(self.annot_ctrl_title_label)
        self.annotation_controls_panel.addSpacing(10)

        mark_layout = QGridLayout()
        mark_layout.addWidget(self.mark_start_button, 0, 0)
        mark_layout.addWidget(self.start_frame_display, 0, 1)
        mark_layout.addWidget(self.mark_end_button, 1, 0)
        mark_layout.addWidget(self.end_frame_display, 1, 1)
        self.annotation_controls_panel.addLayout(mark_layout)
        self.annotation_controls_panel.addSpacing(15)

        self.annotation_controls_panel.addWidget(self.behavior_label)
        self.behavior_combo.addItems(self.behavior_identities)
        self.behavior_combo.setToolTip("Select the behavior type")
        self.annotation_controls_panel.addWidget(self.behavior_combo)
        self.annotation_controls_panel.addSpacing(10)

        self.add_annotation_button.setFixedHeight(35)
        self.annotation_controls_panel.addWidget(self.add_annotation_button)
        self.annotation_controls_panel.addStretch(1) # Push controls to top

        # Add annotation panel FIRST with stretch factor 1 (narrower)
        self.controls_layout.addWidget(annot_panel_widget, 1)

        # Configure Video Area (Right Side - NEW)
        self.video_display_label.setAlignment(Qt.AlignCenter)
        self.video_display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_display_label.setStyleSheet("background-color: black; color: white;")
        self.video_area_layout.addWidget(self.video_display_label, 1) # Video takes expanding space

        self.video_slider.setTickPosition(QSlider.TicksBelow)
        self.video_area_layout.addWidget(self.video_slider) # Slider below video

        # Player Controls (Layout setup remains the same, just added below video)
        self.player_controls_layout.addWidget(self.play_pause_button)
        self.player_controls_layout.addWidget(self.prev_frame_button)
        self.player_controls_layout.addWidget(self.next_frame_button)
        self.player_controls_layout.addSpacing(10)
        self.player_controls_layout.addWidget(self.skip_backward_button)
        self.player_controls_layout.addWidget(self.skip_forward_button)
        self.player_controls_layout.addWidget(self.skip_amount_label)
        self.skip_amount_spinbox.setRange(1, 1000)
        self.skip_amount_spinbox.setValue(10)
        self.skip_amount_spinbox.setFixedWidth(60)
        self.skip_amount_spinbox.setToolTip("Number of frames to skip")
        self.player_controls_layout.addWidget(self.skip_amount_spinbox)
        self.player_controls_layout.addStretch(1)
        self.player_controls_layout.addWidget(self.speed_label)
        self.speed_spinbox.setRange(0.1, 10.0)
        self.speed_spinbox.setSingleStep(0.1)
        self.speed_spinbox.setValue(DEFAULT_PLAYBACK_SPEED)
        self.speed_spinbox.setToolTip("Adjust playback speed (1.0 is normal)")
        self.player_controls_layout.addWidget(self.speed_spinbox)
        self.player_controls_layout.addSpacing(15)
        self.player_controls_layout.addStretch(1)
        self.player_controls_layout.addWidget(self.goto_frame_label)
        self.goto_frame_spinbox.setRange(0, 0)
        self.goto_frame_spinbox.setToolTip("Enter frame number and click Go")
        self.goto_frame_spinbox.setFixedWidth(80)
        self.player_controls_layout.addWidget(self.goto_frame_spinbox)
        self.goto_frame_button.setToolTip("Jump to the specified frame")
        self.goto_frame_button.setFixedWidth(40)
        self.player_controls_layout.addWidget(self.goto_frame_button)
        self.player_controls_layout.addSpacing(15)
        self.player_controls_layout.addWidget(self.current_frame_label)
        self.player_controls_layout.addSpacing(15)
        self.player_controls_layout.addWidget(self.current_time_label)
        self.video_area_layout.addLayout(self.player_controls_layout) # Add player controls below video

        # Add video area SECOND with stretch factor 3 (wider)
        self.controls_layout.addLayout(self.video_area_layout, 3)

        # --- Bottom Area: Annotation Table, Controls, Status Bar ---
        self.main_layout.addLayout(self.annotation_table_area_layout, 1)

        # Configure Annotation Table
        self.annotation_table.setColumnCount(4)
        self.annotation_table.setHorizontalHeaderLabels(
            ["Behavior", "Start Frame", "End Frame", "Duration (s)"]
        )
        self.annotation_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.annotation_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.annotation_table.verticalHeader().setVisible(False)
        header = self.annotation_table.horizontalHeader()
        header.setSectionResizeMode(COL_BEHAVIOR, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_START_FRAME, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_END_FRAME, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_DURATION, QHeaderView.ResizeToContents)
        self.annotation_table.setSortingEnabled(True)
        self.annotation_table.sortByColumn(COL_START_FRAME, Qt.AscendingOrder)
        self.annotation_table.setMinimumHeight(150)

        self.annotation_table_area_layout.addWidget(self.annotation_table, 1)

        # Table Controls
        self.table_controls_layout.addWidget(self.remove_annotation_button)
        self.table_controls_layout.addStretch(1)
        self.table_controls_layout.addWidget(self.export_annotations_button)
        self.annotation_table_area_layout.addLayout(self.table_controls_layout)

        # Status Bar
        self.main_layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready. Browse to a folder containing videos.")

    def _connect_signals(self):
        """ Connect UI element signals to slots and VideoPlayer signals to slots. """
        logging.debug("Connecting signals...")
        try:
            # Folder/Video Selection
            self.browse_folder_button.clicked.connect(self._browse_folder)
            self.video_select_combo.currentIndexChanged.connect(self._on_video_selected)
            # *** MODIFICATION START ***
            # Connect checkbox state change to repopulate dropdown
            self.blind_mode_checkbox.stateChanged.connect(self._populate_video_dropdown)
            # *** MODIFICATION END ***


            # Video Player UI Controls -> VideoPlayer Actions
            self.video_slider.valueChanged.connect(self._on_slider_value_changed)
            self.video_slider.sliderPressed.connect(self._on_slider_pressed)
            self.video_slider.sliderReleased.connect(self._on_slider_released)
            self.play_pause_button.clicked.connect(self._toggle_play_pause)
            self.prev_frame_button.clicked.connect(self.video_player.prev_frame) # Direct connect
            self.next_frame_button.clicked.connect(self.video_player.next_frame) # Direct connect
            self.skip_backward_button.clicked.connect(self._skip_backward)
            self.skip_forward_button.clicked.connect(self._skip_forward)
            self.goto_frame_button.clicked.connect(self._on_goto_frame_clicked)
            # self.reverse_button # No dedicated button action now
            self.speed_spinbox.valueChanged.connect(self.video_player.set_speed) # Direct connect

            # VideoPlayer Signals -> UI Update Slots
            self.video_player.videoLoaded.connect(self._handle_video_loaded)
            self.video_player.videoLoadFailed.connect(self._handle_video_load_failed)
            self.video_player.frameChanged.connect(self._handle_frame_changed)
            self.video_player.playbackStateChanged.connect(self._handle_playback_state_changed)
            self.video_player.errorOccurred.connect(self._handle_player_error)

            # Annotation Controls
            self.mark_start_button.clicked.connect(self._mark_start)
            self.mark_end_button.clicked.connect(self._mark_end)
            self.add_annotation_button.clicked.connect(self._add_annotation)

            # Table Controls and Interaction
            self.remove_annotation_button.clicked.connect(self._remove_annotation)
            self.export_annotations_button.clicked.connect(self._export_annotations)
            self.annotation_table.itemChanged.connect(self._on_table_item_changed)
            self.annotation_table.itemSelectionChanged.connect(self._on_table_selection_changed)
            self.annotation_table.cellClicked.connect(self._on_table_cell_clicked)

            logging.debug("Signals connected successfully.")

        except Exception as e:
            logging.error(f"Error connecting signals: {e}\n{traceback.format_exc()}", exc_info=True)
            QMessageBox.critical(self, "Signal Connection Error", f"Failed to connect UI signals:\n{e}")

    # --- State Management ---
    def _update_controls_state(self):
        """ Enable/disable controls based on the application state. """
        folder_selected = self.selected_folder_path is not None
        video_loaded = self.video_player.get_frame_count() > 0 # Check player state

        self.video_select_label.setEnabled(folder_selected)
        self.video_select_combo.setEnabled(folder_selected and bool(self.video_files_in_folder))
        # *** MODIFICATION START ***
        # Enable checkbox only if a folder is selected
        self.blind_mode_checkbox.setEnabled(folder_selected)
        # *** MODIFICATION END ***

        # Video loaded dependent
        self.video_display_label.setEnabled(video_loaded)
        self.video_slider.setEnabled(video_loaded)
        self.play_pause_button.setEnabled(video_loaded)
        self.prev_frame_button.setEnabled(video_loaded)
        self.next_frame_button.setEnabled(video_loaded)
        self.skip_backward_button.setEnabled(video_loaded)
        self.skip_forward_button.setEnabled(video_loaded)
        self.skip_amount_label.setEnabled(video_loaded)
        self.skip_amount_spinbox.setEnabled(video_loaded)
        # self.reverse_button.setEnabled(video_loaded)
        self.speed_spinbox.setEnabled(video_loaded)
        self.current_frame_label.setEnabled(video_loaded)
        self.current_time_label.setEnabled(video_loaded)
        self.goto_frame_label.setEnabled(video_loaded)
        self.goto_frame_spinbox.setEnabled(video_loaded)
        self.goto_frame_button.setEnabled(video_loaded)

        # Annotation controls dependent on video loaded
        self.mark_start_button.setEnabled(video_loaded)
        self.mark_end_button.setEnabled(video_loaded)
        self.behavior_label.setEnabled(video_loaded)
        self.behavior_combo.setEnabled(video_loaded)
        self.add_annotation_button.setEnabled(video_loaded)

        # Table controls dependent on video loaded and potentially table selection
        self.annotation_table.setEnabled(video_loaded)
        self.remove_annotation_button.setEnabled(video_loaded and bool(self.annotation_table.selectedItems()))
        self.export_annotations_button.setEnabled(video_loaded and self.annotation_table.rowCount() > 0)

        # Update labels/displays if disabling
        if not video_loaded:
            self.video_display_label.setText("Video Not Loaded")
            self.video_display_label.setPixmap(QPixmap())
            self.video_display_label.setStyleSheet("background-color: black; color: white;")
            self.current_frame_label.setText("Frame: - / -")
            self.current_time_label.setText("Time: --:--:--.---")
            self.start_frame_display.setText("Start: -")
            self.end_frame_display.setText("End: -")
            self.annotation_table.setRowCount(0)
            self.annotations = []
            self.current_start_frame = None
            self.current_end_frame = None
            self.unsaved_changes = False
            self.video_slider.setRange(0,0)
            self.goto_frame_spinbox.setRange(0,0)

    # --- File and Video Handling ---
    def _select_folder(self, new_folder_path: Path):
        if new_folder_path == self.selected_folder_path: return

        # *** MODIFICATION START ***
        # Check unsaved changes *before* changing folder
        if self.current_video_path and not self._check_unsaved_changes():
            logging.info("Folder change cancelled due to unsaved changes.")
            return # Don't change folder if user cancels
        # *** MODIFICATION END ***


        logging.info(f"Folder selected: {new_folder_path}")
        self.selected_folder_path = new_folder_path
        self.selected_folder_label.setText(f"Folder: {self.selected_folder_path}")
        self.selected_folder_label.setToolTip(str(self.selected_folder_path))

        # Reset video-specific state (handled by _on_video_selected(0) or loading new)
        self.video_player.release() # Release player
        self._video_frame_count = 0
        self._video_fps = 0.0
        self.video_files_in_folder = []
        self.current_video_path = None
        self.video_select_combo.clear()
        self.annotations = []
        self._update_annotation_table()
        # *** MODIFICATION START ***
        self._blind_mode_mapping = {} # Clear mapping
        self._video_annotation_status = {} # Clear status cache
        # *** MODIFICATION END ***
        self._update_controls_state() # Update UI state (disables video controls)

        self._populate_video_dropdown() # Populate video dropdown with files in the folder

    def _browse_folder(self):
        """ Opens a dialog to select a folder containing videos. """
        logging.info("Browse folder button clicked.")
        start_path = str(self.selected_folder_path) if self.selected_folder_path else str(Path.home())
        folder_path_str = QFileDialog.getExistingDirectory(self, "Select Folder", start_path)

        if folder_path_str:
            new_folder_path = Path(folder_path_str)
            self._select_folder(new_folder_path)
        else:
            logging.info("Folder selection cancelled.")

    # *** MODIFICATION START ***
    # Updated function signature to accept internal calls without args
    def _populate_video_dropdown(self, _=None): # Accept optional arg from signal
        """
        Finds video files, checks for annotations, and populates the dropdown,
        handling normal and blind modes.
        """
        if not self.selected_folder_path: return

        # Block signals to prevent recursive calls during population
        self.video_select_combo.blockSignals(True)
        self.video_select_combo.clear()
        self._blind_mode_mapping = {} # Clear previous mapping
        self._video_annotation_status = {} # Clear status cache

        videos_path = Path(os.path.join(self.selected_folder_path, "videos"))
        logging.info(f"Scanning for videos and annotations in: {videos_path}")
        self.video_files_in_folder = []
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv', '*.mpg', '*.mpeg']
        temp_video_list: List[Tuple[Path, bool]] = [] # Store path and annotation status

        # Step 1: Find videos and check for corresponding annotations
        target_annotations_dir = self.selected_folder_path / "annotated_behaviors"
        for ext in video_extensions:
            try:
                found_files = list(videos_path.glob(ext.lower())) + list(videos_path.glob(ext.upper()))
                unique_files = list(set(found_files))
                for video_path in unique_files:
                    # Check for corresponding annotation CSV
                    video_stem = video_path.stem
                    annotation_filename = f"{video_stem}_annotations.csv"
                    annotation_path = target_annotations_dir / annotation_filename
                    has_annotation = annotation_path.exists()
                    temp_video_list.append((video_path, has_annotation))
                    self._video_annotation_status[video_path] = has_annotation # Cache status
            except Exception as e:
                logging.error(f"Error searching for '{ext}' files or checking annotations in {videos_path}: {e}")

        temp_video_list.sort(key=lambda item: item[0].name) # Sort by original name
        self.video_files_in_folder = [item[0] for item in temp_video_list] # Update main list

        # Step 2: Populate dropdown based on blind mode
        is_blind = self.blind_mode_checkbox.isChecked()
        if self.video_files_in_folder:
            logging.info(f"Found {len(self.video_files_in_folder)} video file(s). Blind mode: {is_blind}")
            self.video_select_combo.addItem("Select a video...")

            # Prepare items for dropdown (name, actual_path)
            dropdown_items: List[Tuple[str, Path]] = []
            if is_blind:
                # Create shuffled indices
                indices = list(range(len(temp_video_list)))
                random.shuffle(indices)
                for i, original_index in enumerate(indices):
                    actual_path, has_annotation = temp_video_list[original_index]
                    checkmark = "✓ " if has_annotation else "  "
                    # Use generic names but keep track of the real path
                    displayed_name = f"{checkmark}Video {i + 1}"
                    dropdown_items.append((displayed_name, actual_path))
                    # Store mapping from displayed name to actual path
                    self._blind_mode_mapping[displayed_name] = actual_path
            else:
                # Normal mode: Use actual names with checkmarks
                for actual_path, has_annotation in temp_video_list:
                    checkmark = "✓ " if has_annotation else "  "
                    displayed_name = f"{checkmark}{actual_path.name}"
                    dropdown_items.append((displayed_name, actual_path))
                    # Mapping is direct in normal mode, but store for consistency if needed
                    self._blind_mode_mapping[displayed_name] = actual_path

            # Add items to the dropdown
            for displayed_name, _ in dropdown_items:
                 self.video_select_combo.addItem(displayed_name)

            self.status_bar.showMessage(f"Found {len(self.video_files_in_folder)} video(s). Select one to load.", 5000)
        else:
            logging.warning(f"No video files found in {videos_path}.")
            self.video_select_combo.addItem("No videos found in folder")
            self.status_bar.showMessage("No video files found in the selected folder.", 5000)

        self.video_select_combo.blockSignals(False) # Re-enable signals
        self._update_controls_state()

        # If a video was previously selected, try to re-select it
        if self.current_video_path:
            found_idx = -1
            is_blind_now = self.blind_mode_checkbox.isChecked()
            for idx in range(1, self.video_select_combo.count()): # Skip placeholder
                item_text = self.video_select_combo.itemText(idx)
                mapped_path = self._get_actual_path_from_dropdown_text(item_text)
                if mapped_path == self.current_video_path:
                    found_idx = idx
                    break
            if found_idx != -1:
                 logging.debug(f"Re-selecting video at index {found_idx}")
                 self.video_select_combo.setCurrentIndex(found_idx)
            else:
                 logging.warning("Previously selected video not found after repopulating dropdown.")
                 self.video_select_combo.setCurrentIndex(0) # Select placeholder

    def _get_actual_path_from_dropdown_text(self, text: str) -> Optional[Path]:
        """Helper to get the actual video path from the displayed dropdown text."""
        return self._blind_mode_mapping.get(text)

    # *** MODIFICATION END ***

    def _on_video_selected(self, index: int):
        """ Handles the selection of a video from the dropdown. """
        # *** MODIFICATION START ***
        # Get the displayed text from the combo box item
        selected_item_text = self.video_select_combo.itemText(index)
        # Use the mapping (works for both blind and normal mode)
        selected_video_path = self._get_actual_path_from_dropdown_text(selected_item_text)

        if selected_video_path: # If a valid video path was resolved
        # *** MODIFICATION END ***
            if selected_video_path != self.current_video_path:
                logging.info(f"Video selected: {selected_video_path.name} (Dropdown text: '{selected_item_text}')")

                if not self._check_unsaved_changes():
                    # User cancelled, revert dropdown
                    # Need to find the index corresponding to the *previous* current_video_path
                    previous_idx = 0
                    if self.current_video_path:
                         for idx in range(self.video_select_combo.count()):
                             item_text = self.video_select_combo.itemText(idx)
                             mapped_path = self._get_actual_path_from_dropdown_text(item_text)
                             if mapped_path == self.current_video_path:
                                 previous_idx = idx
                                 break
                    self.video_select_combo.blockSignals(True)
                    self.video_select_combo.setCurrentIndex(previous_idx)
                    self.video_select_combo.blockSignals(False)
                    return

                self.status_bar.showMessage(f"Loading video: {selected_video_path.name}...")
                QApplication.processEvents()
                self._load_video(selected_video_path) # Call internal load wrapper
            else:
                logging.debug("Selected video is already loaded.")
        elif index == 0: # Placeholder "Select a video..." selected
             # *** MODIFICATION START ***
             # Check unsaved changes even when selecting placeholder
             if self.current_video_path and not self._check_unsaved_changes():
                 # User cancelled, revert dropdown to the one matching current_video_path
                 previous_idx = 0
                 for idx in range(self.video_select_combo.count()):
                     item_text = self.video_select_combo.itemText(idx)
                     mapped_path = self._get_actual_path_from_dropdown_text(item_text)
                     if mapped_path == self.current_video_path:
                         previous_idx = idx
                         break
                 self.video_select_combo.blockSignals(True)
                 self.video_select_combo.setCurrentIndex(previous_idx)
                 self.video_select_combo.blockSignals(False)
                 return
             # *** MODIFICATION END ***

             self.video_player.release() # Release player
             self._video_frame_count = 0
             self._video_fps = 0.0
             self.current_video_path = None
             self.annotations = [] # Clear annotations
             self.unsaved_changes = False
             self._update_annotation_table()
             self._update_controls_state()
        # else: "No videos found" or invalid item selected - do nothing

    def _load_video(self, video_path: Path):
         """Initiates video loading via the VideoPlayer."""
         # Clear previous state related to annotations etc.
         self.current_video_path = video_path # Store path immediately
         self.annotations = []
         self.unsaved_changes = False
         self._update_annotation_table()
         self.current_start_frame = None
         self.current_end_frame = None
         self.start_frame_display.setText("Start: -")
         self.end_frame_display.setText("End: -")
         # Reset UI elements handled by _handle_video_loaded or _handle_video_load_failed
         self.video_player.load_video(video_path)

    # --- Video Player Signal Handlers ---

    def _handle_video_loaded(self, frame_count: int, fps: float, duration_s: float):
        """Slot called when VideoPlayer successfully loads a video."""
        logging.info(f"GUI: Video loaded - {frame_count} frames, {fps:.2f} FPS")

        # --- Clear previous state BEFORE loading new ---
        self.annotations = []
        self.unsaved_changes = False
        self.current_start_frame = None
        self.current_end_frame = None
        self.start_frame_display.setText("Start: -")
        self.end_frame_display.setText("End: -")
        # --- End clearing state ---

        self._video_frame_count = frame_count
        self._video_fps = fps
        self.video_slider.setRange(0, max(0, frame_count - 1))
        self.goto_frame_spinbox.setRange(0, max(0, frame_count - 1))

        # --- Attempt to import annotations ---
        import_successful = self._import_annotations()
        if import_successful:
            status_message = f"Video loaded. {len(self.annotations)} previous annotations imported."
            # Ensure table is updated AFTER import attempt
            self._update_annotation_table()
        else:
             # Import failed or no file found, ensure table is empty/updated
             self._update_annotation_table() # Clears table if self.annotations is empty
             status_message = f"Video loaded. No previous annotations found or loaded."
        # --- End import attempt ---

        # Reset unsaved changes flag *after* import, as imported data is considered saved
        self.unsaved_changes = False

        self.status_bar.showMessage(status_message, 5000)
        self._update_controls_state() # Enable controls based on video loaded state

    def _handle_video_load_failed(self, error_message: str):
        """Slot called when VideoPlayer fails to load a video."""
        logging.error(f"GUI: Video load failed - {error_message}")
        QMessageBox.critical(self, "Video Load Error", error_message)
        self.current_video_path = None # Clear path as loading failed
        self._video_frame_count = 0
        self._video_fps = 0.0
        self.video_display_label.setText("Video Load Failed")
        self.video_display_label.setStyleSheet("background-color: darkred; color: white;")
        self.status_bar.showMessage("Video loading failed.", 5000)
        if self.video_select_combo.count() > 0:
            self.video_select_combo.setCurrentIndex(0) # Reset dropdown
        self._update_controls_state() # Disable controls

    def _handle_frame_changed(self, frame_no: int, timestamp_str: str, pixmap: QPixmap, label_size_hint: object):
        """Slot called when VideoPlayer emits a new frame."""
        # Update slider only if user isn't dragging it
        if not self._slider_is_pressed:
            self.video_slider.blockSignals(True) # Prevent slider change from seeking again
            self.video_slider.setValue(frame_no)
            self.video_slider.blockSignals(False)

        # Update labels
        max_frame_index = max(0, self._video_frame_count - 1)
        self.current_frame_label.setText(f"Frame: {frame_no} / {max_frame_index}")
        self.current_time_label.setText(f"Time: {timestamp_str}")

        # Update display (scale pixmap to fit label)
        if not pixmap.isNull():
            label_size = label_size_hint if label_size_hint else self.video_display_label.size()
            if label_size.isValid() and label_size.width() > 0 and label_size.height() > 0:
                 scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 self.video_display_label.setPixmap(scaled_pixmap)
            else: # Fallback if label size is invalid (e.g., during init)
                 self.video_display_label.setPixmap(pixmap) # Show original size
            self.video_display_label.setStyleSheet("background-color: black;") # Ensure normal style
            # Pass size hint back to player for next frame? if not label_size_hint and self.video_display_label.size().isValid():
                 # self.video_player.set_display_size_hint(self.video_display_label.size())

        else:
            # Handle null pixmap (e.g., read error)
            self.video_display_label.setText("Frame Read Error")
            self.video_display_label.setPixmap(QPixmap()) # Clear
            self.video_display_label.setStyleSheet("background-color: darkred; color: white;")

    def _handle_playback_state_changed(self, state: int):
        """Slot called when VideoPlayer changes playback state."""
        if state == STATE_PLAYING:
            if self._pause_icon: self.play_pause_button.setIcon(self._pause_icon)
            else: self.play_pause_button.setText("Pause")
            self.status_bar.showMessage("Playing...", 2000)
        elif state == STATE_PAUSED:
            if self._play_icon: self.play_pause_button.setIcon(self._play_icon)
            else: self.play_pause_button.setText("Play")
            self.status_bar.showMessage("Paused.", 2000)
        elif state == STATE_STOPPED:
             if self._play_icon: self.play_pause_button.setIcon(self._play_icon)
             else: self.play_pause_button.setText("Play")
             self.status_bar.showMessage("Stopped.", 2000)
             # Reset slider/labels if needed upon stop? Usually handled by release/load.

    def _handle_player_error(self, error_message: str):
        """Slot called for generic errors from VideoPlayer."""
        logging.error(f"GUI: Received player error - {error_message}")
        QMessageBox.warning(self, "Player Error", error_message)
        self.status_bar.showMessage(f"Player Error: {error_message}", 5000)

    # --- UI Interaction Slots ---
    def _on_slider_pressed(self):
        """Called when the user presses the mouse button on the slider."""
        if self.video_player.get_frame_count() <= 0: return
        self._slider_is_pressed = True
        # Pause playback if playing when user grabs slider
        if self.video_player.get_playback_state() == STATE_PLAYING:
            self.video_player.pause()

    def _on_slider_released(self):
        """Called when the user releases the mouse button on the slider."""
        if self.video_player.get_frame_count() <= 0: return
        self._slider_is_pressed = False
        # Seek video to the final slider position after release
        target_frame = self.video_slider.value()
        self.video_player.seek(target_frame)

    def _on_slider_value_changed(self, position: int):
        """Called when the slider's value changes (programmatically or by user drag)."""
        if self.video_player.get_frame_count() <= 0: return
        # Only seek if the user is dragging the slider
        if self._slider_is_pressed:
            self.video_player.seek(position)
        else:
            # If changed programmatically (by player signal), just update labels
            # Labels are updated in _handle_frame_changed now. pass
            pass # Keep this empty

    def _toggle_play_pause(self):
        """Toggles video playback via VideoPlayer."""
        if self.video_player.get_frame_count() <= 0: return
        current_state = self.video_player.get_playback_state()
        if current_state == STATE_PLAYING:
            self.video_player.pause()
        else: # Paused or Stopped
            self.video_player.play()

    def _skip_backward(self):
        """Skips backward by the amount specified in the skip spinbox."""
        if self.video_player.get_frame_count() <= 0: return
        # Pause playback if playing
        if self.video_player.get_playback_state() == STATE_PLAYING:
            self.video_player.pause()

        try:
            skip_amount = self.skip_amount_spinbox.value()
            current_frame = self.video_player.get_current_frame()
            target_frame = current_frame - skip_amount
            # seek handles clamping to 0 automatically
            self.video_player.seek(target_frame)
        except Exception as e:
            logging.error(f"Error during skip backward: {e}", exc_info=True)
            self._handle_player_error(f"Could not skip backward.\nError: {e}")

    def _skip_forward(self):
        """Skips forward by the amount specified in the skip spinbox."""
        if self.video_player.get_frame_count() <= 0: return
        # Pause playback if playing
        if self.video_player.get_playback_state() == STATE_PLAYING:
            self.video_player.pause()

        try:
            skip_amount = self.skip_amount_spinbox.value()
            current_frame = self.video_player.get_current_frame()
            target_frame = current_frame + skip_amount
            # seek handles clamping to max frame automatically
            self.video_player.seek(target_frame)
        except Exception as e:
            logging.error(f"Error during skip forward: {e}", exc_info=True)
            self._handle_player_error(f"Could not skip forward.\nError: {e}")

    def _on_goto_frame_clicked(self):
        """Handles the Go button click to jump to a specific frame via VideoPlayer."""
        if self.video_player.get_frame_count() <= 0: return
        try:
            target_frame = self.goto_frame_spinbox.value()
            # Validation is implicitly handled by seek's clamping
            logging.info(f"Go To Frame button clicked. Seeking to frame {target_frame}")
            self.video_player.seek(target_frame)
        except Exception as e:
            logging.error(f"Error in Go To Frame action: {e}\n{traceback.format_exc()}", exc_info=True)
            self._handle_player_error(f"Could not go to specified frame.\nError: {e}")


    # --- Annotation Logic ---
    def _mark_start(self):
        """Stores the current frame number as the potential start frame."""
        if self.video_player.get_frame_count() <= 0:
            self.status_bar.showMessage("Load a video first.", 2000)
            return
        current_frame = self.video_player.get_current_frame()
        if current_frame >= 0:
            self.current_start_frame = current_frame
            self.start_frame_display.setText(f"Start: {self.current_start_frame}")
            logging.debug(f"Marked start frame: {self.current_start_frame}")
            self.status_bar.showMessage(f"Start frame marked at {self.current_start_frame}.", 2000)
            if self.current_end_frame is not None and self.current_start_frame > self.current_end_frame:
                self.current_end_frame = None
                self.end_frame_display.setText("End: -")
                logging.debug("Cleared end frame as new start frame is later.")

    def _mark_end(self):
        """Stores the current frame number as the potential end frame."""
        if self.video_player.get_frame_count() <= 0:
            self.status_bar.showMessage("Load a video first.", 2000)
            return
        current_frame = self.video_player.get_current_frame()
        if current_frame >= 0:
            if self.current_start_frame is not None and current_frame < self.current_start_frame:
                QMessageBox.warning(self, "Invalid End Frame",
                                     f"End frame ({current_frame}) cannot be before start frame ({self.current_start_frame}).")
                return

            self.current_end_frame = current_frame
            self.end_frame_display.setText(f"End: {self.current_end_frame}")
            logging.debug(f"Marked end frame: {self.current_end_frame}")
            self.status_bar.showMessage(f"End frame marked at {self.current_end_frame}.", 2000)

    def _add_annotation(self):
        """Adds the currently marked start/end frames and identity to the annotations."""
        if self.video_player.get_frame_count() <= 0:
            self.status_bar.showMessage("Load a video first.", 2000)
            return

        behavior = self.behavior_combo.currentText()
        # Add more robust check if placeholder item exists
        if not behavior or (self.behavior_combo.currentIndex() == 0 and self.behavior_combo.count() > 1 and "select" in behavior.lower()):
             QMessageBox.warning(self, "Missing Information", "Please select a behavior.")
             return

        if self.current_start_frame is None:
            QMessageBox.warning(self, "Missing Information", "Please mark a start frame.")
            return
        if self.current_end_frame is None:
            QMessageBox.warning(self, "Missing Information", "Please mark an end frame.")
            return
        if self.current_start_frame > self.current_end_frame:
             QMessageBox.critical(self, "Logic Error", "Start frame cannot be after end frame.")
             return # Should be caught by _mark_end, but safety check

        new_annotation = {
            'Behavior': behavior,
            'Start Frame': self.current_start_frame,
            'End Frame': self.current_end_frame
        }
        logging.info(f"Adding annotation: {new_annotation}")
        self.annotations.append(new_annotation)
        self.unsaved_changes = True
        self._update_annotation_table()

        # Clear markers
        self.current_start_frame = None
        self.current_end_frame = None
        self.start_frame_display.setText("Start: -")
        self.end_frame_display.setText("End: -")
        self.status_bar.showMessage(f"Annotation '{behavior}' added.", 3000)

    # --- Table Logic ---
    def _update_annotation_table(self):
        """ Populates the annotation table from the internal self.annotations list. """
        if self._is_updating_table: return
        self._is_updating_table = True
        self.annotation_table.setSortingEnabled(False)
        self.annotation_table.setRowCount(0)

        if not self.annotations:
            self.annotation_table.setSortingEnabled(True)
            self._is_updating_table = False
            self._update_controls_state()
            return

        if not any(annotation['Behavior'] == 'video_end' for annotation in self.annotations):
            # Add "video_end" as a 1-frame event at the last frame
            last_frame = self.video_player.get_frame_count() - 1
            self.annotations.append({
                'Behavior': 'video_end',
                'Start Frame': last_frame,
                'End Frame': last_frame
            })
            logging.info("Added 'video_end' annotation at the last frame.")

        self.annotation_table.setRowCount(len(self.annotations))
        fps = self.video_player.get_fps() # Get current FPS

        for row_idx, annotation in enumerate(self.annotations):
            behavior = annotation.get('Behavior', 'N/A')
            start_frame = annotation.get('Start Frame', -1)
            end_frame = annotation.get('End Frame', -1)

            duration_s = 0.0
            if start_frame >= 0 and end_frame >= start_frame and fps > 0:
                duration_s = (end_frame - start_frame + 1) / fps
            duration_str = f"{duration_s:.3f}" if duration_s >= 0 else "N/A"

            item_behavior = QTableWidgetItem(behavior)
            item_start = QTableWidgetItem(str(start_frame))
            item_end = QTableWidgetItem(str(end_frame))
            item_duration = QTableWidgetItem(duration_str)

            # Set flags
            item_behavior.setFlags(item_behavior.flags() & ~Qt.ItemIsEditable)
            item_start.setFlags(item_start.flags() | Qt.ItemIsEditable)
            item_end.setFlags(item_end.flags() | Qt.ItemIsEditable)
            item_duration.setFlags(item_duration.flags() & ~Qt.ItemIsEditable)

            # Alignment
            item_start.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_end.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_duration.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Set items
            self.annotation_table.setItem(row_idx, COL_BEHAVIOR, item_behavior)
            self.annotation_table.setItem(row_idx, COL_START_FRAME, item_start)
            self.annotation_table.setItem(row_idx, COL_END_FRAME, item_end)
            self.annotation_table.setItem(row_idx, COL_DURATION, item_duration)

            # Store original index in UserRole of a non-editable item (Behavior)
            item_behavior.setData(Qt.UserRole, row_idx)

        self.annotation_table.setSortingEnabled(True)
        self._is_updating_table = False
        self._update_controls_state()

    def _on_table_selection_changed(self):
        """ Slot when table selection changes - jump video to start frame. """
        self._update_controls_state() # Update button states
        selected_items = self.annotation_table.selectedItems()
        if not selected_items: return

        selected_row = selected_items[0].row()
        start_frame_item = self.annotation_table.item(selected_row, COL_START_FRAME)

        if start_frame_item:
            try:
                target_frame = int(start_frame_item.text())
                logging.debug(f"Table selection changed: row {selected_row}, seeking to start frame {target_frame}")
                # Don't pause if just selecting, let user control playback
                self.video_player.seek(target_frame)
            except ValueError:
                logging.error(f"Error parsing frame number from table cell: {start_frame_item.text()}")
            except Exception as e:
                 logging.error(f"Error seeking video on table selection: {e}", exc_info=True)

    def _on_table_cell_clicked(self, row: int, column: int):
        """ Slot when a specific cell is clicked. Jump to end frame if it's that column. """
        if column == COL_END_FRAME:
            end_frame_item = self.annotation_table.item(row, COL_END_FRAME)
            if end_frame_item:
                try:
                    target_frame = int(end_frame_item.text())
                    logging.debug(f"End Frame cell clicked (Row {row}), seeking to end frame {target_frame}")
                    self.video_player.seek(target_frame)
                except ValueError:
                     logging.error(f"Error parsing end frame number from table cell: {end_frame_item.text()}")
                except Exception as e:
                     logging.error(f"Error seeking video on end frame cell click: {e}", exc_info=True)

    def _on_table_item_changed(self, item: QTableWidgetItem):
        """ Slot when a table cell (Start Frame, End Frame) is edited. """
        if self._is_updating_table: return

        row = item.row()
        col = item.column()
        behavior_item = self.annotation_table.item(row, COL_BEHAVIOR)
        if not behavior_item:
            logging.error(f"Cannot find behavior item for edited row {row}. Reverting table.")
            self._update_annotation_table(); return

        original_index = behavior_item.data(Qt.UserRole)
        if original_index is None or not (0 <= original_index < len(self.annotations)):
            logging.error(f"Invalid original index {original_index} for edited row {row}. Reverting table.")
            self._update_annotation_table(); return

        annotation_to_update = self.annotations[original_index]
        needs_table_revert = False
        change_made = False
        max_frame = self.video_player.get_frame_count() - 1

        try:
            if col == COL_START_FRAME or col == COL_END_FRAME:
                new_value = int(item.text())

                other_col = COL_END_FRAME if col == COL_START_FRAME else COL_START_FRAME
                other_item = self.annotation_table.item(row, other_col)
                if not other_item: raise ValueError("Cannot find corresponding frame item.")
                other_value = int(other_item.text())

                start_frame, end_frame = (new_value, other_value) if col == COL_START_FRAME else (other_value, new_value)

                if not (0 <= start_frame <= max_frame and 0 <= end_frame <= max_frame):
                    QMessageBox.warning(self, "Input Error", f"Frame numbers must be between 0 and {max_frame}.")
                    needs_table_revert = True
                elif start_frame > end_frame:
                    QMessageBox.warning(self, "Input Error", f"Start frame ({start_frame}) cannot be after end frame ({end_frame}).")
                    needs_table_revert = True
                else:
                    updated = False
                    if start_frame != annotation_to_update.get('Start Frame'):
                        annotation_to_update['Start Frame'] = start_frame
                        updated = True
                    if end_frame != annotation_to_update.get('End Frame'):
                        annotation_to_update['End Frame'] = end_frame
                        updated = True

                    if updated:
                        logging.info(f"Updated annotation {original_index} -> Start={start_frame}, End={end_frame}")
                        change_made = True # Internal data modified

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Frame numbers must be integers.")
            needs_table_revert = True
        except Exception as e:
            logging.error(f"Error updating annotation from table edit: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error updating annotation:\n{e}")
            needs_table_revert = True

        finally:
            # Refresh table if needed (revert or duration change)
            if needs_table_revert or change_made:
                 # Use blockSignals to prevent infinite loops if _update triggers signals
                 self.annotation_table.blockSignals(True)
                 self._update_annotation_table() # Refresh the whole table for consistency
                 self.annotation_table.blockSignals(False)
            if change_made:
                 self.unsaved_changes = True

    def _remove_annotation(self):
        """ Removes the selected annotation. """
        selected_rows = self.annotation_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Action Failed", "Select an annotation row to remove.")
            return

        selected_row_idx = selected_rows[0].row()
        behavior_item = self.annotation_table.item(selected_row_idx, COL_BEHAVIOR)
        if not behavior_item:
             logging.error(f"Cannot find behavior item for selected row {selected_row_idx}. Cannot remove.")
             return

        original_index = behavior_item.data(Qt.UserRole)
        if original_index is None or not (0 <= original_index < len(self.annotations)):
             logging.error(f"Invalid original index {original_index} for selected row {selected_row_idx}. Cannot remove.")
             return

        annotation_to_remove = self.annotations[original_index]
        behavior = annotation_to_remove.get('Behavior', '?')
        start_f = annotation_to_remove.get('Start Frame', '?')
        end_f = annotation_to_remove.get('End Frame', '?')

        reply = QMessageBox.question(self, "Confirm Removal",
                                     f"Remove annotation:\nBehavior: {behavior}\nFrames: [{start_f} - {end_f}]?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                logging.info(f"Removing annotation at original index {original_index}")
                del self.annotations[original_index]
                self.unsaved_changes = True
                self._update_annotation_table() # Refresh table (indices in UserRole will be wrong until refresh)
                self.status_bar.showMessage("Annotation removed.", 3000)
            except IndexError:
                 logging.error(f"IndexError removing annotation original index {original_index}. List len: {len(self.annotations)}")
                 QMessageBox.critical(self, "Error", "Failed to remove annotation (index error).")
            except Exception as e:
                 logging.error(f"Error removing annotation: {e}", exc_info=True)
                 QMessageBox.critical(self, "Error", f"Unexpected error during removal:\n{e}")

    def _import_annotations(self) -> bool:
        """
        Attempts to import annotations for the current video from the default location. Updates self.annotations if successful.

        Returns:
            bool: True if annotations were found and loaded successfully, False otherwise.
        """
        if not self.current_video_path or not self.selected_folder_path:
            logging.warning("Import annotations skipped: Video path or project path missing.")
            return False

        try:
            project_directory = self.selected_folder_path
            target_directory = project_directory / "annotated_behaviors"
            video_stem = self.current_video_path.stem
            filename = f"{video_stem}_annotations.csv"
            import_path = target_directory / filename

            if not import_path.exists():
                logging.info(f"No annotation file found at: {import_path}")
                self.annotations = [] # Ensure annotations are empty
                return False # No file found is not an error, just no data

            logging.info(f"Found annotation file, attempting import from: {import_path}")

            # Read the CSV
            try:
                df = pd.read_csv(import_path, delimiter=',')
                logging.info(df.columns)
            except pd.errors.EmptyDataError:
                logging.warning(f"Annotation file is empty: {import_path}")
                self.annotations = []
                return False # Empty file is like no annotations
            except Exception as read_err: # Catch other potential pandas read errors
                logging.error(f"Error reading CSV file {import_path}: {read_err}", exc_info=True)
                raise # Re-raise to be caught by the outer try-except

            # Validate essential columns
            required_columns = ['Behavior', 'Start Frame', 'End Frame']
            if not all(col in df.columns for col in required_columns):
                logging.error(f"Annotation file missing required columns: {required_columns}. File: {import_path}")
                raise ValueError(f"Annotation file missing required columns: {required_columns}")

            # Convert to list of dictionaries and validate types
            imported_annotations = []
            # Use .itertuples() for efficiency and cleaner access
            for _, row in df.iterrows():
                 # Check if frame numbers are valid integers
                start_frame = int(row['Start Frame'])
                end_frame = int(row['End Frame'])
                behavior = str(row['Behavior'])

                # Add basic validation (optional, but good practice)
                if start_frame < 0 or end_frame < 0 or start_frame > end_frame:
                     logging.warning(f"Skipping invalid annotation entry in {import_path}: Start={start_frame}, End={end_frame}")
                     continue # Skip this row
                if not behavior:
                     logging.warning(f"Skipping annotation entry with missing behavior in {import_path}: Start={start_frame}, End={end_frame}")
                     continue # Skip this row

                imported_annotations.append({
                    'Behavior': behavior,
                    'Start Frame': start_frame,
                    'End Frame': end_frame
                    # 'Duration (s)' is recalculated in _update_annotation_table
                })

            self.annotations = imported_annotations
            logging.info(f"Successfully imported {len(self.annotations)} annotations.")
            return True

        except (FileNotFoundError, ValueError, KeyError, TypeError, AttributeError) as e: # Catch specific expected errors during processing
            logging.error(f"Failed to import or parse annotations from {import_path}: {e}", exc_info=True)
            QMessageBox.warning(self, "Import Warning", f"Could not load previous annotations for this video.\nFile might be missing, corrupted, or in the wrong format.\n\nError: {e}")
            self.annotations = [] # Clear potentially partially loaded annotations
            return False
        except Exception as e: # Catch unexpected errors
            logging.critical(f"Unexpected error during annotation import: {e}", exc_info=True)
            QMessageBox.critical(self, "Import Error", f"An unexpected error occurred while importing annotations:\n{e}")
            self.annotations = []
            return False

    def _export_annotations(self) -> bool:
        """
        Exports the current annotations for the loaded video to a CSV file
        in the 'project_directory/annotated_behaviors' folder without user prompt.
        """
        if not self.annotations:
            QMessageBox.information(self, "Export Info", "No annotations available to export for the current video.")
            return False # Indicate export didn't happen

        if not self.current_video_path:
            QMessageBox.warning(self, "Export Error", "Cannot determine filename, no video loaded.")
            return False # Indicate export didn't happen

        if not self.selected_folder_path:
             QMessageBox.critical(self, "Export Error", "Cannot determine project directory (selected folder path is missing).")
             logging.error("Export failed: self.selected_folder_path is None.")
             return False

        # --- Determine save location automatically ---
        try:
            project_directory = self.selected_folder_path
            target_directory = project_directory / "annotated_behaviors"

            # Ensure the target directory exists
            target_directory.mkdir(parents=True, exist_ok=True)
            logging.info(f"Ensured target directory exists: {target_directory}")

            video_stem = self.current_video_path.stem
            filename = f"{video_stem}_annotations.csv"
            save_path = target_directory / filename

        except OSError as e:
             logging.error(f"Error creating target directory {target_directory}: {e}", exc_info=True)
             QMessageBox.critical(self, "Export Failed", f"Could not create target directory:\n{target_directory}\n\nError: {e}")
             self.status_bar.showMessage("Annotation export failed (Directory Error).", 5000)
             return False
        except Exception as e: # Catch unexpected errors during path creation
             logging.error(f"Error determining save path: {e}", exc_info=True)
             QMessageBox.critical(self, "Export Failed", f"An unexpected error occurred while determining the save path:\n{e}")
             self.status_bar.showMessage("Annotation export failed (Path Error).", 5000)
             return False
        # --- End of automatic location determination ---

        logging.info(f"Automatically exporting {len(self.annotations)} annotations to: {save_path}")
        self.status_bar.showMessage(f"Saving annotations to {save_path.name}...")
        QApplication.processEvents() # Update status bar before potentially long save

        try:
            # Create DataFrame from the list of dictionaries
            export_df = pd.DataFrame(self.annotations)

            # Calculate Duration column if FPS is valid
            fps = self.video_player.get_fps()
            if fps > 0:
                export_df['Duration (s)'] = (export_df['End Frame'] - export_df['Start Frame'] + 1) / fps
            else:
                export_df['Duration (s)'] = pd.NA # Indicate unknown duration

            # Ensure desired column order
            columns_ordered = ['Behavior', 'Start Frame', 'End Frame', 'Duration (s)']
            # Filter columns to ensure they exist
            export_df = export_df[[col for col in columns_ordered if col in export_df.columns]]

            export_df.sort_values(by=['Start Frame'], inplace=True)
            export_df.to_csv(save_path, index=False, float_format='%.3f')

            self.unsaved_changes = False # Reset flag after successful save
            # Use a less intrusive success message or remove it if saving automatically is the norm
            # Option 1: Status bar message only
            # self.status_bar.showMessage(f"Annotations saved to {save_path.name}", 5000)
            # Option 2: Keep the message box for explicit confirmation
            QMessageBox.information(self, "Export Successful", f"Annotations automatically saved to:\n{save_path}")
            self.status_bar.showMessage(f"Annotations exported successfully to {save_path.name}", 5000)

            return True # Indicate success

        except PermissionError:
            logging.error(f"Permission denied when trying to save to {save_path}.", exc_info=True)
            QMessageBox.critical(self, "Export Failed", f"Permission denied.\nCould not save annotations to:\n{save_path}\n\nPlease check file permissions.")
            self.status_bar.showMessage("Annotation export failed (Permission Denied).", 5000)
            return False # Indicate failure
        except IOError as e:
            logging.error(f"IOError during export to {save_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Failed", f"An error occurred while writing the file:\n{save_path}\n\nError: {e}\n(Is the disk full?)")
            self.status_bar.showMessage("Annotation export failed (I/O Error).", 5000)
            return False # Indicate failure
        except Exception as e:
            logging.error(f"Failed to export annotations to {save_path}: {e}\n{traceback.format_exc()}", exc_info=True)
            QMessageBox.critical(self, "Export Failed", f"An unexpected error occurred during export:\n{save_path}\n\nError: {e}")
            self.status_bar.showMessage("Annotation export failed (Unexpected Error).", 5000)
            return False # Indicate failure

    # --- Robustness Helper ---
    def _check_unsaved_changes(self) -> bool:
        """ Checks for unsaved changes and prompts the user. Returns True if okay to proceed. """
        if not self.unsaved_changes: return True
        if not self.current_video_path: return True # Should not happen

        video_name = self.current_video_path.name
        reply = QMessageBox.question(self, "Unsaved Changes",
                                     f"Save changes for '{video_name}' before proceeding?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)

        if reply == QMessageBox.Save:
            logging.info("User chose Save.")
            return self._export_annotations() # Proceed only if save succeeds
        elif reply == QMessageBox.Discard:
            logging.info("User chose Discard.")
            self.unsaved_changes = False
            return True # Okay to proceed
        else: # Cancel
            logging.info("User chose Cancel.")
            return False # Cancel the operation

    # --- Event Handlers ---
    def keyPressEvent(self, event):
        """ Handle keyboard shortcuts. """
        key = event.key()
        modifiers = event.modifiers()

        if self.annotation_table.state() == QAbstractItemView.EditingState:
            super().keyPressEvent(event); return

        if self.video_player.get_frame_count() > 0: # Only if video loaded
             if key == Qt.Key_Space:
                 self._toggle_play_pause()
             elif key == Qt.Key_Left:
                 self.video_player.prev_frame()
             elif key == Qt.Key_Right:
                 self.video_player.next_frame()
             elif key == Qt.Key_S and not modifiers:
                 self._mark_start()
             elif key == Qt.Key_E and not modifiers:
                 self._mark_end()
             # Add 'A' for add annotation maybe?
             # elif key == Qt.Key_A and not modifiers:
             #     self._add_annotation()
             else:
                 super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """ Handle window closing event, checking for unsaved changes. """
        logging.info("AnnotationWindow close event triggered.")
        if not self._check_unsaved_changes():
            logging.info("Close event ignored due to user cancellation.")
            event.ignore()
            return

        logging.info("Cleaning up AnnotationWindow before closing...")
        self.video_player.release() # Release video resources via player
        logging.info("Annotation window closed.")
        event.accept()

# === END FILE: scripts/behavior_annotator/annotation_window.py ===