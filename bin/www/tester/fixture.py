#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import time
from pytest import Pci1761

def enum(**enums):
	return type('Enum', (), enums)

di = enum(
	test_start = 0,
	scan_start = 1
)

do = enum(
	test_end = 0,
	test_ng = 1,
	scan_end = 2,
	scan_ng = 3
)

class Fixture(Pci1761):
	def IsReadyForTest(self):
		return self.get(di.test_start)

	def IsReadyForScan(self):
		return self.get(di.scan_start)

	def test_reset(self):
		self.set(do.test_ng, 0)
		self.set(do.test_end, 0)
		
	def test_pass(self):
		self.set(do.test_ng, 0)
		time.sleep(0.010)
		self.set(do.test_end, 1)

	def test_fail(self):
		self.set(do.test_ng, 1)
		time.sleep(0.010)
		self.set(do.test_end, 1)
		
	def scan_reset(self):
		self.set(do.scan_ng, 0)
		self.set(do.scan_end, 0)

	def scan_pass(self):
		self.set(do.scan_ng, 0)
		time.sleep(0.010)
		self.set(do.scan_end, 1)

	def scan_fail(self):
		self.set(do.scan_ng, 1)
		time.sleep(0.010)
		self.set(do.scan_end, 1)
