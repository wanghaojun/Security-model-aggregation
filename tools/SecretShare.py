from Crypto.Protocol.SecretSharing import Shamir
from tools import  config
import random
import sys
def share(secret,k,n):
    secret = int(secret)
    bytes_size = config.parameter_size_256//8
    secret_bytes = secret.to_bytes(bytes_size,'little')
    secret_bytes_spilt = []

    for i in range(bytes_size//16):
        start = 16 * i
        secret_bytes_spilt.append(secret_bytes[start:start+16])

    share_secrets = []
    for i in range(n):
        share_secrets.append([i+1])

    for secret_bytes in secret_bytes_spilt:
        split_res = Shamir.split(k,n,secret_bytes,False)
        for (index,s) in split_res:
            if index == share_secrets[index-1][0]:
                share_secrets[index-1].append(s)

    return share_secrets

def reconstruction(shares):
    secret_num = len(shares[0]) -1
    re_secret_bytes = bytes()
    for i in range(1,secret_num+1):
        spilt = []
        for item in shares:
            spilt.append((item[0],item[i]))
        re_secret_bytes += Shamir.combine(spilt, False)
    re_secret = int.from_bytes(re_secret_bytes,'little')
    return re_secret







