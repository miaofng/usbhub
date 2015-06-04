#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
import sqlite3

class Db:
	def __init__(self):
		self.conn = sqlite3.connect('irt.db')
		def dict_factory(cursor, row):
			d = {}
			for idx, col in enumerate(cursor.description):
				d[col[0]] = row[idx]
			return d
		self.conn.row_factory = dict_factory
	def __del__(self):
		self.conn.close()

	def cfg_get(self, name):
		cursor = self.conn.cursor()
		cursor.execute('SELECT * FROM cfg WHERE name=?', (name,))
		record = cursor.fetchone()
		return record["value"]

	def cfg_set(self, name, value):
		cursor = self.conn.cursor()
		cursor.execute('UPDATE cfg SET value=? WHERE name=?', (str(value), name, ))
		self.conn.commit()

	def model_get(self, name):
		cursor = self.conn.cursor()
		cursor.execute('SELECT * FROM model WHERE name=?', (name,))
		record = cursor.fetchone()
		return record


#module self test
if __name__ == '__main__':
	import json

	db = Db();
	print db.cfg_get('gft_last')
	nr_ok = db.cfg_get('nr_ok')
	nr_ok = int(nr_ok)
	print "nr_ok = %d"%nr_ok
	db.cfg_set("nr_ok", nr_ok + 1)
	name = raw_input("pls input the model name to query:")
	model = db.model_get(name)
	print model
	if model != None:
		barcode = json.loads(model["barcode"])
		#barcode["x"] = barcode["x"] + 1
		print barcode
