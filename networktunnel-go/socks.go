package networktunnel

type socksCipher struct {
	proCipher, cipher *Cipher
}

func (s *socksCipher) SetProCipher(cipher *Cipher) {
	s.proCipher = cipher
}

func (s *socksCipher) SetCipher(cipher *Cipher) {
	s.cipher = cipher
}
