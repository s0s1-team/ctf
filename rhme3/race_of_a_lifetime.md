## Race of a Lifetime (100)

### Description

You are participating in a race around the world. The prize would be a personalized flag, together with a brand new car. Who wouldn't want that? You are given some locations during this race, and you need to get there as quick as possible. The race organisation is monitoring your movements using the GPS embedded in the car. However, your car is so old and could never win against those used by the opposition. Time to figure out another way to win this race.

### Write-up

There is console interface for GPS available on the UART. It shows your position on the map
along with other textual information. The task was to travel to several destination points
without exhausting number of moves and without exceeding transport speed (e.g. for airplane
7.5 pt/move).

Solution in Python with `pwntools`:

```python
from pwn import *
import math

GPS = {
    "the Riscure office":   (51.997838,  4.3853637),
    "CDG":                  (49.0096906, 2.5457358),
    "PVG":                  (31.1443439, 121.8060843),
    "SFO":                  (37.6213129,-122.3811441),
    "550 Kearny St, San Francisco, CA, United States": (37.7932696, -122.4065364),
}

def read_coords_begin(tty):
    tty.recvuntil("Latitude:")
    lat = float(tty.recvuntil("\t").strip())
    tty.recvuntil("Longitude:")
    lon = float(tty.recvuntil("\n").strip())
    return (lat, lon)

def read_coords(tty):
    tty.recvuntil("Location:")
    location = tty.recvline().strip()
    if location in GPS:
        return GPS[location]
    lat, lon = map(float, location.split(" "))
    return (lat, lon)

def read_destination(tty):
    tty.recvuntil("Head to ")
    destination = tty.recvline().replace("to get the directions.", "").strip()
    return destination

def enter_name(tty):
    tty.recvuntil("Enter your name to start:")
    tty.send("S0S1\n")
    tty.recvline()

def create_track(start, end, max_speed=1.0, number=None):
    track = []
    if number is None:
        d = math.sqrt(((end[0] - start[0]) ** 2) + ((end[1] - start[1]) ** 2))
        number = int(math.ceil(d / max_speed))
    for i in xrange(number):
        lat = start[0] + ((end[0] - start[0]) * (i + 1) / number)
        lon = start[1] + ((end[1] - start[1]) * (i + 1) / number)
        track.append("%.6f %.6f" % (lat, lon))
    print "FROM: %s TO: %s IN: %d" % (start, end, number)
    return track

def move(tty, track):
    for pos in track:
        l = tty.recvuntil(">", timeout=1)
        if l == '':
            return False
        print "SENDING: %s" %  pos
        tty.send(pos + "\n")
        tty.recvline() # pos
        l = tty.recvline()
        if "Unexpected location." in l or "Too late." in l:
            return False
    return True

def foo():
    tty = serialtube("/dev/tty.usbserial", baudrate=115200, timeout=0)
    enter_name(tty)
    start_pos = read_coords_begin(tty)
    destination = read_destination(tty)
    if not destination in GPS:
        print "Not found: %s" % destination
    end_pos = GPS[destination]
    
    # -> riscure
    track_to_riscure = create_track(start_pos, end_pos)
    if not move(tty, track_to_riscure):
        tty.interactive()
        return
    
    # get ECU
    riscure_pos = end_pos
    destination1_pos = read_coords(tty)
    
    print "riscure -> cdg"
    track_to_paris = create_track(riscure_pos, GPS["CDG"], max_speed=1.0)
    if not move(tty, track_to_paris):
        tty.interactive()
        return

    print "cdg -> pvg"
    track_to_bejing = create_track(GPS["CDG"], GPS["PVG"], max_speed=7.5)
    if not move(tty, track_to_bejing):
        tty.interactive()
        return

    print "pvg -> destination1"
    track_to_destination1 = create_track(GPS["PVG"], destination1_pos, number=8, max_speed=0.3)
    if not move(tty, track_to_destination1):
        tty.interactive()
        return
    
    ## bring ECU
    destination2_pos = read_coords(tty)
    
    print "destination1 -> pvg"
    track_to_bejing = create_track(destination1_pos, GPS["PVG"], max_speed=0.3)
    if not move(tty, track_to_bejing):
        tty.interactive()
        return
    
    print "pvg -> cdg"
    track_to_paris = create_track(GPS["PVG"], GPS["CDG"], max_speed=7.5)
    track_to_paris.append(track_to_paris[-1])
    if not move(tty, track_to_paris):
        tty.interactive()
        return

    print "cdg -> sfo"
    track_to_sanfrancisco = create_track(GPS["CDG"], GPS["SFO"], number=16, max_speed=7.5)
    if not move(tty, track_to_sanfrancisco):
        tty.interactive()
        return
    
    print "sfo -> destination2"
    track_to_destination2 = create_track(GPS["SFO"], destination2_pos, max_speed=0.3)
    if not move(tty, track_to_destination2):
        tty.interactive()
        return
    
    # go to riscure
    print "destination2 -> sfo"
    track_to_sanfrancisco = create_track(destination2_pos, GPS["SFO"], max_speed=0.3)
    if not move(tty, track_to_sanfrancisco):
        tty.interactive()
        return

    print "sfo -> cdg"
    track_to_paris = create_track(GPS["SFO"], GPS["CDG"], number=16, max_speed=7.5)
    if not move(tty, track_to_paris):
        tty.interactive()
        return

    print "cdg -> riscure"
    track_to_paris = create_track(GPS["CDG"], riscure_pos, max_speed=1.0)
    if not move(tty, track_to_paris):
        tty.interactive()
        return

    tty.interactive()

foo()
```