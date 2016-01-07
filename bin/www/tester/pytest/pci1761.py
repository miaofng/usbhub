#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

#import win32com.client
#import pythoncom
from ctypes import *
from comtypes.client import *
from instrument import Instrument
import time

# def enum(**enums):
	# return type('Enum', (), enums)

# MAX_DEVICE_DESC_LEN = 64


class Pci1761(Instrument):
	def __init__(self, brd = 0):
		Instrument.__init__(self)
		self.di = di = CreateObject("BDaqOcx.InstantDiCtrl.1")
		self.do = do = CreateObject("BDaqOcx.InstantDoCtrl.1")
		di.setSelectedDevice("PCI-1761,BID#%d"%brd)
		do.setSelectedDevice("PCI-1761,BID#%d"%brd)

	def release(self):
		if self.di:
			self.di.Cleanup()
			self.di = None
		if self.do:
			self.do.Cleanup()
			self.do = None

	def query(self, **arg):
		type = arg["type"]
		port = arg["port"]
		bit = arg["bit"]
		if type == "w":
			data = arg["data"]
			self.do.WriteBit(port, bit, data)
		else:
			data = c_ubyte(0)
			self.di.ReadBit(port, bit, data)
			return data.value

	def get(self, signal):
		return self.query(type="r", port=0, bit=signal)

	def set(self, signal, level):
		self.query(type='w', port=0, bit=signal, data=level)

if __name__ == "__main__":
	from sys import *
	import signal

	card = Pci1761()
	while True:
		time.sleep(0.01)
		level = card.get(0)
		print "\rlevel = %d"%level ,
		card.set(0, level)
