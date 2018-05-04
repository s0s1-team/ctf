## Car Key Fob hardware backdoor (500)

### Description

We reverse engineered the firmware of a key-fob we found. There is an indication that there is a backdoor in a hardware module through a scan-chain that provides access to all the cars. It appears to use pin 1, 2, 43, and 44 from the chip. It also has a challenge-response mechanism of 128-bits. A list of ~~possible password candidates~~ elements with which the password could be constructed is found in the firmware and printed below.

PS. The scan-chain is emulated in software. Therefore, the worst case branch takes around 0.54 ms, and therefore you shouldn't drive the clock faster than 1.8 khz.

PPS. The Encryption used by this key-fob is very Advanced.

PPPS. Remember that the bits in the output of the scan chain come in reverse order. Also, the location for the provided ciphertext is different from the one where the challenge is received.

```
princess
fob
qwerty
secr3t
admin
backdoor
user
password
letmein
passwd
123456
administrator
car
zxcvbn
monkey
hottie
love
userpass
wachtwoord
geheim
secret
manufacturer
tire
brake
gas
riscurino
delft
sanfransisco
shanghai
gears
login
welcome
solo
dragon
zaq1zaq1
iloveyou
monkey
football
starwars
startrek
cheese
pass
riscure
aes
des
```

### Write-up

**TL;DR**
> AES 128 bit, `caradministrator`, reverse order MSB challenge at 0-127 position, reverse order MSB response at 224-351, flag in shift-register (not UART) at challenge's position

The challenge was in _misc_ category. The board implements shift-register protocol challenge-response protocol. We have a number of passwords and should guess the right one.

Probably this was the task we spent the most time on. It was periodically closed for bugfixes. Also because of no progress organizers periodically gave hints and they were very helpful (thanks Alex G.). Nevertheless the task was fun.

We used Arduino and Beaglebone Black to solve this task: each member had its own setup and scripts :).

The first task was to find out what every pin is responsible for. In terms of JTAG names here is what we got:
- A4: TDI 
- A5: TDO
- A2: TCK
- A3: TMS

Using pins we could provide and get data from the board. We found out that size of register is 512 bit. The main bits were:
- 2 self-destructing bits (450 and 460). Once set they halted the board.
- Challenge request bit (354). After setting it the first 128 bit were challenge.
- Response request bit (355). Used after when sending response. If response was bad message "Authentication failed" was printed on UART.

Here we faced the first bug, we didn't have much clock available to put our response. The board was resetting prior we could put our response.

After the bug was fixed, our next part was to guess algorithm: PPS and PPPS weren't present in description from the start of the challenge. We tried different algos: AES, MD5, SHA1, etc. We used hashing and padding on passwords. And we got nothing. After some time we decided to put aside this challenge

We came back to the challenge after first hint was revealed:
> **T**he **E**ncryption used by this key-fob is very **A**dvanced

There were 2 candidates with this hint: TEA (because of capitals) and AES (because of _advanced_). The former assumption was wrong.

Also organizers changed a bit description. Instead of _possible password candidates_ we've got _elements with which the password could be constructed_. So we needed to combine passwords. The number of password candidates increased dramatically: from 45 to 31796. And number of bruteforce tries also increased because of different algorithms and MSB/LSB bit numbering. 

At some time new hint emerged. We narrowed our bruteforce space and got some hints from organizers: flag will be at the place of challenge if there will be no "Authorization failed" message and the key consist of 2 passwords.

Playing a bit more we found password: `caradministrator`. Challenge and response were in reverse order MSB. Response should be put starting at 224 offset. On the first try we didn't get the flag. There was another bug in the challenge. But after fixes flag was received.

See scripts for more information.