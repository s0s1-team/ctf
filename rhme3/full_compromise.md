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

By looking to generated csv files we can see that only few subfunctions has differance.