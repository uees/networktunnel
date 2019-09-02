package networktunnel

import "networktunnel/socks"

// RemoteSocksServer 远程服务器
type RemoteSocksServer struct {
	state                byte
	peerAddress, address socks.Addr
	tcpClient            *remoteTCPClient
	udpClient            *remoteUDPClient
	udpPort              uint
	socksCipher
}

// SetState 设置状态
func (s *RemoteSocksServer) SetState(sate byte) {
	s.state = sate
}

// 启动服务器

// 处理握手信息

// 处理数据交换

type remoteTCPClient struct{}

type remoteUDPClient struct{}
