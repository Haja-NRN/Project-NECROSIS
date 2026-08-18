from pathlib import Path
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

class RSAService:
    def __init__(self, public_key_path):
        self.public_key_path = Path(public_key_path)
        self.public_key = None

    def load_public_key(self):
        """Charge la clé publique RSA depuis le fichier."""
        with self.public_key_path.open("rb") as file:
            self.public_key = serialization.load_pem_public_key(
                file.read()
            )

        return self.public_key

    def get_public_key(self):
        """Retourne la clé publique actuellement chargée."""
        if self.public_key is None:
            self.load_public_key()

        return self.public_key

    def encrypt(self, data):
        """Chiffre une donnée avec la clé publique RSA."""

        public_key = self.get_public_key()

        if isinstance(data, str):
            data = data.encode("utf-8")

        encrypted_data = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(
                    algorithm=hashes.SHA256()
                ),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Format pratique pour JSON/HTTP
        return base64.b64encode(encrypted_data).decode("utf-8")
    
rsa_service = RSAService(
    "keys/public_key.pem"
)

# Exemple d'utilisation
# aes_service = AESService()

# rsa_service = RSAService(
#     "keys/public_key.pem"
# )

# # 1. Générer une nouvelle clé AES
# aes_key = aes_service.get_new_code()

# # 2. Chiffrer cette clé AES avec RSA
# encrypted_aes_key = rsa_service.encrypt(aes_key)

# print(encrypted_aes_key)