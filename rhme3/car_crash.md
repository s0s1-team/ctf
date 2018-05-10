## Car Crash (500)

### Description

This ECU firmware dump, or what's left of it, was taken out of a crashed prototype car. We have to extract the logs from it to investigate the crash. Bad luck, we get some strange garbage printed instead.

Attached is a program you can reverse-engineer and a program you can test. Don't mix them up.

### Write-up

The first part of the task was to reverse binary. The application
was responsible for storing EDRs in encrypted form and decrypting them.
Reversing showed that the app uses implementation [Kuznyechik block cipher](https://en.wikipedia.org/wiki/Kuznyechik) for EDR encryption.

The implementation was reference except SBoxes were modified.
Additionally inverse SBox for decryption was corrupted. The dump also 
contained encryption key and encrypted EDRs.

Decryption using provided inverse SBox failed. We were getting garbage,
but after reconstructing inverse SBox from SBox we succeed.
And here are successfully decrypted EDRs:

```
2018-01-12 18:12:52.024	ECU	ERR	CAN DECODER ERROR, SKIPPING MSG
2018-01-12 18:12:52.353	ECU	WRN	CAN BUFFER FULL
2018-01-12 18:12:52.494	ABS	ERR	ABS OFFLINE
2018-01-12 18:12:54.950	ECU	DBG	DUMP SERVICE FLAG f3baeed203317349c00b4d467390ef1d
```