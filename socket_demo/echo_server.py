import socket

HOST = '127.0.0.1'
PORT = 8889   # 监听的端口 （非系统级的端口：大于 1023)


# socket.socket() 创建了一个 socket 对象
# 传入的 socket 地址族参数 socket.AF_INET 表示因特网 IPv4 地址族
# SOCK_STREAM 表示使用 TCP 的 socket 类型
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skt:
    # Use the socket object without calling skt.close()

    # bind() 用来关联 socket 到指定的网络接口（IP 地址）和端口号
    skt.bind((HOST, PORT))
    skt.listen()

    # accept() 方法阻塞并等待传入连接。当一个客户端连接时，它将返回一个新的 socket 对象
    # 你将用这个 socket 对象和客户端进行通信
    conn, addr = skt.accept()
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024)
            # 如果 conn.recv() 方法返回一个空 byte 对象 b''，然后客户端关闭连接，循环结束
            if not data:
                break
            conn.sendall(data)
