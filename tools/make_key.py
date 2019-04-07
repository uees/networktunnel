import os
import random
import configparser
import string
import base64
import binascii

from networktunnel.ciphers import AES128CFB, TableManager

from settings import BASE_DIR


def main():
    parser = configparser.ConfigParser()
    filepath = os.path.join(BASE_DIR, 'default.conf')
    parser.read(filepath)

    key = ''.join(random.sample(string.ascii_letters + string.digits, 16))
    parser.set("local", "key", key)
    parser.set("remote", "key", key)

    aes_manager = AES128CFB('sdsdjsk')
    salt = base64.b64encode(binascii.b2a_hex(aes_manager.random_iv()))
    parser.set("local", "pro_salt", salt.decode())
    parser.set("remote", "pro_salt", salt.decode())

    parser.set("local", "data_salt", "keys/encrypt_password.pem")
    parser.set("remote", "data_salt", "keys/decrypt_password.pem")

    with open(filepath, 'w') as fp:
        parser.write(fp)


if __name__ == "__main__":
    main()
