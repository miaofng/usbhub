#!/usr/bin/env python
#coding:utf8
#programmable power supply HMP4040
#xulijun@2015-9-23 initial version

import serial #http://pythonhosted.org/pyserial/
import functools
import io
import time

class HmpOutputError(Exception): pass
class HmpEchoTimeout(Exception): pass

class Hmp4040:
	timeout = 1 #unit S
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

		self.idn = self.query("*idn?")
		self.reset()
		self.cls()

	#auto add eol
	def query(self, cmdline, eol = '\n'):
		self.uart.flushInput()
		self.uart.write(cmdline + eol)
		time.sleep(0.05)

	#auto remove eol
	def readline(self, eol = "\n"):
		linebuf = ""
		deadline = time.time() + self.timeout
		while True:
			if time.time() > deadline:
				raise HmpEchoTimeout

			nbytes = self.uart.inWaiting()
			if nbytes > 0:
				data = self.uart.read(nbytes)
				linebuf = linebuf + data

				idx = linebuf.find(eol)
				if idx >= 0:
					result = linebuf[:idx]
					return result

	def reset(self):
		self.query("*rst")
	def cls(self):
		self.query("*cls")
	def err(self):
		#such as: -230,"Data stale"
		self.query("system:err?")
		return self.readline()

	def set_vol(self, ch, vset, curr):
		self.query("INST OUT%d"%ch)
		self.query("INST?")
		echo = self.readline()
		if len(echo) != 6 or int(echo[4:5]) != ch:
			print echo
			raise HmpOutputError

		self.query("APPLY %f,%f"%(vset,curr))
		time.sleep(0.5)
		self.query("APPLy?")
		echo = self.readline()
		[vget, iget] = echo.split(",")
		vget = float(vget)
		delta = abs(vget - vset)
		if delta > 0.1:
			raise HmpOutputError

		self.query("OUTP ON")

	def output_en(self,ch,en):
		self.query("INST OUT%d"%ch)
		if en:
			self.query("OUTP ON")
		else:
			self.query("OUTP OFF")

	def lock(self,en):
		if en:
			self.query("SYSTem:RWLock")
		else:
			self.query("SYSTem:LOCal")
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

