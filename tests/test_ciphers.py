# python -m twisted.trial tests.test_ciphers
from twisted.trial import unittest

from networktunnel.ciphers import AES128CFB, TableManager


class SocksServerTestCase(unittest.TestCase):

    def test_aes128cfb(self):
        aes_manager = AES128CFB('sdsdjsk')
        iv = aes_manager.random_iv()

        self.assertEqual(len(iv), aes_manager.IV_SIZE)
        self.assertTrue(isinstance(iv, bytes))

        message = 'sda'

        iv, encrypt = aes_manager.make_encrypter(iv)
        self.assertTrue(callable(encrypt))

        secret_message = encrypt(message.encode())

        print(secret_message)
        print(len(secret_message))

        decrypt = aes_manager.make_decrypter(iv)
        self.assertTrue(callable(decrypt))

        self.assertEqual(decrypt(secret_message).decode(), message)

    def test_table(self):
        local_table = TableManager()
        remote_table = TableManager()

        message = 'sda'

        iv, encrypt = local_table.make_encrypter('../keys/encrypt_password.pem')
        self.assertTrue(callable(encrypt))

        secret_message = encrypt(message.encode())

        print(secret_message)
        print(len(secret_message))

        decrypt = remote_table.make_decrypter('../keys/decrypt_password.pem')
        self.assertTrue(callable(decrypt))

        self.assertEqual(decrypt(secret_message).decode(), message)
