#!/usr/bin/env python
#coding:utf8

import io
import time
import os
import sys, signal
import serial

class ScannerException(Exception): pass

class Scanner:
	uart = None
	data = ''

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port, baud = 115200):
		self.uart = serial.Serial(port, baud)

	def __del__(self):
		self.release()

	def read(self):
		nbytes = self.uart.inWaiting()
		if nbytes > 0:
			data = self.uart.read(nbytes)
			self.data = self.data + data

		idx = self.data.find('\r')
		if idx < 0:
			return

		data = self.data[0:idx]
		idx = idx + 1
		self.data = self.data[idx:]
		return data

if __name__ == '__main__':
	from shell import Shell
	from db import Db
	import settings

	def signal_handler(signal, frame):
		sys.exit(0)

	scanner = Scanner(settings.scanner_port)
	while True:
		barcode = scanner.read()
		if barcode:
			print barcode


