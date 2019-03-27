#!/usr/bin/env python3

import socket

BUF_SIZE = 1024
host = socket.gethostname()
port = 8888
server_addr = (host, port)

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
    server.bind(server_addr)  # 套接字绑定IP和端口
    # udp 不需要 listen 和 accept
    while True:
        print("waiting for data")
        bytes_data, client_addr = server.recvfrom(BUF_SIZE)  # 从客户端接收数据, 这里应该会阻塞
        print('Connected by', client_addr, ' Receive Data : ', bytes_data.decode('utf-8'))
        server.sendto(bytes_data, client_addr)  # 发送数据给客户端
