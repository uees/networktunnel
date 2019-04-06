# python -m tools.make_key

import os

from Crypto import Random
from Crypto.PublicKey import RSA

from settings import BASE_DIR

key_dir = os.path.join(BASE_DIR, 'keys')


# 伪随机数生成器
random_generator = Random.new().read

# rsa算法生成实例
rsa = RSA.generate(1024, random_generator)

# master的秘钥对的生成
private_pem = rsa.exportKey()

# 生成公私钥对文件
with open(os.path.join(key_dir, 'private.pem'), 'wb') as f:
    f.write(private_pem)

public_pem = rsa.publickey().exportKey()
with open(os.path.join(key_dir, 'public.pem'), 'wb') as f:
    f.write(public_pem)
