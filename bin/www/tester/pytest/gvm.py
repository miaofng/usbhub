#!/usr/bin/env python
#coding:utf8
# 1, probe: soft trig => report() => log()
# 2, scan/fscn: scan trig => report() => log()

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
import random
import json
import numpy as np
#from instrument import Instrument
#from test import Test

#0.02NPLC	3.0ppm*RANGE	3000reads/s<0.3mS>
#0.06NPLC	1.5ppm*RANGE	1000reads/s<1.0mS>
# 0.2NPLC	0.7ppm*RANGE	0300reads/s<3.3mS>
#   1NPLC	0.3ppm*RANGE	0050reads/s<020mS>
ppm = 1

#according to rut board design
bus_mp = 0 #measure
bus_mn = 1
bus_up = 2 #power supply for relay
bus_un = 3

dict_range = {
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

dict_ms = {
	"0"	: 16,
	"1"	: 32,
	"2"	: 64,
	"3"	: 128,
	"4"	: 256,
	"5"	: 512,
	"6"	: 1000,
	"7"	: 2000,
	"8"	: 4000,
	"9"	: 8000,
}

dict_v = {
	"0" : 28,
	"1"	: 50,
	"2"	: 100,
	"3"	: 250,
	"4"	: 500,
	#newly added
	"5"	: 750,
	"6"	: 1000,
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
	#newly added
	"8"	: 1500,
	"9"	: 2000,
}

gftp = re.compile(r"""
	(
		(?P<q0>[\[<].*[>\]])\s*						#[DIODE CHECK] or <Broken loop scan>
		|
		(?P<xx>//\S*).*								#//A405
		|
		(
			(?P<i0>[OLRABXUW])(?P<p0>[\d,NX]*)		#LN or A5 or L0140010 or O2,6,10,11
			((?P<i1>G)(?P<p1>[\d]*)|)				#U143G71
		)
		(
			\s*(?P<q1>[\[{<].*[>}\]])\s*$				#...	<K10>
			|
			\s*$									#...
		)
	)
""", re.X) #re.I

class GvmTimeout(Exception):pass
class GvmPwrError(Exception):pass
class GvmCalError(Exception):pass
class GvmSyntaxError(Exception):pass

class Gvm():
	#16mS->4mS, 32mS->8mS
	ms_fast_factor = 1
	passed = True
	ecode = 0

	diode = False
	hwen = False #hardware enable
	pmem = []
	dmem = None
	apin = None #pins for hv test
	pins = [] #missed pin search
	#epin = {} #bad apins of hv

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

	def __init__(self, db = None, mask = None):
		self.hwen = False
		self.hven = True
		self.hvtravel = True
		self.db = db
		if db:
			dpsCal = self.db.cfg_get("dpsCal")
			self.dpsCal = json.loads(dpsCal)
			hven = self.db.cfg_get("hvtest")
			hvtravel = self.db.cfg_get("hvtravel")
			self.hven = bool(int(hven))
			self.hvtravel = bool(int(hvtravel))

		self.mask = mask
		self.executers = {}
		self.executers["O"] = self.ex_O
		self.executers["L"] = self.ex_L
		self.executers["R"] = self.ex_R
		self.executers["A"] = self.ex_A
		self.executers["B"] = self.ex_B
		self.executers["X"] = self.ex_X
		self.executers["U"] = self.ex_U
		self.executers["W"] = self.ex_W

	def Connect(self, irt = None, dmm = None):
		self.hwen = False
		if irt:
			self.hwen = True
			self.dmm = dmm
			self.irt = irt
			irt.__reset__()

	def start(self):
		#only affect register & dmem_r/w
		self.A = self.B = None
		self.L = {"LN": False, }
		self.M = {}
		self.N = {}
		self.dmem = Queue.Queue()
		self.apin = []
		self.pins = []
		#self.epin = {}

		if not self.hwen:
			return

		#instrument reset
		self.irt.query("POWER HS 12.0")
		self.irt.query("POWER HS ON")
		self.power("LV", 12.0)
		self.irt.query("POWER LV ON")
		self.dps_lv = 12.0
		if self.hven:
			self.power("HV", 5.0)
			self.dps_hv = 5.0
		self.power("IS", 0.001)
		self.dps_is = 0.001
		self.irt.pipeline(True)
		self.dmm.stop()
		self.dmm.trig_ext(slope="POS", sdelay = 0)

	def stop(self):
		if not self.hwen:
			return

		self.irt.pipeline(False)
		if self.hven:
			self.power("HV", 5.0)
		self.dmm.stop()

	dps_banks = [
		{"dps": "HV", "cal": "HV_0100", "min": 0, "max": 99},
		{"dps": "HV", "cal": "HV_1000", "min": 99, "max": 1000},
		{"dps": "LV", "cal": "LV_0024", "min": 2, "max": 25},
		{"dps": "IS", "cal": "IS_0025", "min": 0.001*0.9, "max": 0.025*0.9},
		{"dps": "IS", "cal": "IS_0100", "min": 0.025*0.9, "max": 0.100*0.9},
		{"dps": "IS", "cal": "IS_0500", "min": 0.100*0.9, "max": 0.500*0.9},
		{"dps": "IS", "cal": "IS_1500", "min": 0.500*0.9, "max": 2.000},
	]

	def power(self, dps, val):
		for bank in self.dps_banks:
			matched = bank["dps"] == dps
			matched &= val > bank["min"]
			matched &= val <= bank["max"]
			if matched:
				#got it ..
				if not hasattr(self, "dpsCal"):
					self.irt.query("POWER %s %.3f"%(dps, val))
					return

				bank_name = bank["cal"]
				cal_ok = False
				prefix = bank_name + "_passed"
				if prefix in self.dpsCal:
					cal_ok = self.dpsCal[prefix]

				if not cal_ok:
					raise GvmCalError

				if bank_name in self.dpsCal:
					coeff = self.dpsCal[bank_name]
					p = np.poly1d(coeff)
					self.irt.query("POWER %s %.3f"%(dps, p(val)))
					return
				else:
					raise GvmCalError

		#bank not found :(
		raise GvmPwrError

	#this routine is introduced to avoid UI been stucked
	#when leakage test with large nr of points. readall()
	#is called in advance to get the test result then
	#update the UI display
	def Switch(self, opt, bus0, line0, line1=None, bus1=None):
		deadline = time.time() + 10.0
		while True:
			try:
				self.irt.switch(opt, bus0, line0, line1, bus1)
				break
			except Queue.Full:
				qsz = self.dmem.qsize()
				self.readall(qsz / 10)

			#timeout error to avoid deadlock
			#should not reach here!
			assert(time.time() < deadline)

	def AddMeasure(self, sub = None):
		ofs = 0
		if sub:
			ofs = sub["ofs"]

		A = self.A
		B = self.B

		if isinstance(A, list):
			A = np.array(A) + ofs
			A = A.tolist()
		else:
			A = A + ofs

		if isinstance(B, list):
			B = np.array(B) + ofs
			B = B.tolist()
		else:
			B = B + ofs

		measure = self.M
		measure["A"] = A
		measure["B"] = B
		measure = copy.copy(measure)
		measure["sub"] = sub
		self.dmem.put(measure)

		if not self.hwen:
			return

		if isinstance(B, list):
			#to avoid change ARM, static switch method is used
			#so we need to open all first
			self.irt.open_all_lines(bus_mp)
			self.irt.open_all_lines(bus_mn)
			for line in A:
				self.Switch("CLOS", bus_mp, line)
			for line in B:
				self.Switch("CLOS", bus_mn, line)
			#self.irt.trig()
			self.Switch("SCAN", bus_mp, A[0])
			self.Switch("SCAN", bus_mn, B[0])
		else:
			self.Switch("SCAN", bus_mp, A)
			self.Switch("SCAN", bus_mn, B)

	def mode(self):
		if not self.M:
			self.M = {
				"irt": None,
				"dmm": None,
				"arm": None,
				"ms": None
			}

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

		xarm = self.N["arm"] != self.M["arm"]
		if xarm:
			self.readall()
			self.irt.arm(self.N["arm"])

		xms = self.N["ms"] != self.M["ms"]
		if xms:
			self.readall()
			self.irt.mdelay(self.N["ms"] * self.ms_fast_factor)

		#set up dps
		if "mA" in self.N:
			is_A = self.N["mA"] / 1000.0
			xis = is_A != self.dps_is
			if xis:
				self.readall()
				self.dps_is = is_A
				self.power("IS", is_A)

		if "hv" in self.N:
			hv = self.N["hv"]
			xhv = hv != self.dps_hv
			if xhv:
				self.readall()
				self.dps_hv = hv
				self.power("HV", hv)

		if "lv" in self.N:
			lv = self.N["lv"]
			xlv = lv != self.dps_lv
			if xlv:
				self.readall()
				self.dps_lv = lv
				self.power("LV", lv)

		#time.sleep(0.1)
		if self.diode:
			self.N["diode"] = True
		self.M = self.N
		self.N = {}

	def ex_O(self, instr):
		p0 = instr.group("p0")
		self.hven &= "11" in p0
		return True

	def ex_L(self, instr):
		#L0(over)1(mS)4(hv)0(exp)010(Mohm)
		p0 = instr.group("p0")
		q1 = instr.group("q1")
		if p0 == "N":
			self.L["LN"] = True
			return True
		try:
			#!!!ignore spec range setting, only support 0(over)
			ms = p0[1]
			ms = dict_ms[ms]
			hv = p0[2]
			hv = dict_v[hv]
			Mohm = int(p0[4:7])

			if q1 and q1[0] is "{":
				modifier = json.loads(q1)
				if "HV" in modifier:
					hv = modifier["HV"] * 1.0
		except:
			self.log_instr_exception(instr)

		#uAmax = hv*1.0/Mohm
		#if uAmax > 2000:
		#	self.log_instr_exception(instr, "hv current setting should <2mA")
		# if uAmax > 1000:
			# bank = 10.0
		# elif uAmax > 100:
			# bank = 1.0
		# else:
			# bank = 0.1 #unit: mA

		#fixed to 1.0mA bank
		bank = 1.0

		self.L["type"] = 'L'
		self.L["ms"] = ms
		self.L["hv"] = hv
		self.L["min"] = Mohm * 1E6
		self.L["max"] = None
		self.L["LN"] = False

		self.L["irt"] = "HVR"
		self.L["arm"] = 2
		#self.L["dmm"] = "CURR:DC %.3fE-3,%.3fE-9"%(bank, bank*ppm)
		self.L["dmm"] = "CURR:DC %.3fE-3 "%bank
		#self.N = self.L
		#self.mode()
		return True

	def ex_R(self, instr):
		#R0(range)1(mS)2(mA)0(exp)020(value) {"IS": 0.010, "LV": 12.0}
		p0 = instr.group("p0")
		q1 = instr.group("q1")
		try:
			sr = p0[0] #spec range
			sr = dict_range[sr]
			ms = p0[1]
			ms = dict_ms[ms]
			mA = p0[2]
			mA = dict_mA[mA]
			exp = int(p0[3])
			val = int(p0[4:7])

			if q1 and q1[0] is "{":
				modifier = json.loads(q1)
				if "IS" in modifier:
					mA = modifier["IS"] * 1000
				if "LV" in modifier:
					lv = modifier["LV"] * 1.0
					self.N["lv"] = lv

		except:
			self.log_instr_exception(instr)

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
			#emsg = "Current Source Voltage Over-range(%dmA,%s%.0fohm)"%(mA, sign, ohm)
			#self.log_instr_exception(instr, emsg)
			vmax = 10.0
		elif vmax > 0.9:
			bank = 10.0
		elif vmax > 0.09:
			bank = 1.0
		else:
			bank = 0.1

		if self.diode:
			bank = 10.0

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

		self.A = pin
		self.pins.append(pin)
		if not self.L["LN"]:
			self.apin.append(pin)
			for sub in self.subs:
				self.apin.append(pin + sub["ofs"])

		return True

	def ex_B(self, instr):
		try:
			#	B122	<F25>
			p0 = instr.group("p0")
			pin = int(p0) - 1
			assert pin >= 0
		except:
			self.log_instr_exception(instr)

		self.B = pin
		self.pins.append(pin)
		self.AddMeasure()
		for sub in self.subs:
			self.AddMeasure(sub)
		return True

	def ex_X(self, instr):
		#disconnect all lines on power bus
		if self.hwen:
			self.irt.open_all_lines(bus_up)
			self.irt.open_all_lines(bus_un)
		return True

	def ex_U(self, instr):
		try:
			#U222G181
			i1 = instr.group("i1")
			p0 = instr.group("p0")
			p1 = instr.group("p1")

			assert i1 is "G"
			line_pwr = int(p0) - 1
			line_gnd = int(p1) - 1
		except:
			self.log_instr_exception(instr)

		self.pins.append(line_pwr)
		self.pins.append(line_gnd)
		if self.hwen:
			self.Switch("CLOS", bus_up, line_pwr)
			self.Switch("CLOS", bus_un, line_gnd)
			for sub in self.subs:
				self.Switch("CLOS", bus_up, line_pwr + sub["ofs"])
				self.Switch("CLOS", bus_un, line_gnd + sub["ofs"])
		return True

	def ex_W(self, instr):
		p0 = instr.group("p0")
		q1 = instr.group("q1")
		try:
			ms = p0[0]
			ms = dict_ms[ms]
			if q1 and q1[0] is "{":
				modifier = json.loads(q1)
				if "WAIT" in modifier:
					ms = modifier["WAIT"] * 1000
		except:
			self.log_instr_exception(instr)

		deadline = time.time() + ms / 1000.0
		self.readall()
		tick = 0
		waitpoint = False
		while time.time() < deadline:
			time.sleep(0.016)
			tick += 0.016
			if waitpoint is False:
				if tick > 1.5:
					tick -= 1.5
					waitpoint = True
					self.log("waiting ....", None, "")
			else:
				if tick > 0.5:
					tick -= 0.5
					self.log(".", None, "")

		if waitpoint:
			self.log("")

		return True

	def Run(self):
		self.start()
		self.passed = True
		self.ecode = 0

		for instr in self.pmem:
			self.lvtest(instr)

		self.readall()
		passed = self.passed;

		if self.hven and len(self.apin) > 0:
			self.passed = True
			if "type" in self.L:
				self.log("")
				self.PassTest(self.L, self.apin)
				self.readall()

				#hv test fail??
				if self.hvtravel and not self.passed:
					self.log("Search For Leakage Failed Pins:")
					self.Travel(self.L, self.apin)

		passed &= self.passed
		self.stop()

		pins = list(set(self.pins))
		pins = np.array(pins) + 1
		pins = pins.tolist()
		self.log("%d pins in total: %s"%(len(pins), str(pins)))
		self.log("Test Finished", passed)

		if passed:
			return passed
		else:
			ecode = -1 - self.ecode
			return ecode

	def Learn(self, lines, diode_en = False):
		self.start()
		bank = 10.0
		measure = {
			"type"	: 'R',
			"ms"	: 16,
			"mA"	: 10,
			"min"	: 1000,
			"max"	: None,
			"irt"	: "W4R",
			"arm"	: 2,
#			"dmm"	: "VOLT:DC %.3f"%bank,
			"dmm"	: "VOLT:DC %.3f,%.3fE-6"%(bank, bank * ppm),
		}

		self.passed = True
		self.PassTest(measure, lines)
		self.readall()
		groups = []
		if not self.passed:
			groups = self.Travel(measure, lines, diode_en)
		self.stop()
		return groups

	def Travel(self, measure, lines, diode_en = False):
		def efunc(a, b):
			self.A = a
			self.B = b
			self.AddMeasure()
			passed = self.readall(1)
			if diode_en:
				self.A = b
				self.B = a
				self.AddMeasure()
				passed &= self.readall(1)
			return not passed

		measure["TRAVEL"] = True
		self.M = measure
		return self.travel(lines, efunc)

	def travel(self, lines, efunc = None):
		#lines = list(set(lines)) #remove identical a line
		lines = sorted(set(lines),key=lines.index)
		groups = []
		while True:
			if len(lines) <= 1:
				break

			A = lines[:1]
			B = lines[1:]
			lines = B
			elines = self.FastFail(A, B, efunc, [])
			if len(elines) > 0:
				if efunc is None:
					print "elines: %s"%str(elines)

			group = {}
			group["A"] = A[0]
			group["B"] = elines
			groups.append(copy.deepcopy(group))
			for line in elines:
				lines.remove(line)

		if efunc is None:
			for group in groups:
				print group
		return groups

	def FastFail(self, a, b, efunc = None, elines = []):
		#a/b should be a list object
		#there may be several failure lines
		if efunc is None:
			def efunc_demo(a, b):
				result = random.randint(0, 1)
				msg = ["no fail", "fail"]
				print "%2d: %-20s => %s"%(a[0], str(b), msg[result])
				return result
			efunc = efunc_demo

		err = efunc(a, b)
		if err:
			N = len(b)
			if N == 1:
				elines += b
			else:
				N >>= 1
				l = b[:N]
				r = b[N:]
				elines = self.FastFail(a, l, efunc, elines)
				elines = self.FastFail(a, r, efunc, elines)
		return elines

	def FastPass(self, alines, yfunc = None):
		alines = list(set(alines)) #remove identical a line
		N = len(alines)
		X = int(pow(N, 0.5))
		Y = N / X
		n = N - X * Y
		if n > 0:
			X = X + 1
			n = X * Y - N
			dummys = np.empty(n)
			dummys.fill(-1)
			alines = alines + dummys.tolist()

		alines = np.array(alines)
		alines = alines.reshape((Y, X))
		if yfunc is None:
			def yfunc_demo(a, b):
				print ""
				print "a: %s"%str(a)
				print "b: %s"%str(b)

			yfunc = yfunc_demo
			print alines

		for y in range(Y - 1):
			a = alines[y, :]
			b = alines[(y+1):, :]
			a = a.reshape(a.size).tolist()
			b = b.reshape(b.size).tolist()
			a=map(int, a)
			b=map(int, b)
			a = filter(lambda line: line >= 0, a)
			b = filter(lambda line: line >= 0, b)
			yfunc(a, b)

		for x in range(X - 1):
			a = alines[:, x]
			b = alines[:, (x+1):]
			a = a.reshape(a.size).tolist()
			b = b.reshape(b.size).tolist()
			a=map(int, a)
			b=map(int, b)
			a = filter(lambda line: line >= 0, a)
			b = filter(lambda line: line >= 0, b)
			yfunc(a, b)

	def PassTest(self, measure_config, lines):
		self.N = measure_config
		self.mode()
		def yfunc(alines, blines):
			self.A = alines
			self.B = blines
			self.AddMeasure()

		self.FastPass(lines, yfunc)

	def lvtest(self, instr):
		opcode = instr.group('i0')
		if opcode:
			if opcode in self.executers:
				func = self.executers[opcode]
				func(instr)
			else:
				self.log_instr_exception(instr)
		else:
			square = instr.group("q0") #like: [DIODE CHECK]
			if square:
				if square == "[DIODE CHECK]":
					self.diode = True
				elif square == "[DIODE END]":
					self.diode = False
				elif square[0] == "[":
					self.log_instr_exception(instr)

	def load(self, path, model = None):
		#return None when success or last error
		subs = []
		if model:
			#load settings from db
			model = self.db.model_get(model)
			nrow = model["nrow"]
			ncol = model["ncol"]
			nofs = model["nofs"]
			npts = model["npts"]
			nsub = int(nrow) * int(ncol)

			for isub in range(nsub):
				if isub > 0:
					ofs = isub * int(npts) + int(nofs)
					sub = {"ofs": ofs}
					sub["idx"] = isub
					subs.append(sub)

		self.subs = subs
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
					emsg = "%s...syntax error"%line
					self.log(emsg, False)
		gft.close()
		if emsg:
			self.pmem = [] #clean all

		return emsg

	def readall(self, nr_of_sample = None, report = None):
		if nr_of_sample == 0:
			return True

		passed = True
		if not self.hwen:
			return passed

		n = 0;
		deadline = None
		while True:
			if nr_of_sample:
				if n >= nr_of_sample:
					break
			else:
				if self.dmem.empty():
					break

			if deadline is None:
				deadline = time.time() + 5

			if time.time() > deadline:
				raise GvmTimeout

			time.sleep(0.01)
			npoints = self.dmm.poll()
			if npoints > 0:
				if npoints > 20:
					npoints = 20 #to avoid pyvisa timeout err

				if nr_of_sample:
					if npoints > nr_of_sample:
						npoints = nr_of_sample
				deadline = time.time() + 5
				results = self.dmm.read(npoints)
				for result in results:
					if report:
						report(result, n)
					else:
						measure = self.dmem.get(False)
						passed &= self.report(measure, result)
					n += 1
		return passed

	def unitconv(self, v):
		unit_list = [
			["T", 1.0e12],
			["G", 1.0e9],
			["M", 1.0e6],
			["K", 1.0e3],
			["", 1.0e0]
		]
		for unit in unit_list:
			min = unit[1]
			if abs(v) >= min:
				v /= min
				break
		if unit[0] == "T":
			#over-range
			v = 999.9
		return v, unit[0]

	def report(self, measure, result):
		if measure["type"] == "R":
			if "diode" in measure:
				pass
			else:
				result = result * 1000 / measure["mA"]
		else: #L
			result = - result
			result = measure["hv"] / result

		#pass or failed?
		min = measure["min"]
		max = measure["max"]
		passed = True
		if min:
			passed = passed and (result >= min)
		if max:
			passed = passed and (result <= max)

		if "TRAVEL" in measure:
			#travel search
			na = len(measure["A"])
			nb = len(measure["B"])
			#do not show travel inter-steps
			if na != 1 or nb != 1 or passed:
				return passed
			measure["A"] = measure["A"][0]
			measure["B"] = measure["B"][0]
		else:
			#pass test
			self.passed = self.passed and passed
			if not passed:
				idx = 0
				if "sub" in measure:
					sub = measure["sub"]
					if sub:
						idx = sub["idx"]

				self.ecode |= (1 << idx)

		#show the report
		self.Report(measure, result, passed)
		return passed

	#only for display purpose
	def Report(self, measure, result, passed = None):
		A = measure["A"]
		B = measure["B"]

		if measure["type"] == "R":
			v, unit = self.unitconv(result)
			if "diode" in measure:
				unit += "V"
			else:
				unit += "Ohm"
		else: #L
			v, unit = self.unitconv(result)
			unit += "Ohm"

		min_str = max_str = "-"
		if measure["min"]:
			min = measure["min"]
			min, min_unit = self.unitconv(min)
			min_str = "%.1f%s"%(min, min_unit)
		if measure["max"]:
			max = measure["max"]
			max, max_unit = self.unitconv(max)
			max_str = "%.1f%s"%(max, max_unit)

		if isinstance(A, list): #hv pass test display
			A = np.array(A) + 1
			B = np.array(B) + 1
			if measure["type"] == "L":
				self.log("A(+): %s"%", ".join(map(str, A)))
				self.log("B(-): %s"%", ".join(map(str, B)))
				line = "R(A, B) = %6.01f %-4s"%(v, unit)
				line += "  <@%04dV, %6s, %6s>"%(measure["hv"], min_str, max_str)
				self.log(line, passed)
				self.log("")
			elif measure["type"] == "R":
				if 0:
					self.log("A(+): %s"%", ".join(map(str, A)))
					self.log("B(-): %s"%", ".join(map(str, B)))
					line = "R(A, B) = %6.01f %-4s"%(v, unit)
					line += "  <@%04dV, %6s, %6s>"%(measure["mA"], min_str, max_str)
					self.log(line, passed)
					self.log("")
		else:
			#R(123, 445) = 17.1K
			if measure["type"] == "R":
				if "diode" in measure:
					line = "V(%4d, %4d) = %6.01f %-4s"%(A+1, B+1, v, unit)
					line += "  <@%04dmA, %6s, %6s>"%(measure["mA"], min_str, max_str)
				else:
					line = "R(%4d, %4d) = %6.01f %-4s"%(A+1, B+1, v, unit)
					line += "  <@%04dmA, %6s, %6s>"%(measure["mA"], min_str, max_str)
			else:
				line = "R(%4d, %4d) = %6.01f %-4s"%(A+1, B+1, v, unit)
				line += "  <@%04dV, %6s, %6s>"%(measure["hv"], min_str, max_str)
			self.log(line, passed)

	def log(self, info, passed = None, eol = "\n"):
		line = "%-64s"%info
		if passed == True:
			line = line + " [PASS]"
		elif passed == False:
			line = line + " [FAIL]"
		else:
			pass
		line = line + eol
		print line ,

	def log_instr_exception(self, instr, emsg = None):
		if emsg is None:
			emsg = "instruction exception"
		emsg = "%s...%s"%(instr.string, emsg)
		self.log(emsg, False)
		raise GvmSyntaxError

	def FastProbe(self, x, y, yfunc = None):
		#both x, y is included in search range
		yes = False
		m = y

		if yfunc is None:
			ok = random.randint(x, y)
			def yfunc_demo(x, m):
				print("x = %4d m = %4d"%(x, m))
				yes = ok >= x
				yes &= ok <= m
				return yes

			yfunc = yfunc_demo

		while True:
			yes = yfunc(x, m)
			if yes and (x == m):
				return x

			if yes:
				y = m
			else:
				x = m + 1

			m = (x + y) >> 1
			if m < x:
				break

	def probe(self, lines = 1024):
		self.dmm.stop()
		resolution = 100.0*ppm*1e-6
		dmm_cfg = "100, %f"%resolution
		self.irt.mode("RPB")

		def yfunc(x, m):
			#self.irt.mode("RPB")
			self.irt.open(0, 0, lines)
			self.irt.close(0, x, m)
			time.sleep(0.005)
			ohm = self.dmm.measure_fres(dmm_cfg)
			ohm = float(ohm)
			yes = ohm <= 20.0
			#print("R(%4d:%4d, 0) = %5.1f ohm"%(x+1, m+1, ohm))
			if yes and (x == m): #found ??
				measure = {
					"A": x,
					"B": -1, #probe pin
					"type": "R",
					"mA": 1,
					"min": None,
					"max": 20.0, #unit: ohm
				}

				result = ohm / 1000 #trick: measure["mA"] = 1
				self.report(measure, result)
			return yes

		ok = self.FastProbe(0, lines - 1, yfunc)
		return ok;

	def scan(self, start = 0, lines = 512):
		self.dmm.stop()
		self.dmm.trig_ext(slope="POS", sdelay = 0)
		resolution = 100.0*ppm*1e-6
		self.dmm.config("FRES 100, %f"%resolution)
		self.dmm.start()
		self.irt.pipeline(True)
		self.irt.mode("RPB")
		self.irt.arm(1)
		self.irt.mdelay(4)
		self.irt.switch("SCAN", bus_mp, start, start + lines - 1)

		def report(result, n):
			measure = {
				"A": None,
				"B": -1, #probe pin
				"type": "R",
				"mA": 1,
				"min": None,
				"max": 20.0, #unit: ohm
			}

			measure["A"] = n + start
			result = result / 1000 #trick: measure["mA"] = 1
			self.report(measure, result)

		self.readall(lines, report)
		self.irt.pipeline(False)

	def fscn(self, start = 0, lines = 512):
		self.dmm.stop()
		self.dmm.trig_ext(slope="POS", sdelay = 0)
		resolution = 100.0*ppm*1e-6
		self.dmm.config("FRES 100, %f"%resolution)
		self.dmm.start()
		self.irt.pipeline(True)
		self.irt.mode("RPB")
		self.irt.arm(1)
		self.irt.mdelay(4)
		self.irt.switch("FSCN", bus_mp, start, start + lines - 1, 3)

		def report(result, n):
			measure = {
				"A": None,
				"B": -1, #probe pin
				"type": "R",
				"mA": 1,
				"min": None,
				"max": 20.0, #unit: ohm
				"bus": None,
			}

			measure["A"] = (n >> 2) + start
			measure["bus"] = n & 0x03
			result = result / 1000 #trick: measure["mA"] = 1
			self.report(measure, result)

		self.readall(lines * 4, report)
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

	def cal_hv_init(self):
		self.irt.query("POWER HV 0.0")
		self.irt.query("POWER VS OFF")
		time.sleep(0.1)
		self.dmm.stop()
		time.sleep(0.1)
		self.dmm.measure_dcv()
		time.sleep(0.1)
		self.irt.mode("OFF")
		time.sleep(0.1)
		self.irt.query("POWER LV OFF")
		self.irt.query("relay 25,16,18", False)

	def cal_hv_measure(self, hv_set):
		self.irt.query("POWER VS ON")
		self.irt.query("POWER HV %.3f"%hv_set)
		hv_get = self.dmm.measure_dcv()
		self.irt.query("POWER VS OFF")
		hv_get = float(hv_get)
		return hv_get

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
	from db import Db

	subcmd = argv[1]
	db = Db("../irt.db")
	gvm = Gvm(db)
	if subcmd != "try" and subcmd != "pass" and subcmd != "fail":
		dmm = Dmm()
		irt = Matrix()
		gvm.Connect(irt, dmm)

	argc = len(argv)
	if argc > 1:
		if subcmd == "probe":
			timer = time.time()
			line = gvm.probe() + 1
			timer = time.time() - timer
			if line:
				print "line = %d"%line
			print "Test Finished In %.3f S"%timer
			sys.exit(0)
		elif(subcmd == "run") or (subcmd == "try"):
			fname = "./sample.gft"
			if argc > 2:
				fname = argv[2]

			gvm.load(fname)
			if subcmd == "try":
				gvm.dump_pmem()
				sys.exit(0)
			timer = time.time()
			gvm.Run()
			timer = time.time() - timer
			print "Test Finished In %.1f S"%(timer)
			sys.exit(0)
		elif subcmd == "scan":
			line_start = 0
			lines = 32
			if argc > 2:
				line_start = int(argv[2])
			if argc > 3:
				lines = int(argv[3])
			timer = time.time()
			gvm.scan(line_start, lines)
			timer = time.time() - timer
			print "Test Finished In %.1f S"%(timer)
			sys.exit(0)
		elif subcmd == "fscn":
			line_start = 0
			lines = 32
			if argc > 2:
				line_start = int(argv[2])
			if argc > 3:
				lines = int(argv[3])
			timer = time.time()
			gvm.fscn(line_start, lines)
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
		elif subcmd == "cal_hv":
			start = 0.00
			end = 500.0
			N = 50
			if argc > 2:
				start = float(argv[2])
			if argc > 3:
				end = float(argv[3])
			if argc > 4:
				N = int(argv[4])

			gvm.cal_hv_init()
			gvm.cal_hv_measure(start)
			time.sleep(0.1)

			for i in range(0, N):
				hv_set = start + i*(end - start)/N
				hv_get = gvm.cal_hv_measure(hv_set)

				hv_set += 0.00000001
				delta = (hv_get - hv_set) / hv_set * 100
				print "CAL: %8.0f => %8.0f V, %8.1f%%" % (hv_set, hv_get, delta)
			gvm.cal_hv_measure(0)
			sys.exit(0)
		elif subcmd == "learn":
			ofs = 0
			n = 32
			if argc > 2:
				n = int(argv[2])

			lines = range(ofs, ofs + lines)
			groups = gvm.Learn(lines)
			for group in groups:
				print group
			sys.exit(0)
		elif subcmd == "query":
			cmdline = argv[2:]
			cmdline = " ".join(cmdline)
			irt.query(cmdline)
			print "Q: %s"%cmdline
			print "A: %s"%irt.echo
			sys.exit(0)
		elif subcmd == "pass":
			N = 19
			if argc > 2:
				N = int(argv[2])
			gvm.FastPass(range(N))
			sys.exit(0)
		elif subcmd == "fail":
			N = 5
			if argc > 2:
				N = int(argv[2])
			gvm.travel(range(N))
			sys.exit(0)

	print "gvm.py try [xx.gft]				for syntax check only"
	print "gvm.py run [xx.gft]"
	print "gvm.py measure A B				measure R(A,B)"
	print "gvm.py scan [start [lines]]		measure R(line_x, probe)"
	print "gvm.py cal_is [start [end [N]]]	dps is calibration, unit: A"
	print "gvm.py cal_lv [start [end [N]]]	dps lv calibration, unit: V"
	print "gvm.py cal_hv [start [end [N]]]	dps hv calibration, unit: V"
	print "gvm.py probe						which line is pressed?"
	print "gvm.py query cmdline				irt cmd query"
	print "gvm.py pass [nr_of_lines]		irt fast pass algo demo"
	print "gvm.py fail [nr_of_lines]		irt fast fail algo demo"
	print "gvm.py learn						irt learn"

