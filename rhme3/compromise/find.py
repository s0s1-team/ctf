import os
from os import walk
import subprocess
import re
import struct

#mypath="./1000_binaries/bins"
bins_path="./bins"
tst_path="./tst"
strip_path="./strip"
func_path="./funcs"
NUM_FUNC=155

testvectors=["1001111101","0101100111","1100111010","0110110011","1111101010","1010100100"]

data_endh_off=0x144*2
data_endl_off=0x14e*2
data_startl_off=0x145*2
data_starth_off=0x146*2

read_datal_off=0x147*2
read_datah_off=read_datal_off+2

stack_startl_off=0x153*2
stack_starth_off=stack_startl_off+2
stack_endl_off=0x157*2
stack_endh_off=0x152*2
entry_offset=0x15b*2

def arg_from_opc(opc):
    return ((opc&0xF00)>>4|(opc&0xF))

def to_shrt(inp):
    return struct.unpack("H",inp)[0]

def read_addr(f,offl,offh):
    #print hex(offl), hex(offh)
    f.seek(offl)
    dl=arg_from_opc(to_shrt(f.read(2)))
    f.seek(offh)
    dh=arg_from_opc(to_shrt(f.read(2)))
    return (dh<<8)|dl

def read_fw(f):
    data_end=read_addr(f,data_endl_off,data_endh_off)
    data_start=read_addr(f,data_startl_off,data_starth_off)
    read_data=read_addr(f,read_datal_off,read_datah_off)
    stack_start=read_addr(f,stack_startl_off,stack_starth_off)
    stack_end=read_addr(f,stack_endl_off,stack_endh_off)
    f.seek(entry_offset)
    entry=to_shrt(f.read(2))
    
    return (data_start,data_end,read_data,stack_start,stack_end,entry)

def read_func(f):
    outbuf=""
    opc=f.read(2)
    while opc!="\x08\x95" and opc!="\x18\x95": # ret and reti
        outbuf+=opc
        opc=f.read(2)
        if opc=="":
            return outbuf
    outbuf+=opc
    return outbuf
    
def strip_args(f,data_start):
    f.seek(0)
    outbuff=""
    i=0
    ret_counter=0
    while i<(data_start/2):
        #print hex(i)
        opc=f.read(2)
        #print repr(opc)
        i_op=to_shrt(opc)
        #if i_op==0x9508: #ret
        #    ret_counter+=1
#        if i_op&0xFE0F==0x9000:  #LDS
#            outbuff+=opc+"\x00\x00"
#            f.read(2)
#            i+=1
#        elif i_op&0xFE0F==0x9200:  #STS
#            outbuff+=opc+"\x00\x00"
#            f.read(2)
#            i+=1
        if i_op&0xFE0E==0x940E:  #CAll
            outbuff+=opc+"\x00\x00"
            f.read(2)
            i+=1
        elif i_op&0xFE0E==0x940C:  #JMP
            outbuff+=opc+"\x00\x00"
            f.read(2)
            i+=1
#        elif i_op&0xE000==0xE000:  #LDI
#            outbuff+=struct.pack("H",i_op&0xF0F0)
#        elif i_op&0xE000==0x4000:  #sbci
#            outbuff+=struct.pack("H",i_op&0xF0F0)
#        elif i_op&0xE000==0x5000:  #sbci
#            outbuff+=struct.pack("H",i_op&0xF0F0)
#        elif i_op&0xF000==0x3000:  #cpi
#            outbuff+=struct.pack("H",i_op&0xF0F0)
#        elif i_op&0xF000==0x6000:  #ori
#            outbuff+=struct.pack("H",i_op&0xF0F0)
#        elif i_op&0xF000==0x7000:  #andi
#           outbuff+=struct.pack("H",i_op&0xF0F0)
        else:
            outbuff+=opc
        i+=1
    #print ret_counter
    return outbuff

def mesure(f1,f2):
    proc=subprocess.Popen(["radiff2", "-s", f1,f2], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    buff=proc.communicate()[0]
    m=re.search("similarity: (\S+)(\r\n|\n)distance: (\d+)",buff)

    return (m.group(1), m.group(3))        

def comp_radar(inp_path,out_file):    
    f = []
    for (dirpath, dirnames, filenames) in walk(inp_path):
        f.extend(filenames)
        break

    outbuff=""
    for i in range(1,len(f)):
        calc=mesure(inp_path+"/"+f[0],inp_path+"/"+f[i])
        if calc[1]!="0":
            outbuff+=f[i]+";"+calc[0]+";"+calc[1]+";\n" 
           
    if outbuff!="":
        fout=open(out_file,"w")
        fout.write(outbuff)
        fout.close()
    
    
#strip arguments
def strip_args_from_files(inp_path):
    f = []
    for (dirpath, dirnames, filenames) in walk(inp_path):
        f.extend(filenames)
        break

    for i in range(len(f)):
        f_obj=open(bins_path+"/"+f[i],"rb")
        addr=read_fw(f_obj)
        if addr[0]!=0x2000:
            print "data_start mism" 
            break
        data_sz=addr[1]-addr[0]
        stack_sz=addr[4]-addr[3]
        f_new=open(strip_path+"/"+f[i]+".stripped","wb")
        str_bin=strip_args(f_obj,addr[2])
        f_new.write(str_bin)
        f_new.close()
        f_obj.close()

def separatefuncs():
    f = []
    for (dirpath, dirnames, filenames) in walk(strip_path):
        f.extend(filenames)
        break


    files=[]
    for i in range(len(f)):
        files.append(open(strip_path+"/"+f[i],"rb"))

    for i in range(NUM_FUNC):
        dirname=func_path+"/sub"+str(i)
        os.makedirs(dirname)
        for j in range(len(files)):
            fbin=open(dirname+"/"+f[j],"wb")
            buff=read_func(files[j])
            fbin.write(buff)
            fbin.close()

    for i in files:
        i.close()
        
def read_funcs_list(inp):
    funcs = []
    funcs.append(0)
    f=open(inp,"rb")
    for i in range(NUM_FUNC):
        read_func(f)
        funcs.append( f.tell()/2)
    f.close()
    return funcs

def read_calls(inp,funcs):
    f=open(inp,"rb")
    calls=[]
    for j in xrange(NUM_FUNC):
        f_calls=[]
        func_bin=read_func(f)
        i=0
        while i<len(func_bin):
            opc=to_shrt(func_bin[i:i+2])
            if opc&0xFE0E==0x940E or opc&0xFE0E==0x940C:
                addr=to_shrt(func_bin[i+2:i+4])
                i+=4
                f_calls.append(resolv_call(addr,funcs))
            i+=2
        calls.append(f_calls)
    f.close()
    return calls

def resolv_call(addr,funcs):
    for i in xrange(len(funcs)-1):
        if addr<funcs[i]:
            print "ahtung, address error"
            break
        if addr>=funcs[i+1]:
            continue
        return (i,addr-funcs[i])
    return (len(funcs)-1,addr-funcs[-1])

def pring_calls(calls):
    for i in xrange(len(calls)):
        print "sub ",i
        for j in xrange(len(calls[i])):
            print "\t",calls[i][j][0],
            if calls[i][j][1]!=0:
                print "off +"+hex(calls[i][j][1]),
            print

def read_sampl_calls():
    f = []
    for (dirpath, dirnames, filenames) in walk(bins_path):
        f.extend(filenames)
        break
    samples_calls=[]

    for i in xrange(len(f)):
        print "read sample",i
               
        funcs=read_funcs_list(bins_path+"/"+f[i])
        calls=read_calls(bins_path+"/"+f[i],funcs)
        samples_calls.append(calls)
    
    return samples_calls
    
def comp_calls(samples_calls):
    for s in xrange(1,len(samples_calls)):
        print "comp sample ",s
        for f in xrange(len(samples_calls[s])):
            for c in xrange(len(samples_calls[s][f])):
                if samples_calls[0][f][c][0]!=samples_calls[s][f][c][0]:
                    print "call mismatch",s,f,c,hex(samples_calls[0][f][c][0]),samples_calls[s][f][c][0]
                if samples_calls[0][f][c][1]!=samples_calls[s][f][c][1]:
                    print "call offset mismatch",s,f,c

def get_test_array1(f):
    fd=open(f,"rb")
    fd.seek(10*2)
    if (to_shrt(fd.read(2))!=0x940e):
        print "bin error",f
        return
    fd.read(2)
    array1=[]
    for i in range(100):
        array1.append(5) # memset 5
    array2=[]
    for i in range(100): #first array operation
        fd.read(4) #skip opcode
        opc=to_shrt(fd.read(2))
        c=0xdeadbeef
        if opc&0xF0F0==0x5080:  # SUBI
            c=arg_from_opc(opc) #const from argument
            fd.read(4)
        elif opc==0x9380:   # optimised, no operation
            c=0
            fd.read(2)
        else:
            print "opc error", hex(opc),hex(fd.tell())
            return

        array1[100-i-1]-=c
        if array1[100-i-1]<0:
            array1[100-i-1]+=0x100
    for i in range(100): #second array operation
        fd.read(4)
        opc=to_shrt(fd.read(2))
        c=0xbeefdead
        #print hex(0x63-i), hex(opc)
        if opc&0xF0F0==0xE080: # LDI
            c=arg_from_opc(opc)
            fd.read(6)
        elif opc==0x9380:   # optimised, no operation
            c=0
            fd.read(2)
        elif opc&0xF0F0==0x9080: # COM
            c=0xFF
            fd.read(4)        
        else:
            print "opc error", hex(opc),hex(fd.tell())
            return        
        #print hex(c)
        array2.append(c)
    array2=array2[::-1]
    out=[]
    for i in range(100):
        out.append(array1[i]^array2[i])
    fd.close()
    return (array1,array2,out)

def get_test_array2(f,in_arr):
    out_arr=list(in_arr)
    fd=open(f,"rb")
    fd.seek(17*2)
    if (to_shrt(fd.read(2))!=0xF7E1):
        print "bin error",f
        return

    for i in range(100):
        fd.read(4)
        opc=to_shrt(fd.read(2))
        c=0xdeadbeef
        if opc&0xD2F8==0x8098: # Y+c
            c=((opc&7)|((opc&0xC00)>>7)|((opc&0x2000)>>8))-1
            fd.read(6)            
        elif opc==0x01CE:   # SUBI
            opc=to_shrt(fd.read(2))
            if (opc&0xF0F0!=0x5080):
                print i,hex(opc), "fix needed",hex(fd.tell()/2)
                return
            c=0x100-arg_from_opc(opc)-1
            fd.read(12)
        else:
            print "opc error", hex(opc),hex(fd.tell()/2)
            return
        if c<0 or c>99:
            print "error offset",c
            return
        out_arr[100-i-1]^=in_arr[c]

    tst_array_base=0x2a6b
    for i in range(100):
        opc=to_shrt(fd.read(2))
        if opc==0x9190: # lds   
            off1=to_shrt(fd.read(2))-tst_array_base
            fd.read(2)
            off2=to_shrt(fd.read(2))-tst_array_base
            if off1!=100-i-1 or off2>=100:
                print hex(100-i-1),"offset mism", hex(off1),hex(fd.tell()/2)
                return        
            fd.read(6)
            out_arr[off1]^=out_arr[off2]
        elif opc==0x9210: #     lds r18
            off1=to_shrt(fd.read(2))-tst_array_base
            if off1!=100-i-1:
                print hex(100-i-1),"offset mism", hex(off1),hex(fd.tell()/2)
                return
            out_arr[off1]=0
        else:
            print "opc error", hex(opc),hex(fd.tell()/2)                
    if to_shrt(fd.read(2))!=0x59CC:
        print "end opcode mism"
        return

    fd.close()
    return out_arr

def save_test_array():
    f = []
    for (dirpath, dirnames, filenames) in walk(strip_path):
        f.extend(filenames)
        break

    for fl in f:
        tst1=get_test_array1(func_path+"/sub19/"+fl)
        tst2=get_test_array2(func_path+"/sub18/"+fl,tst1[2])
        
        fout=open(tst_path+"/"+fl,"wb")
        fout.write(bytearray(tst2))
        fout.close()

def check_test(f,num):
    fl=open(f,"rb")
    buff=fl.read(100)
    fl.close()

    for i in range(100):
        for j in range(10):
            if str(ord(buff[(i+j)%100])&1)!=testvectors[num][j]:
                break
            if j==9:
               return True
    return False

def find_match():
    f = []
    for (dirpath, dirnames, filenames) in walk(tst_path):
        f.extend(filenames)
        break

    matched_1=[]
    for fl in f:
        if check_test(tst_path+"/"+fl,0):
            matched_1.append(fl)
    matched_2=[]
    for fl in matched_1:
        if check_test(tst_path+"/"+fl,2):
            matched_2.append(fl)
    matched_3=[]
    for fl in matched_2:
        if check_test(tst_path+"/"+fl,5):
            matched_3.append(fl)
    print matched_3

        
        
    
strip_args_from_files(bins_path)
separatefuncs()
#for i in range(NUM_FUNC):
#    if os.path.exists("funcs/sub"+str(i)):
#        comp_radar("funcs/sub"+str(i),"funcs/sub"+str(i)+".csv")

#sampl_calls=read_sampl_calls()
#comp_calls(sampl_calls)

save_test_array()
find_match()
