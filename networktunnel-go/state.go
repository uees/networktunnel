package networktunnel

// socks client 状态
const (
	clientCreated                          = byte(1)    // 创建
	clientConnected                        = iota       // 连接
	clientSentInitialHandshake                          // 发送握手信息
	clientReceivedInitialHandshakeResponse              // 接收到握手信息的响应
	clientSentAuthentication                            // 发送认证信息
	clientReceivedAuthenticationResponse                // 认证结果的响应
	clientWaitingCommand                                // 等待命令
	clientSentCommand                                   // 发送命令
	clientReceivedCommandResponse                       // 收到对命令的响应
	clientWaitingConnection                             // 等待连接
	clientEstablished                                   // 连接确认
	clientDisconnected                                  // 断开了连接
	clientError                            = byte(0xff) // 错误
)

// SOCKS server 状态
const (
	serverCreated         = byte(1) // 创建
	serverConnected       = iota    // 连接
	serverReceivedMethods           // 收到协商认证请求
	serverSentMethod                // 确认了认证方法
	serverReceivedAuth              // 接收到认证请求
	serverSentAuthResult            // 完成认证
	serverReceivedCommand           // 收到了命令
	serverWaitingConnection
	serverEstablished               // 连接确认
	serverDisconnected              // 断开了连接
	serverError        = byte(0xff) // 错误
)
