#
# REVISED FILE: registerpage.py
#
import os
import cv2
import io
import zipfile
import requests
import time
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QDialog, QProgressBar
)
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot

# [NEW] Import theme instead of hard-coding colors
import theme 

# [NEW] Path to your assets
CASCADE_PATH = "assets/haarcascade_frontalface_default.xml"
API_URL = "https://morsz.azeroth.site" # Your server URL


# [NEW] Worker thread for face registration
# This now emits the video frame to be displayed
class FaceRegisterWorker(QObject):
    """
    Runs face capture and network upload in a separate thread 
    to avoid freezing the GUI.
    """
    # Signal(QImage, str) - emits (video_frame, status_text)
    progress_frame = Signal(QImage, str)
    # Signal(int) - emits percentage for progress bar
    progress_value = Signal(int)
    # Signal(bool, str) - emits (success, message)
    finished = Signal(bool, str)
    
    def __init__(self, username, camera_index=0):
        super().__init__()
        self.username = username
        self.camera_index = camera_index # Use the selected camera index
        self.images_to_capture = 50
        self._is_running = True

    @Slot()
    def run(self):
        """This is the function that runs in the new thread."""
        try:
            if not os.path.exists(CASCADE_PATH):
                raise FileNotFoundError(f"Haar cascade not found at {CASCADE_PATH}")

            face_detector = cv2.CascadeClassifier(CASCADE_PATH)
            
            cap = cv2.VideoCapture(self.camera_index) 
            if not cap.isOpened():
                raise IOError(f"Cannot open webcam at index {self.camera_index}.")

            image_list = []
            count = 0
            
            while count < self.images_to_capture and self._is_running:
                ret, frame = cap.read()
                if not ret:
                    self.progress_frame.emit(None, "Error: Can't read frame.")
                    break
                
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(gray, 1.3, 5)

                status_text = "Looking for face..."
                
                if len(faces) > 0:
                    (x, y, w, h) = faces[0] # Use first face
                    face_roi = gray[y:y+h, x:x+w]
                    
                    if face_roi.size > 0:
                        image_list.append(face_roi)
                        count += 1
                        status_text = f"Captured image {count}/{self.images_to_capture}"
                        
                        # Draw rectangle on the color frame for display
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        
                        # Pause to get different angles
                        time.sleep(0.1) 
                
                # Convert cv2 frame (BGR) to QImage (RGB)
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # Emit the frame and status
                self.progress_frame.emit(qt_image, status_text)
                self.progress_value.emit(int((count / self.images_to_capture) * 100))
            
            cap.release()
            
            if not self._is_running:
                self.finished.emit(False, "Capture canceled by user.")
                return

            if len(image_list) < self.images_to_capture:
                raise Exception(f"Capture failed. Only got {len(image_list)} images.")

            self.progress_frame.emit(None, f"Captured {len(image_list)} images. Zipping...")
            self.progress_value.emit(100)

            # --- Zip images in memory ---
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, image_array in enumerate(image_list):
                    is_success, buffer = cv2.imencode(".jpg", image_array)
                    if is_success:
                        zf.writestr(f"image_{i}.jpg", buffer.tobytes())
            
            mem_zip.seek(0)
            self.progress_frame.emit(None, "Uploading to server...")

            # --- Send to server ---
            files = {'file': ('faces.zip', mem_zip, 'application/zip')}
            data = {'username': self.username}
            response = requests.post(f"{API_URL}/register-face", files=files, data=data, timeout=60)

            if response.status_code == 200:
                self.finished.emit(True, "Face registered successfully! Training started.")
            else:
                self.finished.emit(False, f"Server error: {response.json().get('message', 'Unknown error')}")

        except Exception as e:
            self.finished.emit(False, f"Error: {e}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()

    def stop(self):
        self._is_running = False

# [NEW] The pop-up dialog
class FaceCaptureDialog(QDialog):
    """
    This is the new pop-up window that shows the webcam feed.
    """
    # Signal that registration is complete
    registration_complete = Signal()
    
    def __init__(self, username, camera_index, parent=None):
        super().__init__(parent)
        self.username = username
        self.camera_index = camera_index
        
        self.thread = None
        self.worker = None

        self.setWindowTitle("Register Face")
        self.setModal(True) # Block the main window
        self.setMinimumSize(640, 580)
        
        # --- Widgets ---
        self.video_label = QLabel("Starting camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border-radius: 10px;")
        self.video_label.setFixedSize(600, 450)

        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button)
        
        self.apply_styles()
        
    def apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.COLOR_BACKGROUND}; }}
            QLabel {{ color: {theme.COLOR_TEXT}; font-size: 11pt; }}
            QProgressBar {{ 
                text-align: center; 
                color: {theme.COLOR_PANE_LEFT};
                font-weight: bold;
            }}
            QProgressBar::chunk {{ 
                background-color: {theme.COLOR_GOLD}; 
                border-radius: 5px;
            }}
        """)
        self.cancel_button.setStyleSheet(theme.button_style(
            base=theme.COLOR_RED, 
            hover=theme.COLOR_RED_HOVER,
            pressed=theme.COLOR_RED_PRESSED,
            text_color=theme.COLOR_TEXT
        ))

    def start_capture(self):
        """Starts the worker thread."""
        self.thread = QThread()
        self.worker = FaceRegisterWorker(self.username, self.camera_index)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.progress_frame.connect(self.update_frame)
        self.worker.progress_value.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_finished)
        self.thread.started.connect(self.worker.run)
        
        # Clean up
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    @Slot(QImage, str)
    def update_frame(self, qt_image, status_text):
        """Updates the video feed label and status text."""
        if qt_image:
            # Scale the image to fit the label, keeping aspect ratio
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        self.status_label.setText(status_text)
        
    @Slot(bool, str)
    def on_finished(self, success, message):
        """Shows the final result and closes the dialog."""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Failed", message)
            
        self.registration_complete.emit()
        self.accept() # Close the dialog

    def closeEvent(self, event):
        """Handle user closing the window."""
        if self.worker:
            self.worker.stop()
        if self.thread:
            self.thread.quit()
            self.thread.wait() # Wait for thread to finish
        self.registration_complete.emit()
        event.accept()


# [MAIN CLASS]
class RegisterPage(QWidget):

    def __init__(self, switch_to_login, user_manager):
        super().__init__()
        self.switch_to_login = switch_to_login
        self.user_manager = user_manager
        
        self.capture_dialog = None
        self.init_ui()
        self.apply_styles()
        
    def init_ui(self):
        # ... (your init_ui code is unchanged, I'm just pasting it here) ...
        self.resize(480, 520) 
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Create New Account 💜")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("titleLabel")

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setFixedHeight(45)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(45)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm Password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.returnPressed.connect(self.handle_register)
        self.confirm_input.setFixedHeight(45)

        # Button layout
        button_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Account")
        self.create_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.create_btn.clicked.connect(self.handle_register)
        self.create_btn.setFixedHeight(45)
        
        self.face_btn = QPushButton("Register with Face")
        self.face_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.face_btn.clicked.connect(self.handle_register_face)
        self.face_btn.setFixedHeight(45)
        
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.face_btn)

        self.back_btn = QPushButton("Back to Login")
        self.back_btn.setFont(QFont("Segoe UI", 10))
        self.back_btn.clicked.connect(self.switch_to_login)
        self.back_btn.setObjectName("backButton") 

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setObjectName("statusLabel")

        layout.addWidget(title)
        layout.addSpacing(15)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.confirm_input)
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        layout.addWidget(self.back_btn)
        layout.addWidget(self.status_label)
        
    def apply_styles(self):
        # ... (your apply_styles code is unchanged) ...
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.COLOR_BACKGROUND};
            }}
            QLabel {{
                color: {theme.COLOR_TEXT};
                background-color: transparent;
            }}
            QLabel#titleLabel {{
                color: {theme.COLOR_GOLD};
            }}
            QLabel#statusLabel {{
                color: {theme.COLOR_TEXT_SUBTLE};
                font-size: 10pt;
            }}
            QLineEdit {{ {theme.input_style()} }}
            
            /* Button 1: Create Account */
            QPushButton#create_btn {{ {theme.button_style()} }}
            
            /* Button 2: Face Register (secondary style) */
            QPushButton#face_btn {{ 
                {theme.button_style(
                    base=theme.COLOR_CARD, 
                    hover=theme.COLOR_CARD_BG, 
                    pressed=theme.COLOR_CARD,
                    text_color=theme.COLOR_GOLD
                )}
                border: 2px solid {theme.COLOR_GOLD};
            }}
            
            QPushButton#backButton {{ {theme.link_style()} }}
        """)
        self.create_btn.setObjectName("create_btn")
        self.face_btn.setObjectName("face_btn")

    def handle_register(self, show_success_popup=True):
        """
        Handles password registration. 
        Returns True on success, False on failure.
        """
        user = self.user_input.text()
        p1 = self.pass_input.text()
        p2 = self.confirm_input.text()
        
        if not user or not p1 or not p2:
            QMessageBox.warning(self, "Error", "All fields must be filled.")
            return False
        if p1 != p2: 
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return False

        try:
            self.status_label.setText("Registering account...")
            self.set_ui_busy(True)
            
            # --- This should also be in a thread, but for now ---
            # --- we'll assume it's fast enough or fix it later ---
            success, message = self.user_manager.register_user(user, p1)
            
            if success:
                if show_success_popup:
                    QMessageBox.information(self, "Success", f"{message} 💙")
                self.user_input.clear()
                self.pass_input.clear()
                self.confirm_input.clear()
                self.status_label.setText("")
                self.set_ui_busy(False)
                return True # Success
            else:
                QMessageBox.warning(self, "Error", message)
                self.status_label.setText("Registration failed.")
                self.set_ui_busy(False)
                return False # Failure
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to server: {e}")
            self.status_label.setText("Connection failed.")
            self.set_ui_busy(False)
            return False # Failure

    def set_ui_busy(self, is_busy):
        """Disables or enables buttons during processing."""
        self.create_btn.setEnabled(not is_busy)
        self.face_btn.setEnabled(not is_busy)
        self.user_input.setEnabled(not is_busy)
        self.pass_input.setEnabled(not is_busy)
        self.confirm_input.setEnabled(not is_busy)
        
    def handle_register_face(self):
        username = self.user_input.text()
        if not username:
            QMessageBox.warning(self, "Error", "Please fill out all fields first.")
            return
            
        # First, register the user via password
        # We pass False to suppress the "Success" popup
        # because the face dialog will show its own.
        if not self.handle_register(show_success_popup=False):
            # Password registration failed, so stop.
            return 
        
        # Password registration was successful, now register face
        self.status_label.setText("Starting face capture...")

        # --- [NEW] We need to know which camera to use ---
        # For now, let's hard-code index 1 (your Logi 270 cam)
        # We can make this a dropdown later if you want.
        CAMERA_INDEX_TO_USE = 1 # <-- [IMPORTANT] Change this if your camera index is different
        
        self.capture_dialog = FaceCaptureDialog(username, CAMERA_INDEX_TO_USE, self)
        # Connect the final signal to switch pages
        self.capture_dialog.registration_complete.connect(self.on_face_reg_complete)
        # Show the modal dialog
        self.capture_dialog.show()
        # Start the capture *after* showing
        self.capture_dialog.start_capture()

    def on_face_reg_complete(self):
        """Called when the face dialog closes."""
        self.status_label.setText("")
        # Optional: automatically switch to login
        # self.switch_to_login()