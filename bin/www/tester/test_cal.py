#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-14
#

import threading
import os
import time
import random
import numpy as np
import json
from pytest import *

class IRCal(Test):
	def __init__(self, tester, opts):
		Test.__init__(self, tester, opts)
		self.dmm = tester.instrument_get("dmm")
		self.irt = tester.instrument_get("irt")
		self.gvm = gvm = Gvm()
		gvm.Connect(self.irt, self.dmm)
		self.coeff = {}

	def cal_lv(self, bank_name, vset_list):
		prefix = "LV_%s"%bank_name
		vget_list = []

		self.gvm.cal_lv_init()
		for vset in vset_list:
			vget = self.gvm.cal_lv_measure(vset)
			vget_list.append(vget)
			self.log("%s: %8.1f => %8.1f V"%(prefix, vset, vget))

		self.gvm.cal_lv_measure(0)

		x = np.array(vset_list)
		y = np.array(vget_list)
		c = np.polyfit(x, y, 2)
		self.log("%s: fitting coefficient = %s"%(prefix, str(c)))
		self.coeff[prefix] = c.tolist()

		p = np.poly1d(c)
		z = p(x)
		delta = z - x
		equal = delta.sum()/len(vset_list)
		sumsq = (delta * delta).sum()/len(vset_list)
		sumsq = pow(sumsq, 0.5)

		passed = equal < 0.5;
		passed &= sumsq < 0.5;
		self.log("%s: equal = %.3f V, sumsq = %.3f V"%(prefix, equal, sumsq), passed)
		self.coeff[prefix + "_passed"] = passed + 0
		return passed;

	def cal_hv(self, bank_name, vset_list):
		prefix = "HV_%s"%bank_name
		vget_list = []

		self.gvm.cal_hv_init()
		for vset in vset_list:
			vget = self.gvm.cal_hv_measure(vset)
			vget_list.append(vget)
			self.log("%s: %8.1f => %8.1f V"%(prefix, vset, vget))

		self.gvm.cal_hv_measure(0)

		x = np.array(vset_list)
		y = np.array(vget_list)
		c = np.polyfit(x, y, 2)
		self.log("%s: fitting coefficient = %s"%(prefix, str(c)))
		self.coeff[prefix] = c.tolist()

		p = np.poly1d(c)
		z = p(x)
		delta = z - x
		equal = delta.sum()/len(vset_list)
		sumsq = (delta * delta).sum()/len(vset_list)
		sumsq = pow(sumsq, 0.5)

		passed = abs(equal) < max(vset_list)*0.5;
		passed &= sumsq < max(vset_list)*0.5;
		self.log("%s: equal = %.0f V, sumsq = %.0f V"%(prefix, equal, sumsq), passed)
		self.coeff[prefix + "_passed"] = passed + 0
		return passed;

	def cal_is(self, bank_name, mA_list):
		#convet mA to A
		vset_list = np.array(mA_list)/1000.0
		prefix = "IS_%s"%bank_name
		vget_list = []

		self.gvm.cal_is_init()
		for vset in vset_list:
			vget = self.gvm.cal_is_measure(vset)
			vget_list.append(vget)
			self.log("%s: %8.3f => %8.3f A"%(prefix, vset, vget))

		self.gvm.cal_is_measure(0)

		x = np.array(vset_list)
		y = np.array(vget_list)
		c = np.polyfit(x, y, 2)
		self.log("%s: fitting coefficient = %s"%(prefix, str(c)))
		self.coeff[prefix] = c.tolist()

		p = np.poly1d(c)
		z = p(x)
		delta = z - x
		equal = delta.sum()/len(vset_list)
		sumsq = (delta * delta).sum()/len(vset_list)
		sumsq = pow(sumsq, 0.5)

		err_equal = abs(equal) / max(vset_list)
		err_sumsq = sumsq / max(vset_list)

		passed = err_equal <= 0.02
		passed &= err_sumsq <= 0.03
		self.log("%s: error_equal = %.3f%%, error_sumsq = %.3f%%"%(prefix, err_equal*100, err_sumsq * 100), passed)
		self.coeff[prefix + "_passed"] = passed + 0
		return passed;

	def Run(self):
		self.Start(None, "../../cal.log")
		passed = self.cal_lv("0024", range(4, 25, 1))

		passed &= self.cal_hv("0100", range(10, 100, 5))
		passed &= self.cal_hv("1000", range(100, 1000, 50))

		passed &= self.cal_is("0025", range(1, 20, 1)) #25*0.9 = 22.5
		passed &= self.cal_is("0100", range(25, 90, 5)) #100*0.9 = 90
		passed &= self.cal_is("0500", range(100, 450, 25)) #500*0.9=450
		passed &= self.cal_is("1500", range(500, 2000, 100))

		#self.coeff["passed"] = passed + 0
		dpsCal = json.dumps(self.coeff)
		self.tester.db.cfg_set("dpsCal", dpsCal)
		self.log("Test Finished", passed)

		return passed

