#!/usr/bin/env python3

import socket

server_addr = ('127.0.0.1', 8000)
buffer_size = 1024

while True:
    msg = input('>>: ').strip()
    if not msg:
        continue
    if msg == 'quit':
        break

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(server_addr)
        client.send(msg.encode('utf-8'))
        data = client.recv(buffer_size)
        print('收到服务端发来的消息: ', data.decode('utf-8'))
