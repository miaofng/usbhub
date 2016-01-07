#!/usr/bin/env python
#coding:utf8

import io
import time
from scanner import *

class Fs36(Scanner):
	uart = None
	data = ''

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port = None, baud = 115200):
		if port is None:
			port = self.search("Honeywell N5600")

		Scanner.__init__(self, port, baud)

	def trig(self):
		self.data = ''
		self.uart.flushInput()
		self.uart.write("\x16T\r")

if __name__ == '__main__':
	import os
	import sys, signal

	scanner = Fs36()
	while True:
		barcode = scanner.read(1)
		if barcode:
			print list(barcode)
		time.sleep(3)


