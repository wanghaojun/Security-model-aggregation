from tools import KeyAgreement as KA
from tools import AuthenticatedEncryption as AE
from tools import SecretShare as ss
from tools import config
import random
import numpy as np

def AE_test():
    p,g = KA.init_parameters(1024)
    sk1, pk1 = KA.generate_key(p, g)
    sk2, pk2 = KA.generate_key(p, g)
    key2 = KA.key_agreement(pk1, sk2, p)
    m = '[1,2,000000]'.encode('utf-8')
    c,tags,nonce = AE.encrypt(key2,m)
    m =AE.decrypt(key2,c,tags,nonce)
    print(m)
    # print(m.decode('utf-8'))



def KA_test():
    p,g = KA.init_parameters(1024)
    sk1,pk1 = KA.generate_key(p,g)
    sk2,pk2 = KA.generate_key(p,g)
    key2 = KA.key_agreement(pk1,sk2,p)
    key1 = KA.key_agreement(pk2,sk1,p)
    print(key1)
    print(key2)
    print(key1==key2)

def SS_test():
    p, g = KA.init_parameters(1024)
    sk1, pk1 = KA.generate_key(p, g)
    sk2, pk2 = KA.generate_key(p, g)

    secrets = ss.share(sk1, 2, 3)
    re_sk1 = ss.reconstruction(random.sample(secrets, 2))
    key = KA.key_agreement(pk2, sk1, p)

    re_key = KA.key_agreement(pk2, re_sk1, p)

    m = '[1,2,000000]'.encode('utf-8')
    c, tags, nonce = AE.encrypt(key, m)
    m = AE.decrypt(re_key, c, tags, nonce)


if __name__ == '__main__':

    p, g = KA.init_parameter(config.parameter_size_256)
    sk1, pk1 = KA.generate_key(p, g)
    sk2, pk2 = KA.generate_key(p, g)
    sk3, pk3 = KA.generate_key(p, g)
    print(sk1)
    secrets = ss.share(sk1,2,3)

    # client1
    key12 = KA.key_agreement(pk2,sk1,p)
    key13 = KA.key_agreement(pk3,sk1,p)
    m2 = str(secrets[1][0]).encode() + '|'.encode() + secrets[1][1] + '|'.encode() + secrets[1][2]
    m3 = str(secrets[2][0]).encode() + '|'.encode() + secrets[2][1] + '|'.encode() + secrets[2][2]
    c2, tags2, nonce2 = AE.encrypt(key12, m2)
    c3, tags3, nonce3 = AE.encrypt(key13, m3)

    #client2
    key21 = KA.key_agreement(pk1,sk2,p)
    t2 = AE.decrypt(key21, c2, tags2, nonce2)
    index_20,secret_20,secret_21 = t2.split('|'.encode())

    # client3
    key31 = KA.key_agreement(pk1, sk3, p)
    t3 = AE.decrypt(key31, c3, tags3, nonce3)
    index_30, secret_30, secret_31 = t3.split('|'.encode())

    share = []
    share.append([int(index_30), secret_30, secret_31])
    share.append([int(index_20),secret_20,secret_21])

    re_sk1 = ss.reconstruction(share)
    print(re_sk1)

    print(key12)
    ks = []
    key = key12
    for i in range(0, len(key), 4):
        ks.append(int.from_bytes(key[i:i + 4], 'little'))
    r = np.zeros(10)
    for seed in ks:
        seed %= 2 ** 32 - 1
        np.random.seed(seed)
        r += np.random.random(10)


    # re_sk1 = ss.reconstruction(secrets[:1])
    # key = KA.key_agreement(pk2,sk1,p)

    # re_key = KA.key_agreement(pk2,re_sk1,p)

    # m = '[1,2,000000]'.encode('utf-8')
    # c, tags, nonce = AE.encrypt(key, m)
    # m = AE.decrypt(re_key, c, tags, nonce)


