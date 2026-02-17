from PySide6.QtCore import Signal, QObject, QThread
import cv2
import csv
import os
import time
import shutil
from datetime import datetime


class Webcam_Signals(QObject):
    status_signal = Signal(str)


class Webcam_Capture_Thread(QThread):
    """
    QThread for webcam video capture synchronized with data recording.
    Camera must be opened on the main thread (macOS AVFoundation requirement)
    and passed via set_capture() before setting start_recording = True.
    """

    def __init__(self, fps=30.0):
        super(Webcam_Capture_Thread, self).__init__()

        self.signals = Webcam_Signals()

        self.target_fps = fps

        self.stop_flag = False
        self.start_recording = False
        self.stop_recording = False
        self.is_recording = False

        self.cap = None

        self.final_video_path = ""
        self.final_timestamps_path = ""

        self.temp_video_path = ""
        self.temp_timestamps_path = ""

    def set_capture(self, cap):
        """Set an already-opened cv2.VideoCapture (must be called from main thread)."""
        self.cap = cap

    def stop(self):
        self.stop_flag = True
        self.stop_recording = True
        time.sleep(1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.terminate()
        for f in [self.temp_video_path, self.temp_timestamps_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        print("Webcam capture thread terminated...")

    def run(self):
        while not self.stop_flag:

            if self.start_recording:
                self.start_recording = False
                self.is_recording = True

                if self.cap is None or not self.cap.isOpened():
                    self.signals.status_signal.emit(
                        "Webcam not available. Video will not be recorded.")
                    self.is_recording = False
                    continue

                temp_base = datetime.now().strftime("%Y%m%d_%H%M%S") + "_webcam_temp"
                self.temp_video_path = temp_base + ".avi"
                self.temp_timestamps_path = temp_base + "_timestamps.csv"

                actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                writer = cv2.VideoWriter(
                    self.temp_video_path, fourcc, self.target_fps,
                    (actual_w, actual_h))

                ts_file = open(self.temp_timestamps_path, 'w', newline='')
                ts_writer = csv.writer(ts_file)
                ts_writer.writerow(['frame_number', 'timestamp'])

                frame_number = 0
                frame_interval = 1.0 / self.target_fps

                self.signals.status_signal.emit("Webcam recording started.")

                while self.is_recording and not self.stop_flag:
                    loop_start = time.perf_counter()

                    ret, frame = self.cap.read()
                    if ret:
                        timestamp = datetime.now().isoformat()
                        writer.write(frame)
                        ts_writer.writerow([frame_number, timestamp])
                        frame_number += 1

                    if self.stop_recording:
                        self.is_recording = False
                        self.stop_recording = False
                        break

                    elapsed = time.perf_counter() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                self.cap.release()
                self.cap = None
                writer.release()
                ts_file.close()

                if self.final_video_path and os.path.exists(self.temp_video_path):
                    shutil.move(self.temp_video_path, self.final_video_path)
                if self.final_timestamps_path and os.path.exists(self.temp_timestamps_path):
                    shutil.move(self.temp_timestamps_path, self.final_timestamps_path)

                self.signals.status_signal.emit(
                    f"Webcam recording saved ({frame_number} frames).")

                self.final_video_path = ""
                self.final_timestamps_path = ""

            else:
                time.sleep(0.1)
