#include <mcp_can.h>
#include <SPI.h>

unsigned int rxId;
unsigned char len = 0;
unsigned char chr = 0;
unsigned char rxBuff[12];
unsigned char txBuff[12];
unsigned int tp=0;

MCP_CAN CAN0(10);                               // Set CS to pin 10


void setup()
{
  Serial.begin(115200);
  if(CAN0.begin(CAN_100KBPS,MCP_8MHz) == CAN_OK) Serial.print("CAN init OK\n");
  else Serial.print("Can init fail!!\r\n");
  pinMode(2, INPUT);                            // Setting pin 2 for /INT input
}

void print_data()
{
  Serial.print("ID: ");
  Serial.print(rxId, HEX);
  Serial.print("  Data: ");
  for(int i = 0; i<len; i++)                // Print each byte of the data
    {
    if(rxBuff[i] < 0x10)                     // If data byte is less than 0x10, add a leading zero
       {
       Serial.print("0");
       }
    Serial.print(rxBuff[i], HEX);
    Serial.print(" ");
    }
  Serial.println();  
}

void can_send()
  {
    CAN0.sendMsgBuf((unsigned long)txBuff[8]|(txBuff[9]<<8), 0, txBuff[10], txBuff);
    txBuff[11]=0;
  }

void loop()
{
  if(!digitalRead(2))                         // If pin 2 is low, read receive buffer
    {
      CAN0.readMsgBuf(&rxBuff[10], rxBuff); // Read data: len = data length, buf = data byte(s)
      //CAN0.readMsgBuf(&len, rxBuff);
      rxId = CAN0.getCanId();
      //print_data();
      rxBuff[8]=rxId;
      rxBuff[9]=rxId>>8;
      rxBuff[11]='\n';      
      Serial.write(rxBuff,12);
    }
  if (Serial.available())
    {
    txBuff[tp] =Serial.read();
    tp++;    
    }
  
  if (tp==12)
  {
    if (txBuff[11]=='\n')
        can_send();
    else
        Serial.print("---errore--\n");
    tp=0;
  }
}
