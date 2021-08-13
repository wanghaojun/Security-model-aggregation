from tools import KeyAgreement as KA
from tools import SecretShare as SS
from tools import AuthenticatedEncryption as AE
from Double_Cloud import utils
import numpy as np
import random
import Double_Cloud.models as model
import torch
import logging
import time

logger = logging.Logger("protocol",level=logging.INFO)
LOG_FORMAT = "%(name)s - %(asctime)s  - %(levelname)s - %(message)s"
current_time = lambda: int(round(time.time() * 1000))
logging.basicConfig(level=logging.INFO,format=LOG_FORMAT)

class Client:

    def __init__(self, id, conf, train_dataset):

        self.conf = conf

        self.id = id
        self.name = 'client_' + str(self.id)
        self.diff = dict()

        self.local_model = model.get_model("resnet18")
        self.train_dataset = train_dataset

        all_range = list(range(len(self.train_dataset)))
        data_len = int(len(self.train_dataset) / self.conf['client_num'])
        train_indices = all_range[id * data_len: (id + 1) * data_len]
        self.train_loader = torch.utils.data.DataLoader(self.train_dataset, batch_size=conf["batch_size"],
                                                        sampler=torch.utils.data.sampler.SubsetRandomSampler(
                                                            train_indices))

        self.c_p, self.c_g = None, None
        self.c_sk, self.c_pk = None, None

        self.s_p, self.s_g = None, None
        self.s_sk, self.s_pk = None, None

        self.client_pk = []

        self.secrets = []

        self.e = []
        self.e_other = []

        self.p_u_v = {}

        self.b_u = None
        self.p_u = {}

        self.y_u = {}

        self.U_recon = None
        self.share = []

    # round_0_0 生成两对公钥私钥 256位用来做掩饰 1024位用来密钥交换进行加密
    def gen_pk_sk(self):
        self.c_p, self.c_g = KA.init_parameter(self.conf['c_size'])
        self.c_sk, self.c_pk = KA.generate_key(self.c_p, self.c_g)

        self.s_p, self.s_g = KA.init_parameter(self.conf['s_size'])
        self.s_sk, self.s_pk = KA.generate_key(self.s_p, self.s_g)

    # round_0_1 发送两队公钥到服务器
    def send_cpk_spk(self):
        return self.id, self.c_pk, self.s_pk

    # round_1_0 从服务器接收所有的公钥
    def receive_client_pk(self, client_pk):
        self.client_pk = client_pk

    # round_1_1 生成s_sk的秘密分享
    def share_secrets(self):
        n = len(self.client_pk)
        t = self.conf['share_secrets_t']
        if n >= t:
            self.secrets = SS.share(self.s_sk, t, n)

    # round_1_2 对秘密分享使用密钥交换的密钥加密
    # 加密内容m: u_id + v_id + secret_index + secret_1 + secret_2 中间使用分隔符分割
    def encrypt(self):
        u = self.id
        u_sk = self.c_sk
        p = self.c_p
        split = self.conf['split'].encode()
        for i in range(len(self.client_pk)):
            pk = self.client_pk[i]
            secret = self.secrets[i]
            v = pk[0]
            v_pk = pk[1]
            key = KA.key_agreement(v_pk, u_sk, p)
            m = str(u).encode() + split + str(v).encode() + split + str(secret[0]).encode() + split + secret[
                1] + split + secret[2]
            c, tag, nonce = AE.encrypt(key, m)
            self.e.append((u, v, c, tag, nonce))

    # round_1_3 向服务端发送加密后的数据
    # e的内容：[u_id,v_id,cipher-text,tag,nonce]
    def send_e(self):
        return self.id, self.e

    # round_2_0 从服务器接收为其加密的秘密分享
    def receive_e_other(self, e_other):
        self.e_other = e_other

    def receive_model(self,model):
        for name, param in model.state_dict().items():
            self.local_model.state_dict()[name].copy_(param.clone())

    # round_2_1 模型参数更新
    def model_update(self,model):

        for name, param in model.state_dict().items():
            self.local_model.state_dict()[name].copy_(param.clone())

        optimizer = torch.optim.SGD(self.local_model.parameters(), lr=self.conf['lr'],
                                    momentum=self.conf['momentum'])
        self.local_model.train()
        for e in range(self.conf["local_epochs"]):

            for batch_id, batch in enumerate(self.train_loader):
                data, target = batch

                if torch.cuda.is_available():
                    data = data.cuda()
                    target = target.cuda()

                optimizer.zero_grad()
                output = self.local_model(data)
                loss = torch.nn.functional.cross_entropy(output, target)
                loss.backward()

                optimizer.step()
            # logging.info(self.name + " local epochs:" + str(e))
        for name, data in self.local_model.state_dict().items():
            self.diff[name] = (data - model.state_dict()[name]).cpu().numpy()
        # print(self.diff['conv1.weight'])

    def model_updata_test(self):
        for name,data in self.local_model.items():
            self.diff[name] = np.ones((2,2,3,4))

    # round_2_2 计算掩饰值1
    def compute_mask_1(self):
        self.p_u_v = dict()
        for name, data in self.diff.items():
            self.p_u_v[name] = np.zeros(data.shape)
        u = self.id
        seeds = dict()
        # 计算 与其他客户端密钥交换生成的种子
        for item in self.client_pk:
            v = int(item[0])
            if u == v:
                continue
            elif self.e_other[v] != 0:
                pk = int(item[2])
                sk = self.s_sk
                p = self.s_p
                key = KA.key_agreement(pk, sk, p)
                seed = 0
                for i in range(0, len(key), 4):
                    seed += int.from_bytes(key[i:i + 4], 'little')
                seed %= 2 ** 32 - 1
                seeds[v] = seed
        # 根据种子计算随机数
        for v,seed in seeds.items():
            np.random.seed(seed)
            for name, data in self.p_u_v.items():
                if u > v:
                    self.p_u_v[name] += np.random.random(data.shape)
                elif u < v:
                    self.p_u_v[name] -= np.random.random(data.shape)


    # round_2_3 计算掩饰值2
    def compute_mask_2(self):
        self.b_u = int(random.random() * (10 ** 16)) % (2 ** 32 - 1)
        self.p_u = dict()
        for name, data in self.diff.items():
            np.random.seed(self.b_u)
            self.p_u[name] = np.random.random(data.shape)

    # round_2_4 计算掩饰后的私有向量
    def compute_mask_vector(self):
        for name, data in self.diff.items():
            self.y_u[name] = data + self.p_u[name] + self.p_u_v[name]


    # round_2_5 向服务器A发送b_u
    def send_b_u_A(self):
        return self.id, self.b_u

    # round_2_6 向服务器B发送带掩饰的私有向量
    def send_y_u_B(self):
        return self.id, self.y_u

    # round_3_0 接收来自服务器A的用户列表U_recon
    def receive_u_recon(self, U_recon):
        self.U_recon = U_recon

    # round_3_1 解密需要重建密钥的用户集合
    def decrypt_e_other(self):
        self.share = [0] * len(self.U_recon)
        split = self.conf['split'].encode()
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



