#!/usr/bin/env python
#coding:utf8

import io
import os
import time
import sys, signal
#import threading
import traceback
#import settings
#import fnmatch
import re
import math
import Queue
import copy

#0.02NPLC	3.0ppm*RANGE	3000reads/s<0.3mS>
#0.06NPLC	1.5ppm*RANGE	1000reads/s<1.0mS>
# 0.2NPLC	0.7ppm*RANGE	0300reads/s<3.3mS>
#   1NPLC	0.3ppm*RANGE	0050reads/s<020mS>
ppm = 1.5

#according to rut board design
bus_mp = 0 #measure
bus_mn = 1
bus_up = 2 #power supply for relay
bus_un = 3

dict_ms = {
	"0"	: 4,#4,
	"1"	: 8,#8,
	"2"	: 16, #16,
	"3"	: 32, #32,
	"4"	: 64, #64,
	"5"	: 128, #128,
	"6"	: 256, #256,
	"7"	: 512,
	"8"	: 1024,
	"9"	: 2048,
}

dict_spec = {
	"0"	: "<",
	"1"	: ">",
	"2"	: 0.01, #+/-1%
	"3"	: 0.03,
	"4"	: 0.05,
	"5"	: 0.10,
	"6"	: 0.20,
	"7"	: 0.30,
	"8"	: 0.40,
	"9"	: 0.50,
}

dict_v = {
	"0" : 28,
	"1"	: 50,
	"2"	: 100,
	"3"	: 250,
	"4"	: 500,
	"5"	: 1000,
}

dict_mA = {
	"0"	: 10,
	"1"	: 20,
	"2"	: 50,
	"3"	: 100,
	"4"	: 200,
	"5"	: 500,
	"6"	: 750,
	"7"	: 1000,
	"8"	: 2000,
}

gftp = re.compile(r"""
	(
		(?P<q0>[\[<].*[>\]])\s*						#[DIODE CHECK] or <Broken loop scan>
		|
		(?P<xx>//\S*).*								#//A405
		|
		(
			(?P<i0>[OLRABXUW])(?P<p0>[\d,N]*)		#LN or A5 or L0140010 or O2,6,10,11
			((?P<i1>G)(?P<p1>[\d]*)|)				#U143G71
		)
		(
			\s*(?P<q1>[\[<].*[>\]])\s*$				#...	<K10>
			|
			\s*$									#...
		)
	)
""", re.X) #re.I

class GvmTimeout(Exception):pass
class Gvm:
	hwen = False #hardware enable
	pmem = []
	dmem = None
	apin = None #pins for hv test

	#dps
	dps_is = None
	dps_lv = None
	dps_hv = None

	#registers
	A = None
	B = None
	L = None #leakage mode settings
	M = None #current mode settings
	N = None #new mode settings

	def ex_O(self, instr):
		return True

	def ex_L(self, instr):
		#L0140010
		p0 = instr.group("p0")
		if p0 == "N":
			self.L["LN"] = True
			return True
		try:
			#ignore spec range setting, only support over(0)
			ms = p0[1]
			ms = dict_ms[ms]
			hv = p0[2]
			hv = dict_v[hv]
			Mohm = int(p0[4:6])
		except:
			self.log_instr_exception(instr)
			return False

		mAmax = hv/Mohm/1000
		if mAmax > 2:
			self.log_instr_exception(instr, "hv current setting should <2mA")

		self.L["type"] = 'L'
		self.L["hv"] = hv
		self.L["min"] = Mohm
		self.L["LN"] = False

		self.L["irt"] = "HVR"
		self.L["dmm"] = "CURR:DC %.3fE-3,%.3fE-9"%(mAmax, mAmax*ppm)
		return True

	def ex_R(self, instr):
		#R0120020
		p0 = instr.group("p0")
		try:
			sr = p0[0] #spec range
			sr = dict_spec[sr]
			ms = p0[1]
			ms = dict_ms[ms]
			mA = p0[2]
			mA = dict_mA[mA]
			exp = int(p0[3])
			val = int(p0[4:7])
		except:
			self.log_instr_exception(instr)
			return False

		min = max = None
		val *= math.pow(10, exp)
		if sr is "<":
			max = val
		elif sr is ">":
			min = val
		else:
			min = val * (1.0 - sr)
			max = val * (1.0 + sr)

		#dmm bank
		if False:
			print instr.string
			print "is = %dmA"%mA
			print "min = "+str(min)+" ohm"
			print "max = "+str(max)+" ohm"

		ohm = max
		sign = "<"
		if ohm is None:
			ohm = min
			sign = ">"

		vmax = mA * ohm / 1000.0
		bank = 10.0

		if vmax > 12.0:
			emsg = "Current Source Voltage Over-range(%dmA,%s%.0fohm)"%(mA, sign, ohm)
			self.log_instr_exception(instr, emsg)
			#return False
			vmax = 10.0
		elif vmax > 0.9:
			bank = 10.0
		elif vmax > 0.09:
			bank = 1.0
		else:
			bank = 0.1

		self.N["type"] = 'R'
		self.N["ms"] = ms
		self.N["mA"] = mA
		self.N["min"] = min
		self.N["max"] = max

		#instr config
		self.N["irt"] = "W4R"
		self.N["arm"] = 2
		self.N["dmm"] = "VOLT:DC %.3f,%.3fE-6"%(bank, bank * ppm)
		#print self.N["dmm"]
		self.mode()
		return True

	def ex_A(self, instr):
		try:
			#A207		<KL30>
			p0 = instr.group("p0")
			pin = int(p0) - 1
			assert pin >= 0
		except:
			self.log_instr_exception(instr)
			return False

		self.A = pin
		if not self.L["LN"]:
			self.apin.put(pin)

		return True

	def ex_B(self, instr):
		try:
			#	B122	<F25>
			p0 = instr.group("p0")
			pin = int(p0) - 1
			assert pin >= 0
		except:
			self.log_instr_exception(instr)
			return False

		self.B = pin
		self.measure()
		return True

	def ex_X(self, instr):
		#disconnect all lines on power bus
		if self.hwen:
			self.irt.switch("OPEN", bus_up, 0, 2047)
			self.irt.switch("OPEN", bus_un, 0, 2047)
		return True

	def ex_U(self, instr):
		try:
			#U222G181
			i1 = instr.group("i1")
			p0 = instr.group("p0")
			p1 = instr.group("p1")

			assert i1 is "G"
			line_pwr = int(p0)
			line_gnd = int(p1)
		except:
			self.log_instr_exception(instr)
			return False

		if self.hwen:
			self.irt.switch("CLOS", bus_up, line_pwr)
			self.irt.switch("CLOS", bus_un, line_gnd)
		return True

	def ex_W(self, instr):
		return True

	def log(self, info, passed=None):
		line = "%-64s"%info
		if passed == True:
			line = line + " [PASS]"
		elif passed == False:
			line = line + " [FAIL]"
		else:
			pass

		print line

	def log_instr_exception(self, instr, emsg = None):
		if emsg is None:
			emsg = "instruction exception"
		emsg = "%s...%s"%(instr.string, emsg)
		self.log(emsg, False)

	def unitconv(self, v):
		unit_list = [["T", 1.0e12], ["G", 1.0e9], ["M", 1.0e6], ["K", 1.0e3], ["", 1.0e0]]
		for unit in unit_list:
			min = unit[1]
			if abs(v) > min:
				v /= min
				break
		if unit[0] == "T":
			#over-range
			v = 999.9
		return v, unit[0]

	def report(self, measure, result):
		A = measure["A"]
		B = measure["B"]
		type = measure["type"]
		if "diode" in measure:
			type = "D"

		if type is "R":
			result = result * 1000 / measure["mA"]
			v, unit = self.unitconv(result)
			unit += "Ohm"
		elif type is "D":
			v, unit = self.unitconv(result)
			unit += "V"
		else:
			result = measure["hv"] / result
			v, unit = self.unitconv(result)
			unit += "Ohm"

		passed = True
		min_str = max_str = "-"
		if measure["min"]:
			min = measure["min"]
			passed = passed and (result >= min)
			min, min_unit = self.unitconv(min)
			min_str = "%.1f%s"%(min, min_unit)
		if measure["max"]:
			max = measure["max"]
			passed = passed and (result <= max)
			max, max_unit = self.unitconv(max)
			max_str = "%.1f%s"%(max, max_unit)

		#R(123, 445) = 17.1K
		line = "%s(%4d, %4d) = %8.01f %-4s"%(type, A+1, B+1, v, unit)
		if type == "R" or type == "D":
			line += "  <%3dmA, %6s, %6s>"%(measure["mA"], min_str, max_str)

		self.log(line, passed)

	def readall(self):
		if not self.hwen:
			return
		deadline = None
		while not self.dmem.empty():
			time.sleep(0.1)
			npoints = self.dmm.poll()
			if npoints > 0:
				if npoints > 20:
					npoints = 20 #to avoid pyvisa timeout err
				deadline = time.time() + self.M["ms"] / 1000 + 0.5
				results = self.dmm.read(npoints)
				for result in results:
					measure = self.dmem.get(False)
					self.report(measure, result)

			if self.dmem.empty():
				#:)
				break

			if deadline is None:
				deadline = time.time() + self.M["ms"] / 1000 + 0.5

			if time.time() > deadline:
				#:(
				raise GvmTimeout

	def reset(self):
		#only affect register & dmem_r/w
		self.A = self.B = None
		self.L = {}
		self.M = {}
		self.N = {}
		self.dmem = Queue.Queue()
		self.apin = Queue.Queue()

		if not self.hwen:
			return

		#instrument reset
		self.irt.pipeline(True)
		self.dmm.trig_ext(slope="POS", sdelay = 0)

	def close(self):
		if not self.hwen:
			return

		self.irt.pipeline(False)
		self.dmm.stop()

	def mode(self):
		if len(self.M) is 0:
			self.M = { "irt": None, "dmm": None, "arm": None, "ms": None}

		if not self.hwen:
			self.M = self.N
			self.N = {}
			return

		xirt = self.N["irt"] != self.M["irt"]
		xdmm = self.N["dmm"] != self.M["dmm"]
		if xirt or xdmm:
			#print "#########################"
			#all data inside dmm will lost
			self.readall()
			self.dmm.stop()
			if xirt:
				xdmm = True
				self.dmm.config("VOLT:DC AUTO")
				self.irt.mode(self.N["irt"])
			if xdmm:
				self.dmm.config(self.N["dmm"])
				self.dmm.query("SENSE:VOLT:DC:ZERO:AUTO 0")
				self.dmm.error_check()
			self.dmm.start()

		if self.N["arm"] != self.M["arm"]:
			self.irt.arm(self.N["arm"])

		if self.N["ms"] != self.M["ms"]:
			self.irt.mdelay(self.N["ms"])

		#set up dps
		if "mA" in self.N:
			is_A = self.N["mA"] / 1000.0
			if is_A != self.dps_is:
				self.dps_is = is_A
				self.irt.query("POWER IS %.3f"%is_A)

		self.M = self.N
		self.N = {}

	def measure(self):
		measure = self.M
		measure["A"] = self.A
		measure["B"] = self.B
		measure = copy.copy(measure)
		self.dmem.put(measure)

		if self.hwen:
			self.irt.switch("SCAN", bus_mp, self.A)
			self.irt.switch("SCAN", bus_mn, self.B)

	def __init__(self, irt=None, dmm=None):
		self.executers = {}
		self.executers["O"] = self.ex_O
		self.executers["L"] = self.ex_L
		self.executers["R"] = self.ex_R
		self.executers["A"] = self.ex_A
		self.executers["B"] = self.ex_B
		self.executers["X"] = self.ex_X
		self.executers["U"] = self.ex_U
		self.executers["W"] = self.ex_W
		self.irt = irt
		self.dmm = dmm

	def run(self, hwen=False):
		self.hwen = hwen
		self.reset()

		passed = True
		#low voltage open/short/resistor/diode/relay tests
		for instr in self.pmem:
			timer = time.time()
			passed &= self.lvtest(instr)
			timer = time.time() - timer
			#print "GVM: LVTEST = %.3f S"%timer

		self.readall()

		#high voltage leakage current test
		if passed:
			passed = self.hvtest()

		self.close()
		return passed

	def hvtest(self):
		pass

	def lvtest(self, instr):
		passed = False
		opcode = instr.group('i0')
		if opcode:
			if opcode in self.executers:
				func = self.executers[opcode]
				passed = func(instr)
			else:
				self.log_instr_exception(instr)
				passed = False
		else:
			square = instr.group("q0") #like: [DIODE CHECK]
			if square:
				if square == "[DIODE CHECK]":
					self.N["diode"] = True
				elif square == "[DIODE END]":
					self.N["diode"] = False
				elif square[0] == "[":
					self.log_instr_exception(instr, "Not Supported")
					passed = False
		return passed

	def load(self, path):
		#return None when success or last error
		self.pmem = []

		emsg = None
		gft = open(path, 'r')
		for line in gft.readlines():
			line = line.strip(' \t\n\r')
			if line:
				line = str.upper(line)
				matched = gftp.match(line)
				if matched:
					self.pmem.append(matched)
				else:
					emsg = "line%04d: %s...syntax error"%(i, line)
					self.log(emsg, False)
		gft.close()
		if emsg:
			self.pmem = [] #clean all

		return emsg

	def load_from_string(self, gft):
		self.pmem = []
		emsg = None

		lines = re.split("[\r\n]+", gft)
		for line in gft.readlines():
			line = line.strip(' \t\n\r')
			if line:
				line = str.upper(line)
				matched = gftp.match(line)
				if matched:
					self.pmem.append(matched)
				else:
					emsg = "line%04d: %s...syntax error"%(i, line)
					self.log(emsg, False)
		if emsg:
			self.pmem = []

		return emsg

	def scan(self, start = 0, end = 511):
		self.dmm.stop()
		self.dmm.trig_ext(slope="POS", sdelay = 0)
		self.dmm.config("FRES 100,MAX")
		self.dmm.start()
		self.irt.pipeline(True)
		self.irt.mode("OFF")
		self.irt.mode("RPB")
		self.irt.arm(1)
		self.irt.mdelay(4)
		self.irt.switch("SCAN", bus_mp, start, end)
		measure = {
			"A": None,
			"B": -1, #probe pin
			"type": "R",
			"mA": 1,
			"min": None,
			"max": 20.0, #unit: ohm
		}

		line = 0
		deadline = None
		while True:
			time.sleep(0.1)
			npoints = self.dmm.poll()
			if npoints > 0:
				deadline = time.time() + 0.5
				results = self.dmm.read(npoints)
				for result in results:
					measure["A"] = line
					result = result / 1000 #trick: measure["mA"] = 1
					self.report(measure, result)
					line = line + 1

			if deadline is None:
				deadline = time.time() + 0.5
			if line >= end:
				break
		self.irt.pipeline(False)

	def cal_is_init(self):
		self.dmm.stop()
		self.dmm.measure_dcv()
		self.irt.mode("OFF")
		self.irt.query("relay 17,16,13", False)
		self.irt.query("POWER HS ON")
		self.irt.query("POWER HS 12.0")

	def cal_is_measure(self, is_set):
		self.irt.query("POWER IS %.3f"%is_set)
		is_get = self.dmm.measure_dci()
		is_get = float(is_get)
		return is_get

	def cal_lv_init(self):
		self.dmm.stop()
		self.dmm.measure_dcv()
		self.irt.mode("OFF")
		self.irt.query("relay 26,16,18", False)
		self.irt.query("POWER LV ON")

	def cal_lv_measure(self, lv_set):
		self.irt.query("POWER LV %.3f"%lv_set)
		lv_get = self.dmm.measure_dcv()
		lv_get = float(lv_get)
		return lv_get

	def dump_pmem(self):
		for instr in self.pmem:
			print "\nline: %s"%instr.string
			print "i0: %s"%instr.group("i0")
			print "p0: %s"%instr.group("p0")
			print "i1: %s"%instr.group("i1")
			print "p1: %s"%instr.group("p1")
			print "q0: %s"%instr.group("q0")
			print "q1: %s"%instr.group("q1")
			print "xx: %s"%instr.group("xx")

if __name__ == "__main__":
	from sys import *
	import signal
	from dmm import Dmm
	from matrix import Matrix

	irt = Matrix("COM6")
	dmm = Dmm()
	gvm = Gvm(irt, dmm)

	argc = len(argv)
	if argc > 1:
		subcmd = argv[1]
		if (subcmd == "run") or (subcmd == "try"):
			fname = "./sample.gft"
			if argc > 2:
				fname = argv[2]

			gvm.load(fname)
			#gvm.dump_pmem()
			timer = time.time()
			gvm.run(subcmd == "run")
			timer = time.time() - timer
			print "Test Finished In %.1f S"%(timer)
			sys.exit(0)
		elif subcmd == "scan":
			line_start = 0
			line_end = 511
			if argc > 2:
				line_start = int(argv[2]) - 1
			if argc > 3:
				line_end = int(argv[3]) - 1
			timer = time.time()
			gvm.scan(line_start, line_end)
			timer = time.time() - timer
			print "Test Finished In %.1f S"%(timer)
			sys.exit(0)
		elif subcmd == "cal_is":
			start = 0.00
			end = 0.20
			N = 20
			if argc > 2:
				start = float(argv[2])
			if argc > 3:
				end = float(argv[3])
			if argc > 4:
				N = int(argv[4])

			gvm.cal_is_init()
			for i in range(0, N):
				is_set = start + i*(end - start)/N
				is_get = gvm.cal_is_measure(is_set)

				is_set += 0.00000001
				delta = (is_get - is_set) / is_set * 100
				print "CAL: %8.3f => %8.3f A, %8.1f%%" % (is_set, is_get, delta)
			sys.exit(0)
		elif subcmd == "cal_lv":
			start = 4.00
			end = 24.00
			if argc > 2:
				start = float(argv[2])
			if argc > 3:
				end = float(argv[3])

			gvm.cal_lv_init()
			for i in range(0, 20):
				lv_set = start + i*(end - start)/20
				lv_get = gvm.cal_lv_measure(lv_set)

				lv_set += 0.00000001
				delta = (lv_get - lv_set) / lv_set * 100
				print "CAL: %8.3f => %8.3f V, %8.1f%%" % (lv_set, lv_get, delta)
			sys.exit(0)
		elif subcmd == "query":
			cmdline = argv[2:]
			cmdline = " ".join(cmdline)
			irt.query(cmdline)
			print "Q: %s"%cmdline
			print "A: %s"%irt.echo
			sys.exit(0)

	print "gvm.py try [xx.gft]				for syntax check only"
	print "gvm.py run [xx.gft]"
	print "gvm.py measure A B				measure R(A,B)"
	print "gvm.py scan [start [end]]		measure R(line_x, probe)"
	print "gvm.py cal_is [start [end [N]]]	dps is calibration, unit: A"
	print "gvm.py cal_lv [start [end [N]]]	dps lv calibration, unit: V"
	print "gvm.py query cmdline				irt cmd query"
