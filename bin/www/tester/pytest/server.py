#!/usr/bin/env python
#coding:utf8

import socket
import select
import Queue
import time
import sys

class Server:
	imsg = {}
	omsg = {}

	def __init__(self, saddr):
		print 'irt server init .. %s:%d '%saddr
		self._server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self._server.setblocking(False)
		self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._server.bind(saddr)
		self._server.listen(100)
		self._inputs = [self._server]
		self._outputs = []

	def __del__(self):
		for s in self._inputs:
			s.close()

	def clear(self, sock):
		if sock is self._server:
			return

		if sock in self._inputs:
			self._inputs.remove(sock)

		if sock in self._outputs:
			self._outputs.remove(sock)

		sock.close()

		del self.imsg[sock]
		del self.omsg[sock]

	def _update(self):
		rs,ws,es = select.select(self._inputs, self._outputs, self._inputs, 0)
		if not (rs or ws or es):
			return

		for s in rs:
			if s is self._server:
				conn,addr = s.accept()
				#print 'connect by',addr
				conn.setblocking(False)
				if len(self._inputs) > 64:
					print "inputs = %d"%len(self._inputs)
					for sock in self._inputs[1:32]:
						self.clear(sock)
						if sock in ws:
							ws.remove(sock)

				self._inputs.append(conn)
				self.imsg[conn] = Queue.Queue()
				self.omsg[conn] = Queue.Queue()
			else:
				#print 'recv ok...'
				try:
					data = s.recv(1024)
				except socket.error:
					data = None

				if data:
					#print data
					self.imsg[s].put(data)
				else:
					#socket close
					self.clear(s)
					if s in ws:
						ws.remove(s)

		for s in ws:
			try:
				msg = self.omsg[s].get_nowait()
			except Queue.Empty:
				self._outputs.remove(s)
			else:
				s.send(msg)

		for s in es:
			self.clear(s)

	def recv(self):
		self._update()
		for s in self.imsg.keys():
			try:
				msg = self.imsg[s].get_nowait()
			except Queue.Empty:
				continue
			else:
				req = {}
				req["sock"] = s
				req["data"] = msg
				return req

	def send(self, req):
		s = req["sock"]
		self.omsg[s].put(req["data"])
		if s not in self._outputs:
			self._outputs.append(s)
			#print "outputs = %d"%len(self._outputs)


