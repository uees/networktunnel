#!/usr/bin/env python3

import Queue
import select
import socket

# Create a TCP/IP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

# Bind the socket to the port
server_address = ('127.0.0.1', 10000)
print('starting up on %s port %s' % server_address)
server.bind(server_address)

# Listen for incoming connections
server.listen(5)

# Sockets from which we expect to read
inputs = [server]

# Sockets to which we expect to write
outputs = []

# Outgoing message queues (socket:Queue)
message_queues = {}


if __name__ == "__main__":

    while inputs:
        # Wait for at least one of the sockets to be ready for processing
        print('\nwaiting for the next event')
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        for s in readable:
            # Readable list 中的socket 可以有3种可能状态，
            # 第一种是如果这个 socket 是 main "server" socket, 它负责监听客户端的连接，
            # 如果这个 main server socket 出现在 readable 里，那代表这是 server 端已经 ready 来接收一个新的连接进来了，
            # 为了让这个 main server 能同时处理多个连接，在下面的代码里，我们把这个 main server 的 socket 设置为非阻塞模式。
            if s is server:
                # A "readable" server socket is ready to accept a connection
                connection, client_address = s.accept()
                print('new connection from', client_address)
                connection.setblocking(0)
                inputs.append(connection)

                # Give the connection a queue for data we want to send
                message_queues[connection] = Queue.Queue()

            # 第二种情况是这个 socket 是已经建立了的连接，它把数据发了过来，这个时候你就可以通过 recv() 来接收它发过来的数据，
            # 然后把接收到的数据放到 queue 里，这样你就可以把接收到的数据再传回给客户端了。
            else:
                data = s.recv(1024)
                if data:
                    # A readable client socket has data
                    print('received "%s" from %s' % (data, s.getpeername()))
                    message_queues[s].put(data)
                    # Add output channel for response
                    if s not in outputs:
                        outputs.append(s)

                # 第三种情况就是这个客户端已经断开了，所以你再通过 recv() 接收到的数据就为空了，
                # 所以这个时候你就可以把这个跟客户端的连接关闭了。
                else:
                    # Interpret empty result as closed connection
                    print('closing', client_address, 'after reading no data')
                    # Stop listening for input on the connection
                    if s in outputs:
                        outputs.remove(s)  # 既然客户端都断开了，我就不用再给它返回数据了，所以这时候如果这个客户端的连接对象还在outputs列表中，就把它删掉
                    inputs.remove(s)  # inputs中也删除掉
                    s.close()  # 把这个连接关闭掉

                    # Remove message queue
                    del message_queues[s]

        # 对于 writable list 中的 socket，也有几种状态，如果这个客户端连接在跟它对应的 queue 里有数据，
        # 就把这个数据取出来再发回给这个客户端，否则就把这个连接从 output list 中移除，这样下一次循
        # 环 select() 调用时检测到 outputs list 中没有这个连接，那就会认为这个连接还处于非活动状态

        # Handle outputs
        for s in writable:
            try:
                next_msg = message_queues[s].get_nowait()
            except Queue.Empty:
                # No messages waiting so stop checking for writability.
                print('output queue for', s.getpeername(), 'is empty')
                outputs.remove(s)
            else:
                print('sending "%s" to %s' % (next_msg, s.getpeername()))
                s.send(next_msg)

        # 最后，如果在跟某个 socket 连接通信过程中出了错误，就把在 inputs\outputs\message_queue
        # 中的这个连接对象都删除，再把连接关闭掉

        # Handle "exceptional conditions"
        for s in exceptional:
            print('handling exceptional condition for', s.getpeername())
            # Stop listening for input on the connection
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()

            # Remove message queue
            del message_queues[s]
