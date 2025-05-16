# === START FILE: scripts/behavior_annotator/video_player.py ===
# video_player.py
"""
Video Player class using OpenCV and PyQt signals for integration
into the Behavior Annotator GUI.
Handles video loading, playback control, frame seeking, and display.
"""
import logging
import traceback
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

# Import config constants and utilities
from config import DEFAULT_FALLBACK_FPS, STATE_PAUSED, STATE_PLAYING, STATE_STOPPED
from utils import format_timestamp

class VideoPlayer(QObject):
    """
    Handles video loading, playback, seeking, and frame extraction.
    Emits signals for GUI updates.
    """
    # Signals for communication with the GUI
    # Emits: frame_count, fps, duration_s
    videoLoaded = pyqtSignal(int, float, float)
    # Emits: error message string
    videoLoadFailed = pyqtSignal(str)
    # Emits: current_frame_number, current_timestamp_str, QPixmap_of_frame, label_size_hint (QSize)
    frameChanged = pyqtSignal(int, str, QPixmap, object) # Use object for QSize hint for robustness
    # Emits: new_playback_state (STATE_PLAYING, STATE_PAUSED, STATE_STOPPED)
    playbackStateChanged = pyqtSignal(int)
    # Emits: generic error message string
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_capture: Optional[cv2.VideoCapture] = None
        self._video_path: Optional[Path] = None
        self._fps: float = DEFAULT_FALLBACK_FPS
        self._frame_count: int = 0
        self._duration_s: float = 0.0
        self._current_frame_no: int = -1
        self._playback_speed: float = 1.0
        self._playback_state: int = STATE_STOPPED
        self._target_display_size: Optional[object] = None # Store QSize hint

        self._video_timer = QTimer(self)
        self._video_timer.timeout.connect(self._advance_frame)

    def _is_ready(self) -> bool:
        """Check if the video capture is initialized and opened."""
        return self._video_capture is not None and self._video_capture.isOpened()

    def _set_playback_state(self, state: int):
        """Sets the playback state and emits a signal if changed."""
        if state != self._playback_state:
            self._playback_state = state
            logging.debug(f"VideoPlayer: Playback state changed to {state}")
            self.playbackStateChanged.emit(self._playback_state)

    def _emit_frame(self, frame_no: int, cv_frame: Optional[np.ndarray]):
        """Converts frame to QPixmap and emits frameChanged signal."""
        if cv_frame is None:
            # Handle case where frame read might fail even if ret is true initially
            logging.warning(f"VideoPlayer: Attempted to display None frame at index {frame_no}.")
            # Optionally emit an empty pixmap or an error signal?
            # Let's emit with current frame number but empty pixmap for now.
            pixmap = QPixmap()
        else:
             pixmap = self._convert_cv_to_pixmap(cv_frame)

        # Format timestamp
        timestamp_str = "--:--:--.---"
        if self._fps > 0 and frame_no >= 0:
             time_s = frame_no / self._fps
             timestamp_str = format_timestamp(time_s)

        self._current_frame_no = frame_no
        self.frameChanged.emit(frame_no, timestamp_str, pixmap, self._target_display_size)

    def _convert_cv_to_pixmap(self, frame: np.ndarray) -> QPixmap:
        """Converts OpenCV frame (BGR) to QPixmap."""
        pixmap = QPixmap() # Default empty pixmap
        try:
            if not frame.flags['C_CONTIGUOUS']:
                frame = np.ascontiguousarray(frame)

            if len(frame.shape) == 3 and frame.shape[2] == 3: # Color
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888) # Use BGR directly
            elif len(frame.shape) == 2: # Grayscale
                h, w = frame.shape
                bytes_per_line = w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            else:
                logging.error(f"VideoPlayer: Unsupported frame shape {frame.shape}")
                return pixmap # Return empty

            pixmap = QPixmap.fromImage(qt_image)

        except Exception as e:
            logging.error(f"VideoPlayer: Error converting frame to QPixmap: {e}\n{traceback.format_exc()}", exc_info=True)
            # Return empty pixmap on error
        return pixmap

    def _read_and_emit_frame(self, frame_no: int):
        """Reads a specific frame, updates state, and emits."""
        if not self._is_ready(): return

        ret, frame = self._video_capture.read()
        if ret:
            self._emit_frame(frame_no, frame)
            # Check if this was the last frame
            if frame_no >= self._frame_count - 1 and self._playback_state == STATE_PLAYING:
                 logging.debug("VideoPlayer: Last frame reached during playback.")
                 self.pause() # Auto-pause at end
        else:
            logging.warning(f"VideoPlayer: Failed to read frame {frame_no} during operation.")
            # Handle read failure - maybe stop playback or emit error?
            if self._playback_state == STATE_PLAYING:
                self.pause()
            # Emit the previous frame number again, but with no pixmap? Or emit error?
            # Let's emit current frame number with empty pixmap
            self._emit_frame(self._current_frame_no, None)

    def _advance_frame(self):
        """Advances video by one frame during playback."""
        if not self._is_ready() or self._playback_state != STATE_PLAYING:
            self._video_timer.stop()
            return

        current_pos = self._current_frame_no
        if current_pos < self._frame_count - 1:
            # Read the frame *after* the current one. OpenCV advances implicitly.
            self._read_and_emit_frame(current_pos + 1)
        else:
            # Already at the last frame, stop timer
            logging.debug("VideoPlayer: Advance frame called at end, stopping timer.")
            self.pause()

    # --- Properties ---
    def get_fps(self) -> float:
        return self._fps

    def get_frame_count(self) -> int:
        return self._frame_count

    def get_duration(self) -> float:
        return self._duration_s

    def get_current_frame(self) -> int:
        """Returns the current frame number (0-based index)."""
        return self._current_frame_no

    def get_playback_state(self) -> int:
        return self._playback_state

    # --- Control Methods ---
    def set_display_size_hint(self, size: object):
        """Stores the target QSize for scaling hints (optional)."""
        self._target_display_size = size

    def load_video(self, video_path: Path):
        """Loads the video file."""
        logging.info(f"VideoPlayer: Attempting to load {video_path}")
        self.release() # Ensure any previous video is released
        self._video_path = video_path

        try:
            self._video_capture = cv2.VideoCapture(str(video_path))
            if not self._is_ready():
                raise IOError(f"Could not open video file: {video_path}")

            # Get properties
            self._fps = self._video_capture.get(cv2.CAP_PROP_FPS)
            self._frame_count = int(self._video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

            # Validate
            if self._fps <= 0:
                logging.warning(f"Video reported invalid FPS ({self._fps}). Using fallback: {DEFAULT_FALLBACK_FPS}.")
                self._fps = DEFAULT_FALLBACK_FPS
            if self._frame_count <= 0:
                # Attempt calculation from duration
                # Note: Reading duration before frames might be unreliable with some backends
                duration_msec = self._video_capture.get(cv2.CAP_PROP_POS_MSEC) # Check initial pos
                if duration_msec > 0: logging.warning("Video reported non-zero POS_MSEC at start.")
                # Try seeking to end and reading msec? Risky. Let's rely on frame count first.
                # If frame count fails, try calculating from reported duration if available
                backend_duration = self._video_capture.get(cv2.CAP_PROP_POS_AVI_RATIO) # This might not be duration
                # A more reliable way might be using ffprobe if available, but sticking to cv2:
                if self._fps > 0: # Estimate based on seeking near end? Complex.
                     logging.warning(f"Video reported invalid frame count ({self._frame_count}). Trying to estimate...")
                     # As a last resort, try reading frames until failure (VERY SLOW for long videos)
                     # Or just raise error if initial count is bad. Let's raise error for now.
                     if self._frame_count <= 0: # Check again after FPS validation
                          raise ValueError("Could not determine valid frame count.")

            self._duration_s = self._frame_count / self._fps if self._fps > 0 else 0.0
            video_w = int(self._video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_h = int(self._video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

            logging.info(f"VideoPlayer: Loaded {video_w}x{video_h}, {self._frame_count} frames, {self._duration_s:.2f}s, {self._fps:.2f} FPS")

            # Seek to first frame and emit loaded signal
            self.seek(0) # This will emit the first frame
            self._set_playback_state(STATE_PAUSED) # Treat as paused at start
            self.videoLoaded.emit(self._frame_count, self._fps, self._duration_s)

        except Exception as e:
            logging.error(f"VideoPlayer: Failed to load video: {video_path}\nError: {e}\n{traceback.format_exc()}", exc_info=True)
            self.release() # Clean up on failure
            self.videoLoadFailed.emit(f"Failed to load video: {video_path.name}\nError: {e}")

    def release(self):
        """Releases video resources."""
        if self._video_timer.isActive():
            self._video_timer.stop()
        if self._video_capture and self._video_capture.isOpened():
            logging.debug("VideoPlayer: Releasing video capture.")
            try:
                self._video_capture.release()
            except Exception as e:
                logging.error(f"VideoPlayer: Error releasing video capture: {e}")
        self._video_capture = None
        self._video_path = None
        self._frame_count = 0
        self._duration_s = 0.0
        self._fps = DEFAULT_FALLBACK_FPS
        self._current_frame_no = -1
        self._set_playback_state(STATE_STOPPED)

    def seek(self, frame_no: int):
        """Seeks to a specific frame and emits the frameChanged signal."""
        if not self._is_ready():
            logging.warning("VideoPlayer: Seek attempted but not ready.")
            return

        target_frame = max(0, min(frame_no, self._frame_count - 1))
        logging.debug(f"VideoPlayer: Seeking to frame {target_frame}...")

        try:
            # Set position and read the frame at that exact position
            self._video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            self._read_and_emit_frame(target_frame)

        except Exception as e:
            logging.error(f"VideoPlayer: Error during seek to frame {target_frame}: {e}\n{traceback.format_exc()}", exc_info=True)
            self.errorOccurred.emit(f"Could not seek to frame {target_frame}.\nError: {e}")

    def play(self):
        """Starts or resumes playback."""
        if not self._is_ready() or self._playback_state == STATE_PLAYING:
            return

        # If at end, seek to start before playing
        if self._current_frame_no >= self._frame_count - 1:
             logging.info("VideoPlayer: Play called at end, restarting from frame 0.")
             self.seek(0)
             # Ensure seek finishes and emits frame before starting timer? Potential race condition.
             # Let's assume seek completes reasonably fast.

        timer_interval_ms = int(1000 / (self._fps * self._playback_speed)) if self._fps > 0 else 40
        timer_interval_ms = max(10, timer_interval_ms) # Min interval

        self._video_timer.start(timer_interval_ms)
        self._set_playback_state(STATE_PLAYING)
        logging.info(f"VideoPlayer: Play started (Interval: {timer_interval_ms}ms)")

    def pause(self):
        """Pauses playback."""
        if not self._is_ready() or self._playback_state != STATE_PLAYING:
            return

        self._video_timer.stop()
        self._set_playback_state(STATE_PAUSED)
        logging.info("VideoPlayer: Playback paused.")

    def set_speed(self, speed: float):
        """Sets the playback speed multiplier."""
        self._playback_speed = max(0.1, min(speed, 10.0)) # Clamp speed
        logging.debug(f"VideoPlayer: Speed set to {self._playback_speed:.1f}x")
        # If playing, update timer interval
        if self._playback_state == STATE_PLAYING:
            timer_interval_ms = int(1000 / (self._fps * self._playback_speed)) if self._fps > 0 else 40
            timer_interval_ms = max(10, timer_interval_ms)
            self._video_timer.setInterval(timer_interval_ms)
            logging.debug(f"VideoPlayer: Timer interval updated to {timer_interval_ms}ms")

    def next_frame(self):
        """Steps forward one frame."""
        if not self._is_ready(): return
        if self._playback_state == STATE_PLAYING: self.pause()

        next_f = min(self._current_frame_no + 1, self._frame_count - 1)
        if next_f != self._current_frame_no:
             self.seek(next_f)

    def prev_frame(self):
        """Steps backward one frame."""
        if not self._is_ready(): return
        if self._playback_state == STATE_PLAYING: self.pause()

        prev_f = max(self._current_frame_no - 1, 0)
        if prev_f != self._current_frame_no:
             self.seek(prev_f)
# === END FILE: scripts/behavior_annotator/video_player.py ===