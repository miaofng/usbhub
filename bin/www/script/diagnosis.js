var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')
var sprintf = require('sprintf-js').sprintf

//to be stored in browser's session
var diagnosis = {
	scan_status: {},
	minputs: null,
};

var scan_status = null;

function grid_clean(type)
{
	bpos = 0;
	curr = 1024;

	if(type == "delta") {
		diag_status = diagnosis.scan_status;
		if(diag_status != null) {
			if(diag_status.mode == "PROBE") {
				id = diag_status.curr + 1;
				$('#'+id).css("background-color", "white");
				diagnosis.scan_status = null;
				return;
			}

			bpos = diag_status.bpos;
			curr = diag_status.curr;
		}
	}

	diagnosis.scan_status = null;
	for(i = 0; i <= curr; i ++) {
		id = i + bpos + 1;
		$('#'+id).css("background-color", "white");
	}
}

function bit_get(bitm, bpos) {
	word = Math.floor(i / 32);
	bpos = i % 32;
	v = bitm[word] >> bpos;//(1 << bpos);
	v = (v & 1) ? true : false;
	return v;
}

function grid_show(scan_status, type)
{
	if(scan_status == null)
		return;

	//probe
	if(scan_status.mode == "PROBE") {
		grid_clean("delta");
		id = scan_status.curr + 1;
		$('#'+id).css("background-color", "#00FF00");
		diagnosis.scan_status = scan_status;
		return;
	}

	i = 0;
	if(type == "delta") {
		diag_status = diagnosis.scan_status;
		if(diag_status != null) {
			i = diag_status.curr;
		}
	}

	bitm = scan_status.bitm;
	bpos = scan_status.bpos;
	curr = scan_status.curr;

	for(; i <= curr; i ++) {
		if(i >= 0) {
			pass = bit_get(bitm, i);
			id = i + bpos + 1;
			if(pass)
				$('#'+id).css("background-color", "#00ff00");
			else
				$('#'+id).css("background-color", "#ff0000");
		}
	}

	diagnosis.scan_status = scan_status;
}

function grid_init()
{
	var html = []

	//create table head
	count = 0
	for(slot = -1; slot < 32; slot ++) {
		ul = []

		if(slot < 0) {
			ul.push('<ul class="head">')
			ul.push('<li></li>')
		}
		else {
			ul.push('<ul>')
			n = slot + 1
			ul.push('<li class="head">' + n + '</li>')
		}

		for(line = 0; line < 32; line ++) {
			if(slot >= 0) {
				n = slot * 32 + line
				n = n + 1
				ul.push('<li id="' + n + '">' + n + '</li>')
			}
			else {
				n = line + 1
				ul.push('<li>' + n + '</li>')
			}
		}

		ul.push('</ul>')
		html.push(ul.join(' '));
	}

	$('#list').html(html.join('\r\n'));
	grid_show(diagnosis.scan_status, "all")
}

function trim(str)
{
	return str.replace(/(^\s*)|(\s*$)/g,"");
}

function meas_generate_file(cb)
{
	//save settings
	ctrls = $(".minput")
	minputs = {}
	for(var i = 0; i < ctrls.length; i ++) {
		ctrl = ctrls[i]
		minputs[ctrl.id] = ctrl.value
	}
	diagnosis.minputs = minputs

	bin_dir = process.cwd();
	gft_path = path.join(bin_dir, "manual_measure.gft");
	date = new Date();
	type = minputs.meas_type
	mA = minputs.meas_mA
	hv = minputs.meas_hv
	A = minputs.meas_A
	B = minputs.meas_B
	rly = trim(minputs.meas_rly)
	if (rly.length > 0) {
		rly = rly.replace(/;/g, "\r\n")
		rly = "X\r\n" + rly + "\r\nW3\r\n"
	}

	A = parseInt(A);
	B = parseInt(B);

	err  = isNaN(A);
	err |= isNaN(B);
	err |= A <= 0;
	err |= B <= 0;
	err |= A > 1024;
	err |= B > 1024;
	if (err) {
		alert("Illegal input value !!!");
		return;
	}

	gft = [];
	line = sprintf("//%s %s",
		date.toLocaleDateString(),
		date.toTimeString().substr(0, 8)
	);
	gft.push(line);
	gft.push("O2,6,10,11 <Continuity & Leakage>");
	gft.push("")

	switch(type) {
	case "D":
		gft.push("[DIODE CHECK]");
		//32mS, <1000ohm
		line = sprintf("R01%s3001", mA);
		gft.push(line);
		if(rly.length > 0) {
			gft.push(rly.toUpperCase());
		}
		line = sprintf("A%d", A);
		gft.push(line);
		line = sprintf("	B%d", B);
		gft.push(line);
		gft.push("[DIODE END]");
		break;
	case "R":
		//32mS, <1000ohm
		line = sprintf("R01%s3001", mA);
		gft.push(line);
		if(rly.length > 0) {
			gft.push(rly.toUpperCase());
		}
		line = sprintf("A%d", A);
		gft.push(line);
		line = sprintf("	B%d", B);
		gft.push(line);
		break;
	case "L":
		//16mS, >1Mohm
		line = sprintf("L00%s0001", hv);
		gft.push(line);
		if(rly.length > 0) {
			gft.push(rly.toUpperCase());
		}
		line = sprintf("A%d", A);
		gft.push(line);
		line = sprintf("A%d", B);
		gft.push(line);
		break;
	default:
		break;
	}

	//gft.push("");
	//gft.push("O2,10,11");
	//gft.push("R0140010");
	//gft.push("L0140010");
	if(rly.length > 0) {
		//gft.push("X");
	}
	gft.push("")
	gft.push("<END OF PROGRAM>");

	gft = gft.join("\r\n");
	fs.writeFile(gft_path, gft, function (err) {
		if (err) throw err;
		cb(gft_path)
	});
}

var datafile_crc = [];
function load_report(id, datafile) {
	if (datafile == null)
		return

	fs.readFile(datafile, "ascii", function (err, content) {
		if(err) {
			content = ''
		}
		else {
			crc = crc32.str(content);
			if(crc == datafile_crc[id]) return;
			else datafile_crc[id] = crc;

			content = content.replace(/.*\[FAIL\]$/gmi, function(x) {
				return "<span class='record_fail'>"+x+"</span>";
			});
		}

		var obj = $(id);
		obj.html(content+"\n");
		//obj.scrollTop(obj[0].scrollHeight);
		div = obj.parent();
		div.scrollTop(div[0].scrollHeight);
	});
}

function tick_update()
{
	irt.query("status", function(data) {
		data = JSON.parse(data);
		load_report("#report", data.test[0].datafile)
		if(data.testing) {
			$("#scan").val("STOP");
			$("#meas_run").attr("disabled", true);
			$("#scan_type").attr("disabled", true);
			$("#scan_slot").attr("disabled", true);
		}
		else {
			$("#scan").val("RUN");
			$("#meas_run").attr("disabled", false);
			$("#scan_type").attr("disabled", false);
			$("#scan_slot").attr("disabled", $("#scan_type").val() != "SLOT");
		}

	});

	irt.query("scan", function(data) {
		scan_status = JSON.parse(data);
		grid_show(scan_status, "delta");
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.diagnosis != null) {
		diagnosis = JSON.parse(session.diagnosis);
	}

	minputs = diagnosis.minputs
	if(minputs != null) {
		for (ctrl_id in minputs) {
			$("#"+ctrl_id).val(minputs[ctrl_id])
		}
	}

	grid_init()
	$("#scan_type").change(function() {
		$("#scan_slot").attr("disabled", this.value != "SLOT");
		grid_clean("all");
	})
	$("#scan_slot").change(function() {
		grid_clean("all");
	})
	$("#meas_type").change(function() {
		//$("#meas_rly").attr("disabled", this.value[1] != "@");
		$("#meas_mA").attr("disabled", this.value == "L");
		$("#meas_hv").attr("disabled", this.value != "L");
	})

	$("#meas_run").click(function(){
		meas_generate_file(function(gft_path) {
			//alert("ok");
			cmdline = [];
			cmdline.push("test");
			cmdline.push("--test=gft");
			cmdline.push("--mode=STEP");
			cmdline.push('"$path"'.replace("$path", gft_path));
			cmdline = cmdline.join(" ");
			console.log(cmdline)
			irt.query(cmdline, function(data) {});
		});
	});

	$("#scan").click(function(){
		cmdline = [];
		if($(this).val() == "RUN") {
			grid_clean("delta");
			scan_type = $("#scan_type").val();
			scan_slot = $("#scan_slot").val();

			cmdline.push("test");
			cmdline.push("--test=scn");
			cmdline.push(scan_type);
			cmdline.push(scan_slot);
			cmdline = cmdline.join(" ");
		}
		else {
			cmdline.push("stop");
		}

		irt.query(cmdline, function(data) {});
	});

	var tick = setInterval("tick_update()", 100);
	$(window).unload(function(){
		clearInterval(tick);
		irt.exit();
		session.diagnosis = JSON.stringify(diagnosis);
	});
});