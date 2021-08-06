from flask_socketio import SocketIO,send,emit
from flask import Flask
import time

class serverA():
    def __init__(self):
        self.app = Flask('NAME')
        self.app.config['SECRET_KEY'] = 'secret'
        self.sockio = SocketIO(self.app)
        self.is_send = False

        @self.sockio.on('my_message')
        def handle_message(data):
            print('receive message:' + str(data))
            time.sleep(3)
            emit("my_response", "this is server", broadcast=True)




if __name__ == '__main__':
    s = serverA()
    s.sockio.run(s.app,port=5001)


