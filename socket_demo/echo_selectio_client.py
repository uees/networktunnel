#!/usr/bin/env python3

import socket

messages = [
    b'This is the message. ',
    b'It will be sent ',
    b'in parts.',
]

server_address = ('127.0.0.1', 10000)

# Create a TCP/IP socket
socks = [
    socket.socket(socket.AF_INET, socket.SOCK_STREAM),
    socket.socket(socket.AF_INET, socket.SOCK_STREAM),
]

# Connect the socket to the port where the server is listening
print('connecting to %s port %s' % server_address)

for s in socks:
    s.connect(server_address)

    for message in messages:

        # Send messages on both sockets
        print('%s: sending "%s"' % (s.getsockname(), message))
        s.send(message)

        # Read responses on both sockets
        data = s.recv(1024)
        print('%s: received "%s"' % (s.getsockname(), data))
        if not data:
            print('closing socket', s.getsockname())
            s.close()
