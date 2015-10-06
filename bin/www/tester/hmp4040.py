#!/usr/bin/env python
#coding:utf8
#programmable power supply HMP4040
#xulijun@2015-9-23 initial version

import serial #http://pythonhosted.org/pyserial/
import functools
import io
import time

class HmpOutputError(Exception): pass

class Hmp4040:
	timeout = 5 #unit S
	def __del__(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port, baud=115200):
		self.uart = serial.Serial(port, baud,
			serial.EIGHTBITS,
			serial.PARITY_NONE,
			serial.STOPBITS_ONE,
			timeout = self.timeout,
			writeTimeout = self.timeout
		)
		self.sio = io.TextIOWrapper(
			io.BufferedRWPair(self.uart, self.uart, 1),
			newline = '\r',
			line_buffering = True
		)
		self.cio_write = functools.partial(self.__write__, prefix = "\r\n")

		self.idn = self.cio_write("*idn?")
		self.reset()
		self.cls()

	def __write__(self,cmd,prefix=""):
		cmd_buf = cmd + prefix
		self.uart.write(cmd_buf)

	def write(self,cmd):
		self.uart.write(cmd)

	def read_line(self):
		eol = b'\n'
		leneol = len(eol)
		line = bytearray()
		timeout = 1000 #ms
		while timeout >0:
			rd_len = self.uart.inWaiting()
			if(rd_len > 0):
				c = self.uart.read(rd_len)
				if c:
					line += c
					if line[-leneol:] == eol:
						break
				else:
					timeout = -1
			timeout = timeout-100
			time.sleep(0.1)
		else:
			assert "read timeout"
		return bytes(line)

	def reset(self):
		self.cio_write("*rst")
	def cls(self):
		self.cio_write("*cls")
	def err(self):
		#such as: -230,"Data stale"
		return self.cio_write("system:err?")

	def set_vol(self, ch, vset, curr):
		self.cio_write("INST OUT%d"%ch)
		time.sleep(0.05)
		self.uart.flushInput()
		self.cio_write("INST?")
		echo = self.read_line()
		if int(echo[4:5]) != ch:
			raise HmpOutputError
		self.cio_write("APPLY %f,%f"%(vset,curr))
		time.sleep(0.5)
		self.uart.flushInput()
		self.cio_write("APPLy?")
		echo = self.read_line()
		[vget, iget] = echo.split(",")
		vget = float(vget)
		delta = abs(vget - vset)
		if delta > 0.1:
			raise HmpOutputError
		self.cio_write("OUTP ON")
		time.sleep(0.1)

	def output_en(self,ch,en):
		self.cio_write("INST OUT%d"%ch)
		time.sleep(0.05)
		if en:
			self.cio_write("OUTP ON")
		else:
			self.cio_write("OUTP OFF")

	def lock(self,en):
		if en:
			self.cio_write("SYSTem:RWLock")
		else:
			self.cio_write("SYSTem:LOCal")
		return


if __name__ == '__main__':
	def cmd_setvol(hmp4040, argc, argv):
		print argc
		if argc == 4:
			ch = int(argv[1])
			vol = int(argv[2])
			curr = int(argv[3])
		else:
			raise "wrong para"
		hmp4040.set_vol(ch,vol,curr)

	def cmd_lock(hmp4040, argc, argv):
		if argc == 2:
			value = int(argv[1])
			hmp4040.lock(value)
		else:
			raise "wrong para"

	from sys import *
	import signal

	def signal_handler(signal, frame):
		sys.exit(0)

	from shell import Shell
	signal.signal(signal.SIGINT, signal_handler)
	hpm4040 = Hmp4040("COM78")
	saddr = ('localhost', 10003)
	shell = Shell(saddr)
	shell.register("setvol", functools.partial(cmd_setvol, hpm4040), "setvol 1 5 2")
	shell.register("lock", functools.partial(cmd_lock, hpm4040), "lock 1/0")

	while True:
		shell.update()

