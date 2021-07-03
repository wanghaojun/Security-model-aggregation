from flask_socketio import SocketIO,send,emit
from flask import Flask
import time

class serverA():
    def __init__(self):
        self.app = Flask('NAME')
        self.app.config['SECRET_KEY'] = 'secret'
        self.sockio = SocketIO(self.app)

        @self.sockio.on('my_message')
        def handle_message(data,m):
            print('receive message:' + str(data) + str(m))
            emit('my_response', data)


if __name__ == '__main__':
    s = serverA()
    s.sockio.run(s.app,port=5001)



