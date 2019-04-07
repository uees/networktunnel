import base64
import binascii
import struct

from networktunnel.ciphers import RSAManager, TableManager, ciphers
from networktunnel.helpers import udp_frame_header_length


class ShadowProtocol(object):

    def __init__(self, key, data_salt, data_cipher, pro_salt, pro_cipher):
        data_cip_cls = ciphers.get(data_cipher)
        pro_cip_cls = ciphers.get(pro_cipher)

        if data_cip_cls in (RSAManager, TableManager):
            self.data_salt = data_salt
        else:
            self.data_salt = binascii.a2b_hex(base64.b64decode(data_salt.encode()))

        self.data_cipher_manager = data_cip_cls(key)

        if pro_cip_cls in (RSAManager, TableManager):
            self.pro_salt = pro_salt
        else:
            self.pro_salt = binascii.a2b_hex(base64.b64decode(pro_salt.encode()))

        self.pro_cipher_manager = pro_cip_cls(key)

    def decrypt_data(self, message):
        _, encrypt = self.data_cipher_manager.make_encrypter(self.data_salt)
        return encrypt(message)

    def encrypt_data(self, ciphertext):
        decrypt = self.data_cipher_manager.make_decrypter(self.data_salt)
        return decrypt(ciphertext)

    def encrypt_protocol(self, message):
        _, encrypt = self.pro_cipher_manager.make_encrypter(self.pro_salt)
        return encrypt(message)

    def decrypt_protocol(self, ciphertext):
        decrypt = self.pro_cipher_manager.make_decrypter(self.pro_salt)
        return decrypt(ciphertext)

    def encrypt_protocol_data(self, message):
        message = message[1:]  # 去除第一位版本标识
        return self.encrypt_protocol(message)

    def decrypt_protocol_data(self, ciphertext):
        message = self.decrypt_protocol(ciphertext)
        return b''.join([b'\x05', message])  # 解密后加上第一位版本号

    def encrypt_udp_data(self, message):
        atyp = ord(message[3:4])
        header_length = udp_frame_header_length(atyp, message)

        # 去除头3位无用的数据后再加密
        secret_header_data = self.encrypt_protocol(message[3:header_length])
        secret_data = self.encrypt_data(message[4:])

        return b''.join([
            bytes([len(secret_header_data)]),
            secret_header_data,
            secret_data
        ])

    def decrypt_udp_data(self, ciphertext):
        secret_header_length = ord(ciphertext[0:1])
        header_data = self.decrypt_protocol(ciphertext[1:secret_header_length + 1])
        data = self.decrypt_data(ciphertext[secret_header_length + 1:])

        return b''.join([
            struct.pack('!HB', 0, 0),
            header_data,
            data
        ])
