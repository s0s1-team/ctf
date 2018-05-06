## Ransom (50)

### Description

In theory, this firmware mod was supposed to give you 30% extra horsepower and torque. In reality, it's something different. For real this time.

### Write-up

Most easiest task due to possible bug, which was fixed in Ransom 2.0.

First we locate *vfprintf* function from libc (large and complicated) and using cross-references we moving up and locate *serial\_print*. By looking through  *serial\_print* calls and paramters (string pointers) we can map printed strings with code branches.

Among the strings most interesting for us this one:

	RAM:210A "It was a pleasure doing business with you.\nYour car is now unlocked."

By looking at code tree of *main* function we can see repeating loop of prompt printing, input reading and duoble call of *check* input function and jump to success branch. 


![data](images/data_init1.png)

*Check* is just time safe memory comparison function (xor) with one interisting bug, someone missed loop increment and comparison checks only first byte, sounds nice)

Next move up by code tree to locate unlock key generation at SP+0x3B, here we see  interesting string "%02X", which means unlock key is hexademical text, all we need to do is to try 16 digits.
Flashing firmware, several tries and we have 50 points.