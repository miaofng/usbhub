#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import time
from pytest import Hostlink

def enum(**enums):
	return type('Enum', (), enums)

mr = enum(
	ready4test	= "D1007",
	ready4scan	= "D1006",
)

mw = enum(
	track		= "D0162", #unit: mm
	mode		= "D1000", #4=>Adjust Track Width
	#scan_ng	= "D1000",
	scan_end	= "D1001", #1 ok, 2 ng

	test_end	= "D1002",
	test_ok		= "D1003",
)

class Fixture(Hostlink):
	def cmd_plc_read(self, argc, argv):
		assert(argc == 2)
		reg = argv[1]
		return self.get(reg)

	def cmd_plc_write(self, argc, argv):
		assert(argc == 3)
		reg = argv[1]
		val = int(argv[2])
		self.set(reg, val)

	def on_event_add(self, tester, name):
		tester.shell.register("plcr", self.cmd_plc_read, "plcr D1000.5")
		tester.shell.register("plcw", self.cmd_plc_write, "plcw D1000 3")

	last_update = time.time()
	def update(self, tester, name):
		now = time.time()
		if now - self.last_update < 0.5:
			#poll error code every 0.5s
			return

		self.last_update = now
		#D98, D99
		ecodes = self.dm_read(98, 2)
		D98 = ecodes[0]
		D99 = ecodes[1]
		if D98 or D99:
			return {"D98": D98, "D99": D99}

	def track(self, width_mm):
		width_mm = (float)(width_mm)
		assert((width_mm >= 80.0) and (width_mm <= 300.0))

		#convert unit from mm
		width = int(width_mm * 10)
		self.set(mw.track, width)
		self.set(mw.mode, 4)

	def __init__(self, port="COM1", baud=115200):
		Hostlink.__init__(self, port, baud)

	def IsReadyForTest(self):
		return self.get(mr.ready4test)

	def IsReadyForScan(self):
		return self.get(mr.ready4scan)

	def test_reset(self):
		#self.set(mw.test_ng, 0)
		self.set(mw.test_end, 0)

	def test_pass(self):
		#self.set(mw.test_ng, 0)
		self.set(mw.test_ok, 1)
		time.sleep(0.010)
		self.set(mw.test_end, 1)

	def test_fail(self):
		#self.set(mw.test_ng, 1)
		self.set(mw.test_ok, 0)
		time.sleep(0.010)
		self.set(mw.test_end, 1)

	def scan_reset(self):
		#self.set(mw.scan_ng, 0)
		#self.set(mw.scan_end, 0)
		self.set(mw.scan_end, 0)

	def scan_pass(self):
		# self.set(mw.scan_ng, 0)
		# time.sleep(0.010)
		# self.set(mw.scan_end, 1)
		self.set(mw.scan_end, 1)

	def scan_fail(self):
		# self.set(mw.scan_ng, 1)
		# time.sleep(0.010)
		# self.set(mw.scan_end, 1)
		self.set(mw.scan_end, 2)
