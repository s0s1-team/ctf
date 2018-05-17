#!python3
from itertools import product
from Crypto.Cipher import AES
# import queue
from collections import deque
import threading
import time

import sys
if sys.version_info[0] == 2:
    PT = "704d656cbe4b258f1e3278978de51252".decode('hex')
    CT = "8d58af5eb39260928972cfc4e6496283".decode('hex')
else:
    PT = bytes.fromhex("704d656cbe4b258f1e3278978de51252")
    CT = bytes.fromhex("8d58af5eb39260928972cfc4e6496283")
# Q = queue.Queue()
DQ = deque()
DONE = False
FOUND = False

def checker():
    global DONE, DQ, PT, CT, FOUND
    while True:
        try:
            if len(DQ) == 0 and DONE and FOUND:
                break
            k = DQ.popleft()
            aes = AES.new(k, AES.MODE_ECB)
            if aes.encrypt(PT) == CT:
                print("!!! Found:", k.hex())
                FOUND = True
        except IndexError:
            pass

def bar():
    global DQ, DONE

    # keys = [
    #     [b'\x71', b'\xf1'], # 1 +
    #     [b'\xa0', b'\x20'], # 2 +
    #     [b'\xb2', b'\xf2'], # 3 ?
    #     [b'\x5f'], # 4 ?
    #     [b'\x98', b'\x18'], # 5 ? d8
    #     [b'\xdb', b'\xda', b'\xd9'], # 6 ?
    #     [b'\x4c', b'\x44'], # 7 CC ?
    #     [b'\xf2'], # 8 F6 D2 ?
    #     [b'\x98', b'\x99'], # 9 ?
    #     [b'\x48'], # A 40 +
    #     [b'\x05', b'\x01'], # B +
    #     [b'\x2a'], # C 28 22 +
    #     [b'\xbd'], # D b9 3d ? 35
    #     [b'\xd8', b'\xd9'], # E ?
    #     [b'\x18', b'\x08'], # F ?
    # ]
    
    keys = [
        [b'\x71', b'\xf1'],
        [b'\xa0', b'\x20'],
        [b'\xb2', b'\xf2'],
        [b'\x5f'],
        [b'\x98', b'\xd8'],
        [b'\xdb', b'\xda', b'\xd9'],
        [b'\x4c', b'\x44'],
        [b'\xf2'],
        [b'\x98', b'\x99'],
        [b'\x48'],
        [b'\x05', b'\x01'],
        [b'\x2a'],
        [b'\xbd', b'\x35'],
        [b'\xd8', b'\xd9'],
        [b'\x18', b'\x08'],
    ]

    num_worker_threads = 8
    for i in range(num_worker_threads):
        t = threading.Thread(target=checker)
        t.daemon = True
        t.start()

    print("started")

    count = 0
    for kp in product(*keys):
        kp = list(b"".join(kp))
        for i in range(256):
            k = [i] + kp
            for j in range(1, 16):
                k[j] = k[j - 1] ^ k[j]
            kb = bytes(k)
            DQ.append(kb)
            count += 1
            if count % 100000 == 0:
                print(count, len(DQ))
                while len(DQ) > 1000000:
                    time.sleep(0.1)

    print("generated:", count)
    while len(DQ) != 0:
        time.sleep(1)
    DONE = True
    print("done")

bar()
# 718020d28d558ec230a9e1e4ce73aab2