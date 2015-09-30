import time
import serial

class UctrlIoError(Exception): pass

class Uctrl:
	def __init__(self, port, baud = 115200):
		self.uart = serial.Serial(self.com,self.baud)
		self.uart.write("shell -a\r")

	def __del__(self):
		self.uart.close()

	def query(self, cmdline):
		self.uart.flushInput()
		self.uart.write(command+"\n\r")
		echo = self.uart.readline()
		if echo[0:2] != "OK":
			raise UctrlIoError

	def mode(self, mode, enable):
		cmdline = "uht %s %s"%(mode, enable)
		self.query(cmdline)

	def reset(self):
		cmdline = "uht init"
		self.query(cmdline)

	def vbat(self, onoff):
		cmdline = "uht sw%s"%onoff
		self.query(cmdline)
