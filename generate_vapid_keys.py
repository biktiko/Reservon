from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

def generate_vapid_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Получаем публичный ключ уже в нужном формате:
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_b64url = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('utf-8')
    
    # Для приватного ключа нужно достать "сырое" значение ключа:
    private_value = private_key.private_numbers().private_value
    # Преобразуем число в байты (32 байта для SECP256R1)
    private_bytes = private_value.to_bytes(32, 'big')
    private_b64url = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('utf-8')
    
    return private_b64url, public_b64url

if __name__ == "__main__":
    private_key_str, public_key_str = generate_vapid_keys()
    print("Private Key:", private_key_str)
    print("Public Key:", public_key_str)
