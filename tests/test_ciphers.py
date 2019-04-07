# python -m twisted.trial tests.test_ciphers
import base64
import binascii

from twisted.trial import unittest

from config import  ConfigManager
from networktunnel.ciphers import AES128CFB, TableManager, ciphers

conf = ConfigManager().default


class SocksServerTestCase(unittest.TestCase):

    def test_aes128cfb(self):
        aes_manager = AES128CFB(conf.get('local', 'key'))
        salt = conf.get('local', 'pro_salt')

        iv = binascii.a2b_hex(base64.b64decode(salt.encode()))

        self.assertEqual(len(iv), aes_manager.IV_SIZE)
        self.assertTrue(isinstance(iv, bytes))

        message = b'\x05\x01\x80'

        iv, encrypt = aes_manager.make_encrypter(iv)
        self.assertTrue(callable(encrypt))

        secret_message = encrypt(message)

        print(secret_message)
        print(len(secret_message))

        decrypt = aes_manager.make_decrypter(iv)
        self.assertTrue(callable(decrypt))

        self.assertEqual(decrypt(secret_message), message)

        decrypt = aes_manager.make_decrypter(iv)  # 每次都要 make_decrypter
        print(decrypt(b'\xe5e'))

    def test_table(self):
        local_table = TableManager()
        remote_table = TableManager()

        message = 'sda'

        iv, encrypt = local_table.make_encrypter('../keys/encrypt_password.pem')
        self.assertTrue(callable(encrypt))

        secret_message = encrypt(message.encode())

        decrypt = remote_table.make_decrypter('../keys/decrypt_password.pem')
        self.assertTrue(callable(decrypt))

        self.assertEqual(decrypt(secret_message).decode(), message)
