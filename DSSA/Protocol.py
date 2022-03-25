from DSSA import Config
from DSSA import Client
from DSSA import ServerA
from DSSA import ServerB
import numpy as np
import random

def disconnect(clients_s):
    for i in range(len(clients_s)):
        if clients_s[i]:
            r = random.random()
            if r <= Config.loss:
                clients_s[i] = 0
    return clients_s


if __name__ == '__main__':
    # 初始化客户端
    print("init start")
    client_num = Config.client_num
    clients = []
    for i in range(client_num):
        clients.append(Client.Client(i))
    serverA = ServerA.ServerA()
    serverB = ServerB.ServerB()
    temp = [0] * client_num
    temp_bu = [0] * client_num
    temp_yu = [0] * client_num
    clients_s = [1] * client_num
    print("init end")

    # round 0
    print("round0 start")
    for c in clients:
        c.gen_pk_sk()
        id, c_pk, s_pk = c.send_cpk_spk()
        serverA.receive_client_pk(id, c_pk, s_pk)

    # disconnect
    clients_s = disconnect(clients_s)

    for i in range(client_num):
        if clients_s[i]:
            temp[i] = serverA.send_client_pk(i)
    print("round0 end")


    # round 1
    print("round1 start")
    print("active clients num： ", sum(clients_s))

    for i in range(client_num):
        if clients_s[i]:
            c = clients[i]
            c.receive_client_pk(temp[i])
            c.share_secrets()
            c.encrypt()
            id, e = c.send_e()
            serverA.receive_e(id, e)

    # disconnect
    clients_s = disconnect(clients_s)

    for i in range(client_num):
        if clients_s[i]:
            temp[i] = serverA.send_e_other(i)

    print("round1 end")

    # round 2
    print("round2 start")
    print("active clients num： ", sum(clients_s))

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

    # disconnect
    clients_s = disconnect(clients_s)

    for i in range(client_num):
        if clients_s[i]:
            serverA.receive_b_u(i, temp_bu[i])

    # disconnect
    clients_s = disconnect(clients_s)

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
    print("round2 end")

    # clients_s[7] = 0

    # round 3
    print("round3 start")
    print("active clients num： ", sum(clients_s))

    # disconnect
    clients_s = disconnect(clients_s)
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
    print("round3 end")

    print("aggregation result:")
    print(serverA.res)

    print("true result:")
    s = np.zeros(Config.w_size)
    n = 0
    for c in clients:
        if u_5[c.id]:
            s += c.w
            n += 1
    print("aggregation number: " + str(n))

    print(s)
    print(s == serverA.res)




















