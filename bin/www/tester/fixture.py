#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

from pytest import Pci1761

class Fixture(Pci1761):
	def IsReady(self):
		return self.get(0) #in 0
		
	def Pass(self):
		self.set(0, 1) #out 0
		self.set(1, 0)
		
	def Fail(self): #out 1
		self.set(0, 0)
		self.set(1, 1)

	def scan_IsReady(self):
		return self.get(1) #in 1
		
	def scan_Pass(self):
		self.set(2, 1) #out 2
		self.set(3, 0)

	def scan_Fail(self):
		self.set(2, 0)
		self.set(3, 1) #out 3
