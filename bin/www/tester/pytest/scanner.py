#!/usr/bin/env python
#coding:utf8

import io
import time
import os
import sys, signal
import serial
import serial.tools.list_ports
from instrument import Instrument

class ScannerException(Exception): pass

class Scanner(Instrument):
	uart = None
	data = ''

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port = None, baud = 115200):
		self.uart = serial.Serial(port, baud)

	def __del__(self):
		self.release()

	def search(self, key=""):
		port_list = list(serial.tools.list_ports.comports())
		for item in port_list:
			port = item[0]
			desc = item[1]
			if key in desc:
				return port

	def _read(self):
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

	def read(self, timeout = 0, count = 3):
		if timeout is 0:
			return self._read()

		for tries in range(count):
			if hasattr(self, "trig"):
				self.trig()

			deadline = time.time() + timeout
			while time.time() < deadline:
				barcode = self._read()
				if barcode:
					return barcode

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


