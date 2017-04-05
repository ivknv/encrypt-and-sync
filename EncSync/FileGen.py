#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import os

words = ["word", "test", "what", "thing", "stuff", "some", "something", "synctest"]
separators = ["_", "-", "--", "__"]
content_separators = separators + [" ", "\n"]

def coinflip():
    return random.randint(0, 1)

def genfilename():
    nwords = random.randint(1, 6)
    s = ""
    
    for i in range(nwords - 1):
         if random.randint(0, 2) == 1:
             s += random.choice(words)
         else:
             s += str(random.randint(0, 10000))
         s += random.choice(separators)

    if coinflip() == 1:
         s += random.choice(words)
    else:
         s += str(random.randint(0, 10000))

    s += ".test"

    return s

def genfilecontent():
    nwords = random.randint(0, 30010)
    
    for i in range(nwords - 1):
        s = ""

        if coinflip() == 1:
             s += random.choice(words)
        else:
             s += str(random.randint(0, 10000))
        s += random.choice(content_separators)

        yield s

    if coinflip() == 1:
        yield random.choice(words)
    else:
        yield str(random.randint(0, 10000))


def genfile(path):
    path = os.path.abspath(path)
    newpath = os.path.join(path, "FILE_" + genfilename())

    while os.path.exists(newpath):
        newpath = os.path.join(path, "FILE_" + genfilename())

    with open(newpath, 'w') as f:
        for chunk in genfilecontent():
            f.write(chunk)
    
    return newpath

def gendir(path):
    newpath = os.path.join(path, "DIR_" + genfilename())

    while os.path.exists(newpath):
        newpath = os.path.join(path, "DIR_" + genfilename())

    os.mkdir(newpath)

    return newpath

def genfiles(path, num, total_num):
    num = min(num, total_num)
    total_num -= num

    num_files = random.randint(0, num)
    num_dirs = num - num_files

    for i in range(num_files):
        genfile(path)

    for i in range(num_dirs):
        newpath = gendir(path)
        num_nested = random.randint(0, total_num)
        if num_nested:
            genfiles(newpath, num_nested, total_num)
            total_num -= num_nested
