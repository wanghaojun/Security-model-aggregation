from Double_Cloud import models
import numpy as np
from tools import SecretShare as SS
from tools import KeyAgreement as KA
import torch

import logging,time

logger = logging.Logger("protocol",level=logging.INFO)
LOG_FORMAT = "%(name)s - %(asctime)s  - %(levelname)s - %(message)s"
current_time = lambda: int(round(time.time() * 1000))
logging.basicConfig(level=logging.INFO,format=LOG_FORMAT)
class ServerA:
    def __init__(self,conf,eval_dataset):
        self.name = 'serverA'
        self.conf = conf
        self.global_model = models.get_model(self.conf["model_name"])
        self.eval_loader = torch.utils.data.DataLoader(eval_dataset, batch_size=self.conf["batch_size"], shuffle=True)

        self.client_num = self.conf['client_num']
        self.size = self.conf['w_size']

        self.client_pk = [0] * self.client_num
        self.U_1 = [0] * self.client_num

        self.e_u_v = [[0 for _ in range(self.client_num)] for i in range(self.client_num)]
        self.U_2 = [0] * self.client_num

        self.b_u = [0] * self.client_num
        self.U_3 = [0] * self.client_num

        self.sum = None
        self.U_5 = None

        self.U_recon = [0] * self.client_num
        self.shares = []

        self.p_u_sum = dict()
        self.p_u_v_sum = dict()
        self.sk_recon = [0] * self.client_num
        self.s_p, self.s_g = KA.init_parameter(self.conf['s_size'])
        self.res = dict()

    def reset(self):
        self.b_u = [0] * self.client_num
        self.U_3 = [0] * self.client_num

        self.sum = None
        self.U_5 = None

        self.U_recon = [0] * self.client_num
        self.shares = []

        self.p_u_sum = dict()
        self.p_u_v_sum = dict()
        self.sk_recon = [0] * self.client_num
        self.s_p, self.s_g = KA.init_parameter(self.conf['s_size'])
        self.res = dict()

    # round_0_0 接受客户端的公钥
    # 用户列表为U_1
    def receive_client_pk(self, u, c_pk, s_pk):

        self.client_pk[u] = [u, c_pk, s_pk]
        self.U_1[u] = 1

    # round_0_1 向U_1用户集合发送收到的公钥集合
    def send_client_pk(self,u):
        u = int(u)
        if self.U_1[u]:
            return self.client_pk

    # round_1_0 接受来自客户端的密文
    # u 发送客户端id
    # e的内容：[u_id, v_id,cipher-text,tag,nonce]
    # 用户列表为U_2
    def receive_e(self, u, e):
        u = int(u)
        self.U_2[u] = 1
        for item in e:
            if str(u) == str(item[0]):
                v = int(item[1])
                self.e_u_v[u][v] = item

    # round_1_1 向客户端发送其它客户端给他的密文
    def send_e_other(self, v):
        v = int(v)
        if self.U_2[v]:
            return [e_u[v] for e_u in self.e_u_v]

    # round_2_0 接受来自客户端的b_u
    def receive_b_u(self, u, b_u):
        u = int(u)
        self.b_u[u] = b_u
        self.U_3[u] = 1

    # round_2_1 发送存活客户端列表给服务器B
    def send_survive_client(self):
        return self.U_3

    # round_2_2 接收来自服务器B的sum和U_5
    def receive_u5_sum(self, U_5, sum):
        self.U_5 = U_5
        self.sum = sum

    # round_2_3 求需要恢复密钥的掉线用户集合（u in U_2 and u not in U_5）:
    def compute_u_recon(self):
        for i in range(self.client_num):
            if self.U_2[i] and not self.U_5[i]:
                self.U_recon[i] = 1

    # round_2_4 向U_3客户端发送需要恢复密钥的用户集合U_recon
    def send_recon(self, u):
        if self.U_3[u]:
            return self.U_recon

    # round_3_0 接收来自服务器A的分享值
    def receive_share(self, u, share):
        self.shares.append(share)

    # round_3_1 聚合掩饰值2 p_u
    def sum_p_u(self):
        for name,data in self.sum.items():
            self.p_u_sum[name] = np.zeros(data.shape)
        for i in range(self.client_num):
            if self.U_5[i]:
                for name, data in self.sum.items():
                    np.random.seed(self.b_u[i])
                    self.p_u_sum[name] += np.random.random(data.shape)

    # round_3_2 重建掉线用户U_recon密钥
    def reconstruction(self):
        t = self.conf['share_secrets_t']
        for i in range(self.client_num):
            if self.U_recon[i]:
                share = [x[i] for x in self.shares]
                share = share[:t+1]
                if len(share) >= t:
                    self.sk_recon[i] = SS.reconstruction(share)

    # round_3_3 计算掉线用户U_recon带来的损失
    def sum_recon_p_u_v(self):
        p = self.s_p
        for name,data in self.sum.items():
            self.p_u_v_sum[name] = np.zeros(data.shape)

        for u in range(self.client_num):
            if self.sk_recon[u]:
                sk = self.sk_recon[u]
                seeds = dict()
                for v in range(self.client_num):
                    if self.U_5[v]:
                        seed = 0
                        pk = self.client_pk[v][2]
                        key = KA.key_agreement(pk,sk,p)
                        for i in range(0, len(key), 4):
                            seed += int.from_bytes(key[i:i + 4], 'little')
                        seed %= 2**32 -1
                        seeds[v] = seed
                for v, seed in seeds.items():
                    np.random.seed(seed)
                    for name, data in self.p_u_v_sum.items():
                        if u > v:
                            self.p_u_v_sum[name] += np.random.random(data.shape)
                        elif u < v:
                            self.p_u_v_sum[name] -= np.random.random(data.shape)


    # round_3_4 计算最终聚合结果
    def compute_res(self):
        for name,data in self.sum.items():
            self.res[name] = self.sum[name] - self.p_u_sum[name] + self.p_u_v_sum[name]


    def global_model_update(self):
        for name,data in self.global_model.state_dict().items():
            update_per_layer = torch.from_numpy(np.array(self.res[name])).cuda() * self.conf["lambda"]
            update_per_layer = update_per_layer.to(torch.float32)
            if data.type() != update_per_layer.type():
                data.add_(update_per_layer.to(torch.int64))
            else:
                data.add_(update_per_layer)
            # if data.type() != update_per_layer.type():
            #     data.add_(update_per_layer.to(torch.float32))
            # else:
            #     data.add_(update_per_layer)


    def model_eval(self):
        self.global_model.eval()
        total_loss = 0.0
        correct = 0
        dataset_size = 0
        for batch_id, batch in enumerate(self.eval_loader):
            data, target = batch
            dataset_size += data.size()[0]

            if torch.cuda.is_available():
                data = data.cuda()
                target = target.cuda()

            output = self.global_model(data)

            total_loss += torch.nn.functional.cross_entropy(output, target, reduction='sum').item()  # sum up batch loss
            pred = output.data.max(1)[1]  # get the index of the max log-probability
            correct += pred.eq(target.data.view_as(pred)).cpu().sum().item()

        acc = 100.0 * (float(correct) / float(dataset_size))
        total_l = total_loss / dataset_size

        return acc, total_l, dataset_size
