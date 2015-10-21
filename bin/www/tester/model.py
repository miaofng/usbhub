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


class ModelException(Exception):
	def __init__(self, info):
		print >> sys.stderr, info
		sys.stderr.flush()

class Model:
	def __init__(self, station):
		self.station = station
		self.passmark = getattr(settings, "passmark_station%d"%station)

	def usb_parse(self, model, index):
		port = getattr(model, "usb%d"%(index + 1))
		port["index"] = index

		####identify test
		usb_identify = getattr(model, "usb_identify", None)
		usb_identify = getattr(model, "usb_identify%d"%(index + 1), usb_identify)
		if usb_identify is None:
			raise ModelException("usb%d.identify not found"%(index + 1))
		identify = copy.deepcopy(usb_identify)
		identify["passmark"] = self.passmark[index]["normal"]
		port["identify"] = identify

		#benchmark test
		benchmark = None
		if "benchmark" in port:
			benchmark_cfg = port["benchmark"]
			if isinstance(benchmark_cfg, bool):
				if benchmark_cfg:
					benchmark = getattr(model, "usb_benchmark", None)
					benchmark = getattr(model, "usb_benchmark%d"%(index + 1), benchmark)
					if benchmark is None:
						raise ModelException("usb%d.benchmark not found"%(index + 1))
			elif isinstance(benchmark_cfg, dict):
				benchmark = copy.deepcopy(benchmark_cfg)
			else:
				raise ModelException("usb%d.benchmark type unknown"%(index + 1))

		if benchmark is not None:
			benchmark["passmark"] = self.passmark[index]["normal"]

		port["benchmark"] = benchmark

		####hostflip test
		hostflip = None
		if "hostflip" in port:
			hostflip_cfg = port["hostflip"]
			if isinstance(hostflip_cfg, bool):
				if hostflip_cfg is True:
					hostflip_identify = getattr(model, "usb_hostflip_identify", None)
					hostflip_identify = getattr(model, "usb_hostflip_identify%d"%(index + 1), hostflip_identify)
					if hostflip_identify is None:
						raise ModelException("usb%d.hostflip.identify not found"%(index + 1))

					#if benchmark is none, do not test it
					hostflip_benchmark = getattr(model, "usb_hostflip_benchmark", None)
					hostflip_benchmark = getattr(model, "usb_hostflip_benchmark%d"%(index + 1), hostflip_benchmark)

					hostflip_vdn = getattr(model, "usb_hostflip_vdn", None)
					hostflip_vdn = getattr(model, "usb_hostflip_vdn%d"%(index + 1), hostflip_vdn)
					if hostflip_vdn is None:
						raise ModelException("usb%d.hostflip.vdn not found"%(index + 1))

					hostflip_vdp = getattr(model, "usb_hostflip_vdp", None)
					hostflip_vdp = getattr(model, "usb_hostflip_vdp%d"%(index + 1), hostflip_vdp)
					if hostflip_vdp is None:
						raise ModelException("usb%d.hostflip.vdp not found"%(index + 1))

					hostflip = {
						"vdn" : hostflip_vdn,
						"vdp" : hostflip_vdp,
						"identify": hostflip_identify,
						"benchmark": hostflip_benchmark,
					}

			elif isinstance(hostflip_cfg, dict):
				hostflip = copy.deepcopy(hostflip_cfg)
			else:
				raise ModelException("usb%d.hostflip type unknown"%(index+1))

		#fill hostflip matrix channels & passmark
		if hostflip is not None:
			identify = hostflip["identify"]
			identify["passmark"] = self.passmark[index]["hostflip"]

			benchmark = hostflip["benchmark"]
			if benchmark is not None:
				benchmark["passmark"] = self.passmark[index]["hostflip"]

			vdn = hostflip["vdn"]
			vdp = hostflip["vdp"]

			if index == 0:
				vdn["matrix"] = settings.matrix_usb_vdn[1]
				vdp["matrix"] = settings.matrix_usb_vdp[1]
			else:
				raise ModelException("usb%d.hostflip hardware not support"%(index + 1))

			hostflip["vdn"] = vdn
			hostflip["vdp"] = vdp

		port["hostflip"] = hostflip

		####vopen test
		vopen = None
		if "vopen" in port:
			vopen_cfg = port["vopen"]
			if isinstance(vopen_cfg, bool):
				if vopen_cfg is True:
					vopen = getattr(model, "usb_vcc", None)
					vopen = getattr(model, "usb_vcc%d"%(index + 1), vopen)
			elif isinstance(vopen_cfg, dict):
				vopen = copy.deepcopy(vopen_cfg)
			else:
				raise ModelException("usb%d.vopen type unknown"%(index + 1))

		#fill vopen matrix channel
		if vopen is not None:
			vopen["matrix"] = settings.matrix_usb_vcc[index]

		port["vopen"] = vopen

		####vload test
		vload = None
		if "vload" in port:
			vload_cfg = port["vload"]
			if isinstance(vload_cfg, bool):
				if vload_cfg is True:
					vload = getattr(model, "usb_vload", None)
					vload = getattr(model, "usb_vload%d"%(index + 1), vload)
			elif isinstance(vload_cfg, dict):
				vload = copy.deepcopy(vload_cfg)
			else:
				raise ModelException("usb%d.vload type unknown"%(index + 1))

		#fill vload matrix channel
		if vload is not None:
			vload["matrix"] = settings.matrix_usb_vcc[index]

		port["vload"] = vload

		####cdp test
		vcdp = None
		if "cdp" in port:
			cdp_cfg = port["cdp"]
			if isinstance(cdp_cfg, bool):
				if cdp_cfg is True:
					vcdp = getattr(model, "usb_cdp", None)
					vcdp = getattr(model, "usb_cdp%d"%(index + 1), vcdp)
			elif isinstance(cdp_cfg, dict):
				vcdp = copy.deepcopy(cdp_cfg)
			else:
				raise ModelException("usb%d.cdp type unknown"%(index + 1))

		#fill cdp matrix channel
		if vcdp is not None:
			vcdp["matrix"] = settings.matrix_usb_vdn[index]

		port["cdp"] = vcdp

		####scp test
		scp = None
		if "scp" in port:
			scp_cfg = port["scp"]
			if isinstance(scp_cfg, bool):
				if scp_cfg is True:
					vscp = getattr(model, "usb_scp_vcc", None)
					vscp = getattr(model, "usb_scp_vcc%d"%(index + 1), vscp)
					if vscp is None:
						raise ModelException("usb%d.scp.vcc not found"%(index + 1))

					#if vsc is None, do not test
					vrcv = getattr(model, "usb_scp_recover", None)
					vrcv = getattr(model, "usb_scp_recover%d"%(index + 1), vrcv)

					scp = {
						"vscp" : vscp,
						"vrcv" : vrcv,
					}
			elif isinstance(scp_cfg, dict):
				scp = copy.deepcopy(scp_cfg)
			else:
				raise ModelException("usb%d.scp type unknown"%(index + 1))

		#fill scp matrix channel
		if scp is not None:
			vscp = scp["vscp"]
			vrcv = scp["vrcv"]
			vscp["matrix"] = settings.matrix_usb_vcc[index]
			vrcv["matrix"] = settings.matrix_usb_vcc[index]

		port["scp"] = scp
		return port

	def light_parse(self, model):
		feasa = {}
		for ch in model.light:
			light_cfg = model.light[ch]
			light_cfg = copy.deepcopy(light_cfg)
			feasa[ch - 1] = light_cfg
		return feasa

	def Parse(self, fpath):
		fname = os.path.split(fpath)[1]
		[title, ext] = os.path.splitext(fname)

		model = imp.load_source("model.%d"%self.station, fpath)
		model.name = title
		model.ext = ext

		if not hasattr(model, "vbat"):
			raise ModelException("vbat not found")
		model.vbat["matrix"] = settings.matrix_vbat

		if not hasattr(model, "iq"):
			raise ModelException("iq not found")
		model.iq["matrix"] = settings.matrix_ibat

		if not hasattr(model, "i0"):
			raise ModelException("i0 not found")
		model.i0["matrix"] = settings.matrix_ibat

		model.usb_ports = []
		for index in range(0, 3):
			if hasattr(model, "usb%d"%(index+1)):
				port = self.usb_parse(model, index)
				port = copy.deepcopy(port)
				model.usb_ports.append(port)

		if hasattr(model, "light"):
			model.light = self.light_parse(model)

		return model

if __name__ == '__main__':
	model = Model(1)
	model.Parse("./33270327.py")

