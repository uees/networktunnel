import json
import os
import random

from tools.make_rsakey import key_dir


def choice(dataset: list, bad: int):
    """
    从 dataset 列表中随机选择一个数，但不能是 bad
    :param dataset:
    :param bad:
    :return:
    """
    if bad in dataset:
        tmp = dataset.copy()
        tmp.remove(bad)
    else:
        tmp = dataset

    return random.choice(tmp)


def make_password():
    """
    将0~255的整数随机排序, 并且每一位的数字不能等于索引
    :return:
    """
    dataset = list(range(0, 256))  # 0~255的整数列表
    encrypt_password = [0 for i in range(0, 256)]  # 初始化256长度的加密列表
    decrypt_password = [0 for i in range(0, 256)]  # 初始化256长度的解密列表

    for index in range(0, 256):
        value = choice(dataset, index)
        dataset.remove(value)
        encrypt_password[index] = value
        decrypt_password[value] = index

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
