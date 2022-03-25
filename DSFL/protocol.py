from DSFL import utils
from DSFL import client
from DSFL import serverA
from DSFL import serverB
from DSFL import datasets

import numpy as np
import logging
import time
import random
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
    train_data,eval_data = datasets.get_dataset("../data/", 'cifar')
    for i in range(client_num):
        clients.append(client.Client(i, config, train_data))
    serverA = serverA.ServerA(config,eval_data)
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

    for i in range(client_num):
        clients[i].receive_e_other(temp[i])


    acc, loss, size = serverA.model_eval()
    logging.info("acc: " + str(acc) + ',' + " loss: " + str(loss) + " size: " + str(size))

    # for c in clients:
    #     c.compute_mask_2()

    for e in range(config['global_epochs']):
        # round 2
        # logging.info("round2 start")
        # diff_sum = dict()
        serverA.reset()
        serverB.reset()
        temp_bu = [0] * client_num
        temp_yu = [0] * client_num
        clients_s = [1] * client_num
        drop_ids = random.sample(range(10),int(client_num * config['loss']))
        for id in drop_ids:
            clients_s[id] = 0

        for c in clients:
            # c.receive_model(serverA.global_model)
            c.model_update(serverA.global_model)
            c.compute_mask_1()
            c.compute_mask_2()
            c.compute_mask_vector()

        for i in range(client_num):
            if clients_s[i]:
                c = clients[i]
                _, temp_bu = c.send_b_u_A()
                _, temp_yu= c.send_y_u_B()
                serverA.receive_b_u(i,temp_bu)
                serverB.receive_y_u(i,temp_yu)

        U_3 = serverA.send_survive_client()
        serverB.receive_u_3(U_3)
        serverB.intersection_u3_u4()
        # serverB.sum = dict()
        serverB.sum_y_u()
        u_5, s = serverB.send_u5_sum()
        serverA.receive_u5_sum(u_5, s)
        serverA.compute_u_recon()

        for i in range(client_num):
            if clients_s[i]:
                temp[i] = serverA.send_recon(i)
        # logging.info("round2 end")

        # clients_s[7] = 0

        # round 3
        # logging.info("round3 start")
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
        # logging.info("round3 end")
        serverA.global_model_update()
        acc, loss, size = serverA.model_eval()
        aggregation_num = sum(u_5)
        logging.info("Epoch %d, acc: %f, loss: %f\n, aggregation_num: %d" % (e, acc, loss, aggregation_num))
        if acc <= 10.5:
            break


    def verify_diff():
        diff_sum = dict()
        diff_diff = dict()
        for name,data in serverA.sum.items():
            diff_sum[name] = np.zeros(data.shape)
        for i in range(client_num):
            if clients_s[i]:
                for name,data in clients[i].diff.items():
                    diff_sum[name] += data
        for name,data in diff_sum.items():
            diff_diff[name] = diff_sum[name] - serverA.res[name]
        return diff_sum,diff_diff

    def verify_puv():
        puv_sum = dict()
        puv_diff = dict()
        for name,data in serverA.sum.items():
            puv_sum[name] = np.zeros(data.shape)
        for i in range(client_num):
            if not clients_s[i]:
                for name,data in clients[i].p_u_v.items():
                    puv_sum[name] += data
        for name, data in puv_sum.items():
            puv_diff[name] = puv_sum[name] - serverA.p_u_v_sum[name]

        return puv_sum,puv_diff

    def verify_pu():
        pu_sum = dict()
        pu_diff = dict()
        for name, data in serverA.sum.items():
            pu_sum[name] = np.zeros(data.shape)
        for i in range(client_num):
            if clients_s[i]:
                for name, data in clients[i].p_u.items():
                    pu_sum[name] += data
        for name,data in pu_sum.items():
            pu_diff[name] = pu_sum[name] - serverA.p_u_sum[name]

        return pu_sum,pu_diff





















