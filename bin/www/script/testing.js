var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')

//to be stored in browser's session
var test = {
	"model": null,
	"mode":"AUTO",
	"mask": 0,
	"bplist":{},

	"ui_status": 'INIT', //'LOADING', 'READY', 'XXX ERROR'
	//show irt server status only when ui_status = 'READY'
};

function gft_load(gft) {
	if(gft.length < 1) {
		return;
	}

	fs.readFile(path.resolve(process.cwd(), gft), "ascii", function (err, content) {
		if(err) {
			alert(err.message);
			return;
		}
		else {
			var model = path.basename(gft, ".gft");
			model = path.basename(model, ".py");
			$('#model').html(model);
			irt.cfg_set("gft_last", path.relative(process.cwd(), gft));
			test.model = model;
			test.ui_status = "READY";
		}
	});
}

function update_state(status, ecode) {
	var state = (test.ui_status != "READY") ? test.ui_status : status;
	var bgcolor = "#ff0000";

	switch(state) {
	case "TESTING":
		bgcolor = "#ffff00";
		break;
	case "READY":
	case "PASS":
		bgcolor = "#00ff00";
		break;
	case "INIT":
	case "LOADING":
		bgcolor = "#c0c0c0";
		break;
	case "ERROR":
		$("#button_run").attr("disabled", true);
	case "FAIL":
	default:
		break;
	}

	$("#result").html(state);
	$("#result").css("background-color", bgcolor);
	$("#result2").html(state);
	$("#result2").css("background-color", bgcolor);
}

//for datafile modification monitoring
var datafile_crc = 0;

function load_report(datafile) {
	fs.readFile(datafile, "ascii", function (err, content) {
		if(err) {
		}
		else {
			crc = crc32.str(content);
			if(crc == datafile_crc) return;
			else datafile_crc = crc;

			content = content.replace(/\[(\w+)\]/gi, function(x) {
				if(x == "[PASS]") return "<span class='record_pass'>[PASS]</span>";
				else return "<span class='record_fail'>[FAIL]</span>";
			});
			var ctrl_table = $("#table");
			var ctrl_table2 = $("#table2");
			ctrl_table.html(content+"\n");
			ctrl_table.scrollTop(ctrl_table[0].scrollHeight);
			ctrl_table2.html(content+"\n");
			ctrl_table2.scrollTop(ctrl_table2[0].scrollHeight);
			//console.timeEnd("result_load");
		}
	});
}

function update_status(status) {
	var date = new Date();
	var sdate = date.toLocaleDateString();
	$("#time_cur").html(date.toTimeString().substr(0, 8));
	$("#date").html(sdate);

	if(status == null)
		return;

	$("#num_pass").html(status.nr_ok);
	$("#num_fail").html(status.nr_ng);
	var total = parseInt(status.nr_ok) + parseInt(status.nr_ng);
	$("#num_total").html(total);
	var passrate = parseFloat(status.nr_ok)/total;
	var failrate = 1 - passrate;
	$("#passrate").html(passrate.toString().substr(0, 5));
	$("#failrate").html(failrate.toString().substr(0, 5));
	$("#time_run").html(status.runtime+"s");
	$("#time_test").html(status.testtime+"s");
	var barcode = status.barcode.trim();
	if (barcode.length > 0) {
		$("#barcode").html(barcode);
	}

	//state update
	$(".idleinput").attr("disabled", status.testing);
	$("#button_run").val((status.testing) ? "STOP" : "RUN");
	$("#button_run").attr("disabled", test.ui_status != "READY");
	update_state(status.status, status.ecode);

	//report update
	var datafile = status.datafile;
	if(datafile != null) {
		load_report(datafile);
	}
}

function timer_tick_update() {
	irt.query("status", function(status) {
		status = JSON.parse(status);
		update_status(status);
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.test != null) {
		test = JSON.parse(session.test);
	}

	$("#button_model").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.py'],
			path: './gft'
		});

		Dialog.getFilePath(function (err, fname) {
			test.ui_status = 'LOADING';
			test.mask = 0;
			irt.query("reset", function(data) {});
			gft_load(fname);
		});
	});

	$("#button_run").click(function(){
		var run = $(this).val();
		if(run == "RUN") {
			irt.cfg_get('gft_last', function(fname) {
				fname = path.resolve(process.cwd(), fname);
				cmdline = [];
				cmdline.push("test");
				cmdline.push("--mode=" + test.mode);
				cmdline.push("--mask=" + test.mask);
				cmdline.push('"'+fname+'"');
				cmdline = cmdline.join(" ");
				irt.query(cmdline, function(data) {});
			});
		}
		else {
			irt.query("stop", function(data) {
			});
		}
	});

	irt.cfg_get('gft_last', function(fname) {
		gft_load(fname);
	});

	var timer_tick = setInterval("timer_tick_update()", 100);
	$(window).unload(function(){
		clearInterval(timer_tick);
		irt.exit();
		session.test = JSON.stringify(test);
	});
});