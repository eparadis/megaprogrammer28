#!/usr/bin/env python
# Uses the Arduino firmware given on http://danceswithferrets.org/geekblog/?p=496
#
# -r start end (in decimal) - Standard Hexdump
# -R start end (in decimal) - Hexdump with no index
# -b start end (in decimal) - Binary Dump
# -s file.bin (programming)
# -v file.bin (verify content)
# -S file.bin ('smart' programming)
#
# Normally takes 196 seconds to program a 28C64, and 32 seconds to read.
# --
# Chris Baird,, <cjb@brushtail.apana.org.au> threw
# this together during an all-nighter on 2017-Oct-19.
# This version: 2021-Oct-28, as updated by Michelle Knight (fixed baud rate, plus other minor tartups).

import sys
import serial
import time

RECSIZE = 16

ser = serial.Serial('/dev/cu.usbmodem14301', 115200, timeout=0.1)
sys.argv.pop(0)
dumpstart = -1
dumpend = -1
s = sys.argv[0]
time.sleep(1)                   # weirdness it started needing -cjb


def calcwriteline(a, l):
    ck = 0
    s = "W" + ("%04x" % a) + ":"
    for c in l:
        s = s + ("%02x" % ord(c))
        ck = ck ^ ord(c)
    s = s + "ffffffffffffffffffffffffffffffff"
    s = s[:38]
    if (len(l) & 1):
        ck = ck ^ 255
    ck = ck & 255
    s = s + "," + ("%02x" % ck)
    return s.upper()


def waitokay():
    bad = 0
    while True:
        s = ser.readline()
        print(s)
        if s == b'OK\r\n':
            break
        else:
            bad = bad + 1
        if bad > 20:
            sys.exit("error: no OK response from Arduino!")

if s == "-r":
    dumpstart = int(sys.argv[1])
    dumpend = int(sys.argv[2])
    if dumpstart > -1:
        while (dumpstart <= dumpend):
            addr = "%04x" % dumpstart
            s = "R" + addr + chr(10)
            ser.write(s.encode())
            l = ser.readline()
            print(l.upper(), end=' ')
            waitokay()
            dumpstart = dumpstart + RECSIZE


if s == "-R":
    dumpstart = int(sys.argv[1])
    dumpend = int(sys.argv[2])
    if dumpstart > -1:
        while (dumpstart <= dumpend):
            addr = "%04x" % dumpstart
            s = "R" + addr + chr(10)
            ser.write(s.encode())
            l = ser.readline()
            o = l.upper()
            content = o[5:-5]
            for i in range(0,64,2):
                by = content[i:i+2]
                print(by, end=' ')
            print()
            waitokay()
            dumpstart = dumpstart + RECSIZE


if s == "-b":
    dumpstart = int(sys.argv[1])
    dumpend = int(sys.argv[2])
    if dumpstart > -1:
        while (dumpstart <= dumpend):
            addr = "%04x" % dumpstart
            s = "R" + addr + chr(10)
            ser.write(s.encode())
            l = ser.readline()
            o = l.upper()
            content = o[5:-5]
            for i in range(0,64,2):
                by = content[i:i+2]
                if len(by)>0: 
                    sys.stdout.write(chr(int(by, 16))),
            waitokay()
            dumpstart = dumpstart + RECSIZE


if s == "-s":
    f = open(sys.argv[1], 'rb')
    a = 0
    while True:
        l = f.read(RECSIZE)
        if len(l) == 0:
            break
        s = calcwriteline(a, l)
        print(s)
        sys.stdout.flush()
        ser.write(s + chr(10))
        waitokay()
        sys.stdout.flush()
        if len(l) != RECSIZE:
            break
        a = a + RECSIZE
    f.close()


if s == "-v":
    print('-v mode')
    f = open(sys.argv[1], 'rb')
    a = 0
    badcount = 0
    while True:
        #s = ("R" + ("%04x" % a) + chr(10)).encode('utf-8')
        s = ("R%04x\n" % a).encode()
        print(s)
        print("%d bytes out" % ser.write(s))
        l = ser.readline()
        l = l.upper()
        print(l)
        waitokay()

        romt = "ROM  %04x:" % a

        rom = [None]*RECSIZE
        for p in range(RECSIZE):
            i = 5 + (p*2)
            c = int(l[i:i+2], 16)
            romt = romt + str(" %02x" % c)
            rom[p] = c
        print(romt, "\r", end=' ')
        sys.stdout.flush()

        r = f.read(RECSIZE)
        if len(r) == 0:
            break
        okay = 1
        filet = "FILE %04x:" % a
        for i in range(len(r)):
            filet = filet + " %02x" % r[i]
            if rom[i] != r[i]:
                okay = 0
                badcount = badcount + 1

        if okay == 0:
            print()
            print(filet)
            print("MISMATCH!!")
            print()
            sys.stdout.flush()

        if len(r) != RECSIZE:
            break
        else:
            a = a + RECSIZE

    print()
    print(badcount, "errors!")
    sys.stdout.flush()
    f.close()


if s == "-S":
    f = open(sys.argv[1], 'rb')
    a = 0
    while True:
        s = "R" + ("%04x" % a) + chr(10)
        ser.write(s)
        l = ser.readline()
        l = l.upper()
        waitokay()

        romt = "ROM  %04x:" % a
        rom = [None]*RECSIZE
        for p in range(RECSIZE):
            i = 5 + (p*2)
            c = int(l[i:i+2], 16)
            romt = romt + str(" %02x" % c)
            rom[p] = c

        r = f.read(RECSIZE)
        if len(r) == 0:
            break
        print(romt, end=' ')
        sys.stdout.flush()
        okay = 1
        filet = "FILE %04x:" % a
        for i in range(len(r)):
            if rom[i] != ord(r[i]):
                okay = 0
                filet = filet + " %02x" % ord(r[i])
            else:
                filet = filet + "   "

        if okay == 0:
            s = calcwriteline(a, r)
            print()
            print(filet, "UPDATING")
            sys.stdout.flush()
            ser.write(s+chr(10))
            waitokay()
        else:
            print(" OKAY")
        sys.stdout.flush()

        if len(r) != RECSIZE:
            break
        else:
            a = a + RECSIZE

    f.close()

###
