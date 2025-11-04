import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame,
    QSpacerItem, QSizePolicy, QListWidget
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QSize
from utils import get_resource_path

# [REVISI UI 4.0]
# Menerapkan 4 permintaan terakhir dari pengguna (menambah card
# untuk header, judul sidebar, dan area "mulai chat", serta
# memperbaiki cropping logo).

class DashboardPage(QWidget):
    
    # --- Palet Warna (Tidak Berubah) ---
    COLOR_BACKGROUND = "#1A1B2E"
    COLOR_PANE_LEFT = "#272540"
    COLOR_PANE_RIGHT = "#1A1B2E"
    COLOR_CARD_BG = "#272540"     # [BARU] Warna card disamakan dgn sidebar
    COLOR_CARD = "#3E3C6E"
    COLOR_TEXT = "#F0F0F5"
    COLOR_TEXT_SUBTLE = "#A9A8C0"
    COLOR_GOLD = "#D4AF37"
    COLOR_GOLD_HOVER = "#F0C44F"
    COLOR_GOLD_PRESSED = "#B8860B"
    COLOR_RED = "#ed4956"
    COLOR_RED_HOVER = "#ff7d6e"
    COLOR_RED_PRESSED = "#e63946"
    # -----------------------------------------------

    def __init__(self, logout_callback, switch_to_chat, user_manager):
        super().__init__()
        # --- Fungsionalitas Inti (Tidak Berubah) ---
        self.logout_callback = logout_callback
        self.switch_to_chat = switch_to_chat
        self.user_manager = user_manager
        self.current_user = None
        # -------------------------------------------
        
        self.init_ui()

    def init_ui(self):
        """
        Layout dasar (Sidebar/Main) tetap sama.
        Warna latar diperbarui.
        """
        self.resize(1200, 800)
        self.setStyleSheet(f"background-color: {self.COLOR_BACKGROUND};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        left_pane = self.create_left_pane()
        right_pane = self.create_right_pane()
        
        main_layout.addWidget(left_pane)
        main_layout.addWidget(right_pane)
        
        main_layout.setStretch(0, 1) # 1/4 Lebar
        main_layout.setStretch(1, 3) # 3/4 Lebar

    # [REVISI #3] Panel kiri diperbarui
    def create_left_pane(self):
        """Membangun panel sidebar kiri."""
        
        left_pane = QFrame()
        # Border emas tetap di sisi kanan sidebar
        left_pane.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_PANE_LEFT};
                border-right: 2px solid {self.COLOR_GOLD}; 
            }}
        """)
        
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(20, 30, 20, 20)
        left_layout.setSpacing(15)

        # --- [REQUEST #3] Card untuk Judul "Obrolan" ---
        title_card = QFrame()
        title_card.setStyleSheet(self.card_style()) # Gunakan helper style card
        
        title_layout = QVBoxLayout(title_card)
        title_layout.setContentsMargins(10, 15, 10, 15) # Padding di dlm card
        
        title = QLabel("Obrolan")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        # Stylesheet dihapus dari QLabel, karena sudah dihandle card
        title.setStyleSheet(f"color: {self.COLOR_GOLD}; background-color: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title)
        # -----------------------------------------------

        # --- Bar Pencarian ---
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Cari atau mulai obrolan baru...")
        search_bar.setStyleSheet(self.input_style())
        search_bar.setFixedHeight(45)

        # --- Daftar Kontak (Style tidak berubah) ---
        self.contact_list = QListWidget()
        self.contact_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: 2px solid {self.COLOR_GOLD};
                border-radius: 12px;
                color: {self.COLOR_TEXT};
                font-size: 16px;
                padding: 5px;
            }}
            QListWidget::item {{ padding: 15px 10px; border-radius: 8px; }}
            QListWidget::item:hover {{ background-color: {self.COLOR_CARD}; }}
            QListWidget::item:selected {{
                background-color: {self.COLOR_GOLD};
                color: {self.COLOR_PANE_LEFT};
                font-weight: bold;
            }}
        """)
        self.contact_list.itemClicked.connect(self.on_contact_clicked)

        # --- Susun Widget di Panel Kiri ---
        left_layout.addWidget(title_card) # Menggantikan title label
        left_layout.addWidget(search_bar)
        left_layout.addWidget(self.contact_list)
        
        return left_pane

    # [REVISI #1, #4] Panel kanan diperbarui
    def create_right_pane(self):
        """Membangun panel area utama kanan."""
        
        right_pane = QFrame()
        right_pane.setStyleSheet(f"background-color: {self.COLOR_PANE_RIGHT};")
        
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(50, 40, 50, 50)
        right_layout.setSpacing(25) # Jarak antar card

        # --- [REQUEST #1] Card untuk Header (Logo + Sapaan) ---
        header_card = QFrame()
        header_card.setStyleSheet(self.card_style())
        header_card_layout = QVBoxLayout(header_card)
        # Padding di dalam card header
        header_card_layout.setContentsMargins(25, 25, 25, 25) 
        
        header_layout = self.create_header() # Buat layout header internal
        header_card_layout.addLayout(header_layout) # Masukkan layout ke card
        # ----------------------------------------------------

        # --- [REQUEST #4] Card untuk "Mulai Chat Baru" ---
        new_chat_card = QFrame()
        new_chat_card.setStyleSheet(self.card_style())
        new_chat_layout_internal = QVBoxLayout(new_chat_card)
        # Padding di dalam card "Mulai Chat"
        new_chat_layout_internal.setContentsMargins(30, 30, 30, 30) 
        new_chat_layout_internal.setSpacing(15)
        
        info = QLabel("Mulai Obrolan Baru")
        info.setFont(QFont("Segoe UI", 18, QFont.Bold))
        info.setStyleSheet(f"color: {self.COLOR_GOLD}; background-color: transparent; border: none;")
        
        info_sub = QLabel("Masukkan username untuk memulai percakapan.")
        info_sub.setFont(QFont("Segoe UI", 11))
        info_sub.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; background-color: transparent; border: none;")

        # Layout horizontal untuk Input + Tombol
        new_chat_layout_controls = QHBoxLayout()
        new_chat_layout_controls.setSpacing(10)
        
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Username tujuan...")
        self.recipient_input.setStyleSheet(self.input_style())
        self.recipient_input.setFixedHeight(45)

        self.start_chat_btn = QPushButton("Mulai")
        self.start_chat_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.start_chat_btn.setFixedSize(120, 45)
        self.start_chat_btn.setStyleSheet(self.button_style(
            base=self.COLOR_GOLD,
            hover=self.COLOR_GOLD_HOVER,
            pressed=self.COLOR_GOLD_PRESSED,
            radius=22, 
            text_color=self.COLOR_PANE_LEFT
        ))
        self.start_chat_btn.clicked.connect(self.handle_start_chat)

        new_chat_layout_controls.addWidget(self.recipient_input)
        new_chat_layout_controls.addWidget(self.start_chat_btn, 0)
        
        # Masukkan semua elemen ke dalam layout card "Mulai Chat"
        new_chat_layout_internal.addWidget(info)
        new_chat_layout_internal.addWidget(info_sub)
        new_chat_layout_internal.addLayout(new_chat_layout_controls)
        # -------------------------------------------------------

        # --- Tombol Logout (Tetap di luar card) ---
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.logout_btn.setFixedSize(120, 40)
        self.logout_btn.setStyleSheet(self.button_style(
            base=self.COLOR_RED,
            hover=self.COLOR_RED_HOVER,
            pressed=self.COLOR_RED_PRESSED,
            radius=10
        ))
        self.logout_btn.clicked.connect(self.logout_callback)

        # --- Susun Widget di Panel Kanan ---
        right_layout.addWidget(header_card)       # [Request #1]
        right_layout.addWidget(new_chat_card)     # [Request #4]
        right_layout.addStretch()                 # Spacer
        right_layout.addWidget(self.logout_btn, 0, Qt.AlignmentFlag.AlignRight) 
        
        return right_pane

    # [REVISI #2] Fungsi header diperbarui
    def create_header(self):
        """
        [REVISI #2]
        Membangun layout header (Foto profil, nama).
        Scaling logo diubah agar pas di DALAM border.
        """
        header = QHBoxLayout()
        header.setSpacing(15) # Beri spasi antara logo dan teks
        
        # --- Foto Profil ---
        profile_pic = QLabel()
        profile_pic.setFixedSize(80, 80)
        
        pixmap_path = get_resource_path(os.path.join("assets", "profile.png"))
        pixmap = QPixmap(pixmap_path)
        
        # Style dasar untuk QLabel (lingkaran)
        profile_pic_style = f"""
            QLabel {{
                background-color: {self.COLOR_CARD}; 
                border: 3px solid {self.COLOR_GOLD}; 
                border-radius: 40px;
            }}
        """
        
        if not pixmap.isNull():
            # [REQUEST #2] Auto-crop:
            # Border adalah 3px. Ukuran QLabel 80x80.
            # Area di dalam border adalah 80 - (3*2) = 74px.
            # Kita scale pixmap ke 74x74 agar pas di dalam.
            scaled_pixmap = pixmap.scaled(74, 74, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            profile_pic.setPixmap(scaled_pixmap)
            # Pusatkan pixmap (yg skrg 74x74) di dlm QLabel (yg 80x80)
            profile_pic.setAlignment(Qt.AlignCenter) 
        
        profile_pic.setStyleSheet(profile_pic_style)


        # --- Info Nama & Selamat Datang ---
        name_info = QVBoxLayout()
        name_info.setContentsMargins(0, 0, 0, 0) # Hapus margin
        name_info.setSpacing(2)
        
        self.title_label = QLabel("Hi, ...")
        self.title_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {self.COLOR_TEXT}; background-color: transparent; border: none;")
        
        self.subtitle_label = QLabel("Selamat datang kembali.")
        self.subtitle_label.setFont(QFont("Segoe UI", 12))
        self.subtitle_label.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; background-color: transparent; border: none;")
        
        name_info.addWidget(self.title_label)
        name_info.addWidget(self.subtitle_label)
        name_info.addStretch()

        # --- Susun Header ---
        header.addWidget(profile_pic)
        header.addLayout(name_info)
        header.addStretch()
        
        return header

    # ===================================================================
    # --- FUNGSI LOGIKA (TIDAK BERUBAH) ---
    # ===================================================================

    def set_welcome_message(self, username):
        self.title_label.setText(f"Hi, {username}!")
        self.subtitle_label.setText("Selamat datang kembali di dashboard Anda.")
        self.current_user = username
        self.load_contact_list()

    def load_contact_list(self):
        if not self.current_user: return
        self.contact_list.clear(); self.contact_list.addItem("Memuat kontak...")
        success, contacts = self.user_manager.get_contacts(self.current_user)
        self.contact_list.clear()
        if success and contacts:
            for contact in contacts: self.contact_list.addItem(contact)
        elif success and not contacts:
            self.contact_list.addItem("Belum ada obrolan...")
        else:
            self.contact_list.addItem("Gagal memuat kontak.")

    def on_contact_clicked(self, item):
        recipient = item.text()
        if recipient.startswith("Memuat") or recipient.startswith("Gagal") or recipient.startswith("Belum"):
            return
        users = sorted([self.current_user, recipient])
        shared_password = f"key_rahasia_{users[0]}_{users[1]}" 
        self.switch_to_chat(recipient, shared_password)

    def handle_start_chat(self):
        recipient = self.recipient_input.text().strip()
        if not recipient: 
            QMessageBox.warning(self, "Error", "Isi username tujuan."); return
        if recipient == self.current_user:
            QMessageBox.warning(self, "Error", "Tidak bisa chat dengan diri sendiri."); return
        
        users = sorted([self.current_user, recipient])
        shared_password = f"key_rahasia_{users[0]}_{users[1]}"
        self.switch_to_chat(recipient, shared_password)
        self.recipient_input.clear()
        
        items = self.contact_list.findItems(recipient, Qt.MatchExactly)
        if not items:
            placeholder_item = self.contact_list.findItems("Belum ada obrolan...", Qt.MatchExactly)
            if placeholder_item:
                self.contact_list.takeItem(self.contact_list.row(placeholder_item[0]))
            self.contact_list.addItem(recipient)

    # ===================================================================
    # --- [BARU] FUNGSI HELPER STYLING (Card) ---
    # ===================================================================

    def card_style(self):
        """
        [BARU] Helper style untuk semua card.
        Latar belakang card = warna sidebar, dengan border emas.
        """
        return f"""
            QFrame {{
                background-color: {self.COLOR_CARD_BG};
                border: 2px solid {self.COLOR_GOLD};
                border-radius: 16px;
            }}
        """

    def input_style(self):
        """Stylesheet untuk QLineEdit (tema Indigo + Emas)."""
        return f"""
            QLineEdit {{
                background-color: {self.COLOR_CARD};
                border: 2px solid {self.COLOR_GOLD};
                border-radius: 22px;
                padding: 10px 20px;
                color: {self.COLOR_TEXT};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {self.COLOR_GOLD_HOVER};
            }}
        """

    def button_style(self, base, hover, pressed, radius=12, text_color=None):
        """Stylesheet untuk QPushButton."""
        text_col = text_color if text_color else self.COLOR_TEXT
        return f"""
            QPushButton {{
                background-color: {base};
                color: {text_col};
                border: none;
                border-radius: {radius}px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {pressed}; }}
        """