from cryptography.fernet import Fernet
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List devices')
    parser.add_argument('-k', dest='key', action='store', default='')
    parser.add_argument('-p', dest='password', action='store', default='')
    options = parser.parse_args()
    key = options.key
    password = options.password

    # key = Fernet.generate_key()
    # print('key: {}'.format(key))
    f = Fernet(key)
    print('f: {}'.format(f))
    token = f.encrypt(password)
    print('token: {}'.format(token))
    out = f.decrypt(token)
    print('out: {}'.format(out))
