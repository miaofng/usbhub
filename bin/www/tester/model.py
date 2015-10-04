#!/usr/bin/env python
#coding:utf8
#miaofng@2015-9-26 initial version

import io
import os
import time
import sys, signal
import settings
import imp
import copy

swdebug = True
if hasattr(settings, "swdebug"):
	swdebug = settings.swdebug

class Model:
	vbat = {
		"name": "UT8.1",
		"desc": "VBAT Voltage",
		"limit": {"min": 13.3, "typ": 13.5, "max": 13.7},
		"matrix": [12, 14, None, None],
	}

	iq = {
		"name": "UT8.2",
		"desc": "Q-Current Draw",
		"limit": {"min": 0.025, "typ": 0.035, "max": 0.045},
		"matrix": [None, 15, 13, None],
	}

	i0 = {
		"name": "UT8.3",
		"desc": "Idle Current Draw",
		"limit": {"min": 0.070, "typ": 0.085, "max": 0.100},
		"matrix": [None, 15, 13, None],
	}

	usb_identify = {
		"name": "UT8.4~5",
		"desc": "USB Port Identification",
	}

	usb_benchmark = {
		"name": "UT8.6",
		"desc": "Data Transfer USB",
		"limit": 50,
	}

	usb_vcc = {
		"name": "UT8.7",
		"desc": "No Load Output Voltage",
		"limit": {"min": 4.75, "typ": 5.12, "max": 5.18},
		"matrix": None,
	}

	usb_vload = {
		"name": "UT8.8",
		"desc": "Maximum Current Output Voltage",
		"limit": { "min": 4.60, "typ": 4.90, "max": 5.25},
		"matrix": None,
	}

	test_usb_bypass_identify = {
		"name": "UT8.9",
		"desc": "Hub Bypass Mode Data",
	}

	usb_bypass_vdn = {
		"name": "UT8.10",
		"desc": "Hub Bypass Mode Charging Vd-",
		"limit": {"min": 2.65, "typ": 2.70, "max": 2.75},
		"matrix": None,
	}

	usb_bypass_vdp = {
		"name": "UT8.10",
		"desc": "Hub Bypass Mode Charging Vd+",
		"limit": {"min": 1.95, "typ": 2.00, "max": 2.05},
		"matrix": None,
	}

	light_white = {
		"name": "UT8.11~12",
		"desc": "Lighting - intensity/color",
	}

	light_blue = {
		"name": "UT8.11~12",
		"desc": "Lighting - intensity/color",
	}

	usb_cdp = {
		"name": "UT8.13",
		"desc": "CDP",
		"limit": {"min": 0.50, "typ": 0.60, "max": 0.70},
		"matrix": None,
	}

	usb_scp = {
		"name": "UT8.14/8.15",
		"desc": "Over-Current Limiting",
		"limit": {"min": -0.1, "typ": 0.0, "max": 0.1},
		"matrix": None,
	}

	usb_rcv = {
		"name": "UT8.16/8.17",
		"desc": "Over-Current Recovery",
		"limit": {"min": 4.75, "typ": 5.00, "max": 5.25},
		"matrix": None,
	}

	usb_ports = [
		{"index": 0},
		{"index": 1},
		{"index": 2},
	]

	def __init__(self, station):
		for port in self.usb_ports:
			port["vopen"] = None
			port["vload"] = None
			port["scp"] = None
			port["cdp"] = None
			port["passthrough"] = None
			port["passmark"] = None

			index = port["index"]
			pmname = settings.passmark[station][index]
			if pmname:
				port["passmark"] = {
					"name": pmname,
					"identify": None,
					"benchmark": None,
				}

	def usb_port_enable(self, index):
		port = self.usb_ports[index]
		vopen = copy.deepcopy(self.usb_vcc)
		vopen["matrix"] = settings.matrix_usb_vcc[index]

		vload = copy.deepcopy(self.usb_vload)
		vload["matrix"] = settings.matrix_usb_vcc[index]

		vscp = copy.deepcopy(self.usb_scp)
		vscp["matrix"] = settings.matrix_usb_vcc[index]
		vrcv = copy.deepcopy(self.usb_rcv)
		vrcv["matrix"] = settings.matrix_usb_vcc[index]
		scp = {"vscp": vscp, "vrcv": vrcv}

		vcdp = None
		if index < 2:
			vcdp = copy.deepcopy(self.usb_cdp)
			vcdp["matrix"] = settings.matrix_usb_vdn[index]

		passthrough = None
		if index == 0:
			vdp = copy.deepcopy(self.usb_bypass_vdp)
			vdp["matrix"] = settings.matrix_usb_vdp[1]
			vdn = copy.deepcopy(self.usb_bypass_vdn)
			vdn["matrix"] = settings.matrix_usb_vdn[1]
			passthrough = {"vdp": vdp, "vdn": vdn}

		identify = copy.deepcopy(self.usb_identify)
		benchmark = copy.deepcopy(self.usb_benchmark)

		port["vopen"] = vopen
		port["vload"] = vload
		port["scp"] = scp
		port["cdp"] = vcdp
		port["passthrough"] = passthrough

		passmark = port["passmark"]
		if passmark:
			passmark["identify"] = identify
			passmark["benchmark"] = benchmark

	def Parse(self, fpath):
		fname = os.path.split(fpath)[1]
		[title, ext] = os.path.splitext(fname)

		self.usb_port_enable(0)
		self.usb_port_enable(1)

		model = imp.load_source(title, fpath)
		model.name = title
		model.ext = ext
		model.vbat = self.vbat
		model.iq = self.iq
		model.i0 = self.i0
		model.usb_ports = self.usb_ports
		model.feasa = self.light_white
		return model



