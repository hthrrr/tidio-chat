import sys
import uuid
from time import sleep

from prompt_toolkit.patch_stdout import patch_stdout
from socketio import Client
import argparse
from prompt_toolkit import PromptSession
from threading import Event
from socketio.exceptions import TimeoutError, ConnectionError

class Config:
    name = ""
    visitor_id = uuid.uuid4().hex
    ppk = "zbc1aebecwfgyuygpzu4pbc8g5wv8c0j"

# sio = Client(logger=True, engineio_logger=True)
sio = Client(logger=False, engineio_logger=False, reconnection_attempts=3, reconnection_delay=0.5)
config = Config()
registration_complete = Event()

@sio.event
def connect():
    print("Connected to the server, now registering the user")
    visitor_data = {
        "id": config.visitor_id,
        "project_public_key": config.ppk,
        'name': config.name,
    }
    try:
        sio.call('visitorRegister', visitor_data, timeout=10)
        print("Registration successful")
        print("\nYou can now type messages (type 'quit' to exit):")
        registration_complete.set()
    except TimeoutError:
        registration_complete.set()
        print("Registration timed out")
        sio.disconnect()
        sys.exit(1)
    except Exception as e:
        registration_complete.set()
        print(f"Registration failed: {e}")
        sio.disconnect()
        sys.exit(1)

@sio.event
def connect_error(data):
    print(f"The connection failed: {data}")

@sio.event
def disconnect(reason):
    if reason == sio.reason.CLIENT_DISCONNECT:
        print('you disconnected')
    elif reason == sio.reason.SERVER_DISCONNECT:
        print('the server disconnected the client')
    else:
        print('disconnect reason:', reason)

@sio.on('newMessage')
def on_new_message(data):
    print(f"\nNew message: {data['data']['message']['message']}")

def send_message(text):
    if not text:
        return

    message_data = {
        "message": text,
        "messageId": str(uuid.uuid4()),
        "project_public_key": config.ppk,
        "id": config.visitor_id,
    }

    sio.emit('visitorNewMessage', message_data)

def input_handler():
    prompt_session = PromptSession()
    while sio.connected:
        with patch_stdout():
            try:
                text = prompt_session.prompt("\nyour message: ")
            except KeyboardInterrupt:
                break
        if text.lower() == 'quit':
            break
        send_message(text)
    sio.disconnect()


def parse_args():
    parser = argparse.ArgumentParser(description='Tidio Chat Client')
    parser.add_argument('--name', type=str, help='Your name', default=config.name)
    parser.add_argument('--ppk', type=str, help='Project key', default=config.ppk)
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    config.name = args.name
    config.ppk = args.ppk

    url = f"wss://socket.tidio.co/socket.io"

    try:
        sio.connect(url, transports=['websocket'], retry=True, wait_timeout=10, )
    except ConnectionError as e:
        print("failed to connect: ", e)
        sys.exit(1)


    registration_complete.wait()
    input_handler()
