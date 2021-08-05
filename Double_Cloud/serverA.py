import numpy as np
from flask_socketio import SocketIO, send, emit
import socketio
from Double_Cloud import utils
from tools import SecretShare as SS
from tools import KeyAgreement as KA
from flask import Flask
import time
import logging

logger = logging.Logger("serverA",level=logging.INFO)
LOG_FORMAT = "%(name)s - %(asctime)s  - %(levelname)s - %(message)s"
current_time = lambda: int(round(time.time() * 1000))
logging.basicConfig(level=logging.INFO,format=LOG_FORMAT)
logging.getLogger('werkzeug').setLevel(logging.ERROR)


class ServerA(object):
    def __init__(self, server_conf, model_conf):
        self.name = 'serverA'
        self.server_conf = server_conf
        self.model_conf = model_conf
        self.client_num = self.server_conf['client_num']
        self.size = self.server_conf['w_size']
        self.wait_time = self.server_conf['wait_time']

        # round 0 param
        self.client_pk = {}
        self.round0_time = 0
        self.U_1 = [0] * self.client_num

        self.round1_time = 0
        self.e_u_v = [[0 for _ in range(self.client_num)] for i in range(self.client_num)]
        self.U_2 = [0] * self.client_num

        self.round2_time = 0
        self.b_u = [0] * self.client_num
        self.U_3 = [0] * self.client_num
        self.U_3_send = False

        self.sum = None
        self.U_5 = None

        self.U_recon = [0] * self.client_num
        self.shares = []

        self.p_u_sum = np.zeros(self.size)
        self.p_u_v_sum = np.zeros(self.size)
        self.sk_recon = [0] * self.client_num
        self.s_p, self.s_g = KA.init_parameter(self.server_conf['s_size'])
        self.res = None

        self.app = Flask(self.name)
        self.serverB = socketio.Client()
        self.sio = SocketIO(self.app, logger=False)
        self.sio.on_event('client_pk', self.receive_client_pk)
        self.sio.on_event('encrypt_data', self.receive_e)
        self.sio.on_event('b_u',self.receive_b_u)
        self.sio.on_event('sum',self.receive_u5_sum)


    # round_0
    # 接受客户端的公钥 用户列表为U_1
    # 向U_1用户集合发送收到的公钥集合
    def receive_client_pk(self, u, c_pk, s_pk):
        if not self.round0_time:
            self.round0_time = current_time()
        if current_time() <= self.round0_time + self.wait_time * 1000:
            logging.info("receive pk from :" + str(u))
            self.client_pk[u] = [c_pk, s_pk]
            self.U_1[u] = 1
        else:
            logging.info("receive pk from :" + str(u) + " time out")
        _wait = self.wait_time - (current_time() - self.round0_time) / 1000
        if _wait > 0:
            time.sleep(_wait)
        if self.U_1[u]:
            emit('client_pk', self.client_pk)
        else:
            emit('dis_connect')

    # round_1_0 接受来自客户端的密文
    # u 发送客户端id
    # e的内容：[u_id, v_id,cipher-text,tag,nonce]
    # 用户列表为U_2
    # round_1_1 向U_2中客户端发送其它客户端给他的密文
    def receive_e(self, u, e:{}):
        if not self.round1_time:
            self.round1_time = current_time()
        if current_time() <= self.round1_time + self.wait_time * 1000:
            logging.info("receive encrypt_data from :" + str(u))
            u = int(u)
            self.U_2[u] = 1
            _list = []
            for v, data in e.items():
                v = int(v)
                self.e_u_v[u][v] = data
        else:
            logging.info("receive encrypt_data from :" + str(u) + " time out")
        _wait = self.wait_time - (current_time() - self.round1_time) / 1000
        if _wait > 0:
            time.sleep(_wait)
        if self.U_2[u]:
            _send_list = [e_u[u] for e_u in self.e_u_v]
            _send_dic = {}
            for i in range(len(_send_list)):
                if _send_list[i]:
                    _send_dic[i] = _send_list[i]
            emit('encrypt_data', _send_dic)
        else:
            emit('dis_connect')

    # round_2_0 接受来自客户端的b_u
    def receive_b_u(self, u, b_u):
        if not self.round2_time:
            self.round2_time = current_time()
        if current_time() <= self.round2_time + self.wait_time * 1000:
            logging.info("receive b_u from :" + str(u))
            u = int(u)
            self.b_u[u] = b_u
            self.U_3[u] = 1
        else:
            logging.info("receive b_u from :" + str(u) + " time out")
        _wait = self.wait_time - (current_time() - self.round2_time) / 1000
        if _wait > 0:
            time.sleep(_wait)
        if not self.U_3_send:
            logging.info("send U_3 to serverB")
            self.U_3_send = True
            self.serverB.connect(self.server_conf['serverB_url'])
            self.serverB.emit('u_3', self.U_3)
    # # round_2_1 发送存活客户端列表给服务器B
    # def send_survive_client(self):
    #     return self.U_3

    # round_2_2 接收来自服务器B的sum和U_5
    def receive_u5_sum(self, U_5, sum):
        self.U_5 = U_5
        self.sum = np.array(sum)
        logging.info('receive u_5 and sum from serverB')

    # round_2_3 求需要恢复密钥的掉线用户集合（u in U_2 and u not in U_5）:
    def compute_u_recon(self):
        for i in range(self.client_num):
            if self.U_2[i] and not self.U_5[i]:
                self.U_recon[i] = 1

    # round_2_4 向U_3客户端发送需要恢复密钥的用户集合U_recon
    def send_recon(self, u):
        if self.U_3[u]:
            return self.U_recon

    # round_3_0 接收来自客户端的分享值
    def receive_share(self, u, share):
        self.shares.append(share)

    # round_3_1 聚合掩饰值2 p_u
    def sum_p_u(self):
        for i in range(self.client_num):
            if self.U_5[i]:
                np.random.seed(self.b_u[i])
                p_u = np.random.random(self.size)
                self.p_u_sum += p_u

    # round_3_2 重建掉线用户U_recon密钥
    def reconstruction(self):
        t = self.server_conf['share_secrets_t']
        for i in range(self.client_num):
            if self.U_recon[i]:
                share = [x[i] for x in self.shares]
                share = share[:t + 1]
                if len(share) >= t:
                    self.sk_recon[i] = SS.reconstruction(share)

    # round_3_3 计算掉线用户U_recon带来的损失
    def sum_recon_p_u_v(self):
        p = self.s_p
        for u in range(self.client_num):
            if self.sk_recon[u]:
                sk = self.sk_recon[u]
                p_u_v = np.zeros(self.size)
                for v in range(self.client_num):
                    if self.U_5[v]:
                        pk = self.client_pk[v][2]
                        ks = []
                        key = KA.key_agreement(pk, sk, p)
                        for i in range(0, len(key), 4):
                            ks.append(int.from_bytes(key[i:i + 4], 'little'))
                        r = np.zeros(self.size)
                        for seed in ks:
                            seed %= 2 ** 32 - 1
                            np.random.seed(seed)
                            r += np.random.random(self.size)
                        if u > v:
                            p_u_v += r
                        else:
                            p_u_v -= r
                self.p_u_v_sum += p_u_v

    # round_3_4 计算最终聚合结果
    def compute_res(self):
        _res = (self.sum - self.p_u_sum + self.p_u_v_sum).round(self.server_conf['rounding'] + 1)
        self.res = np.array(_res).round(self.server_conf['rounding'] - 1)

    def start(self):
        self.sio.run(self.app, port=self.server_conf['serverA_port'],log_output=False)


if __name__ == '__main__':
    server = ServerA(utils.load_json('./config/server.json'), utils.load_json('./config/model.json'))
    server.start()

    # server.send_client_pk()
