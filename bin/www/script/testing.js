var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')

//to be stored in browser's session
var test = {
	"jid": null, //operator job id
	"model": null,
	"mode": "AUTO",
	"bplist":{},
	"fname": null,

	"ui_status": 'Starting...', //'LOADING', 'READY', 'XXX ERROR'
	//show irt server status only when ui_status = 'READY'
};

function gft_load(gft) {
	if(gft.length < 1) {
		return;
	}

	test.fname = null;
	fs.readFile(path.resolve(process.cwd(), gft), "ascii", function (err, content) {
		if(err) {
			alert(err.message);
			return;
		}
		else {
			test.fname = gft;
			var model = path.basename(gft, ".gft");
			model = path.basename(model, ".py");
			$('#model').html(model);
			irt.cfg_set("gft_last", path.relative(process.cwd(), gft));
			test.model = model;
			test.ui_status = "READY";
		}
	});
}

function update_state(station, status, testing) {
	//var state = status = (test.ui_status != "READY") ? test.ui_status : status;
	var state = status = (testing) ? status : test.ui_status;
	var bgcolor = "#ff0000";

	switch(state) {
	case "Starting...":
		$("#button_run").attr("disabled", true);
	case "SCANING":
	case "LOADING":
	case "LOADED":
	case "TESTING":
	case "IDLE":
		bgcolor = "#ffff00";
		break;
	case "READY":
	case "PASS":
		bgcolor = "#00ff00";
		break;
	case "INIT":
		bgcolor = "#c0c0c0";
		break;
	case "ERROR":
	case "FAULT":
		$("#button_run").attr("disabled", true);
	case "FAIL":
	case "WASTE":
		status = "FAIL";
	default:
		break;
	}

	id_status = "#status"+station
	id_result = "#result"+station

	$(id_status).html(status);
	$(id_status).css("background-color", bgcolor);
	if(state == "SCANING") {
		$(id_result).css("background-image", "url(img/scan.gif)");
		$(id_result).css("background-size", "400px 250px");
		$(id_result).css("background-repeat", "no-repeat");
		$(id_result).css("background-position", "center top");
	}
	else if(state == "LOADING") {
		$(id_result).css("background-image", "url(img/up.gif)");
		$(id_result).css("background-size", "200px 150px");
		$(id_result).css("background-repeat", "no-repeat");
		$(id_result).css("background-position", "center top");
	}
	else if(state == "LOADED") {
		$(id_result).css("background-image", "url(img/start.png)");
		$(id_result).css("background-size", "400px 300px");
		$(id_result).css("background-repeat", "no-repeat");
		$(id_result).css("background-position", "center top");
	}
	else if(state == "WASTE") {
		$(id_result).css("background-image", "url(img/waste.gif)");
		$(id_result).css("background-size", "400px 300px");
		$(id_result).css("background-repeat", "no-repeat");
		$(id_result).css("background-position", "center top");
	}
	else {
		$(id_result).css('background', 'transparent');
	}
}

//for datafile modification monitoring
var datafile_crc = [];

function load_report(id, datafile) {
	fs.readFile(datafile, "ascii", function (err, content) {
		if(err) {
			content = ''
		}
		else {
			crc = crc32.str(content);
			if(crc == datafile_crc[id]) return;
			else datafile_crc[id] = crc;

			content = content.replace(/\[(\w+)\]/gi, function(x) {
				if(x == "[PASS]") return "<span class='record_pass'>[PASS]</span>";
				else return "<span class='record_fail'>[FAIL]</span>";
			});
		}

		var obj = $(id);
		obj.html(content+"\n");
		obj.scrollTop(obj[0].scrollHeight);
	});
}

var estop = false
var ims = null
var emsg = null

function update_status(status) {
	var date = new Date();
	//var sdate = date.toLocaleDateString();
	//$("#time_cur").html(date.toTimeString().substr(0, 8));
	//$("#date").html(sdate);
	$("#time_cur").html(status.time);
	$("#date").html(status.date);

	if(!status)
		return;

	//fixture
	$("#fixture_id").html(status.fixture_id);
	$("#fixture_pressed").html(status.pressed);
	$("#wastes").html(status.wastes);
	$("#ims_saddr").html(status.ims_saddr);

	//run stm update
	$("#time_run").html(status.runtime+"s");
	$(".idleinput").attr("disabled", status.testing);
	$("#button_run").val((status.testing) ? "STOP" : "RUN");
	$("#button_run").attr("disabled", test.ui_status != "READY");

	//barcode
	$("#barcode0").html(status.barcode[0]);
	$("#barcode1").html(status.barcode[1]);
	$("#duration0").html(status.duration[0]);
	$("#duration1").html(status.duration[1]);

	//status update
	update_state(0, status.status[0], status.testing);
	update_state(1, status.status[1], status.testing);

	//report update
	load_report("#result0", status.datafile[0]);
	load_report("#result1", status.datafile[1]);

	if(status.emsg != emsg) {
		emsg = status.emsg;
		if(emsg.length > 0) {
			$("#warn_txt").html(emsg);
			$("#dialog_warn").dialog("open");
		}
		else {
			$("#dialog_warn").dialog("close");
		}
	}

	if(test.jid) {
		if(status.estop != estop) {
			estop = status.estop;
			if(estop) {
				ims = null
				$("#estop_img").attr("src","img/estop.gif");
				$("#estop_txt").html("Emergency Stop!!! Release it, Then Press Reset Button to Continue..")
				$( "#dialog_estop" ).dialog("open");
			}
			else {
				$( "#dialog_estop" ).dialog("close");
			}
		}

		//ims stop?
		if(!estop) {
			if(status.ims != ims) {
				ims = status.ims
				if(ims == "StopOrder") {
					$("#estop_img").attr("src","img/ims.png");
					$("#estop_txt").html("IMS Stop!!! Tester Is Under Remote Control, Please Wait ...")
					$( "#dialog_estop" ).dialog("open");
				}
				else {
					$( "#dialog_estop" ).dialog("close");
				}
			}
		}
	}
}

function timer_tick_update() {
	irt.query("status", function(status) {
		status = JSON.parse(status);
		update_status(status);
	});
}

function wcl_update() {
	irt.waste_query("plc", function(data) {
		data = JSON.parse(data);
		control = data.control;
		locked = control[1]&(1 << 2); //101.02
		if(locked) $("#wcl_image").attr("src","img/box_lock.png");
		else $("#wcl_image").attr("src","img/box_unlock.png");
	});
}

function timer_statistics_update() {
	if (!test.model)
		return;

	var nr_ok = [0, 0];
	var nr_ng = [0, 0];
	irt.test_stat(test.model, function(rows){
		rows.forEach(function(row, index){
			if(row.station == 1) {
				if(row.failed == 0) {
					nr_ok[1] += row.count;
				}
				else {
					nr_ng[1] += row.count;
				}
			}
			else {
				if(row.failed == 0) {
					nr_ok[0] += row.count;
				}
				else {
					nr_ng[0] += row.count;
				}
			}
		});

		$("#num_pass0").html(nr_ok[0]);
		$("#num_pass1").html(nr_ok[1]);

		$("#num_fail0").html(nr_ng[0]);
		$("#num_fail1").html(nr_ng[1]);

		var total0 = parseInt(nr_ok[0]) + parseInt(nr_ng[0]);
		var total1 = parseInt(nr_ok[1]) + parseInt(nr_ng[1]);
		$("#num_total0").html(total0);
		$("#num_total1").html(total1);

		var passrate0 = parseFloat(nr_ok[0])/total0 + 0.000001;
		var failrate0 = 1.00001 - passrate0;
		var passrate1 = parseFloat(nr_ok[1])/total1 + 0.000001;
		var failrate1 = 1.00001 - passrate1;
		$("#passrate0").html(passrate0.toString().substr(0, 5));
		$("#failrate0").html(failrate0.toString().substr(0, 5));
		$("#passrate1").html(passrate1.toString().substr(0, 5));
		$("#failrate1").html(failrate1.toString().substr(0, 5));
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.test) {
		test = JSON.parse(session.test);
	}

	$( "#dialog_estop" ).dialog({
		autoOpen: false,
		closeOnEscape: false,
		dialogClass: "no-close",
		height: 250,
		width: 500,
		modal: true,
		show: {
			effect: "bounce",
			duration: 500
		},
		hide: {
			effect: "explode",
			duration: 500
		}
	});

	$( "#dialog_jid" ).dialog({
		autoOpen: !test.jid,
		closeOnEscape: false,
		dialogClass: "no-close",
		height: 250,
		width: 500,
		modal: true,
		hide: {
			effect: "puff",
			duration: 500
		}
	});

	$( "#dialog_warn" ).dialog({
		autoOpen: false,
		closeOnEscape: true,
		height: 250,
		width: 500,
		modal: false,
		hide: {
			effect: "puff",
			duration: 500
		}
	});

	$("#jid").dblclick(function(){
		$("#jid_input").val("");
		$( "#dialog_jid" ).dialog("open");
	})

	$("#jid_input").bind('keydown', function(event){
		var key = event.which;
		if (key == 13) {
			var jid = $("#jid_input").val();
			if(jid.length > 3) {
				test.jid = jid;
				$("#jid").html(test.jid);
				$("#dialog_jid").dialog("close");
			}
		}
	});

	$("#button_login").click(function(){
		var jid = $("#jid_input").val();
		if(jid.length > 3) {
			test.jid = jid;
			$("#jid").html(test.jid);
			$("#dialog_jid").dialog("close");
		}
	});

	var wcl_timer;
	$("#wastes").dblclick(function(){
		mode_nxt = $("#button_run").val()
		//alert(mode_nxt)
		if(mode_nxt == "RUN") {
			$( "#dialog_wcl" ).dialog("open");
			wcl_timer = setInterval("wcl_update()", 800);
		}
	})

	$( "#dialog_wcl" ).dialog({
		autoOpen: false,
		height: 290,
		width: 500,
		modal: true,
		hide: {
			effect: "explode",
			duration: 500
		},
		close: function(){
			clearInterval(wcl_timer);
			$("#wcl_passwd").val("");
			$("#wcl_lock").attr("disabled", true);
			$("#wcl_unlock").attr("disabled", true);
		}
	});

	$("#wcl_passwd").bind('keydown', function(event){
		var key = event.which;
		if (key == 13) {
			var passwd = $("#wcl_passwd").val();
			irt.cfg_get('waste_passwd', function(data) {
				if(passwd == data) {
					$("#wcl_lock").attr("disabled", false);
					$("#wcl_unlock").attr("disabled", false);
				}
				else {
					alert("Password Error, Please Retry");
				}
			});
		}
	});

	$("#wcl_unlock").click(function(){
		//plc 301.02 0
		irt.waste_query("plc waste_door unlock", function(data) {
		});
	})
	$("#wcl_lock").click(function(){
		//plc 301.02 1
		irt.waste_query("plc waste_door lock", function(data) {
		});
	})

	//$("#jid_input").val(test.jid);
	$("#jid").html(test.jid);

	$("#button_model").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.py'],
			path: './gft'
		});

		Dialog.getFilePath(function (err, fname) {
			test.ui_status = 'Starting...';
			irt.query("reset", function(data) {});
			gft_load(fname);
		});
	});

	$("#button_mode").val(test.mode);
	$("#button_mode").click(function(){
		if(test.mode == "AUTO") test.mode = "STEP";
		else if(test.mode == "STEP") test.mode = "CAL"
		else test.mode = "AUTO";
		$(this).val(test.mode);
	});

	$("#button_run").click(function(){
		emsg = ""
		var run = $(this).val();
		if(run == "RUN") {
			irt.cfg_get('gft_last', function(fname) {
				fname = path.resolve(process.cwd(), fname);
				cmdline = [];
				cmdline.push("test");
				cmdline.push("--mode=" + test.mode);
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
		//test.fname = fname;
	});

	if (test.fname != null) {
		gft_load(test.fname);
	}

	update_state(0, test.ui_status, 0);
	update_state(1, test.ui_status, 0);

	var timer_tick = setInterval("timer_tick_update()", 500);
	var stimer = setInterval("timer_statistics_update()", 1000);

	$(window).unload(function(){
		clearInterval(timer_tick);
		clearInterval(stimer);
		irt.exit();
		session.test = JSON.stringify(test);
	});
});