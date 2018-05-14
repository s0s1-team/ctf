## Full Compromise (250)

### Description

An attacker managed to hack our CI server and sign+encrypt his malicious code in a ECU firmware, that is now running in millions of cars and doing Chaos knows what. To stop the attackers, we must know what the malicious code is doing. We have a history of all binaries signed by the server on the day of the hack, and a device running the attacker's firmware. Help us find which sample was provided by the attacker and get access to its management interface.

### Write-up

Archive with 1000 binaries is attached to this challenge and our first task is to find out which one has "malicious code".

At first we should convert all binaries from intel hex to raw binary, you can use this command:

    arm-none-eabi-objcopy -I ihex --output-target=binary code00.hex code00.bin

I'm always wanted to try *radiff2* tool in action and this was quite good time for this, but when I compared two binaries my result was far from expected(
Next idea was that malicious code shoul bring sowe extra functions, and I decided to count **ret** opcode in all binaries, but all binaries had exactly same number of returns - 154. Ok maybe malicious code is injected directly inside of some function. I decided to roughly split samples on individual functions using **ret** opcode as separator, strip all absolute adresses from opcode and save it indivual subfolders:

```python
def strip_args(f,data_start):
    f.seek(0)
    outbuff=""
    i=0
    ret_counter=0
    while i<(data_start/2):
        opc=f.read(2)
        i_op=to_shrt(opc)
        if i_op&0xFE0E==0x940E:  #CAll
            outbuff+=opc+"\x00\x00"
            f.read(2)
            i+=1
        elif i_op&0xFE0E==0x940C:  #JMP
            outbuff+=opc+"\x00\x00"
            f.read(2)
            i+=1
        else:
            outbuff+=opc
        i+=1
    return outbuff

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
```

After that I automated *radiff2* compare process for individual funcion and saved results in csv file:

```python
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
```

By looking to generated csv files we can see that only few subfunctions has differance:
 - sub0 - difference is in switch table of unused function and reset handler, so it's not interesting.
 - sub14 and sub25 (main) - difference is in *serial_print* function pointer and it also not interesting for us.
 - *sub8*, *sub18* and *sub19* is quite big functions and have a lot of differences among all samples.

At this point it's clear that only 3 function is different, but where's malicious code, they all have significant diffierence?
Ok let's have a detailed look inside of sample, we can choose anyone, at least we know which function is shared among all them.

By looking through firmware we can see that DAC module and timer interrupt is set during init, after init phase input is avaiting and two branches is availabe: "test mode" and "secret management mode". For "test mode" *sub18* and *sub19* is used to calculate test array, chosen bits of test array is transmitted as analog signal on D7-D8 pins. "Secret mangment mode" use *sub8* for password generation (250 bytes), when user input asterics char system falls in exotic password input mode: password byte value is incremented by entering of any byte to serial interface and different bytes is entered by syncing input with counter overflow. Next interesting thing is that password verification is using "heavy" operations and takes about ~4 hours.

But wait, where is malicious code? So someone just forgot his backdoor password and we need to find it, damn stop always blame hackers in your insecurity)

Things becomes more clear, we need to identify which sample is used by looking analog signal during "test" command, calculate password for located sample and pass verification to "secret management mode", sounds easy, easier than it is)

First of all we need to know how test data is exposed, if you quickly identify that compiler was using division optimisation throu modular multiplication you will see that during running test 10 bits of test array is exposed. Leaked bits are least significant bit of randomly chosen 10 consequent bytes of test array.

[signal]

Next problem we have is to calculate test arrays for 1000 samples, it was obvious that Atmel Studion isn't able to handle this, by looking other emulators I dicided to try well known radare ESIL engine. After few days suffering and looking other open source emulators I admited that test array generation isn't so complicated, operations isn't so complicated and all we need to do just extract arguments from opcodes.

Few hours of coding and we have this two function that extracts all that we need:

```python
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
```


Next we are getting armed with oscilloscope write down 5 bitvectors from test mode and filter our results using script, this should be sufficiently enough to locate which sample is running on your board. After that you can calculate right password for running firmware, for this purpuse Atmel Studio would more then enough, few patches to firmware and setting breakpoint after password calculation, when it hits breakpoint just copy calculated pass to final script.

Last thing left is to run final script for password verification, don't forget to check that printed pass is matching expecatation, or you will be quite supprised in the end, if everything is fine you have ~4 hours of "free time").

I'm still wonder why Car Crash cost 500 points, and all this stuff above just 250 point, but anyway congratulations if get throug it.
