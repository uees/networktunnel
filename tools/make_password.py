import json
import os
import random

from tools.make_key import key_dir


def choice(dataset: list, index: int):
    val = random.choice(dataset)
    if val == index:
        val = choice(dataset, index)

    return val


def make_password():
    dataset = list(range(0, 256))
    encrypt_password = {}
    decrypt_password = {}

    for i in range(0, 256):
        value = choice(dataset, i)
        dataset.remove(value)
        encrypt_password[i] = value
        decrypt_password[value] = i

    return {
        'encrypt': encrypt_password,
        'decrypt': decrypt_password
    }


def save_password(password):
    with open(os.path.join(key_dir, 'encrypt_password.pem'), 'w') as fp:
        json.dump(password['encrypt'], fp)

    with open(os.path.join(key_dir, 'decrypt_password.pem'), 'w') as fp:
        json.dump(password['decrypt'], fp)


if __name__ == "__main__":
    pwd = make_password()
    save_password(pwd)
