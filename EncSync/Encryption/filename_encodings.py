# -*- cofing: utf-8 -*-

import base64
import binascii
import math

__all__ = ["base64_encode", "base64_decode", "base41_encode", "base41_decode",
           "base32_encode", "base32_decode"]

BASE41_CHARSET = b"+,-.0123456789_abcdefghijklmnopqrstuvwxyz"
BASE41_PADDING = b"="

def _chunk(b, size):
    for i in range(math.ceil(len(b) / size)):
        yield b[size * i:size * (i + 1)]

def _count_leading_zeroes(digits, zero=0):
    n = 0

    for d in digits:
        if d == zero:
            n += 1
        else:
            break

    return n

def _convert_decimal(d, base):
    if d == 0:
        return [0]

    output = []

    while d > 0:
        rem = d % base
        d //= base
        output.append(rem)

    return output

def _convert_to_decimal(digits, base):
    result = power = 0

    for digit in digits[::-1]:
        result += digit * base ** power
        power += 1

    return result

def _bytes_to_decimal(b):
    result = power = 0

    for i in b[::-1]:
        result += i * 256 ** power
        power += 1

    return result

def _encode_bytes(b, m, n, charset, padding):
    base = len(charset)
    output = b""

    for chunk in _chunk(b, m):
        leading_zeroes = _count_leading_zeroes(chunk)
        chunk = chunk[leading_zeroes:]
        encoded = charset[0:1] * leading_zeroes

        if chunk:
            decimal = _bytes_to_decimal(chunk)
            digits = _convert_decimal(decimal, base)[::-1]
            encoded += b"".join(charset[i:i + 1] for i in digits)

        encoded += (n - len(encoded)) * padding
        output += encoded

    return output

def _decode_bytes(b, m, n, charset, padding):
    base = len(charset)
    output = b""
    max_decimal = 0

    for i in range(m):
        max_decimal += 255 * 256 ** i

    for chunk in _chunk(b, n):
        if len(chunk) != n:
            raise ValueError("Invalid padding")

        chunk = chunk.rstrip(padding)
        leading_zeroes = _count_leading_zeroes(chunk, charset[0])
        chunk = chunk[leading_zeroes:]

        encoded = b"\0" * leading_zeroes

        if not chunk:
            if len(encoded) > m:
                encoded = encoded[len(encoded) - m:]

            output += encoded
            continue

        digits = [charset.index(i) for i in chunk]
        decimal = _convert_to_decimal(digits, base)

        if decimal > max_decimal:
            raise ValueError("Encoding range exceeded")

        encoded += bytes(_convert_decimal(decimal, 256)[::-1])

        if len(encoded) > m:
            encoded = encoded[len(encoded) - m:]

        output += encoded
        
    return output

def base64_encode(b):
    try:
        return base64.urlsafe_b64encode(b)
    except binascii.Error as e:
        raise ValueError("binascii.Error: %s" % (e,))

def base64_decode(b):
    try:
        return base64.urlsafe_b64decode(b)
    except binascii.Error as e:
        raise ValueError("binascii.Error: %s" % (e,))

def base41_encode(b):
    return _encode_bytes(b, 2, 3, BASE41_CHARSET, BASE41_PADDING)

def base41_decode(b):
    return _decode_bytes(b, 2, 3, BASE41_CHARSET, BASE41_PADDING)

def base32_encode(b):
    try:
        return base64.b32encode(b)
    except binascii.Error as e:
        raise ValueError("binascii.Error: %s" % (e,))

def base32_decode(b):
    try:
        return base64.b32decode(b)
    except binascii.Error as e:
        raise ValueError("binascii.Error: %s" % (e,))
