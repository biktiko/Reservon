# generate_vapid_keys.py

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

def generate_vapid_keys():
    # Генерация приватного ключа ECDSA P-256
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Сериализация приватного ключа в PEM формат
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Сериализация публичного ключа в uncompressed point формате
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    # Кодирование публичного ключа в base64url без заполнителей
    public_b64url = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('utf-8')

    return private_pem.decode('utf-8'), public_b64url

if __name__ == "__main__":
    private_key, public_key = generate_vapid_keys()
    print("Private Key:")
    print(private_key)
    print("\nPublic Key:")
    print(public_key)
