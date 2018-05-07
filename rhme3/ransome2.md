## Ransom 2.0 (150)

### Description

In theory, this firmware mod was supposed to give you 30% extra horsepower and torque. In reality, it's something different. For real this time. For real this time.

### Write-up

As it was expected in this challange comparison function was fixed, and this time we will have to look throug unlock code generation.

Generation is based on "user ID", which isn't changing trough the board reset, so we just need to reverse user ID transformation to unlock key. Reimplementing transformation code using python and we have this tiny script:

```python
inp="3835320109000500".decode('hex')+'\x00'

def process(seed,inp):
    state=seed
    for i in range(inp):
        c=((state>>5)^(state>>3)^(state>>2)^state)&1
        state=(state>>1)|(c<<15)        
    return state

output=""
seed=0x1337
for i in range(len(inp)-1):
    num=ord(inp[i])|(ord(inp[i+1])<<8)
    m=(0xcafe<<i)&0xFFFF
    seed=process(seed,m^num)
    output+=chr(seed&0xFF)
    output+=chr(seed>>8)
    
print output.encode('hex').upper()
```

Don't forget to convert unlock key to upper case and next 150 points is yours)
