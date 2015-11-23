#barcode limitation set
#'?': ignore one char
#'*': ignore all following char
#barcode: "332703260140-003-00102921715500342"
barcode = "33270330*" #1USB+SD-BLUE
fixture_id = 4

vbat = {
	"name": "UT8.1",
	"desc": "VBAT Voltage",
	"limit": {"min": 13.3, "typ": 13.5, "max": 13.7},
}

iq = {
	"name": "UT8.2",
	"desc": "Q-Current Draw",
	"limit": {"min": 0.008, "typ": 0.013, "max": 0.020},
}

i0 = {
	"name": "UT8.3",
	"desc": "Idle Current Draw",
	"limit": {"min": 0.008, "typ": 0.013, "max": 0.020},
}

#usb port general limit settings
usb_identify = {
	"name": "UT8.4~5",
	"desc": "USB Port Identification",
	"limit": None,
}

usb_benchmark = {
	"name": "UT8.6",
	"desc": "USB Transfer Speed",
	"limit": {"w_mbps_min": 50, "r_mbps_min": 50, "a_mbps_min": 50},
}

usb_vcc = {
	"name": "UT8.7",
	"desc": "Vbus@0A",
	"limit": {"min": 4.70, "typ": 5.12, "max": 5.18},
	"ripple": {"max": 0.5},
}

usb_vload = {
	"name": "UT8.8",
	"desc": "Vbus@2.5A",
	"limit": { "min": 4.50, "typ": 4.90, "max": 5.25},
	"ripple": {"max": 0.5},
}

usb_hostflip_identify = {
	"name": "UT8.9",
	"desc": "Host Flip Mode Identify",
}

usb_hostflip_vdn = {
	"name": "UT8.10",
	"desc": "Host Flip Mode Vd-",
	"limit": {"min": 2.65, "typ": 2.70, "max": 2.75},
}

usb_hostflip_vdp = {
	"name": "UT8.10",
	"desc": "Host Flip Mode Vd+",
	"limit": {"min": 1.95, "typ": 2.00, "max": 2.05},
}

light_white = {
	"name": "UT8.11~12",
	"desc": "Lighting",
	"limit": {
		"min": [0.280, 0.280, 0.100, 1000,   0],
		"typ": [0.330, 0.330, 0.400, 4000,  50],
		"max": [0.380, 0.380, 0.700, 7000, 100],
	}
}

light_blue = {
	"name": "UT8.11~12",
	"desc": "Lighting",
	"limit": {
		"min": [0.137, 0.225, 0.020,  200, 150],
		"typ": [0.187, 0.275, 0.400, 4000, 170],
		"max": [0.290, 0.420, 0.700, 7000, 198],
	}
}

usb_cdp = {
	"name": "UT8.13",
	"desc": "CDP Vd-",
	"limit": {"min": 0.50, "typ": 0.60, "max": 0.70},
}

usb_scp_vcc = {
	"name": "UT8.14/8.15",
	"desc": "Vbus@5A",
	"limit": {"min": -0.1, "typ": 0.0, "max": 0.1},
	#"ripple": {"max": 0.5},
}

usb_scp_recover = {
	"name": "UT8.16/8.17",
	"desc": "Vbus@0A Recovery",
	"limit": {"min": 4.75, "typ": 5.00, "max": 5.25},
	#"ripple": {"max": 0.5},
}

#test detail configuration:
#
#test name = {
#  usb1, usb2, usb3, feasa, sd, aux-r, aux-f, apx1, apx2
#}
#
#test item = {
#  benchmark	: usb - passmark speed test, about 3s
#  hostflip	    : usb - exchange down&up stream port
#  carplay		: usb - apple's carplay detection
#  vopen		: usb - open load test
#  vload		: usb - loaded test
#  cdp			: usb - charge device port test
#  scp			: usb - short test
#}

usb1 = {
	"benchmark": True,
	"hostflip" : False,

	"vopen": True,
	"vload": True,

	"cdp": True,
	"scp": True,
}

usb2 = {
	"benchmark": True,
	"hostflip" : False,

	"vopen": True,
	"vload": True,

	"cdp": True,
	"scp": True,
}

sd = {
    "desc": "Data Transfer Speed",
    "cid": "4a1899dd12443222",
    "limit": {
        "w_mbps_min": 1.0, #MBps
        "r_mbps_min": 8.0,
    },
}

light = {
    1: light_blue,
    2: light_blue,
    3: light_blue,
    4: light_blue,
    5: light_blue,
}
