#!/usr/bin/env python
#coding:utf8

import socket
import select
import Queue
from time import sleep
import sys

server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setblocking(False)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

saddr = ('localhost',30001)
server.bind(saddr)
server.listen(10)

inputs = [server]
outputs = []

msg_queues = {}
timeout = 20

while inputs:
	rs,ws,es = select.select(inputs, outputs, inputs, timeout)
	if not (rs or ws or es):
		print 'timeout...'
		continue

	for s in rs:
		if s is server:
			conn,addr = s.accept()
			print 'connect by',addr
			conn.setblocking(False)
			inputs.append(conn)
			msg_queues[conn] = Queue.Queue()
		else:
			print 'recv ok...'
			data = s.recv(1024)
			if data:
				print data
				msg_queues[s].put(data)
				if s not in outputs:
					outputs.append(s)
			else:
				if s in outputs:
					outputs.remove(s)
				inputs.remove(s)
				s.close()
				del msg_queues[s]

	for s in ws:
		print 'writable ..'
		try:
			msg = msg_queues[s].get_nowait()
		except Queue.Empty:
			print 'msg empty'
			outputs.remove(s)
		else:
			s.send(msg)

	for s in es:
		print 'except ',s.getpeername()
		if s in inputs:
			inputs.remove(s)
		if s in outputs:
			outputs.remove(s)
		s.close()
		del msg_queues[s]
