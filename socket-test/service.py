from flask_socketio import SocketIO,send,emit
from flask import Flask
import time

app = Flask('NAME')
app.config['SECRET_KEY'] = 'secret'
sockio = SocketIO(app)

@sockio.on('my_message')
def handle_message(data):
    print('receive message:' + str(data))
    time.sleep(10)
    emit('my_response',data['id'])

if __name__ == '__main__':
    sockio.run(app,port=9000)


