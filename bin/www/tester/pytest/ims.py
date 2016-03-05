#!/usr/bin/env python
#coding:utf8

from server import Server
from instrument import Instrument
import copy
import array

class IMS(Instrument):
	ims = None

	def __init__(self, ipaddr, port = 5000):
		Instrument.__init__(self)
		self.saddr = saddr = (ipaddr, port)
		self.ims = Server(saddr)

	def update(self, tester, name):
		req = self.ims.recv()
		rx = []
		tx = []
		if req:
			data = req["data"]
			if len(data) == 10:
				for item in data: rx.append(ord(item))

		if len(rx) == 0:
			return

		cmds = {
			0x01: None, #Ready Request
			0x03: "StopOrder", #Stop Command
			0x05: "StartOrder", #Start Command
		}

		cmd = rx[9]
		if cmd in cmds:
			tx = copy.copy(rx)
			tx[1] = 0x0B
			tx[9] = cmd + 1
			tx.append(0x06)
			tx = array.array('B', tx)
			req["data"] = tx.tostring()
			self.ims.send(req)
			return cmds[cmd]

import time
if __name__ == '__main__':
	ims = IMS("127.0.0.1")
	while True:
		time.sleep(0.01)
		cmd = ims.recv()
		if cmd:
			print cmd


