from tools import KeyAgreement as KA
from tools import SecretShare as SS
from tools import AuthenticatedEncryption as AE
from Double_Cloud import utils
import numpy as np
import random
import socketio
import time
import logging

LOG_FORMAT = "%(asctime)s  - %(message)s"
current_time = lambda: int(round(time.time() * 1000))
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class Client:

    def __init__(self, id, client_conf, model_conf):

        self.id = id
        self.client_conf = client_conf
        self.model_conf = model_conf
        self.w = np.ndarray(int(self.client_conf['w_size']))
        self.model = None
        self.name = 'client_' + str(self.id)
        self.survive = True

        self.c_p, self.c_g = None, None
        self.c_sk, self.c_pk = None, None

        self.s_p, self.s_g = None, None
        self.s_sk, self.s_pk = None, None

        self.client_pk = {}

        self.secrets = []

        self.e = {}
        self.e_other = []

        self.p_u_v = None
        self.p_u_v_c = 0

        self.b_u = None
        self.p_u = None

        self.y_u = np.ndarray(int(self.client_conf['w_size']))

        self.U_recon = None
        self.share = []

        self.sioA = socketio.Client()
        self.sioA.connect(self.client_conf['serverA_url'])
        self.sioB = socketio.Client()
        self.sioA.on('dis_connect', self.dis_connect)
        self.sioA.on('client_pk', self.receive_client_pk)
        self.sioA.on('encrypt_data', self.receive_e_other)
        self.sioA.on("u_recon",self.receive_u_recon)

    def dis_connect(self):
        self.survive = False
        logging.info(self.name + " dropped")

    # round_0_0 生成两对公钥私钥 256位用来做掩饰 1024位用来密钥交换进行加密
    def gen_pk_sk(self):
        self.c_p, self.c_g = KA.init_parameter(self.client_conf['c_size'])
        self.c_sk, self.c_pk = KA.generate_key(self.c_p, self.c_g)

        self.s_p, self.s_g = KA.init_parameter(self.client_conf['s_size'])
        self.s_sk, self.s_pk = KA.generate_key(self.s_p, self.s_g)

    # round_0_1 发送两队公钥到服务器
    def send_cpk_spk(self):
        self.sioA.emit('client_pk', (self.id, str(self.c_pk), str(self.s_pk)))

    # round_1_0 从服务器接收所有的公钥
    def receive_client_pk(self, client_pk):
        self.client_pk = client_pk
        logging.info(self.name + " receive pk :" + str(len(client_pk)))

    # round_1_1 生成s_sk的秘密分享
    def share_secrets(self):
        n = len(self.client_pk)
        t = self.client_conf['share_secrets_t']
        if n >= t:
            self.secrets = SS.share(self.s_sk, t, n)

    # round_1_2 对秘密分享使用密钥交换的密钥加密
    # 加密内容m: u_id + v_id + secret_index + secret_1 + secret_2 中间使用分隔符分割
    def encrypt(self):
        u = self.id
        u_sk = self.c_sk
        p = self.c_p
        split = self.client_conf['split'].encode()
        i = 0
        for id, pks in self.client_pk.items():
            secret = self.secrets[i]
            v = id
            v_pk = int(pks[1])
            key = KA.key_agreement(v_pk, u_sk, p)
            m = str(u).encode() + split + str(v).encode() + split + str(secret[0]).encode() + split + secret[
                1] + split + secret[2]
            c, tag, nonce = AE.encrypt(key, m)
            self.e[v] = [c,tag,nonce]
            i += 1

    # round_1_3 向服务端发送加密后的数据
    # e的内容：[u_id,v_id,cipher-text,tag,nonce]
    def send_e(self):
        self.sioA.emit('encrypt_data', (self.id, self.e))

    # round_2_0 从服务器接收为其加密的秘密分享
    def receive_e_other(self, e_other):
        logging.info(self.name + " receive encrypt_data :" + str(len(e_other)))
        self.e_other = e_other

    # round_2_1 模型参数更新
    def model_update(self):
        self.w = np.ones(self.client_conf['w_size'])

    # round_2_2 计算掩饰值1
    def compute_mask_1(self):
        self.p_u_v = np.zeros(self.w.shape)
        u = self.id
        count = 0
        for key,item in self.client_pk.items():
            v = int(key)
            if u == v or str(v) not in self.e_other:
                continue
            pk = int(item[1])
            sk = self.s_sk
            p = self.s_p
            shape = self.p_u_v.shape
            seed = 0
            key = KA.key_agreement(pk, sk, p)
            for i in range(0, len(key), 4):
                seed += int.from_bytes(key[i:i + 4], 'little')
                seed %= 2 ** 32 - 1
            np.random.seed(seed)
            r = np.random.random(shape)
            if u > v:
                self.p_u_v += r
            else:
                self.p_u_v -= r
        self.p_u_v_c = count

    # round_2_3 计算掩饰值2
    def compute_mask_2(self):
        self.b_u = int(random.random() * (10 ** 16)) % (2 ** 32 - 1)
        np.random.seed(self.b_u)
        self.p_u = np.random.random(self.w.shape)

    # round_2_4 计算掩饰后的私有向量
    def compute_mask_vector(self):
        self.y_u = self.w + self.p_u + self.p_u_v

    # round_2_5 向服务器A发送b_u
    def send_b_u_A(self):
        self.sioA.emit('b_u', (self.id, self.b_u))

    # round_2_6 向服务器B发送带掩饰的私有向量
    def send_y_u_B(self):
        self.sioB.connect(self.client_conf['serverB_url'])
        self.sioB.emit('y_u', (self.id, self.y_u.tolist()))


    # round_3_0 接收来自服务器A的用户列表U_recon
    def receive_u_recon(self, U_recon):
        self.U_recon = U_recon
        logging.info("receive u_recon len:" )

    # round_3_1 解密需要重建密钥的用户集合
    def decrypt_e_other(self):
        self.share = [0] * len(self.U_recon)
        split = self.client_conf['split'].encode()
        for i in range(len(self.U_recon)):
            if self.U_recon[i]:
                e = self.e_other[i]
                u, v, c, tags, nonce = e[0], e[1], e[2], e[3], e[4]
                pk = self.client_pk[u][1]
                sk = self.c_sk
                p = self.c_p
                key = KA.key_agreement(pk, sk, p)
                m = AE.decrypt(key, c, tags, nonce)
                c_u, c_v, index, secret_0, secret_1 = m.split(split)
                c_u, c_v, index = int(c_u), int(c_v), int(index)
                if c_u == u and c_v == v == self.id:
                    self.share[u] = [index, secret_0, secret_1]

    # round_3_2 向服务器A发送分享值:
    def send_share(self):
        return self.id, self.share

    def get_model(self):
        self.sioA.emit("model")

    def receive_model(self, model):
        self.model = model


if __name__ == '__main__':
    clients = []
    for i in range(5):
        client = Client(i, utils.load_json('./config/client.json'), utils.load_json('./config/model.json'))
        clients.append(client)
    for c in clients:
        c.gen_pk_sk()
        c.send_cpk_spk()
        # time.sleep(1)

    for c in clients:
        while c.survive and len(c.client_pk) == 0:
            continue

    for c in clients:
        if not c.survive:
            clients.remove(c)

    for c in clients:
        c.share_secrets()
        c.encrypt()
        c.send_e()

    for c in clients:
        while c.survive and len(c.e_other) == 0:
            continue

    for c in clients:
        if not c.survive:
            clients.remove(c)

    for c in clients:
        c.model_update()
        c.compute_mask_1()
        c.compute_mask_2()
        c.compute_mask_vector()
        c.send_y_u_B()

    for c in clients:
        c.send_b_u_A()


