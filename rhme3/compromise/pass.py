import serial


password="d8df9093e3c50dee034f2c9ab243873bb963cb21840c1ed534cb34283d31c656e4e74c2b957943826fdc639a7f3a13b40e361f62052d2160116b0a6f77df95928c26de7af256e2390a6818366c9f89f4f6e7269bb96241418e603d9c9867455f7c87f99adbe72b97ff13e47feac537ac6d09a4cac339d74da4bfcae2a0c3f02ec31272390714b026edce2a53aa48c25ad53784824da54d25bf1b2e5067a661df96b9cff37e1cf86e76f05ae0cbed91a03218fce2f6f9013ba00d09100faaabb9b518f0511a444b529a242cc7d4e5065820177187afd3b3a3723695c615446428763cdb6f12a884ca84a5f0f7336049250f6acd3027a4eab30462".decode('hex')

def enter_pass(tty,passw):
    delay=6
    c=1
    #sleep(0.2)
    for i in range(len(passw)):
        print str(c)+" sent"
        if ord(passw[i])==0:
            tty.write("a"*0x100)
        else:
            tty.write("a"*ord(passw[i]))
        if c%20==0:
            sleep(delay-2)
        else:
            sleep(delay)
        c+=1
    tty.write("*")
    while True:
        st=tty.readline()
        print st
        if st=="You entered the following string: \r\n":
            break
    for i in range(12):
        print tty.readline()   
    
    

with serial.Serial('/dev/ttyUSB0',115200) as tty:
    while tty.readline()!="Starting...\r\n":
        pass
    print tty.readline()
    print tty.readline()
    print tty.readline()
    
    tty.write("*\n")
    print tty.readline()
    
    enter_pass(tty,password)

    while True:
        print tty.read(1),
        sys.stdout.flush()
        
        

