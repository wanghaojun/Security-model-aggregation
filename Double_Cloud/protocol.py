from Double_Cloud import utils
from Double_Cloud import client
from Double_Cloud import serverA
from Double_Cloud import serverB

import numpy as np
import logging
import time

logger = logging.Logger("protocol",level=logging.INFO)
LOG_FORMAT = "%(name)s - %(asctime)s  - %(levelname)s - %(message)s"
current_time = lambda: int(round(time.time() * 1000))
logging.basicConfig(level=logging.INFO,format=LOG_FORMAT)
# logging.getLogger('werkzeug').setLevel(logging.ERROR)

if __name__ == '__main__':
    # 初始化客户端
    logging.info("init start")
    clients = []
    config = utils.load_json('./config/conf.json')
    client_num = config['client_num']
    for i in range(client_num):
        clients.append(client.Client(i, config))
    serverA = serverA.ServerA(config)
    serverB = serverB.ServerB(config)
    temp = [0] * client_num
    temp_bu = [0] * client_num
    temp_yu = [0] * client_num
    clients_s = [1] * client_num
    logging.info("init end")

    # round 0
    logging.info("round0 start")
    for c in clients:
        c.gen_pk_sk()
        id, c_pk, s_pk = c.send_cpk_spk()
        serverA.receive_client_pk(id, c_pk, s_pk)

    for i in range(client_num):
        if clients_s[i]:
            temp[i] = serverA.send_client_pk(i)
    logging.info("round0 end")

    # clients_s[5] = 0

    # round 1
    logging.info("round1 start")
    for i in range(client_num):
        if clients_s[i]:
            c = clients[i]
            c.receive_client_pk(temp[i])
            c.share_secrets()
            c.encrypt()
            id, e = c.send_e()
            serverA.receive_e(id, e)

    for i in range(client_num):
        if clients_s[i]:
            temp[i] = serverA.send_e_other(i)
    logging.info("round1 end")

    # round 2
    logging.info("round2 start")
    for i in range(client_num):
        if clients_s[i]:
            c = clients[i]
            c.receive_e_other(temp[i])

            c.model_update()
            c.compute_mask_1()
            c.compute_mask_2()
            c.compute_mask_vector()

            _, temp_bu[i] = c.send_b_u_A()
            _, temp_yu[i] = c.send_y_u_B()

    # clients_s[1] = 0
    for i in range(client_num):
        if clients_s[i]:
            serverA.receive_b_u(i, temp_bu[i])

    clients_s[2] = 0
    for i in range(client_num):
        if clients_s[i]:
            serverB.receive_y_u(i, temp_yu[i])

    U_3 = serverA.send_survive_client()
    serverB.receive_u_3(U_3)
    serverB.intersection_u3_u4()
    serverB.sum_y_u()
    u_5, s = serverB.send_u5_sum()
    serverA.receive_u5_sum(u_5, s)
    serverA.compute_u_recon()

    for i in range(client_num):
        if clients_s[i]:
            temp[i] = serverA.send_recon(i)
    logging.info("round2 end")

    # clients_s[7] = 0

    # round 3
    logging.info("round3 start")
    for i in range(client_num):
        if clients_s[i]:
            c = clients[i]
            c.receive_u_recon(temp[i])
            c.decrypt_e_other()
            id, share = c.send_share()
            serverA.receive_share(id, share)

    serverA.sum_p_u()
    serverA.reconstruction()
    serverA.sum_recon_p_u_v()
    serverA.compute_res()
    logging.info("round3 end")

    # logging.info("aggregation result:" )

    # verify
    logging.info("true result:")
    s = np.zeros(config['w_size'])
    for c in clients:
        if u_5[c.id]:
            s += c.w
    logging.info(s)
    logging.info(s == serverA.res)



















