#!/usr/bin/env python
#coding:utf8

swdebug = False
swdebug_estop = False
enable_selfcheck = False
scanner_port = "COM12"
plc_port = "COM1"
hmp_port = "COM2"
uctrl_ports = ["", "COM10"]
matrix_port = "COM11"
dmm_port = "USB0::0x0957::0x0607::MY53011514::INSTR"

fixture_mov_timeout = 10
passmark = {
	0: [None, None, None],
	1: ["PMQ7VH1P", "PMQ7WKYY", None],
}

#matrix ch assign of usb dn port vcc
matrix_usb_vcc = {
	0: [0, 14, None, None],
	1: [4, 14, None, None],
	2: [10, 14, None, None],
}

matrix_usb_vdn = {
	0: [2, 14, None, None],
	1: [6, 14, None, None],
	2: None,
}

matrix_usb_vdp = {
	0: None,
	1: [8, 14, None, None],
	2: None,
}
