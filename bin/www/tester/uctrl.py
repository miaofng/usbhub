import time
import serial

class UctrlIoError(Exception): pass

class Uctrl:
	timeout = 5 #unit: S
	def __init__(self, port, baud = 115200):
		self.uart = serial.Serial(port, baud, timeout = self.timeout)
		self.uart.write("shell -a\r")

	def __del__(self):
		self.uart.close()

	def query(self, cmdline):
		self.uart.flushInput()
		self.uart.write(cmdline+"\n\r")
		echo = self.uart.readline()
		if echo[0:2] != "OK":
			raise UctrlIoError

	def mode(self, mode, enable):
		cmdline = "uht %s %s"%(mode, enable)
		self.query(cmdline)

	def reset(self):
		cmdline = "uht init"
		self.uart.write(cmdline+"\n\r")


	def vbat(self, onoff):
		cmdline = "uht sw%s"%onoff
		self.uart.write(cmdline+"\n\r")
