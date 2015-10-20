#!/usr/bin/env python
#coding:utf8

swdebug = False
swdebug_estop = False
enable_selfcheck = False
scanner_port = "COM21"
plc_port = "COM20"
hmp_port = "COM19"
uctrl_ports = ["COM18", "COM8"]
matrix_port = "COM11"
feasa_ports = ["", "COM14"]
ims_port = 10000
rasp_ips = ["192.168.20.11", "192.168.8.11"]
dmm_port = "USB0::0x0957::0x0607::MY53011514::INSTR"

fixture_mov_timeout = 10
passmark_station0 = {
	0: {"normal": None, "hostflip": None},
	1: {"normal": None, "hostflip": None},
	2: {"normal": None, "hostflip": None},
}

passmark_station1 = {
	0: {"normal": "PMQ7VH1P", "hostflip": "PMQ7VH1P"},
	1: {"normal": "PMQ7WKYY", "hostflip": None},
	2: {"normal": None, "hostflip": None},
}

#matrix assignments
#matrix bus:  V+ V-/I- I+ NC

matrix_vbat = [12, 14, None, None]
matrix_ibat = [None, 15, 13, None]

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
