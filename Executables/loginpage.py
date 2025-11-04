#
# REVISED FILE: loginpage.py (dengan Pop-up)
#
import os
import cv2
import io
import requests
import time
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QDialog
)
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot

# [NEW] Import theme instead of hard-coding colors
import theme 

# [NEW] Path to your assets
CASCADE_PATH = "assets/haarcascade_frontalface_default.xml"
API_URL = "https://morsz.azeroth.site" # Your server URL


# [NEW] Worker thread for face login
class FaceLoginWorker(QObject):
    """
    Runs face capture and network auth in a separate thread.
    """
    # [FIX] Signals are now separate
    frame_updated = Signal(QImage)
    status_updated = Signal(str)
    
    # Signal(str) - emits username on success
    login_success = Signal(str)
    # Signal(str) - emits error message on failure
    login_failed = Signal(str)
    
    finished = Signal() # Signal to clean up thread
    
    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
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

            start_time = time.time()
            captured_frame = None
            
            # Try for 10 seconds to get a clear face
            while time.time() - start_time < 10.0 and self._is_running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_flipped = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame_flipped, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(gray, 1.3, 5)

                status_text = "Looking for face..."

                if len(faces) > 0:
                    (x, y, w, h) = faces[0] # Use first face
                    
                    # Draw rectangle on the color frame for display
                    cv2.rectangle(frame_flipped, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    status_text = "Face found... Authenticating..."
                    
                    # Found a face! Use this frame for auth.
                    captured_frame = cv2.flip(frame_flipped, 1) # Un-flip
                
                # Convert cv2 frame (BGR) to QImage (RGB)
                rgb_image = cv2.cvtColor(frame_flipped, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # Emit the frame and status
                self.frame_updated.emit(qt_image)
                self.status_updated.emit(status_text)
                
                if captured_frame is not None:
                    break # Exit loop once face is found
                
                time.sleep(0.05) # 20 FPS

            cap.release()

            if not self._is_running:
                self.login_failed.emit("Login canceled by user.")
                self.finished.emit()
                return

            if captured_frame is None:
                raise Exception("No face detected. Please try again.")

            # --- Encode frame and send to server ---
            self.status_updated.emit("Authenticating with server...")
            is_success, buffer = cv2.imencode(".jpg", captured_frame)
            if not is_success:
                raise Exception("Failed to encode image.")

            image_bytes = io.BytesIO(buffer.tobytes())
            
            files = {'file': ('login_image.jpg', image_bytes, 'image/jpeg')}
            response = requests.post(f"{API_URL}/login-face", files=files, timeout=30)

            result = response.json()
            if response.status_code == 200 and result.get("success"):
                self.login_success.emit(result.get("username"))
            else:
                self.login_failed.emit(result.get("message", "Unknown error"))

        except Exception as e:
            self.login_failed.emit(f"Error: {e}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
            self.finished.emit()

    def stop(self):
        self._is_running = False

# [NEW] The pop-up dialog for Login
class FaceLoginDialog(QDialog):
    """
    This is the new pop-up window that shows the webcam feed for login.
    """
    # Signal(str) - emits username on success
    login_success = Signal(str)
    
    def __init__(self, camera_index, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        
        self.thread = None
        self.worker = None

        self.setWindowTitle("Login with Face")
        self.setModal(True) # Block the main window
        self.setMinimumSize(640, 550)
        
        # --- Widgets ---
        self.video_label = QLabel("Starting camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border-radius: 10px;")
        self.video_label.setFixedSize(600, 450)

        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addWidget(self.cancel_button)
        
        self.apply_styles()
        
    def apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.COLOR_BACKGROUND}; }}
            QLabel {{ color: {theme.COLOR_TEXT}; font-size: 11pt; }}
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
        self.worker = FaceLoginWorker(self.camera_index)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.frame_updated.connect(self.update_frame)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.login_success.connect(self.on_login_success)
        self.worker.login_failed.connect(self.on_login_failed)
        self.thread.started.connect(self.worker.run)
        
        # Clean up
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    @Slot(QImage)
    def update_frame(self, qt_image):
        """Updates the video feed label."""
        if qt_image:
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        
    @Slot(str)
    def on_login_success(self, username):
        """Emits the username and closes the dialog."""
        self.login_success.emit(username)
        self.accept()

    @Slot(str)
    def on_login_failed(self, message):
        """Shows the error and closes."""
        QMessageBox.warning(self, "Login Failed", message)
        self.reject() # Close the dialog

    def closeEvent(self, event):
        """Handle user closing the window."""
        if self.worker:
            self.worker.stop()
        if self.thread:
            self.thread.quit()
            self.thread.wait() # Wait for thread to finish
        event.accept()

# [MAIN CLASS]
class LoginPage(QWidget):
    
    def __init__(self, switch_to_dashboard, switch_to_register, user_manager):
        super().__init__()
        self.switch_to_dashboard = switch_to_dashboard
        self.switch_to_register = switch_to_register
        self.user_manager = user_manager
        
        self.login_dialog = None
        
        self.init_ui()
        self.apply_styles()
        
    def init_ui(self):
        # ... (init_ui is unchanged) ...
        self.resize(480, 480) # Made taller
        layout = QVBoxLayout(self)
        layout.setSpacing(15) 
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Welcome Back 💙")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("titleLabel")

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setFixedHeight(45)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.returnPressed.connect(self.handle_login) 
        self.pass_input.setFixedHeight(45)

        self.login_btn = QPushButton("Login")
        self.login_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setFixedHeight(45)
        
        self.face_btn = QPushButton("Login with Face")
        self.face_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.face_btn.clicked.connect(self.handle_login_face)
        self.face_btn.setFixedHeight(45)

        self.register_btn = QPushButton("Don't have an account? Register") 
        self.register_btn.setFont(QFont("Segoe UI", 10))
        self.register_btn.clicked.connect(self.switch_to_register)
        self.register_btn.setObjectName("registerButton") 
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setObjectName("statusLabel")

        layout.addWidget(title)
        layout.addSpacing(15)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addSpacing(10)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.face_btn)
        layout.addWidget(self.register_btn)
        layout.addWidget(self.status_label)

    def apply_styles(self):
        # ... (apply_styles is unchanged) ...
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
            
            QPushButton#loginButton {{ {theme.button_style()} }}
            
            QPushButton#faceButton {{ 
                {theme.button_style(
                    base=theme.COLOR_CARD, 
                    hover=theme.COLOR_CARD_BG, 
                    pressed=theme.COLOR_CARD,
                    text_color=theme.COLOR_GOLD
                )}
                border: 2px solid {theme.COLOR_GOLD};
            }}
            
            QPushButton#registerButton {{ {theme.link_style()} }}
        """)
        self.login_btn.setObjectName("loginButton")
        self.face_btn.setObjectName("faceButton")

    def set_ui_busy(self, is_busy):
        # ... (set_ui_busy is unchanged) ...
        self.login_btn.setEnabled(not is_busy)
        self.face_btn.setEnabled(not is_busy)
        self.user_input.setEnabled(not is_busy)
        self.pass_input.setEnabled(not is_busy)

    def handle_login(self):
        # ... (handle_login is unchanged) ...
        username = self.user_input.text()
        password = self.pass_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Username and password cannot be empty.")
            return
        
        self.set_ui_busy(True)
        self.status_label.setText("Verifying password...")
        
        try:
            if self.user_manager.verify_user(username, password):
                self.user_input.clear()
                self.pass_input.clear()
                self.status_label.setText("")
                self.switch_to_dashboard(username)
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
                self.pass_input.clear()
        except Exception as e:
             QMessageBox.critical(self, "Connection Error", f"Failed to connect to server: {e}")
        
        self.set_ui_busy(False)
        self.status_label.setText("")

    # [NEW] Face login logic
    def handle_login_face(self):
        self.status_label.setText("Starting face login...")
        
        # [IMPORTANT] Anda harus mengubah angka '1' ini
        # ke indeks kamera Anda yang benar (Logi 270 cam)
        CAMERA_INDEX_TO_USE = 1 
        
        self.login_dialog = FaceLoginDialog(CAMERA_INDEX_TO_USE, self)
        
        # Connect the success signal to actually log the user in
        self.login_dialog.login_success.connect(self.on_face_login_success)
        
        # Show the modal dialog
        self.login_dialog.show()
        # Start the capture *after* showing
        self.login_dialog.start_capture()

    # [NEW] Slot for when the worker finishes
    @Slot(str)
    def on_face_login_success(self, username):
        """Called by the dialog when login is successful."""
        self.set_ui_busy(False)
        self.status_label.setText(f"Welcome, {username}!")
        self.user_input.clear()
        self.pass_input.clear()
        
        # Switch to dashboard!
        self.switch_to_dashboard(username)