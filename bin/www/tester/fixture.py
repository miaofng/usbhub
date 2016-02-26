#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import time
from pytest import Hostlink

def enum(**enums):
	return type('Enum', (), enums)

mr = enum(
	wastecount = "D95",
	ready4test	= "D96.01",
	ready4scan	= "D96.03",
	estop = "D96.05",
	raster = "D96.06",
	wastefull = "D96.07",
)

mw = enum(
	scan_ng		= "D1000",
	scan_end	= "D1001",

	test_ng		= "D1002",
	test_end	= "D1003",

	#cyclinder action
	mode		= "D1007", #1 => manual ctrl, 2 => auto
	forward		= "D1100",
	backward	= "D1101",
	down		= "D1102",
	up			= "D1103",

	point		= "D1104",
	point_back	= "D1105",

	light		= "D1200",
	waste_door	= "D1201",
)

class Fixture(Hostlink):
	def cmd_plc_read(self, argc, argv):
		assert(argc == 2)
		reg = argv[1]
		return self.get(reg)

	def cmd_plc_write(self, argc, argv):
		assert(argc == 3)
		self.mode("manual")
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

	_mode_ = ""
	def mode(self, mode = "auto"):
		if mode != "auto":
			mode = "manual"

		if self._mode_ != mode:
			self._mode_ = mode
			modes = {"auto": 2, "manual": 1}
			self.set(mw.mode, modes[mode])

	def __init__(self, port="COM1", baud=115200):
		Hostlink.__init__(self, port, baud)
		self.mode("auto")

	def IsReadyForTest(self):
		return self.get(mr.ready4test)

	def IsReadyForScan(self):
		return self.get(mr.ready4scan)

	def test_reset(self):
		self.set(mw.test_ng, 0)
		self.set(mw.test_end, 0)

	def test_pass(self):
		self.set(mw.test_ng, 0)
		time.sleep(0.010)
		self.set(mw.test_end, 1)

	def test_fail(self):
		self.set(mw.test_ng, 1)
		time.sleep(0.010)
		self.set(mw.test_end, 1)

	def scan_reset(self):
		self.set(mw.scan_ng, 0)
		self.set(mw.scan_end, 0)

	def scan_pass(self):
		self.set(mw.scan_ng, 0)
		time.sleep(0.010)
		self.set(mw.scan_end, 1)

	def scan_fail(self):
		self.set(mw.scan_ng, 1)
		time.sleep(0.010)
		self.set(mw.scan_end, 1)
