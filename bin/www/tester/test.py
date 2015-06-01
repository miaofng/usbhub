#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal

class Test:
	def __init__(self, tester):
		self.flag_stop = "OFF"
		self.tester = tester

	def update(self):
		self.tester.update()

	def mdelay(self, ms):
		now = time.time();
		now = now + ms / 1000.0
		while time.time() < now:
			self.update()

	def stop(self):
		self.flag_stop = "ON"

	def run(self):
		while True:
			self.tester.barcode_get();
			self.tester.start()
			self.mdelay(5000)
			self.tester.passed();
			if self.flag_stop == 'ON':
				return



