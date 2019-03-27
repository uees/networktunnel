#!/usr/bin/env python3

import socketserver


class MyServer(socketserver.BaseRequestHandler):

    def handle(self):
        # 对于 UDP request 是 (client_data_bytes,udp的套接字对象) 元组
        print(self.request)

        data_bytes, sock = self.request
        print('收到客户端的消息是', data_bytes.decode('utf-8'))
        print('addr is: ', self.client_address)  # 获取 client 的地址和端口号

        sock.sendto(data_bytes.upper(), self.client_address)


if __name__ == '__main__':
    server = socketserver.ThreadingUDPServer(('127.0.0.1', 8080), MyServer)  # 多线程
    server.serve_forever()
