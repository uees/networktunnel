# python -m twisted.trial tests.test_ciphers
import os
import base64
import binascii

from twisted.trial import unittest

from config import ConfigManager
from settings import BASE_DIR
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

        decrypt = aes_manager.make_decrypter(iv)
        self.assertTrue(callable(decrypt))

        self.assertEqual(decrypt(secret_message), message)

    def test_table(self):
        local_table = TableManager()
        remote_table = TableManager()

        message = 'sda'

        iv, encrypt = local_table.make_encrypter(os.path.join(BASE_DIR, 'keys/encrypt_password.pem'))
        self.assertTrue(callable(encrypt))

        secret_message = encrypt(message.encode())

        decrypt = remote_table.make_decrypter(os.path.join(BASE_DIR, 'keys/decrypt_password.pem'))
        self.assertTrue(callable(decrypt))

        self.assertEqual(decrypt(secret_message).decode(), message)
