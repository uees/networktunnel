import socket

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol


class Echo(DatagramProtocol):
    def datagramReceived(self, data, addr):
        print("received %r from %s" % (data, addr))
        self.transport.write(data, addr)


# Create new socket that will be passed to reactor later.
portSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 使端口非阻塞并开始监听。
portSocket.setblocking(False)
portSocket.bind(('127.0.0.1', 9999))

# 现在将端口文件描述符传递给反应器。
port = reactor.adoptDatagramPort(
    portSocket.fileno(), socket.AF_INET, Echo())

# portSocket应该由创建它的进程清理.
portSocket.close()

reactor.run()
