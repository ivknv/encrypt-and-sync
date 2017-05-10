#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Crypto.Cipher import AES
from Crypto import Random
import os
import struct
import math
import base64

chunksize = 4096

# Minimum encrypted file size
MIN_ENC_SIZE = struct.calcsize("Q") + 16
DUMMY_IV = b"0" * 16

def pad_size(size):
    if size % 16 == 0:
        return size

    return size + 16 - (size % 16)

def encrypt_file(in_file, out_file, key, filesize=None):
    ivlen = 16
    iv = Random.get_random_bytes(ivlen)
    encryptor = AES.new(key, AES.MODE_CBC, iv)

    close_in, close_out = False, False

    if isinstance(in_file, str):
        filesize = os.path.getsize(in_file)
        in_file = open(in_file, "rb")
        close_in = True
    elif filesize is None:
        fpos = in_file.tell()
        in_file.seek(0, 2)
        filesize = in_file.tell()
        in_file.seek(fpos, 0)

    if isinstance(out_file, str):
        out_file = open(out_file, "wb")
        close_out = True

    padding = b" "

    try:
        out_file.write(struct.pack("<Q", filesize))
        out_file.write(iv)

        while True:
            chunk = in_file.read(chunksize)
            chunklen = len(chunk)
            rem = chunklen % 16

            if chunklen == 0:
                break
            elif rem != 0:
                chunk += padding * (16 - rem)

            out_file.write(encryptor.encrypt(chunk))
    finally:
        try:
            if close_in:
                in_file.close()
        finally:
            if close_out:
                out_file.close()

def encrypt_data(in_data, key):
    ivlen = 16
    iv = Random.get_random_bytes(ivlen)
    encryptor = AES.new(key, AES.MODE_CBC, iv)

    out_data = b""

    size = len(in_data)
    padding = b" "

    out_data += struct.pack('<Q', size)
    out_data += iv

    l = len(in_data)

    for i in range(math.ceil(float(l) / chunksize)):
        chunk = in_data[i * chunksize:(i + 1) * chunksize]
        chunklen = len(chunk)
        rem = chunklen % 16

        if rem != 0:
            chunk += padding * (16 - rem)

        out_data += encryptor.encrypt(chunk)

    return out_data

def decrypt_data(in_data, key):
    ivlen = 16

    llsize = struct.calcsize("Q")

    size = struct.unpack("<Q", in_data[:llsize])[0]
    iv = in_data[llsize:llsize + ivlen]

    decryptor = AES.new(key, AES.MODE_CBC, iv)

    out_data = b""

    offset = llsize + ivlen

    l = len(in_data) - offset

    for i in range(math.ceil(l / float(chunksize))):
        chunk = in_data[offset + i * chunksize:offset + (i + 1) * chunksize]

        out_data += decryptor.decrypt(chunk)

    return out_data[:size]

def decrypt_file(in_file, out_file, key):
    ivlen = 16

    close_in, close_out = False, False

    if isinstance(in_file, str):
        in_file = open(in_file, "rb")
        close_in = True

    if isinstance(out_file, str):
        out_file = open(out_file, "wb")
        close_out = True

    try:
        out_filesize = struct.unpack("<Q", in_file.read(struct.calcsize("Q")))[0]
        iv = in_file.read(ivlen)

        decryptor = AES.new(key, AES.MODE_CBC, iv)

        while True:
            chunk = in_file.read(chunksize)
            if len(chunk) == 0:
                break

            out_file.write(decryptor.decrypt(chunk))
        out_file.truncate(out_filesize)
    finally:
        try:
            if close_in:
                in_file.close()
        finally:
            if close_out:
                out_file.close()

def b64e(b):
    return base64.urlsafe_b64encode(b).decode()

def b64d(s):
    return base64.urlsafe_b64decode(bytearray([ord(c) for c in s]))

def encrypt_filename(filename, key, iv=b""):
    chunksize = 16
    ivlen = 16
    padding = b" "

    if len(iv) == 0:
        iv = Random.get_random_bytes(ivlen)

    if filename in (".", ".."):
        return filename, DUMMY_IV

    filename = filename.encode("utf8")

    encryptor = AES.new(key, AES.MODE_CBC, iv)

    filename_len = len(filename)

    chunknum = math.ceil(filename_len / float(chunksize))

    encrypted = bytearray()
    len_diff = 16 - (filename_len % 16)
    if len_diff == 16:
        len_diff = 0

    encrypted.extend(struct.pack('<B', len_diff))
    encrypted.extend(iv)

    for i in range(chunknum):
        idx = i * 16
        chunk = filename[idx:idx + 16]
        chunklen = len(chunk)
        rem = chunklen % 16
 
        if len(chunk) == 0:
            break
        elif rem != 0:
            chunk += padding * (16 - rem)

        encrypted.extend(encryptor.encrypt(chunk))

    return b64e(encrypted), iv

def get_filename_IV(encrypted):
    s = struct.calcsize("B")
    return b64d(encrypted)[s:s + 16]

def gen_IV():
    return Random.get_random_bytes(16)

def decrypt_filename(encrypted, key):
    chunksize = 16
    ivlen = 16

    if encrypted in (".", ".."):
        return encrypted, DUMMY_IV

    encrypted = b64d(encrypted)

    llsize = struct.calcsize("B")

    iv = encrypted[llsize:llsize + ivlen]

    encryptor = AES.new(key, AES.MODE_CBC, iv)

    encrypted_len = len(encrypted) - llsize - ivlen

    filename_len = encrypted_len - struct.unpack("<B", encrypted[:llsize])[0]
    decrypted = "".encode("utf8")

    for i in range(encrypted_len // 16):
        idx = llsize + ivlen + i * 16
        chunk = encrypted[idx:idx + 16]

        decrypted += encryptor.decrypt(chunk)

    return decrypted[:filename_len].decode("utf8"), iv
