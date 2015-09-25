#!/usr/bin/env python
#coding:utf8

import io
import time
import os
import sys, signal
from shell import Shell
from db import Db
import serial

class ScannerException(Exception): pass

class Scanner:
	uart = None
	data = ''

	def __init__(self, port, baud = 115200):
		if not swdebug:
			self.uart = serial.Serial(port, baud)

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
		self.data = self.data[x:]
		return data
