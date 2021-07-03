import socketio
import time


class Client:
    def __init__(self):
        self.data = None
        self.sioA = socketio.Client()
        self.sioB = socketio.Client()


        self.sioA.on('my_response', self.response)

    def response(self, data):
        self.data = data
        print('from server:' + str(data))

    def send(self):
        self.sioA.connect('http://127.0.0.1:5000/')
        self.sioA.emit('my_message', ('111'.encode(),'2222'))
        self.sioB.connect('http://127.0.0.1:5001/')
        self.sioB.emit('my_message', ('222'.encode(),'2222'))


if __name__ == '__main__':
    # for i in range(60):
    #     sio.emit('my_message', {'id': 1})
    #     time.sleep(1)

    client = Client()
    client.send()

