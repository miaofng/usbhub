#!/usr/bin/env python
#coding:utf8
#miaofng@2015-9-26 initial version

import io
import os
import time
import sys, signal
import settings
import imp

swdebug = True
if hasattr(settings, "swdebug"):
	swdebug = settings.swdebug

class Model:
	def Parse(self, fpath):
		fname = os.path.split(fpath)[1]
		[title, ext] = os.path.splitext(fname)

		model = imp.load_source(title, fpath)
		model.name = title
		model.ext = ext
		return model



