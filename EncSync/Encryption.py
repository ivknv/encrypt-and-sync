#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Crypto.Cipher import AES
from Crypto import Random

import os
import struct
import math
import base64
import binascii

from . import Paths

chunksize = 4096

# Minimum encrypted file size
MIN_ENC_SIZE = struct.calcsize("Q") + 16

DUMMY_IV = b"0" * 16

class EncryptionError(BaseException):
    pass

class DecryptionError(BaseException):
    pass

def pad_size(size):
    """
        Pad `size` to be a multiple of 16.

        :param size: `int`, size to be padded

        :returns: `int`
    """

    if size % 16 == 0:
        return size

    return size + 16 - (size % 16)

def encrypt_file(in_file, out_file, key, filesize=None, iv=None):
    """
        Encrypt a file with a given key.

        :param in_file: path to the input file (`str`) or a file-like object
        :param out_file: path to the output file (`str`) or a file-like object
        :param key: `bytes`, key to encrypt with
        :param filesize: `int`, size of the input file, can be given to avoid its computation
        :param iv: `bytes` or `None`, initialization vector (IV) to use, will be generated if `None`
    """

    ivlen = 16

    if iv is None:
        iv = Random.get_random_bytes(ivlen)

    try:
        encryptor = AES.new(key, AES.MODE_CBC, iv)
    except ValueError as e:
        raise EncryptionError(str(e))

    close_in, close_out = False, False

    if isinstance(in_file, (str, bytes)):
        filesize = os.path.getsize(in_file)
        in_file = open(in_file, "rb")
        close_in = True
    elif filesize is None:
        fpos = in_file.tell()
        in_file.seek(0, 2)
        filesize = in_file.tell()
        in_file.seek(fpos, 0)

    if isinstance(out_file, (str, bytes)):
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

def encrypt_data(in_data, key, iv=None):
    """
        Encrypts data with a given key.

        :param in_data: `bytes`, input data
        :param key: `bytes`, key to encrypt with
        :param iv: `bytes` or `None`, initialization vector (IV) to use, will be generated if `None`

        :returns: `bytes`
    """

    ivlen = 16

    if not isinstance(in_data, bytes):
        raise EncryptionError("Input data must be bytes")

    if iv is None:
        iv = Random.get_random_bytes(ivlen)

    try:
        encryptor = AES.new(key, AES.MODE_CBC, iv)
    except ValueError as e:
        raise EncryptionError(str(e))

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
    """
        Decrypt previously encrypted data.

        :param in_data: `bytes`, input data to be decrypted
        :param key: `bytes`, key to use

        :returns: `bytes`
    """

    ivlen = 16

    if not isinstance(in_data, bytes):
        raise DecryptionError("Input data must be bytes")

    llsize = struct.calcsize("Q")

    try:
        size = struct.unpack("<Q", in_data[:llsize])[0]
    except struct.error:
        raise DecryptionError("Invalid encrypted data")

    iv = in_data[llsize:llsize + ivlen]

    try:
        decryptor = AES.new(key, AES.MODE_CBC, iv)
    except ValueError as e:
        raise DecryptionError(str(e))

    out_data = b""

    offset = llsize + ivlen

    l = len(in_data) - offset

    for i in range(math.ceil(l / float(chunksize))):
        chunk = in_data[offset + i * chunksize:offset + (i + 1) * chunksize]

        out_data += decryptor.decrypt(chunk)

    return out_data[:size]

def decrypt_file(in_file, out_file, key):
    """
        Decrypt previously encrypted file.

        :param in_file: path to the input file (`str`) or file-like object to be decrypted
        :param out_file: path to the output file (`str`) or file-like object
        :param key: `bytes`, key to use
    """

    ivlen = 16

    close_in, close_out = False, False

    if isinstance(in_file, (str, bytes)):
        in_file = open(in_file, "rb")
        close_in = True

    if isinstance(out_file, (str, bytes)):
        out_file = open(out_file, "wb")
        close_out = True

    try:
        try:
            out_filesize = struct.unpack("<Q", in_file.read(struct.calcsize("Q")))[0]
        except struct.error:
            raise DecryptionError("Invalid encrypted data")

        iv = in_file.read(ivlen)

        try:
            decryptor = AES.new(key, AES.MODE_CBC, iv)
        except ValueError as e:
            raise DecryptionError(str(e))

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
    """
        Encrypt filename with a given key.

        :param filename: `str` or `bytes`, filename to encrypt
        :param key: `bytes`, key to encrypt with
        :param iv: `bytes` or `None`, initialization vector (IV) to use, will be generated if empty or `None`

        :returns: `tuple` of 2 elements: encrypted filename (`str`), IV that was used (`bytes`)
    """

    chunksize = 16
    ivlen = 16
    padding = b" "

    if isinstance(filename, str):
        filename = filename.encode("utf8")

    if not isinstance(filename, bytes):
        raise EncryptionError("Filename must be str or bytes")

    if filename in (b".", b".."):
        return filename.decode("utf8"), DUMMY_IV

    if not iv:
        iv = Random.get_random_bytes(ivlen)

    try:
        encryptor = AES.new(key, AES.MODE_CBC, iv)
    except ValueError as e:
        raise EncryptionError(str(e))

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

def get_filename_IV(encrypted_filename):
    """
        Extract initialization vector (IV) from an encrypted filename.

        :param encrypted_filename: `str`, encrypted filename to extract IV from

        :returns: `bytes`
    """

    s = struct.calcsize("B")
    return b64d(encrypted_filename)[s:s + 16]

def gen_IV():
    """
        Generate a new initialization vector (IV).

        :returns: `bytes`
    """

    return Random.get_random_bytes(16)

def decrypt_filename(encrypted, key):
    """
        Decrypt a previously encrypted filename.

        :param encrypted: `str`, previously encrypted filename
        :param key: `bytes`, key to use

        :returns: `tuple` of 2 elements: decrypted filename (`str` or `bytes` in case of UnicodeDecodeError)
                  and IV that was used (`bytes`)
    """

    chunksize = 16
    ivlen = 16

    if isinstance(encrypted, bytes):
        encrypted = encrypted.decode()

    if not isinstance(encrypted, str):
        raise DecryptionError("Filename must be str or bytes")

    if not encrypted:
        return "", b""

    if encrypted in (".", ".."):
        return encrypted, DUMMY_IV

    try:
        encrypted = b64d(encrypted)
    except binascii.Error:
        raise DecryptionError("Invalid encrypted filename")

    llsize = struct.calcsize("B")

    iv = encrypted[llsize:llsize + ivlen]

    try:
        encryptor = AES.new(key, AES.MODE_CBC, iv)
    except ValueError as e:
        raise DecryptionError(str(e))

    encrypted_len = len(encrypted) - llsize - ivlen

    try:
        length_diff = struct.unpack("<B", encrypted[:llsize])[0]
    except struct.error:
        raise DecryptionError("Invalid encrypted filename")

    if length_diff < 0 or length_diff > 15:
        raise DecryptionError("Invalid encrypted filename")

    filename_len = encrypted_len - length_diff

    decrypted = "".encode("utf8")

    for i in range(encrypted_len // 16):
        idx = llsize + ivlen + i * 16
        chunk = encrypted[idx:idx + 16]

        decrypted += encryptor.decrypt(chunk)

    try:
        return decrypted[:filename_len].decode("utf8"), iv
    except UnicodeDecodeError:
        return decrypted[:filename_len], iv


def encrypt_path(path, key, prefix=None, ivs=b"", sep="/"):
    """
        Encrypt path with a given key.

        :param path: path to be encrypted
        :param key: `bytes`, key to encrypt with
        :param prefix: path prefix to leave unencrypted
        :param ivs: `bytes`, initialization vectors (IVs) to encrypt with
        :param sep: path separator

        :returns: `str`
    """

    if not path:
        return path, b""

    prefix = prefix or sep

    orig_path = path
    path = Paths.cut_prefix(path, prefix, sep)

    func = lambda x, iv: encrypt_filename(x, key, iv) if x else ("", b"")
    out_ivs = b""
    path_names = []

    if ivs:
        for name, iv in zip(path.split(sep), (ivs[x:x + 16] for x in range(0, len(ivs), 16))):
            enc_name, iv = func(name, iv)
            path_names.append(enc_name)
            out_ivs += iv
    else:
        for name in path.split(sep):
            enc_name, iv = func(name, b"")
            path_names.append(enc_name)
            out_ivs += iv

    prefix = prefix or sep

    if orig_path.startswith(Paths.dir_normalize(prefix, sep)):
        return Paths.join(prefix, sep.join(path_names), sep), out_ivs

    return sep.join(path_names), out_ivs

def decrypt_path(path, key, prefix=None, sep="/"):
    """
        Decrypt an encrypted path.

        :param path: encrypted path to be decrypted
        :param key: `bytes`, key to decrypt with
        :param prefix: path prefix that was left unencrypted
        :param sep: path separator

        :returns: `str`
    """

    if prefix is not None:
        dec_path, ivs = decrypt_path(Paths.cut_prefix(path, prefix, sep), key, None, sep)

        if path.startswith(Paths.dir_normalize(prefix, sep)):
            return Paths.join(prefix, dec_path, sep), ivs

        return dec_path, ivs

    ivs = b""
    path_names = []

    for name in path.split(sep):
        dec_name, iv = decrypt_filename(name, key) if name else ("", b"")
        path_names.append(dec_name)
        ivs += iv

    return sep.join(path_names), ivs
