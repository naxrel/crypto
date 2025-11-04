# Di dalam file usb_auth.py

import os
import time
import psutil
import sys
import json  # <-- TAMBAHKAN IMPORT INI
from tkinter import messagebox
from utils import get_base_path
from utils import decrypt_config # Ini diimpor dari setup_usb.py
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMetaObject, Qt, Q_ARG

# --- Path Konfigurasi (Tidak berubah) ---
def get_base_path():
    """ 
    Fungsi ini harus disalin dari utils.py karena ini file terpisah
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # Asumsi file ini ada di Executables/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

parent_dir = get_base_path()
LOCAL_CONFIG_FILE = os.path.join(parent_dir, "auth", "auth.config")
USB_KEY_FILE = ".my_crypto_app_key"
from utils import HARDCODED_SECRET as MASTER_SECRET


# --- NAMA FUNGSI DAN LOGIKA DIUBAH ---
def get_all_valid_keys():
    """
    Membaca dan mendekripsi file config lokal untuk mendapatkan DAFTAR
    semua USB key yang valid.
    """
    if not os.path.exists(LOCAL_CONFIG_FILE):
        print(f"⚠️ File {LOCAL_CONFIG_FILE} tidak ditemukan.")
        return []  # Kembalikan list kosong

    try:
        with open(LOCAL_CONFIG_FILE, "rb") as f:
            encrypted_data = f.read()

        # Dekripsi data untuk mendapatkan JSON string dari list
        decrypted_json_list = decrypt_config(encrypted_data, MASTER_SECRET)
        
        if not decrypted_json_list:
            print("⚠️ Gagal mendekripsi config. Pastikan password benar.")
            return []  # Kembalikan list kosong

        # Parse JSON string menjadi Python list
        valid_keys = json.loads(decrypted_json_list)
        
        if not isinstance(valid_keys, list):
             print("⚠️ Data config korup, bukan list.")
             return []

        print(f"Berhasil memuat {len(valid_keys)} kunci yang terdaftar.")
        return valid_keys
        
    except Exception as e:
        print(f"❌ Error membaca {LOCAL_CONFIG_FILE}: {e}")
        return []  # Kembalikan list kosong


def find_removable_drives():
    """Mendeteksi semua drive removable (USB)."""
    # ... (Fungsi ini tidak berubah) ...
    drives = []
    for partition in psutil.disk_partitions():
        if "removable" in partition.opts or not "fixed" in partition.opts:
            drives.append(partition.mountpoint)
    return drives


# --- LOGIKA FUNGSI INI DIUBAH ---
def find_usb_key_drive(valid_key_list: list):
    """
    Mencari USB drive yang memiliki key yang cocok dengan
    SALAH SATU key di dalam valid_key_list.
    """
    drives = find_removable_drives()
    for drive in drives:
        key_path = os.path.join(drive, USB_KEY_FILE)
        if os.path.exists(key_path):
            try:
                with open(key_path, "r") as f:
                    key_value = f.read().strip()
                
                # Cek apakah key di USB ada di dalam DAFTAR key yang valid
                if key_value in valid_key_list:
                    print(f"✅ USB key cocok ditemukan di: {drive}")
                    return drive
                else:
                    print(f"⚠️ Ditemukan USB key di {drive}, tapi key tidak cocok/terdaftar.")
                    
            except Exception:
                continue  # Lanjut ke drive berikutnya jika ada error baca
    return None


# --- ARGUMEN FUNGSI INI DIUBAH ---
def check_usb_key(valid_key_list: list):
    """Mengecek apakah USB dengan key yang cocok sedang terpasang."""
    return find_usb_key_drive(valid_key_list) is not None


# --- ARGUMEN FUNGSI INI DIUBAH ---
def monitor_usb_drive(qt_app, valid_key_list: list):
    """
    Memantau keberadaan SALAH SATU USB key yang valid.
    Jika dilepas, aplikasi akan ditutup.
    """
    print("🔍 Memulai pemantauan USB key (mode multi-key)...")
    while True:
        # check_usb_key sekarang menerima list
        if not check_usb_key(valid_key_list):
            print("❌ SEMUA USB key terdaftar dilepas! Menutup aplikasi...")
            try:
                messagebox.showwarning(
                    "USB Key Removed",
                    "USB key terdaftar dilepas! Aplikasi akan ditutup demi keamanan."
                )
            except Exception:
                pass  # Gagal tampilkan popup jika GUI thread sudah mati

            # Kirim sinyal quit ke thread utama Qt
            QMetaObject.invokeMethod(
                qt_app,
                "quit",
                Qt.QueuedConnection
            )
            return  # Hentikan thread monitor
        time.sleep(2)