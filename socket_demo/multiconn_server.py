#!/usr/bin/env python3

import selectors
import socket
import sys
import types


def accept_wrapper(sel, sock):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)
    # types.SimpleNamespace 类创建了一个对象用来保存我们想要的 socket 和数据
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(sel, key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print("closing connection to", data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print("echoing", repr(data.outb), "to", data.addr)
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("usage:", sys.argv[0], "<host> <port>")
        sys.exit(1)

    host, port = sys.argv[1], int(sys.argv[2])
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((host, port))
    lsock.listen()
    print("listening on", (host, port))

    # 配置 socket 为非阻塞模式
    lsock.setblocking(False)

    sel = selectors.DefaultSelector()
    sel.register(lsock, selectors.EVENT_READ, data=None)

    try:
        while True:
            # sel.select(timeout=None) 调用会阻塞直到 socket I/O 就绪
            events = sel.select(timeout=None)  # 核心部分
            for key, mask in events:
                if key.data is None:
                    # 如果 key.data 为空, 我们就可以知道它来自于监听 socket
                    accept_wrapper(sel, key.fileobj)
                else:
                    # 如果 key.data 不为空，我们就可以知道它是一个被接受的客户端 socket，我们需要为它服务
                    service_connection(sel, key, mask)
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        sel.close()
