import io
import os
import time
import sys, signal
import threading
import traceback

#class UctrlIoError(Exception): pass

class Eloger:
	def __init__(self, e = None):
		if e is not None:
			stack = ''.join(traceback.format_exception(*sys.exc_info()))
			self.log(stack)

	def log(self, info = ""):
		file = open("./log.txt", "a+")
		line = "%s#  %s\n"%(time.strftime('%X'), info)
		file.write(line)
		file.close()

if __name__ == '__main__':
	class ElogNoError(Exception): pass
	try:
		raise ElogNoError
	except Exception as e:
		Eloger(e)

	loger = Eloger()
	loger.log("loger.log ok")