from Double_Cloud import utils
from Double_Cloud import client
from Double_Cloud import serverA
from Double_Cloud import serverB


import numpy as np
# 初始化客户端
print("init start")
clients = []
client_config = utils.load_json('./config/client.json')
model_config = utils.load_json('./config/model.json')
server_config = utils.load_json('./config/server.json')
client_num = server_config['client_num']
for i in range(client_num):
    clients.append(client.Client(i, client_config, model_config))
serverA = serverA.ServerA(server_config,model_config)
serverB = serverB.ServerB(server_config)
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

for i in range(client_num):
    if clients_s[i]:
        temp[i] = serverA.send_client_pk(i)
print("round0 end")

# clients_s[5] = 0


# round 1
print("round1 start")
for i in range(client_num):
    if clients_s[i]:
        c = clients[i]
        c.receive_client_pk(temp[i])
        c.share_secrets()
        c.encrypt()
        id, e = c.send_e()
        serverA.receive_e(id,e)


for i in range(client_num):
    if clients_s[i]:
        temp[i] = serverA.send_e_other(i)
print("round1 end")



# round 2
print("round2 start")
for i in range(client_num):
    if clients_s[i]:
        c = clients[i]
        c.receive_e_other(temp[i])

        c.model_update()
        c.compute_mask_1()
        c.compute_mask_2()
        c.compute_mask_vector()

        _,temp_bu[i] = c.send_b_u_A()
        _,temp_yu[i] = c.send_y_u_B()

# clients_s[1] = 0

for i in range(client_num):
    if clients_s[i]:
        serverA.receive_b_u(i,temp_bu[i])

clients_s[2] = 0
for i in range(client_num):
    if clients_s[i]:
        serverB.receive_y_u(i,temp_yu[i])


U_3 = serverA.send_survive_client()
serverB.receive_u_3(U_3)
serverB.intersection_u3_u4()
serverB.sum_y_u()
u_5, s = serverB.send_u5_sum()
serverA.receive_u5_sum(u_5,s)
serverA.compute_u_recon()

for i in range(client_num):
    if clients_s[i]:
        temp[i] = serverA.send_recon(i)
print("round2 end")

# clients_s[7] = 0

# round 3
print("round3 start")
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
s = np.zeros(serverA.server_conf['w_size'])
for c in clients:
    if u_5[c.id]:
        s += c.w
print(s)
print(s == serverA.res)



















