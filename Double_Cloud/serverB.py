from Double_Cloud import utils
import numpy as  np
from flask_socketio import SocketIO, send, emit
import socketio
from flask import Flask
import logging
import time

logger = logging.Logger("serverA", level=logging.INFO)
LOG_FORMAT = "%(name)s - %(asctime)s  - %(levelname)s - %(message)s"
current_time = lambda: int(round(time.time() * 1000))
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.getLogger('werkzeug').setLevel(logging.ERROR)


class ServerB:

    def __init__(self, conf):
        self.name = 'serverB'
        self.server_conf = conf
        self.client_num = self.server_conf['client_num']
        self.wait_time = self.server_conf['wait_time']

        self.round2_time = 0
        self.y_u = {}
        self.U_3 = []
        self.U_4 = [0] * self.client_num

        self.U_5 = [0] * self.client_num
        self.sum = np.zeros(self.server_conf['w_size'])
        self.app = Flask(self.name)
        self.sio = SocketIO(self.app, logger=False)
        self.serverA = socketio.Client()
        self.serverA.connect(self.server_conf['serverA_url'])
        self.sio.on_event('y_u',self.receive_y_u)
        self.sio.on_event('u_3',self.receive_u_3)

    # round_2_0 接收来自客户端的y_u
    def receive_y_u(self, u, y_u):
        _wait_time = self.server_conf['model_wait_time']
        if not self.round2_time:
            self.round2_time = current_time()
        if current_time() <= self.round2_time + _wait_time * 1000:
            logging.info("receive y_u from :" + str(u))
            u = int(u)
            self.y_u[u] = y_u
            self.U_4[u] = 1
        else:
            logging.info("receive y_u from :" + str(u) + " time out")
        _wait = _wait_time - (current_time() - self.round2_time) / 1000
        if _wait > 0:
            time.sleep(_wait)

    # round_2_1 接收来自serverA的用户列表
    def receive_u_3(self, u_3):
        self.U_3 = u_3
        self.intersection_u3_u4()
        self.sum_y_u()
        self.send_u5_sum()

    # round_2_2 求u3和u4的交集u5
    def intersection_u3_u4(self):
        for i in range(self.client_num):
            if self.U_3[i] and self.U_4[i]:
                self.U_5[i] = 1

    # round_2_3 对y_u求和
    def sum_y_u(self):
        for i in range(self.client_num):
            if self.U_5[i] and self.U_4[i]:
                self.sum += self.y_u[i]

    # round_2_4 发送u_5和sum给服务器A
    def send_u5_sum(self):
        self.serverA.emit('sum', (self.U_5, self.sum))

    def start(self):
        self.sio.run(self.app, port=self.server_conf['serverB_port'], log_output=False)


if __name__ == '__main__':
    serverB = ServerB(utils.load_json('./config/server.json'))
    serverB.start()
