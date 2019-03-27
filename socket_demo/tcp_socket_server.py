#!/usr/bin/env python3

import socketserver


# 首先必须创建一个请求处理类, 它是 BaseRequestHandler 的子类
class MyServer(socketserver.BaseRequestHandler):

    # 重新写其 handle() 方法
    # handle() 完成服务请求所需的所有工作
    def handle(self):
        print('conn is: ', self.request)  # 与 client 的链接请求信息, tcp 连接时 request 是一个 socket 对象
        print('addr is: ', self.client_address)  # 获取 client 的地址和端口号
        print('server is: ', self.server)

        data = self.request.recv(1024)
        print('收到客户端的消息是', data.decode('utf-8'))

        self.request.sendall(data.upper())

    def finish(self):
        self.request.close()


if __name__ == '__main__':
    # 开启多线程，绑定地址，和处理通信的类
    server = socketserver.ThreadingTCPServer(('127.0.0.1', 8000), MyServer)
    server.serve_forever()  # 连接循环
