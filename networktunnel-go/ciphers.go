package networktunnel

import (
	"crypto/aes"
	"crypto/cipher"
)

// Cipher 加密器接口
type Cipher interface {
	Encrypt([]byte) ([]byte, error)
	Decrypt([]byte) ([]byte, error)
}

// AES 加密器
type AES struct {
	key, iv []byte
}

// Encrypt 加密
func (_aes *AES) Encrypt(plaintext []byte) (encrypted []byte, err error) {
	block, err := aes.NewCipher(_aes.key)
	if err != nil {
		return
	}

	// iv := _aes.key[:aes.BlockSize]
	encrypted = make([]byte, len(plaintext))
	stream := cipher.NewCFBEncrypter(block, _aes.iv)
	stream.XORKeyStream(encrypted, plaintext)
	return
}

// Decrypt 解密
func (_aes *AES) Decrypt(encrypted []byte) (decrypted []byte, err error) {
	block, err := aes.NewCipher(_aes.key)
	if err != nil {
		return
	}

	decrypted = make([]byte, len(encrypted))
	stream := cipher.NewCFBDecrypter(block, _aes.iv)
	stream.XORKeyStream(decrypted, encrypted)
	return
}

// NewAESCipher 创建一个AES加密器
func NewAESCipher(key []byte) *AES {
	_aes := new(AES)
	_aes.key = key[:16]
	_aes.iv = _aes.key[:aes.BlockSize]
	return _aes
}

// Table 加密器
type Table struct {
	// 编码用的密码
	encodePassword *password
	// 解码用的密码
	decodePassword *password
}

// Encrypt 加密原数据
func (table *Table) Encrypt(bs []byte) ([]byte, error) {
	for i, v := range bs {
		bs[i] = table.encodePassword[v]
	}
	return bs, nil
}

// Decrypt 解码加密后的数据到原数据
func (table *Table) Decrypt(bs []byte) ([]byte, error) {
	for i, v := range bs {
		bs[i] = table.decodePassword[v]
	}
	return bs, nil
}

// NewTableCipher 新建一个编码解码器
func NewTableCipher(encodePassword *password) *Table {
	decodePassword := &password{}
	for i, v := range encodePassword {
		encodePassword[i] = v
		decodePassword[v] = byte(i)
	}
	return &Table{
		encodePassword: encodePassword,
		decodePassword: decodePassword,
	}
}
