from Double_Cloud import utils
import numpy as  np


class ServerB:

    def __init__(self,conf):
        self.name = 'serverB'
        self.conf = conf
        self.client_num = self.conf['client_num']

        self.y_u = [0] * self.client_num

        self.U_3 = []
        self.U_4 = [0] * self.client_num

        self.U_5 = [0] * self.client_num
        self.sum = np.zeros(self.conf['w_size'])

    # round_2_0 接收来自客户端的y_u
    def receive_y_u(self,u,y_u):
        u = int(u)
        self.y_u[u] = y_u
        self.U_4[u] = 1

    # round_2_1 接收来自serverA的用户列表
    def receive_u_3(self,u_3):
        self.u_3 = u_3

    # round_2_2 求u3和u4的交集u5
    def intersection_u3_u4(self):
        for i in range(self.client_num):
            if self.u_3[i] and self.U_4[i]:
                self.U_5[i] = 1

    # round_2_3 对y_u求和
    def sum_y_u(self):
        for i in range(self.client_num):
            if self.U_5[i] and self.U_4[i]:
                self.sum += self.y_u[i]

    # round_2_4 发送u_5和sum给服务器A
    def send_u5_sum(self):
        return self.U_5,self.sum

















