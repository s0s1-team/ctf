## Climate Controller Catastrophe  (750)

### Description

Catting cars is a major issue these days. It's impossible to sell your stolen car as a whole, so you sell it in parts. Dashboard computers are popular since they break quite often ;-).

Unfortunately, the dashboard computer is paired with the main computer. So, simply exchanging it will not do the trick. In fact, without the handshake to the main computer it will not operate the climate control buttons.

Of course just pairing the dashboard computer isn't cool enough, try to smash the stack instead! We suspect the device isn't using the serial interface for its pairing algorithm.

In addition to the attached challenge and reversing binaries, you're provided a special "challenge" which you can flash to wipe the EEPROM of your dashboard computer.

### Write-up

Challange with maximum points, in some way it wasn't too hard, just amount of code was greater then previous challanges.

This time we have firmware with CAN controllers which is communicated by SPI bus with MCU, for better understanding SPI intercommunication we can use this repository of similar [CAN library](https://github.com/coryjfowler/MCP_CAN_lib), unfortunatly I wasn't able to find exact CAN lib in open source, looks like develpers used own library.

For communication by CAN bus we used Arduino Uno, CAN shield with mcp2515 chip and [CAN bus lib](https://github.com/Seeed-Studio/CAN_BUS_Shield).
Small Arduino sketch was forwarding messages between CAN and Serial interface and python script responsible for processing multi CAN packets.


Among firmware modules you can identify SHA256 algo, HMAC-SHA256, EC routine, but you won't need to look deep inside of all mentioned above. As I discovered a little bit lately firmware implements standart [UDS](https://en.wikipedia.org/wiki/Unified_Diagnostic_Services) handler, nice cheatsheet also available [here](https://automotive.softing.com/fileadmin/sof-files/pdf/de/ae/poster/UDS_Faltposter_softing2016.pdf). UDS include additional protocol for transmiting payloads using multi CAN packets using additional CAN header.



```python

```


