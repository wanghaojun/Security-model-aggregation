import socketio
import time

def response(data):
    print('from server:' + str(data))

if __name__ == '__main__':
    sio = socketio.Client()
    sio.on('my_response', response)

    sio.connect('http://127.0.0.1:5000/')
    sio.emit('my_message', {'id': 2})
    # for i in range(60):
    #     sio.emit('my_message', {'id': 2})
    #     time.sleep(1)

    sio.wait()



