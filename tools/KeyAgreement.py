from Crypto.PublicKey import ElGamal
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import random
import hashlib
import os


def init_parameter(size):
    p, g = None, None
    local_path = os.path.abspath('.')
    param_path = local_path + '//param'
    os.makedirs(param_path, exist_ok=True)

    g_path = param_path + "//" + str(size) + ".g"
    p_path = param_path + "//" + str(size) + ".p"

    if os.path.exists(g_path) and os.path.exists(p_path):
        p_file = open(p_path, 'r')
        p = p_file.read()
        p_file.close()
        g_file = open(g_path, 'r')
        g = g_file.read()
        g_file.close()
    else:
        elgamal_key = ElGamal.generate(size, get_random_bytes)
        p, g = elgamal_key.p, elgamal_key.g
        p_file = open(p_path, 'w')
        p_file.write(str(p))
        p_file.close()
        g_file = open(g_path, 'w')
        g_file.write(str(g))
        g_file.close()

    return p, g


def generate_key(p, g):
    p, g = int(p), int(g)
    x = random.randrange(2, p - 1)
    y = pow(g, x, p)
    return x, y


def key_agreement(pk, sk, p):
    pk, sk, p = map(int, (pk, sk, p))
    key = pow(pk, sk, p)
    h = hashlib.shake_128()
    bytes_key = str(key).encode()
    h.update(bytes_key)
    key = h.digest(16)
    return key
