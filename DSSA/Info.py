class ClientPk:

    def __init__(self, id, c_pk, s_pk):
        self.id = id
        self.c_pk = c_pk
        self.s_pk = s_pk


class Key:

    def __init__(self, size, p, g, sk, pk):
        self.size = size
        self.p = p
        self.g = g
        self.sk = sk
        self.pk = pk



