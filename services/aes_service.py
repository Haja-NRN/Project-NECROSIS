import secrets
import base64
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESService:
    KEY_SIZE = 32       # AES-256
    NONCE_SIZE = 12     # recommandé pour AES-GCM

    def __init__(self):
        self.code = None

    def create(self):
        """Génère une nouvelle clé AES-256."""
        self.code = secrets.token_bytes(self.KEY_SIZE)

    def get_code(self):
        """Retourne la clé AES actuelle."""
        return self.code

    def get_new_code(self):
        """Génère une nouvelle clé et la retourne."""
        self.create()
        return self.get_code()

    def encrypt(self, data):
        """
        Chiffre les données avec la clé AES actuelle.

        Retourne une chaîne Base64 contenant :
            nonce + ciphertext + authentication tag
        """
        if self.code is None:
            raise ValueError("Aucune clé AES n'a été générée.")

        if isinstance(data, str):
            data = data.encode("utf-8")

        nonce = secrets.token_bytes(self.NONCE_SIZE)

        aes = AESGCM(self.code)

        ciphertext = aes.encrypt(
            nonce,
            data,
            None
        )

        # On regroupe nonce + données chiffrées
        encrypted_data = nonce + ciphertext

        # Pratique pour l'envoyer dans une requête HTTP/JSON
        return base64.b64encode(encrypted_data).decode("utf-8")
    def encrypt_file(self, file_path):
        """
        Chiffre le contenu d'un fichier et retourne
        le résultat en Base64.
        """

        if self.code is None:
            raise ValueError("Aucune clé AES n'a été générée.")

        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Fichier introuvable : {file_path}"
            )

        with path.open("rb") as file:
            data = file.read()

        return self.encrypt(data)
    
aes_service = AESService()

# Exemple d'utilisation
# if __name__ == "__main__":
#     aes_service = AESService()

#     key = aes_service.get_new_code()

#     encrypted = aes_service.encrypt_file("C:\\Users\\Haja Nirina\\.venv_image\\Lib\\site-packages\\pip\\_vendor\\certifi\\cacert.pem")

#     print("Key:", key)
#     print("Encrypted:", encrypted)
