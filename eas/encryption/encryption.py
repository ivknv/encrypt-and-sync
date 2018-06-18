#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from Crypto.Cipher import AES
    from Crypto import Random
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome import Random

import os
import struct
import math

from .exceptions import *
from .filename_encodings import *
from .. import pathm

__all__ = ["MIN_ENC_SIZE", "pad_size", "encrypt_file", "decrypt_file",
           "encrypt_file_inplace", "decrypt_file_inplace",
           "encrypt_data", "decrypt_data", "encrypt_filename",
           "decrypt_filename", "get_filename_IV", "gen_IV",
           "encrypt_path", "decrypt_path"]

chunksize = 4096

# Minimum encrypted file size (header size)
MIN_ENC_SIZE = struct.calcsize("Q") + 16

DUMMY_IV = b"0" * 16

ENCODE_FUNCTIONS = {"base64": base64_encode,
                    "base41": base41_encode,
                    "base32": base32_encode}
DECODE_FUNCTIONS = {"base64": base64_decode,
                    "base41": base41_decode,
                    "base32": base32_decode}

def get_encode_function(name_or_func):
    if isinstance(name_or_func, str):
        try:
            return ENCODE_FUNCTIONS[name_or_func]
        except KeyError:
            raise UnknownFilenameEncodingError("Unknown filename encoding: %r" % (name_or_func,))

    return name_or_func

def get_decode_function(name_or_func):
    if isinstance(name_or_func, str):
        try:
            return DECODE_FUNCTIONS[name_or_func]
        except KeyError:
            raise UnknownFilenameEncodingError("Unknown filename encoding: %r" % (name_or_func,))

    return name_or_func

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

        :param in_file: path to the input file (`str` or `bytes`) or a file-like object
        :param out_file: path to the output file (`str` or `bytes`) or a file-like object
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

def encrypt_file_inplace(in_file, key, filesize=None, iv=None):
    """
        Encrypt a file with a given key inplace.

        :param in_file: path to the input file (`str` or `bytes`) or a file-like object
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

    close_in = False

    padding = b" "

    try:
        if isinstance(in_file, (str, bytes)):
            filesize = os.path.getsize(in_file)
            in_file = open(in_file, "rb+")
            close_in = True
        elif filesize is None:
            fpos = in_file.tell()
            in_file.seek(0, 2)
            filesize = in_file.tell()
            in_file.seek(fpos, 0)

        chunk = in_file.read(chunksize + MIN_ENC_SIZE)
        chunk, tail = chunk[:chunksize], chunk[chunksize:]

        chunklen = len(chunk)
        rem = chunklen % 16

        in_file.seek(0)
        in_file.write(struct.pack("<Q", filesize))
        in_file.write(iv)

        if not chunk:
            return

        if rem:
            chunk += padding * (16 - rem)

        in_file.write(encryptor.encrypt(chunk))

        while True:
            chunk = in_file.read(chunksize)
            seek_offset = len(chunk)
            chunk, tail = tail + chunk[:chunksize - len(tail)], chunk[chunksize - len(tail):]

            if not chunk:
                break

            chunklen = len(chunk)
            rem = chunklen % 16

            if rem:
                chunk += padding * (16 - rem)

            in_file.seek(-seek_offset, 1)
            in_file.write(encryptor.encrypt(chunk))
    finally:
        if close_in and not isinstance(in_file, (str, bytes)):
            in_file.close()

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
        Decrypt a previously encrypted file.

        :param in_file: path to the input file (`str` or `bytes`) or file-like object to be decrypted
        :param out_file: path to the output file (`str` or `bytes`) or file-like object
        :param key: `bytes`, key to use
    """

    ivlen = 16

    close_in, close_out = False, False

    if isinstance(in_file, (str, bytes)):
        close_in = True
        in_file = open(in_file, "rb")

    if isinstance(out_file, (str, bytes)):
        close_out = True
        out_file = open(out_file, "wb")

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
            if close_in and not isinstance(in_file, (str, bytes)):
                in_file.close()
        finally:
            if close_out and not isinstance(out_file, (str, bytes)):
                out_file.close()

def decrypt_file_inplace(in_file, key):
    """
        Decrypt a previously encrypted file inplace.

        :param in_file: path to the file (`str` or `bytes`) or file-like object to be decrypted
        :param key: `bytes`, key to use
    """

    ivlen = 16

    close_in = False

    try:
        if isinstance(in_file, (str, bytes)):
            close_in = True
            in_file = open(in_file, "rb+")

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

            if not chunk:
                break

            in_file.seek(-(len(chunk) + MIN_ENC_SIZE), 1)
            in_file.write(decryptor.decrypt(chunk))
            in_file.seek(MIN_ENC_SIZE, 1)

        in_file.truncate(out_filesize)
    finally:
        if close_in and not isinstance(in_file, (bytes, str)):
            in_file.close()

def encrypt_filename(filename, key, iv=b"", filename_encoding="base64"):
    """
        Encrypt filename with a given key.

        :param filename: `str` or `bytes`, filename to encrypt
        :param key: `bytes`, key to encrypt with
        :param iv: `bytes` or `None`, initialization vector (IV) to use, will be generated if empty or `None`
        :param filename_encoding: name of the filename encoding (`str`) or a function

        :returns: `tuple` of 2 elements: encrypted filename (`str` or `bytes`), IV that was used (`bytes`)
    """

    encode = get_encode_function(filename_encoding)

    chunksize = 16
    ivlen = 16
    padding = b" "

    preferred_type = type(filename)

    if isinstance(filename, str):
        filename = filename.encode("utf8")

    if not isinstance(filename, bytes):
        raise EncryptionError("Filename must be str or bytes")

    if filename in (b".", b".."):
        if issubclass(preferred_type, bytes):
            return filename, DUMMY_IV

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

    encrypted = encode(encrypted)

    try:
        if issubclass(preferred_type, str):
            return encrypted.decode("utf8"), iv
    except UnicodeEncodeError:
        pass

    return encrypted, iv

def get_filename_IV(encrypted_filename, filename_encoding="base64"):
    """
        Extract initialization vector (IV) from an encrypted filename.

        :param encrypted_filename: `str` or `bytes`, encrypted filename to extract IV from
        :param filename_encoding: name of the filename encoding (`str`) or a function

        :returns: `bytes`
    """

    decode = get_decode_function(filename_encoding)

    if isinstance(encrypted_filename, str):
        encrypted_filename = encrypted_filename.encode("utf8")

    s = struct.calcsize("B")
    return decode(encrypted_filename)[s:s + 16]

def gen_IV():
    """
        Generate a new initialization vector (IV).

        :returns: `bytes`
    """

    return Random.get_random_bytes(16)

def decrypt_filename(encrypted, key, filename_encoding="base64"):
    """
        Decrypt a previously encrypted filename.

        :param encrypted: `str`, previously encrypted filename
        :param key: `bytes`, key to use
        :param filename_encoding: name of the filename encoding (`str`) or a function

        :returns: `tuple` of 2 elements: decrypted filename (`str` or `bytes`)
                  and IV that was used (`bytes`)
    """

    decode = get_decode_function(filename_encoding)

    chunksize = 16
    ivlen = 16

    preferred_type = type(encrypted)

    if isinstance(encrypted, str):
        encrypted = encrypted.encode("utf8")

    if not isinstance(encrypted, bytes):
        raise DecryptionError("Filename must be str or bytes")

    if not encrypted:
        return preferred_type(), b""

    if encrypted in (b".", b".."):
        if issubclass(preferred_type, str):
            encrypted = encrypted.decode("utf8")

        return encrypted, DUMMY_IV

    try:
        encrypted = decode(encrypted)
    except ValueError:
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

    decrypted = b""

    for i in range(encrypted_len // 16):
        idx = llsize + ivlen + i * 16
        chunk = encrypted[idx:idx + 16]

        decrypted += encryptor.decrypt(chunk)

    decrypted = decrypted[:filename_len]

    try:
        if issubclass(preferred_type, str):
            return decrypted.decode("utf8"), iv
    except UnicodeDecodeError:
        pass

    return decrypted, iv

def encrypt_path(path, key, prefix=None, ivs=b"", sep=None, filename_encoding="base64"):
    """
        Encrypt path with a given key.

        :param path: path to be encrypted
        :param key: `bytes`, key to encrypt with
        :param prefix: path prefix to leave unencrypted
        :param ivs: `bytes`, initialization vectors (IVs) to encrypt with
        :param sep: path separator
        :param filename_encoding: name of the filename encoding (`str`) or a function

        :returns: `tuple` of 2 elements: encrypted path (`str` or `bytes`) and IVs (`bytes`)
    """

    preferred_type = pathm.get_preferred_type([path, prefix, sep])

    if sep is None:
        sep = pathm.get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    encode = get_encode_function(filename_encoding)

    frags = path.split(sep)

    cur_path = preferred_type()
    result = []
    out_ivs = b""

    prefix = pathm.dir_normalize(prefix, sep=sep)

    iv_idx = 0

    if issubclass(preferred_type, str):
        cdir, pdir = ".", ".."
    else:
        cdir, pdir = b".", b".."

    nothing = preferred_type()

    for frag in frags:
        cur_path = pathm._join_filename_properly(cur_path, frag, sep, preferred_type)

        if cur_path.startswith(prefix) and frag not in (cdir, pdir, nothing):
            try:
                frag_iv = ivs[iv_idx:iv_idx + 16]
            except IndexError:
                frag_iv = b""

            frag, frag_ivs = encrypt_filename(frag, key, frag_iv, encode)
            out_ivs += frag_ivs
            iv_idx += 16

        result.append(frag)

    return sep.join(result), out_ivs

def decrypt_path(path, key, prefix=None, sep=None, filename_encoding="base64"):
    """
        Decrypt an encrypted path.

        :param path: encrypted path to be decrypted
        :param key: `bytes`, key to decrypt with
        :param prefix: path prefix that was left unencrypted
        :param sep: path separator
        :param filename_encoding: name of the filename encoding (`str`) or a function

        :returns: `tuple` of 2 elements: decrypted path (`str` or `bytes`) and IVs (`bytes`)
    """

    preferred_type = pathm.get_preferred_type([path, prefix, sep])

    if sep is None:
        sep = pathm.get_default_sep(preferred_type)

    if path is None:
        path = preferred_type()

    decode = get_decode_function(filename_encoding)

    frags = path.split(sep)

    cur_path = preferred_type()
    result = []
    ivs = b""

    prefix = pathm.dir_normalize(prefix, sep=sep)

    for frag in frags:
        cur_path = pathm._join_filename_properly(cur_path, frag, sep, preferred_type)

        if cur_path.startswith(prefix):
            frag, frag_iv = decrypt_filename(frag, key, decode)
            ivs += frag_iv

        result.append(frag)

    return sep.join(result), ivs
