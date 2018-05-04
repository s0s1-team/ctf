#!python2

from __future__ import print_function

import Adafruit_BBIO.GPIO as GPIO
import signal
import serial
import time
import sys
from itertools import izip_longest

RATE = 1500
WINDOW_SIZE = 512
STOP = False

# BIT_SELF_DESTRUCT1 = 1 << 51
# BIT_SELF_DESTRUCT2 = 1 << 61
# BIT_LED  = 1 << 7
# BIT_X = 1 << 155
# BIT_RESP = 1 << 156
# BIT_CHAL = 1 << 157

BIT_SELF_DESTRUCT1 = 460 # 461
BIT_SELF_DESTRUCT2 = 450
BIT_LED  = 504
BIT_RESP = 355
BIT_CHAL = 354

BIT_SELF_DESTRUCT1_MSB = 459
BIT_SELF_DESTRUCT2_MSB = 453
BIT_RESP_MSB = 356
BIT_CHAL_MSB = 357
BIT_LED_MSB = 511

# https://beagleboard.org/Support/bone101/
"""
# UART TX (GPIO_15) / RX (GPIO_14)
config-pin P9.24 uart
config-pin P9.26 uart
# GPIO
config-pin P8.07 gpio
config-pin P8.08 gpio
config-pin P8.09 gpio
config-pin P8.10 gpio
"""
TDI = "P8_7"  # GPIO_66 / A4
TDO = "P8_8"  # GPIO_67 / A5
TCK = "P8_9"  # GPIO_69 / A2
TMS = "P8_10" # GPIO_68 / A3

GPIO.setup(TDI, GPIO.OUT)
GPIO.setup(TDO, GPIO.IN)
GPIO.setup(TCK, GPIO.OUT)
GPIO.setup(TMS, GPIO.OUT)

PASSWORD_FILE = 'passwords'

def cleanup(signal, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGINT, cleanup)

def toggle_bits(data, *args):
    if isinstance(data, str):
        data = list(map(ord, data))
    for bit in args:
        pos, off = bit // 8, bit % 8
        # print("%d p: %d, o: %d" % (bit, pos, off))
        # data[pos] |= (1 << (7 -off))
        data[pos] ^= (1 << off)
    return "".join(map(chr, data))

def create_data(nbits, base=0, *args):
    data = [base] * (nbits // 8)
    return toggle_bits(data, *args)

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def bytes2bits(abytes, msb=False):
    res = []
    for b in abytes:
        res_byte = format(ord(b), '08b')
        if not msb:
            res_byte = res_byte[::-1]
        res += res_byte
    return "".join(res)

def bits2bytes(bits, msb=False):
    res = []
    for b in grouper(bits, 8, 0):
        b = "".join(b)
        if not msb:
            b = b[::-1]
        res.append(chr(int(b, 2)))
    return "".join(res)

class BusyDelay():
    def __init__(self, delay):
        self.delay = delay
    
    def __enter__(self):
        self.start = time.time()
    
    def __exit__(self, type, value, traceback):
        # busy delay
        while (time.time() - self.start) < self.delay:
            pass

def do_tdi(b):
    global TDI
    GPIO.output(TDI, GPIO.LOW if b == '0' else GPIO.HIGH)

def do_tdo():
    global TDO
    return '0' if GPIO.input(TDO) == GPIO.LOW else '1'

def do_tms(low):
    global TMS
    GPIO.output(TMS, GPIO.LOW if low else GPIO.HIGH)

def do_tck(state):
    global TCK
    GPIO.output(TCK, state)

"""
 I   O
 0   1    0   1
   r   f
   _____     _____     _____     _____   
   ^   |     ^   |     ^   |     ^   |   
___|   V_____|   V_____|   V_____|   V___

raising: set output, clock
falling: read input, clock
"""

def shift_inout(data_in, commit, msb):
    global RATE
    delay = 1.0 / (2.0 * RATE)
    data_in_bits = bytes2bits(data_in, msb)
    print("tdi:", data_in_bits)
    data_in_bits = list(data_in_bits)
    #
    tdo = []
    ## TMS
    do_tms(False)
    # work cycle
    while len(data_in_bits) > 0:
        bit = data_in_bits.pop(0)
        # raising edge
        with BusyDelay(delay):
            ## TDI
            do_tdi(bit)
            ## TCK
            do_tck(GPIO.HIGH)
        # falling edge
        with BusyDelay(delay):
            ## TDO
            tdo.append(do_tdo())
            ## TCK
            do_tck(GPIO.LOW)
    print("tdo:", "".join(tdo))
    #
    # need commit?
    if commit:
        # raising edge
        with BusyDelay(delay):
            ## TMS
            do_tms(True)
            ## TCK
            do_tck(GPIO.HIGH)
        # falling edge
        with BusyDelay(delay):
            ## TCK
            do_tck(GPIO.LOW)
        ## TMS
        # do_tms(False)
    return bits2bytes(tdo, msb)

def shift_in(data_in, msb=False, commit=True):
    return shift_inout(data_in, commit, msb)

def shift_out(nbits, msb=False):
    data = create_data(nbits, 0)
    return shift_inout(data, False, msb)

from Crypto.Cipher import AES, ARC4
from Crypto.Hash import HMAC, MD5, SHA256
import xtea
import tea

def process_challenge(challenge, password, mode, *args, **kwargs):
    ## XTEA (little endian)
    if mode == 'xtea':
        x = xtea.new(password, mode=xtea.MODE_ECB, endian="<")
        response = x.encrypt(challenge)

    ## XTEA data<->key (little endian)
    if mode == 'xtea data':
        x = xtea.new(challenge, mode=xtea.MODE_ECB, endian="<")
        response = x.encrypt(password)

    ## XTEA (big endian)
    if mode == 'xtea be':
        x = xtea.new(password, mode=xtea.MODE_ECB, endian=">")
        response = x.encrypt(challenge)

    ## XTEA data<->key (big endian)
    if mode == 'xtea be data':
        x = xtea.new(challenge, mode=xtea.MODE_ECB, endian=">")
        response = x.encrypt(password)

    ### TEA (little endian)
    if mode == 'tea':
        t = tea.TinyEncryptionAlgorithm()
        response = str(t.encrypt(challenge, password, littleendian=True, padding=False))

    ### TEA data<->key (little endian)
    if mode == 'tea data':
        t = tea.TinyEncryptionAlgorithm()
        response = str(t.encrypt(password, challenge, littleendian=True, padding=False))

    ### TEA (big endian)
    if mode == 'tea be':
        t = tea.TinyEncryptionAlgorithm()
        response = str(t.encrypt(challenge, password, littleendian=False, padding=False))

    ### TEA data<->key (big endian)
    if mode == 'tea be data':
        t = tea.TinyEncryptionAlgorithm()
        response = str(t.encrypt(password, challenge, littleendian=False, padding=False))

    # ### TEA (big endian)
    # if mode == 'tea3':
    #     # response  = "".join(map(chr, tea2.decrypt(list(challenge[:8]), list(password), True)))
    #     # response += "".join(map(chr, tea2.decrypt(list(challenge[8:]), list(password))))
    #     t = tea3.TEA(password)
    #     response = t.decrypt_all(challenge)

    # ### TEA data<->key (big endian)
    # if mode == 'tea3 data':
    #     t = tea3.TEA(challenge)
    #     response = t.decrypt_all(password)

    # ### TEA DATA<->KEY
    # t = tea.TinyEncryptionAlgorithm(*args, **kwargs)
    # response = str(t.encrypt(password, challenge, padding=False))

    # ### MD5
    # md5 = MD5.new()
    # md5.update(challenge)
    # md5.update(password)
    # response = md5.digest()

    # ### HMAC_MD5
    # hmacmd5 = HMAC.new(password, digestmod=MD5)
    # hmacmd5.update(challenge)
    # response = hmacmd5.digest()

    # ### AES-128
    if mode == 'aes':
        aes = AES.new(password, AES.MODE_ECB)
        response = aes.encrypt(challenge)

    # ### AES-128 data<->key
    if mode == 'aes data':
        aes = AES.new(challenge, AES.MODE_ECB)
        response = aes.encrypt(password)

    return response

def foo(password, offset, mode, msb=False, reverse=False):
    global BIT_CHAL, BIT_CHAL_MSB, BIT_LED, BIT_LED_MSB, BIT_RESP, BIT_RESP_MSB, BIT_SELF_DESTRUCT1, BIT_SELF_DESTRUCT1_MSB, BIT_SELF_DESTRUCT2, BIT_SELF_DESTRUCT2_MSB, WINDOW_SIZE
    if msb:
        data_chal = create_data(WINDOW_SIZE, 0, BIT_CHAL_MSB)
        # data_chal = create_data(WINDOW_SIZE, 255, BIT_RESP_MSB, BIT_SELF_DESTRUCT1_MSB, BIT_SELF_DESTRUCT2_MSB, BIT_LED_MSB)
    else:
        data_chal = create_data(WINDOW_SIZE, 0, BIT_CHAL)
        # data_chal = create_data(WINDOW_SIZE, 255, BIT_RESP, BIT_SELF_DESTRUCT1, BIT_SELF_DESTRUCT2, BIT_LED)
    shift_in(data_chal, msb, True)
    # time.sleep(0.2)
    ####
    challenge = shift_out(128, msb)
    if reverse:
        challenge = bits2bytes(bytes2bits(challenge, msb)[::-1], msb)
    response = process_challenge(challenge, password, mode)
    if reverse:
        challenge = bits2bytes(bytes2bits(challenge, msb)[::-1], msb)
        response = bits2bytes(bytes2bits(response, msb)[::-1], msb)
    ####

    if msb:
        data_resp = create_data(WINDOW_SIZE, 0, BIT_RESP_MSB)#, BIT_LED_MSB)
    else:
        data_resp = create_data(WINDOW_SIZE, 0, BIT_RESP)#, BIT_LED)
    data_resp = challenge + data_resp[16:]
    # data_resp = '\x00'*16 + data_resp[16:]
    data_resp = data_resp[:offset] + response + data_resp[len(response) + offset:]
    print("c: %s -> r: %s p: %s m: %s (%s)" % ("".join(challenge).encode('hex'), "".join(data_resp).encode('hex'), password, mode, msb))
    d = shift_in(data_resp[16:], msb, True)

    #########################################
    answer = shift_out(128, msb)
    if reverse:
        answer = bits2bytes(bytes2bits(answer, msb)[::-1], msb)
        challenge = bits2bytes(bytes2bits(challenge, msb)[::-1], msb)
        response = bits2bytes(bytes2bits(response, msb)[::-1], msb)
    if answer != '\x00' * 16:
        print("a: %s" % (answer.encode('hex')))
    ##########################################
    print("-" * 30)

def bar(password_file):
    passwords = open(password_file, 'r').readlines()
    ALGO = [
        # ['tea be', False, False],
        # ['tea be', True, False],
        # ['tea be data', False, False],
        # ['tea be data', True, False],
        # ['tea', False, False],
        # ['tea', True, False],
        # ['tea data', False, False],
        # ['tea data', True, False],
        # ['aes', False, False],
        # ['aes', True, False],
        # ['aes data', False, False],
        # ['aes data', True, False],
        # ['xtea', False, False],
        # ['xtea', True, False],
        # ['xtea data', False, False],
        # ['xtea data', True, False],
        # ['xtea be', False, False],
        # ['xtea be', True, False],
        # ['xtea be data', False, False],
        # ['xtea be data', True, False],
        # inversed bits
        # ['tea be', False, True],
        # ['tea be', True, True],
        # ['tea be data', False, True],
        # ['tea be data', True, True],
        # ['tea', False, True],
        # ['tea', True, True],
        # ['tea data', False, True],
        # ['tea data', True, True],
        # ['aes', False, True],
        ['aes', True, True],
        # ['aes data', False, True],
        # ['aes data', True, True],
        # ['xtea', False, True],
        # ['xtea', True, True],
        # ['xtea data', False, True],
        # ['xtea data', True, True],
        # ['xtea be', False, True],
        # ['xtea be', True, True],
        # ['xtea be data', False, True],
        # ['xtea be data', True, True],
    ]
    for p in passwords:
        p = p.rstrip()
        #
        for offset in range(29): # 28
            for algo in ALGO:
                foo(p, offset, *algo)
                if STOP:
                    return

bar(PASSWORD_FILE)
