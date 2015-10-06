#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random
import os

class HUBTest(Test):
	model = None
	check_passed = True

	def __init__(self, tester, model, station = 0):
		Test.__init__(self, tester, station)
		self.model = model
		self.uctrl = tester.uctrl[station]

	def matrix_close(self, image):
		matrix = self.tester.matrix
		matrix.lock.acquire()
		for bus in range(4):
			line = image[bus]
			if line is not None:
				#line = line + 16 * self.station
				matrix.close(bus, line)

	def matrix_open(self, image):
		matrix = self.tester.matrix
		for bus in reversed(range(4)):
			line = image[bus]
			if line is not None:
				#line = line + 16 * self.station
				matrix.open(bus, line)
		matrix.lock.release()

	def mode(self, mode, enable):
		uctrl = self.uctrl
		if mode == "allwork":
			uctrl.mode("port1 usb2.0", enable)
			uctrl.mode("port2 usb2.0", enable)
			uctrl.mode("port3 usb2.0", enable)
		elif mode == "allload":
			uctrl.mode("port1 load", enable)
			uctrl.mode("port2 load", enable)
			uctrl.mode("port3 load", enable)
		elif mode == "allcdp":
			uctrl.mode("port1 cdp", enable)
			uctrl.mode("port2 cdp", enable)
		elif mode == "allscp":
			uctrl.mode("port1 short", enable)
			uctrl.mode("port2 short", enable)
			uctrl.mode("port3 short", enable)
		else:
			uctrl.mode(mode, enable)

	def check_voltage(self, test, prefix=""):
		relays = test["matrix"]
		self.matrix_close(relays)
		time.sleep(0.1)
		v = self.tester.dmm.measure_dcv()
		self.matrix_open(relays)

		v = float(v)
		limit = test["limit"]
		max = limit["max"]
		min = limit["min"]
		passed =  v <= max and v >= min
		self.check_passed = self.check_passed and passed

		msg = "%s measuring %s(%.3f,%.3f)...%.3fV"%(prefix, test["desc"], min, max, v)
		self.log(msg, passed)
		return passed

	def check_current(self, test, prefix=""):
		relays = test["matrix"]
		self.matrix_close(relays)
		time.sleep(0.1)
		i = self.tester.dmm.measure_dci()
		self.matrix_open(relays)

		i = float(i)
		limit = test["limit"]
		max = limit["max"]
		min = limit["min"]
		passed =  i <= max and i >= min
		self.check_passed = self.check_passed and passed

		msg = "%s measuring %s(%.3f,%.3f)...%.3fA"%(prefix, test["desc"], min, max, i)
		self.log(msg, passed)
		return passed

	def check_identify(self, test):
		pass

	def check_benchmark(self, test):
		pass

	def check_feasa(self, test):
		pass

	def update(self):
		Test.update(self)

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

	def Test(self):
		while True:
			self.uctrl.reset()

			stop = self.tester.RequestTest(self)
			if stop:
				break

			subdir = time.strftime("%Y-%m-%d")
			fname = time.strftime("%H_%M_")+self.getBarcode()+".dat"
			fpath = self.getPath(subdir, fname)
			self.Start(fpath)
			self.check_passed = True

			#vbat all loads open
			self.mode("inv", "enable")
			self.check_voltage(self.model.vbat)
			self.mode("inv", "disable")

			#hub is offline except vbat is connected
			self.mode("qc", "enable")
			self.check_current(self.model.iq)
			self.mode("qc", "disable")

			#only upstream usb is pluged-in, so no sd card ...
			self.mode("ic", "enable")
			self.check_current(self.model.i0)
			self.mode("ic", "disable")

			#<<<<<<<<<<<<<<normal working start here<<<<<<<<<<<<<<
			self.mode("allwork", "enable")
			#self.feasa.capture()
			#self.feasa.setAverage(3)
			time.sleep(1)

			#vcc normal?
			for port in self.model.usb_ports:
				vopen = port["vopen"]
				if vopen:
					self.check_voltage(vopen)

			#identify
			# list = self.rasp.list()
			# for port in self.model.usb_ports:
				# passmark = port.passmark
				# if passmark:
					# self.check_identify(passmark, list)

			#start benchmark test
			# self.rasp.benchmark()

			#vload
			self.mode("allload", "enable")
			time.sleep(2)
			for port in self.model.usb_ports:
				vload = port["vload"]
				if vload:
					self.check_voltage(vload)
			self.mode("allload", "disable")

			# #wait benchmark over
			# while True:
				# time.sleep(100)
				# status = self.rasp.status()
				# if status:
					# break;

			# for port in self.model.usb_ports:
				# passmark = port["passmark"]
				# if passmark:
					# self.check_benchmark(passmark)

			#>>>>>>>>>>>>>>normal working end>>>>>>>>>>>>>>>>>>>
			self.mode("allwork", "disable")

			#cdp
			self.mode("allcdp", "enable")
			for port in self.model.usb_ports:
				cdp = port["cdp"]
				if cdp:
					self.check_voltage(cdp)
			self.mode("allcdp", "disable")

			#passthrough
			for port in self.model.usb_ports:
				passthrough = port["passthrough"]
				if passthrough:
					index = port["index"] + 1
					self.mode("port%d bypass"%index, "enable")
					#list = self.rasp.list()
					#self.check_passthrough(port, list)

					self.check_voltage(passthrough["vdp"])
					self.check_voltage(passthrough["vdn"])
					self.mode("port%d bypass"%index, "disable")

			#feasa
			# self.check_feasa(self.model.feasa)

			#scp
			self.mode("allscp", "enable")
			time.sleep(3)
			for port in self.model.usb_ports:
				scp = port["scp"]
				if scp:
					self.check_voltage(scp["vscp"])

			#uut vbat restart
			self.mode("allscp", "disable")
			self.uctrl.vbat("off")
			time.sleep(0.1)
			self.uctrl.vbat("on")
			time.sleep(1)

			for port in self.model.usb_ports:
				scp = port["scp"]
				if scp:
					self.check_voltage(scp["vrcv"])

			#test finished
			self.uctrl.reset()

			if self.check_passed:
				self.Pass()
			else:
				self.Fail()
