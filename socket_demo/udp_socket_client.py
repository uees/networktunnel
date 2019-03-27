#!/usr/bin/env python3

import socket

ip_port = ('127.0.0.1', 8080)
buffer_size = 1024

udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    msg = input('>>: ').strip()
    if not msg:
        continue
    if msg == 'quit':
        break

    udp_client.sendto(msg.encode('utf-8'), ip_port)

    data, addr = udp_client.recvfrom(buffer_size)
    print("接收的数据为： ", data.decode('utf-8'))
