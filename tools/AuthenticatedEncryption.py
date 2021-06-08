from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes

def encrypt(key,m):
    aes = AES.new(key,AES.MODE_EAX)
    cipertext,tag = aes.encrypt_and_digest(m)
    nonce = aes.nonce
    return cipertext,tag,nonce

def decrypt(key,c,tags,nonce):
    aes = AES.new(key,AES.MODE_EAX,nonce)
    m = aes.decrypt_and_verify(c,tags)
    return m






