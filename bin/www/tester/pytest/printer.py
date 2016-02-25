#!/usr/bin/env python
#coding:utf8

import io
import time
import os
import sys, signal
import serial
import serial.tools.list_ports
from instrument import Instrument

class PrinterException(Exception): pass

class Printer(Instrument):
	uart = None

	#error message print variables
	line_max = 0
	line_idx = 0
	pos_x = 0
	pos_y = 0

	#error message print parameters
	pos_x0 = 10
	pos_y0 = 30
	font_width = 22
	font_height = 22
	label_lines = 7

	label_head = "^MCY^XA~TA000~JS0^LT0^MMT^MNW^MTT^PON^PMN^LH0,0^JMA^PR2,2^MD15^JUS^LRN^CI0\n"
	label_tail = "^XZ\n"
	label_line = "^A0N,{fw},{fh}^FO{x},{y}^FD {emsg}^FS\n"

	def print_line(self, info, passed = None):
		if(str(info).find("Test Finished") >= 0):
			if self.line_idx > 0:
				self.write(self.label_tail)

			self.print_init()
			return

		if self.line_idx >= self.line_max:
			return

		if passed != False:
			return

		#print label head
		if self.line_idx % self.label_lines == 0:
			self.write(self.label_head)
			self.pos_x = self.pos_x0
			self.pos_y = self.pos_y0

		#print new line
		zpl = self.label_line.replace("{emsg}", str(info))
		zpl = zpl.replace("{y}", "%d"%self.pos_y)
		self.write(zpl)

		self.pos_y += self.font_height
		self.line_idx += 1

		#print label tail
		if self.line_idx % self.label_lines == 0:
			self.write(self.label_tail)
		elif self.line_idx >= self.line_max:
			self.write(self.label_tail)

	def print_init(self):
		self.label_line = self.label_line.replace("{fw}", "%d"%self.font_width)
		self.label_line = self.label_line.replace("{fh}", "%d"%self.font_height)
		self.label_line = self.label_line.replace("{x}", "%d"%self.pos_x0)
		self.pos_x = self.pos_x0
		self.pos_y = self.pos_y0
		self.line_idx = 0

	def print_label(self, zpl = None):
		if self.line_idx > 0:
			self.print_line("Test Finished")

		self.print_init()
		self.write(zpl)

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def on_event_add(self, tester, name):
		n = tester.db.cfg_get("print_elines")
		self.line_max = int(n)
		self.print_init()

	def __init__(self, port = None, baud = 9600):
		self.uart = serial.Serial(port, baud)

	def __del__(self):
		self.release()

	def write(self, zpl = None):
		self.uart.write(str(zpl))

if __name__ == '__main__':
	printer = Printer(settings.scanner_port)
	printer.write("""
		1
		22
		3333
	""")


