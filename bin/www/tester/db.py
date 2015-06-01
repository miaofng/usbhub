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
		return record["value"];

#module self test
if __name__ == '__main__':
	db = Db();
	print db.cfg_get('gft_last')

