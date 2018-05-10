#!python2
# coding: utf-8
from itertools import izip_longest

LC = bytearray((
    148, 32, 133, 16, 194, 192, 1, 251, 1, 192, 194, 16, 133, 32, 148, 1,
))

PI = bytearray("FCEEDDC68B213A17B556FADAF5579C903EAA279E93609966C1EB2D6D8D5411166B8A6F51E3137CFD5CC07249C401524F40CB4C36ADF35976950BA898304D4A50797B261EEAC80D336AB8637EB9EDCECCF1714B129BDBAB806837CF0297BC81C35B77D3BB1A70D483B609E1B3969F2B28E47418E0673FC53B291B82191FB7075DD522F9E735A94287D73CD6647D23F69A7841ECDEA648FF24DCE8F4C94EA10AD2349D253D1400FB4455F7A08820D1BF05AC45919269895EF286A2AEE5BE4694310C8E6E0EC2E98F65A3732EEF5F04E610A4C7CD06087AF8FE5A843903CAD81C2FB2E2B0AF622ADF8C53476143B438BA581DA77F0F75B1F085D06CA51532D92CBD".decode('hex'))

# reconstruct inverse SBox from SBox
PIinv = bytearray(256)
for x in xrange(256):
    PIinv[PI[x]] = x

PIinv_bad = bytearray("A52D5BDBCDAFD37ED4009E39C046C3F3CF1E5325A4FB1F07727B6479DEF0437CAC05818D97A242126F78E56EFE1ACADF3CBFFC47A0843359EDDA060089A30075309186EBA7B1BDE9952B3E52323D9C2F3F232EE81DA8090DEF36D860287FB6CC15EAE44A8BC7177458B44820F91BC22265512AC971F437619000D54126004BF2575E7A67D9F7B887ABB52104E71CC1C60FB2B314BE386C5C3B168F540EA1136DAA9DB9C8D0FA94003A001156B034BAE3E2F5E06BEC08687D494CEE635DFFBCAE2918C45F2C0003D1459BDC314FD24E5AF8AD9F6266008A88DDFD0B55980293E6736AE10070BBCE8399C54419924D01CBF650B7359A0C8EA9D6820AA60027D796".decode('hex'))

def gf(a, b):
    c = 0
    while b:
        if b & 1:
            c ^= a
        if a & 0x80:
            a = (a << 1) ^ 0x1C3
        else:
            a <<= 1
        b >>= 1
    return c

GF = [bytearray(256) for _ in xrange(256)]

for x in xrange(256):
    for y in xrange(256):
        GF[x][y] = gf(x, y)

def strxor(a, b):
    """ XOR of two strings

    This function will process only shortest length of both strings,
    ignoring remaining one.
    """
    mlen = min(len(a), len(b))
    a, b, xor = bytearray(a), bytearray(b), bytearray(mlen)
    for i in xrange(mlen):
        xor[i] = a[i] ^ b[i]
    return bytes(xor)

def L(blk, rounds=16):
    for _ in range(rounds):
        t = blk[15]
        for i in range(14, -1, -1):
            blk[i + 1] = blk[i]
            t ^= GF[blk[i]][LC[i]]
        blk[0] = t
    return blk

def Linv(blk):
    for _ in range(16):
        t = blk[0]
        for i in range(15):
            blk[i] = blk[i + 1]
            t ^= GF[blk[i]][LC[i]]
        blk[15] = t
    return blk

C = []
for x in range(1, 33):
    y = bytearray(16)
    y[15] = x
    C.append(L(y))

def lp(blk):
    return L([PI[v] for v in blk])

class GOST3412Kuznechik(object):
    """GOST 34.12-2015 128-bit block cipher Кузнечик (Kuznechik)
    """
    def __init__(self, key):
        """
        :param key: encryption/decryption key
        :type key: bytes, 32 bytes

        Key scheduling (roundkeys precomputation) is performed here.
        """
        kr0 = bytearray(key[:16])
        kr1 = bytearray(key[16:])
        self.ks = [kr0, kr1]
        for i in range(4):
            for j in range(8):
                k = lp(bytearray(strxor(C[8 * i + j], kr0)))
                kr0, kr1 = [strxor(k, kr1), kr0]
            self.ks.append(kr0)
            self.ks.append(kr1)

    def encrypt(self, blk):
        blk = bytearray(blk)
        for i in range(9):

            blk = lp(bytearray(strxor(self.ks[i], blk)))
        return bytes(strxor(self.ks[9], blk))

    def decrypt(self, blk):
        blk = bytearray(blk)
        for i in range(9, 0, -1):
            blk = [PIinv[v] for v in Linv(bytearray(strxor(self.ks[i], blk)))]
        return bytes(strxor(self.ks[0], blk))

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def decrypt_edrs():
    key = "631EE5FAB639223D6068F8FEEFE26DBF15B39BDDD79D5B1E84DCE6A89BCFFCA2".decode('hex')
    x = GOST3412Kuznechik(key)
    EDR = [
        "6027A2C40D5326955A54B4B03C1CFBAED0E43C2766A70A772407C34FFAD5064BD1D6C4A7DA53CD77CCDFE19D46DB42713D7F42D0E8BF3926D9EFBDF5A7538068".decode('hex'),
        "6027A2C40D5326955A54B4B03C1CFBAE8E3913BBD6919F6377CACA46B6C9095030925311965A46B4B321777483B0BE72".decode('hex'),
        "6027A2C40D5326955A54B4B03C1CFBAE3075EA28B6262CB7559174EB126C591754BED4BCF9069C73842487FF390F1819A4DB00E0191ACF6A11AC0E5CCD7725C2988C3F9EF2C6D202B4DC968F5AEA2D2B6BEB2DAEB67D80021C265C7ED522818DF1901E028E36B547DB83FF2DA7F93D82F81401603D3FD18BABB10C550EDC2D77".decode('hex'),
    ]
    d = []
    for edr in EDR:
        for b in grouper(edr, 16, '\x00'):
            d.append(x.decrypt(b))
    return "".join(d)

print decrypt_edrs()