# === START FILE: scripts/behavior_annotator/gui.py ===
# gui.py
"""
Main entry point for the Behavior Annotator application.
Performs dependency checks, sets up logging, and launches the GUI window.
"""
import logging
import sys
import traceback
import os

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# --- Dependency Check ---
PYQT5_AVAILABLE = False
CV2_AVAILABLE = False
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QCoreApplication
    PYQT5_AVAILABLE = True
    # Check OpenCV separately
    import cv2
    CV2_AVAILABLE = True
except ImportError as e:
    # Fallback for console message if GUI cannot start
    dep_error_msg = f"Error importing dependencies: {e}\n\nPlease ensure PyQt5 and opencv-python are installed."
    print(dep_error_msg, file=sys.stderr)
    # Attempt Tkinter message box as a last resort
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw() # Hide the main Tk window
        messagebox.showerror("Dependency Error", dep_error_msg)
        root.destroy()
    except ImportError:
        print("Tkinter not available. Cannot show graphical error message.", file=sys.stderr)
    # Exit here if core dependencies are missing
    sys.exit(f"Missing critical dependencies: {e}")

# --- Now import the main window class (only if dependencies are met) ---
if PYQT5_AVAILABLE and CV2_AVAILABLE:
    try:
        from annotation_window import AnnotationWindow
    except ImportError as e:
         # Handle potential issues with local imports if structure is wrong
         logging.critical(f"Failed to import AnnotationWindow: {e}. Check file structure/imports.", exc_info=True)
         QMessageBox.critical(None, "Import Error", f"Failed to import application components:\n{e}\n\nCheck installation and file structure.")
         sys.exit(1)

# --- Main Application Launcher ---
def launch_annotator_gui():
    """ Creates and runs the PyQt5 application and the main AnnotationWindow. """
    if not PYQT5_AVAILABLE or not CV2_AVAILABLE:
         # This case should technically be caught earlier, but as a safeguard:
         logging.critical("Core dependencies (PyQt5, OpenCV) not available. Cannot launch GUI.")
         # Error messages should have already been shown.
         sys.exit("Error: Core dependencies missing.")

    # Ensure only one QApplication instance exists
    app = QApplication.instance()
    if app is None:
        logging.debug("Creating new QApplication instance.")
        app = QApplication(sys.argv)
    else:
        logging.debug("Using existing QApplication instance.")
   
    QCoreApplication.setApplicationName("Behavior Annotator")
    # QCoreApplication.setOrganizationName("Your Organization") # Optional

    # --- Dark Mode Stylesheet ---
    # pia fucked around here with this dark mode vibe
    # Background: Black (#000000 or a very dark gray like #121212)
    # Text: White (#FFFFFF) or light gray (#E0E0E0)
    # Accent (e.g., for buttons, highlights): Purple (e.g., #9B59B6, #8E44AD)
    dark_stylesheet = """
        QMainWindow {
            background-color: #1E1E1E; /* Very dark gray, almost black */
        }
        QWidget {
            background-color: #1E1E1E; /* Default background for other widgets */
            color: #E0E0E0; /* Light gray text for readability */
            font-size: 10pt;
        }
        QLabel {
            color: #E0E0E0; /* Light gray text */
            background-color: transparent; /* Ensure labels don't have their own background unless specified */
        }
        QPushButton {
            background-color: #3E3E3E; /* Darker gray for buttons */
            color: #E0E0E0;           /* Light text on buttons */
            border: 1px solid #555555; /* Subtle border */
            padding: 8px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #8A2BE2; /* BlueViolet for hover - a nice purple */
            color: #FFFFFF;           /* White text on hover */
            border: 1px solid #9B59B6;
        }
        QPushButton:pressed {
            background-color: #7B1FA2; /* Darker purple for pressed state */
        }
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #2C2C2C; /* Slightly lighter dark for input fields */
            color: #E0E0E0;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: url(:/qt-project.org/styles/commonstyle/images/down αρκεarrow-standard.png); /* Consider a custom arrow for dark mode */
        }
        QMenuBar {
            background-color: #2C2C2C;
            color: #E0E0E0;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        QMenuBar::item:selected { /* When hovered or expanded */
            background-color: #8A2BE2; /* Purple accent */
            color: #FFFFFF;
        }
        QMenu {
            background-color: #2C2C2C;
            color: #E0E0E0;
            border: 1px solid #555555;
        }
        QMenu::item {
            padding: 4px 20px 4px 20px;
        }
        QMenu::item:selected {
            background-color: #8A2BE2; /* Purple accent */
            color: #FFFFFF;
        }
        QToolTip {
            background-color: #000000; /* Black tooltip background */
            color: #E0E0E0;            /* Light gray text */
            border: 1px solid #555555;
            padding: 4px;
        }
        QMessageBox {
            background-color: #1E1E1E; /* Ensure QMessageBox background is dark */
            /* font-size: 10pt; /* You can adjust message box font if needed */
        }
        QMessageBox QLabel { /* Target QLabel specifically within QMessageBox if needed */
            background-color: transparent;
            color: #E0E0E0;
        }
        /* Add styling for other specific widgets as needed:
           QCheckBox, QRadioButton, QSlider, QProgressBar, QTabWidget, QScrollBar, etc.
        */
        QScrollBar:vertical {
            background: #2C2C2C;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            height: 0px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        QScrollBar:horizontal {
            background: #2C2C2C;
            height: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:horizontal {
            background: #555555;
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: none;
            width: 0px;
            subcontrol-position: left;
            subcontrol-origin: margin;
        }
    """
    app.setStyleSheet(dark_stylesheet)
    # --- End of Dark Mode Stylesheet ---

    logging.info("Initializing Annotation Window...")
    try:
        window = AnnotationWindow()
        window.show()
        logging.info("Annotation Window displayed. Starting event loop.")

        # Start the PyQt5 event loop
        exit_code = app.exec_()
        logging.info(f"PyQt application event loop finished with exit code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        # Catch-all for errors during window initialization or runtime
        logging.critical(f"Unhandled error during application execution: {e}\n{traceback.format_exc()}", exc_info=True)
        # Attempt to show a critical error message box using QMessageBox
        try:
             msg = QMessageBox()
             msg.setIcon(QMessageBox.Critical)
             msg.setWindowTitle("Application Error")
             msg.setText("An unexpected error occurred during execution.")
             msg.setInformativeText(f"{type(e).__name__}: {e}")
             msg.setDetailedText(traceback.format_exc())
             msg.setStandardButtons(QMessageBox.Ok)
             msg.exec_()
        except Exception as msg_e:
             # If even the message box fails, log it
             logging.error(f"Failed to show the critical error message box: {msg_e}")
        sys.exit(1) # Exit with a non-zero code

# --- Main Execution Block ---
if __name__ == "__main__":
    # Configure logging (basic setup)
    log_level = logging.INFO # Or dynamically set based on args/env
    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        # Optionally add a file handler
                        # handlers=[logging.StreamHandler(), logging.FileHandler("annotator.log")]
                        )

    print("Launching Behavior Annotator GUI...") # Console message
    logging.info("Starting Behavior Annotator application.")
    launch_annotator_gui() # Call the launcher function
    logging.info("Behavior Annotator application finished.")
    print("Behavior Annotator has closed.")

# === END FILE: scripts/behavior_annotator/gui.py ===