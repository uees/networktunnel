#!/usr/bin/env python3

import socket

BUF_SIZE = 1024
host = socket.gethostname()
port = 8888
server_addr = (host, port)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
    while True:
        data = input('Please Input data > ')
        client.sendto(data.encode('utf-8'), server_addr)  # 向服务器发送数据
        bytes_data, addr = client.recvfrom(BUF_SIZE)  # 从服务器接收数据
        print('recvfrom ', addr, ' data:', bytes_data.decode('utf-8'))
