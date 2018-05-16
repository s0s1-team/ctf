#include <mcp_can.h>
#include <SPI.h>

unsigned int rxId;
unsigned char len = 0;
unsigned char rxBuf[8];
char buff[100];  //snprintf buff


MCP_CAN CAN0(10);
MCP_CAN CAN1(9);

unsigned short spd;
unsigned short rpm;
unsigned short temp;
unsigned short aac;
unsigned short maf;

void setup()
{
  Serial.begin(115200);

  if (CAN0.begin(CAN_50KBPS, MCP_16MHz) == CAN_OK) Serial.print("can0 init ok!!\r\n");
  else Serial.print("Can0 init fail!!\r\n");
  pinMode(2, INPUT);
  pinMode(3, INPUT);

  if (CAN1.begin(CAN_50KBPS, MCP_8MHz) == CAN_OK) Serial.print("can1 init ok!!\r\n");
  else Serial.print("Can1 init fail!!\r\n");
  
}

void print_data()
{
  Serial.print("ID: ");
  Serial.print(rxId, HEX);
  Serial.print("  Data: ");
  for (int i = 0; i < len; i++)             // Print each byte of the data
  {
    if (rxBuf[i] < 0x10)                    // If data byte is less than 0x10, add a leading zero
    {
      Serial.print("0");
    }
    Serial.print(rxBuf[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}

unsigned short parse(unsigned char* inp)
{
  return inp[1] | (inp[0] << 8);
}

void set(unsigned char* inp, unsigned short val)
{
  inp[1] = val & 0xFF;
  inp[0] = val >> 8;
}

void loop()
{
  if (!digitalRead(2)) 
  {
    CAN0.readMsgBuf(&len, rxBuf);
    rxId = CAN0.getCanId();
    switch (rxId)
    {
      case 0x23:
        spd = parse(rxBuf);
        rpm = parse(rxBuf + 2);
        sprintf(buff, "++23\tSpeed:%hi RPM:%hu p1:%hhu\n", spd, rpm, rxBuf[4]);
        set(rxBuf, 88);   //seting speed 88 
        Serial.print(buff);
        break;
        
      case 0x202:
        aac = parse(rxBuf);
        temp = parse(rxBuf + 2);        
        sprintf(buff, "++202\tAAC:%hu Temp:%hu p2:%hhu\n", aac, temp, rxBuf[4]);
        Serial.print(buff);
        break;
        
      case 0x19A:
        sprintf(buff, "++19A\tp3:%hhu p1:%hhu\n", rxBuf[0], rxBuf[1]);
        Serial.print(buff);
        break;

      default:
        print_data();
    }
    CAN1.sendMsgBuf(rxId, 0, len, rxBuf);
  }

  
  if (!digitalRead(3))
  {
    CAN1.readMsgBuf(&len, rxBuf);
    rxId = CAN1.getCanId();
    switch (rxId)
    {
      case 0x10C:
        maf=parse(rxBuf + 2);
        temp=parse(rxBuf);
        sprintf(buff, "--10C\tTemp:%hu MAF:%hu p4:%hu p5:%hu\n", temp, maf, parse(rxBuf + 4), parse(rxBuf + 6));
        Serial.print(buff);
        break;

      case 0x1BF:
        sprintf(buff, "--1BF\tBatt:%hu p6:%hu p7:%hu\n", parse(rxBuf), parse(rxBuf+2), parse(rxBuf+4));
        Serial.print(buff);
        break;
        
      case 0x12:
        sprintf(buff, "--12\tp9:%hhu Fuel:%hhu\n", rxBuf[0], rxBuf[1]);
        Serial.print(buff);
        break;
        
      default:
        print_data();
    }
    if (rxId!=0x10C and rxId!=0x1BF) //filtering for check
      CAN0.sendMsgBuf(rxId, 0, len, rxBuf);
  }

}
