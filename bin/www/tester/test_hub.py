#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random
import os
import fnmatch
import eloger
import json

class HUBTest(Test):
	model = None
	check_passed = True

	def __init__(self, tester, model, station = 0):
		Test.__init__(self, tester, station)
		self.model = model
		self.uctrl = tester.uctrl[station]
		self.feasa = tester.feasa[station]
		self.rasp = tester.rasp[station]
		self.dbResult = self.tester.db.get('cfg_get')("dbResult")
		self.dbResult = int(self.dbResult)

	def verifyBarcode(self, barcode):
		if hasattr(self.model, "barcode"):
			template = self.model.barcode
			if not fnmatch.fnmatchcase(barcode, template):
				emsg = []
				emsg.append("Barcode Error")
				emsg.append("expect: %s"%template)
				emsg.append("scaned: %s"%barcode)
				emsg = '\n\r'.join(emsg)
				return emsg

	def matrix_close(self, image):
		matrix = self.tester.matrix
		matrix.lock.acquire()
		for bus in range(4):
			line = image[bus]
			if line is not None:
				line = line + 16 * self.station
				matrix.close(bus, line)
		#matrix.lock.release()

	def matrix_open(self, image):
		matrix = self.tester.matrix
		#matrix.lock.acquire()
		for bus in reversed(range(4)):
			line = image[bus]
			if line is not None:
				line = line + 16 * self.station
				matrix.open(bus, line)
		matrix.lock.release()

	def mode(self, mode, enable):
		uctrl = self.uctrl
		if mode == "allwork":
			uctrl.mode("port1 usb2.0", enable)
			uctrl.mode("port2 usb2.0", enable)
			uctrl.mode("port3 usb2.0", enable)
		elif mode == "allload":
			#uctrl.mode("port1 load", enable)
			#uctrl.mode("port2 load", enable)
			#uctrl.mode("port3 load", enable)
			uctrl.switch("load1", enable)
			uctrl.switch("load2", enable)
		elif mode == "allcdp":
			uctrl.mode("port1 cdp", enable)
			uctrl.mode("port2 cdp", enable)
			uctrl.switch("cdp2", enable) #to fix cdp2 disable bug
		elif mode == "allscp":
			uctrl.mode("port1 short", enable)
			uctrl.mode("port2 short", enable)
			uctrl.mode("port3 short", enable)
		else:
			uctrl.mode(mode, enable)

	def check_ripple(self, test, prefix=""):
		#ripple check is a sub check of vdc test
		#so relay switch is not needed

		count = 0
		while True:
			v = self.tester.dmm.measure_acv()

			v = float(v)
			limit = test["ripple"]
			max = limit["max"]
			passed =  v <= max

			if passed or count > 3:
				break
			else:
				time.sleep(0.01)
				count = count + 1

		self.check_passed = self.check_passed and passed

		msg = "%s%s.ripple(<%.3f)...%.3fV"%(prefix, test["desc"], max, v)
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"]+".ripple", None, max, v, passed)
		return passed

	def check_voltage(self, test, prefix=""):
		relays = test["matrix"]
		self.matrix_close(relays)
		time.sleep(0.1)

		count = 0
		while True:
			v = self.tester.dmm.measure_dcv()

			v = float(v)
			limit = test["limit"]
			max = limit["max"]
			min = limit["min"]
			passed =  v <= max and v >= min

			if passed or count > 3:
				break
			else:
				time.sleep(0.1)
				count = count + 1

				msg = "%s%s(%.3f,%.3f)...%.3fV"%(prefix, test["desc"], min, max, v)
				loger = eloger.Eloger()
				loger.log(msg)

		self.check_passed = self.check_passed and passed

		msg = "%s%s(%.3f,%.3f)...%.3fV"%(prefix, test["desc"], min, max, v)
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"], min, max, v, passed)

		if "ripple" in test:
			ripple_passed = self.check_ripple(test, prefix)
			passed = passed and ripple_passed

		self.matrix_open(relays)
		return passed

	def check_current(self, test, prefix=""):
		relays = test["matrix"]
		self.matrix_close(relays)
		time.sleep(0.01)
		i = self.tester.dmm.measure_dci()
		self.matrix_open(relays)

		i = float(i)
		limit = test["limit"]
		max = limit["max"]
		min = limit["min"]
		passed =  i <= max and i >= min
		self.check_passed = self.check_passed and passed

		msg = "%s%s(%.3f,%.3f)...%.3fA"%(prefix, test["desc"], min, max, i)
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"], min, max, i, passed)
		return passed

	def check_identify(self, test, prefix=""):
		passmark_id = test["passmark"]
		port_speed = 0
		list = self.rasp.list()
		if passmark_id in list:
			port_speed = list[passmark_id]

		passed = port_speed == 480
		self.check_passed = self.check_passed and passed

		msg = "%s%s..."%(prefix, test["desc"])
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"], None, None, port_speed, passed)
		return passed

	def check_benchmark(self, test, prefix=""):
		passmark_id = test["passmark"]
		result = self.rasp.status(passmark_id)

		limit = test["limit"]
		wmin = limit["w_mbps_min"]
		rmin = limit["r_mbps_min"]
		amin = limit["a_mbps_min"]
		w_mbps = 0
		r_mbps = 0
		a_mbps = 0

		passed = False
		if result:
			w_mbps = result["w_mbps"]
			r_mbps = result["r_mbps"]
			a_mbps = result["a_mbps"]

		passed = w_mbps > wmin
		self.check_passed = self.check_passed and passed
		msg = "%s%s.w(>%d)...%dMbps"%(prefix, test["desc"], wmin, w_mbps)
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"]+".w", wmin, None, w_mbps, passed)

		passed = r_mbps > rmin
		self.check_passed = self.check_passed and passed
		msg = "%s%s.r(>%d)...%dMbps"%(prefix, test["desc"], rmin, r_mbps)
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"]+".r", rmin, None, r_mbps, passed)

		passed = a_mbps > amin
		self.check_passed = self.check_passed and passed
		msg = "%s%s.a(>%d)...%dMbps"%(prefix, test["desc"], amin, a_mbps)
		self.log(msg, passed)
		self.SaveResult(prefix, test["desc"]+".a", amin, None, a_mbps, passed)
		return passed

	def check_bridge(self, index):
		prefix = "USB%d: "%(index + 1)

		passed = False
		for count in range(0, 3):
			self.mode("carplay", "enable")
			passed = self.rasp.h2htest(index)
			if passed == "die":
				self.mode("carplay", "disable")
				time.sleep(0.1)
				self.log("h2h bridge test died...:(")
				continue
			else:
				break

		self.check_passed = self.check_passed and passed
		self.log("%sH2H Bridge Looptest..."%prefix, passed)
		self.mode("carplay", "disable")

	def check_sd(self, test, prefix=""):
		echo = self.rasp.cid()
		cid = ""
		if len(echo) > 0:
			cid = str(echo["cid"])

		passed = len(cid) == 32
		self.log("SD: CID...%s"% cid, passed)
		self.check_passed &= passed

		if not passed:
			return

		limit = test["limit"]
		speed = self.rasp.sd()
		passed = False
		if speed:
			passed = speed["w"] > limit["w_mbps_min"]
			self.check_passed &= passed
			msg = "SD: %s%s.w(>%4.01f)...%4.01fMBps"%(prefix, test["desc"], limit["w_mbps_min"], speed["w"])
			self.log(msg, passed)

			passed = speed["r"] > limit["r_mbps_min"]
			self.check_passed &= passed
			msg = "SD: %s%s.r(>%4.01f)...%4.01fMBps"%(prefix, test["desc"], limit["r_mbps_min"], speed["r"])
			self.log(msg, passed)

		else:
			self.check_passed = False
			msg = "SD: %s%s.w(>%4.01f)...None"%(prefix, test["desc"], limit["w_mbps_min"])
			self.log(msg, False)
			msg = "SD: %s%s.r(>%4.01f)...None"%(prefix, test["desc"], limit["r_mbps_min"])
			self.log(msg, False)

	def calibrate_feasa(self, feasa):
		light_cal = {}
		for ch in feasa:
			test = feasa[ch]
			xyidh = self.feasa.getXYI(ch)
			self.log("FEASA CH%02d: Lighting.i = %6.03f cd/m^2"%(ch + 1, xyidh[2]))
			self.log("FEASA CH%02d: Lighting.h = %6.1f degree"%(ch + 1, xyidh[4]))
			light_cal[ch] = {"i": xyidh[2], "h": xyidh[4]}

		if self.check_passed:
			record = {}
			record["model"] = self.model.name
			record["station"] = self.station
			record["name"] = "feasa"
			record["value"] = json.dumps(light_cal)
			self.tester.db.get("cal_add")(record)

	def check_feasa(self, feasa):
		#feasa = {0: {test}, 1: {test}, ... 9: {test}}
		feasa_passed = False
		if self.feasa.IsReady():
			feasa_passed = True
			for ch in feasa:
				test = feasa[ch]
				limit = test["limit"]
				min = limit["min"]
				max = limit["max"]

				xyi = self.feasa.getXYI(ch)

				for idx, val in enumerate(xyi):
					passed = val > min[idx] and val < max[idx]
					feasa_passed = feasa_passed and passed

					chname = ("x","y", "i", "d", "h")[idx]
					if chname == "d":
						msg = "FEASA CH%02d: %s.%s(%6.0f,%6.0f)...%6.0f"%(ch+1, test["desc"], chname, min[idx], max[idx], val)
					elif chname == "h":
						msg = "FEASA CH%02d: %s.%s(%6.0f,%6.0f)...%6.1f"%(ch+1, test["desc"], chname, min[idx], max[idx], val)
					else:
						msg = "FEASA CH%02d: %s.%s(%6.03f,%6.03f)...%6.03f"%(ch+1, test["desc"], chname, min[idx], max[idx], val)
					self.log(msg, passed)
					self.SaveResult("FEASA CH%02d"%ch, "%s.%s"%(test["desc"], chname), min[idx], max[idx], val, passed)

				#light_cal check
				if self.tester.LightCal:
					ityp = self.model.light_cal["%d"%ch]["i"]
					htyp = self.model.light_cal["%d"%ch]["h"]

					ilim = {"min": 0.6, "max": 1.4}
					hlim = {"min": 0.6, "max": 1.4}

					ratio = xyi[2] / ityp
					passed = ratio > ilim["min"] and ratio < ilim["max"]
					feasa_passed = feasa_passed and passed
					msg = "FEASA CH%02d: %s.i(%5.0f%%,%5.0f%%)...%6.01f"%(ch+1, test["desc"], ilim["min"]*100, ilim["max"]*100, ratio*100)
					self.log(msg, passed)

					ratio = xyi[4] / htyp
					passed = ratio > hlim["min"] and ratio < hlim["max"]
					feasa_passed = feasa_passed and passed
					msg = "FEASA CH%02d: %s.h(%5.0f%%,%5.0f%%)...%6.01f"%(ch+1, test["desc"], hlim["min"]*100, hlim["max"]*100, ratio*100)
					self.log(msg, passed)

		self.check_passed = self.check_passed and feasa_passed
		return feasa_passed

	def wait_until_usb_identified(self, timeout = 1):
		self.log("Waiting for USB Identify, <1s")
		deadline = time.time() + timeout
		while time.time() < deadline:
			time.sleep(0.01)
			list = self.rasp.list()
			if len(list) > 0:
				break

	def wait_until_cid_identified(self, timeout = 3):
		self.log("Waiting for SD Card Identify, <3s")
		deadline = time.time() + timeout
		while time.time() < deadline:
			time.sleep(0.01)
			echo = self.rasp.cid()
			if len(echo) > 0: #{"cid": "xxxxxxxx"}
				break

	def wait_until_benchmark_finished(self):
		self.log("Waiting for Benchmark Test, <3s")
		while True:
			time.sleep(0.01)
			ready = self.rasp.IsReady()
			if ready:
				break;

	def wait_until_feasa_captured(self):
		self.log("Waiting for Feasa Capture, <6s")
		while True:
			time.sleep(0.01)
			ready = self.feasa.IsReady()
			if ready:
				break;

	def update(self):
		Test.update(self)

	def SaveResult(self, prefix, name, min, max, value, passed):
		if self.dbResult == 0:
			return

		dat_dir = self.getPath()
		dat_dir = os.path.abspath(dat_dir)
		self.lock.acquire()
		datafile = os.path.relpath(self.dfpath, dat_dir)
		self.lock.release()

		failed = 1
		if passed:
			failed = 0

		record = {}
		record["datafile"] = datafile
		record["failed"] = failed

		if prefix is not None:
			record["prefix"] = prefix

		if name is not None:
			record["name"] = name

		if min is not None:
			record["min"] = min

		if max is not None:
			record["max"] = max

		if value is not None:
			record["value"] = value

		self.tester.db.get('result_add')(record)

	def Record(self):
		dat_dir = self.getPath()
		dat_dir = os.path.abspath(dat_dir)
		self.lock.acquire()
		record = {}
		record["model"] = self.model.name
		record["barcode"] = self.barcode
		record["failed"] = self.ecode
		record["datafile"] = os.path.relpath(self.dfpath, dat_dir)
		record["station"] = self.station
		self.lock.release()
		self.tester.db.get('test_add')(record)

	def Calibrate(self):
		self.log("uctrl reset")
		self.uctrl.reset()

		self.mode("inv", "enable")
		self.check_voltage(self.model.vbat)
		self.mode("inv", "disable")

		self.mode("ic", "enable")
		self.check_current(self.model.i0)
		self.mode("ic", "disable")

		self.mode("allwork", "enable")
		self.wait_until_usb_identified()
		self.feasa.capture() #...about 6s

		self.wait_until_feasa_captured()
		light = getattr(self.model, "light", None)
		if light is not None:
			self.calibrate_feasa(light)

		self.log("uctrl power off")
		self.uctrl.reset()

		if self.check_passed:
			self.Pass()
		else:
			self.Fail()

	def Test(self):
		self.log("uctrl reset")
		self.uctrl.reset()

		#vbat all loads open
		self.mode("inv", "enable")
		self.check_voltage(self.model.vbat)
		self.mode("inv", "disable")

		#hub is offline except vbat is connected
		#time.sleep(0.1) #add by xlj
		self.mode("qc", "enable")
		self.check_current(self.model.iq)
		self.mode("qc", "disable")

		#only upstream usb is pluged-in, so no sd card and etc
		#time.sleep(0.1) #add by xlj
		self.mode("ic", "enable")
		self.check_current(self.model.i0)
		self.mode("ic", "disable")

		#time.sleep(0.1) #add by xlj
		self.mode("allwork", "enable")
		self.wait_until_usb_identified()
		self.feasa.capture() #...about 6s
		time.sleep(0.1)

		#vcc normal?
		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			vopen = port["vopen"]
			if vopen is not None:
				self.check_voltage(vopen, prefix)

		self.rasp.benchmark() #...about 3s

		#vload
		self.mode("allload", "enable")
		self.log("Loading Test")
		time.sleep(0.1)
		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			vload = port["vload"]
			if vload is not None:
				self.check_voltage(vload, prefix)
		self.mode("allload", "disable")

		#passmark test
		self.wait_until_benchmark_finished()
		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			identify = port["identify"]
			self.check_identify(identify, prefix)

			benchmark = port["benchmark"]
			if benchmark is not None:
				self.check_benchmark(benchmark, prefix)

		self.mode("allwork", "disable")

		#h2h bridge test
		for port in self.model.usb_ports:
			h2h = port["h2h"]
			if h2h:
				self.check_bridge(port["index"])
				pass

		#cdp
		#time.sleep(0.1) #add by xlj
		self.mode("allcdp", "enable")
		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			cdp = port["cdp"]
			if cdp is not None:
				self.check_voltage(cdp, prefix)
		self.mode("allcdp", "disable")

		#hostflip
		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			hostflip = port["hostflip"]
			if hostflip is not None:
				index = port["index"] + 1
				#time.sleep(0.1) #add by xlj
				self.mode("port%d bypass"%index, "enable")

				vdp = hostflip["vdp"]
				vdn = hostflip["vdn"]

				time.sleep(1.5)
				self.check_voltage(vdp, prefix)
				self.check_voltage(vdn, prefix)

				self.wait_until_usb_identified()
				identify = hostflip["identify"]
				self.check_identify(identify, prefix)

				#optional, usb_hostflip_benchmark must be set
				benchmark = hostflip["benchmark"]
				if benchmark is not None:
					self.check_benchmark(benchmark, prefix)

				self.mode("port%d bypass"%index, "disable")

		#scp start
		self.log("Short Test(=3s)")
		#time.sleep(0.1) #add by xlj
		self.mode("allscp", "enable")
		deadline = time.time() + 3

		#do not reboot until feasa captured
		self.wait_until_feasa_captured()
		light = getattr(self.model, "light", None)
		if light is not None:
			self.check_feasa(light)

		#short test report
		while deadline > time.time(): pass
		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			scp = port["scp"]
			if scp is not None:
				self.check_voltage(scp["vscp"], prefix)

		#check sd card
		sd = getattr(self.model, "sd", None)
		if sd is not None:
			self.wait_until_cid_identified()
			self.check_sd(sd)

		#uut vbat restart
		self.mode("allscp", "disable")
		self.uctrl.vbat("off")
		time.sleep(0.01)
		self.uctrl.vbat("on")
		time.sleep(0.01)

		for port in self.model.usb_ports:
			prefix = "USB%d: "%(port["index"] + 1)
			scp = port["scp"]
			if scp is not None:
				self.check_voltage(scp["vrcv"], prefix)

		#test finished
		self.uctrl.reset()

		if self.check_passed:
			self.Pass()
		else:
			self.Fail()
