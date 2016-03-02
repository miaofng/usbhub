var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')

var mode_string = {}
var cwd = null

//to be stored in browser's session
var test = {
	"uid": null, //operator job id
	"mode": "AUTO",

	"tserv_ok": 5, //decrease to 0 => server died

	"model_ok": false,
	"model": null,
	"fname": null,
	"bplist":{},

	/*dialog contents*/
	"estop": false,
	"ims": null,
	"emsg": null,
	"emsg_alive": 0,
};

var settings = {
	"mask": {},
};

function model_sub_redraw(nrow, ncol, mask) {
		$("#mask").hide();

		var html = [];
		var nsubs = nrow * ncol;
		for(var i = 0; i < nsubs; i ++) {
			var name = String.fromCharCode("A".charCodeAt()+i);
			var checked = (i in mask) ?  mask[i] : true;
			checked = (checked) ? "checked" : "";

			div = irt.mlstring(function(){/*
				<div>
					<input class="mask_checkbox" id="mask_$id" type="checkbox" $checked />
					<label for="mask_$id">$name</label>
				</div>
			*/});

			div = div.replace("$id", i);
			div = div.replace("$id", i);
			div = div.replace("$name", name);
			div = div.replace("$checked", checked);
			html.push(div);
		}

		html = html.join("\n");
		$("#mask").html(html);
		$( "#mask input" ).button({
			disabled: true,
		});

		var w = 100/ncol + "%";
		var h = 80/nrow + "%";
		$("#mask div").removeAttr("width").removeAttr("height").css({"width":w, "height":h});
		$("#mask").show();

		$(".ui-state-disabled").removeClass('ui-state-disabled');
}

function gft_load(gft) {
	if(gft.length < 1) {
		return;
	}

	test.fname = null;
	fs.readFile(path.resolve(cwd, gft), "ascii", function (err, content) {
		if(err) {
			alert(err.message);
			return;
		}
		else {
			var i = 0;
			content = content.replace(/\r/g, '');
			content = content.replace(/</g, '&lt;');
			content = content.replace(/>/g, '&gt;');
			content = content.replace(/^/gm, function(x) {
				var span = "<span class='linenr'>"+i+"</span>  "
				var span_bp = "<span class='linenr linenr_bp'>"+i+"</span>  "
				span = (test.bplist[i.toString()]) ? span_bp : span;
				i ++;
				return span;
			});
			$('#gft').html(content+"\n\n");

			//add event handle
			$(".linenr").click(function(){
				var line = $(this).html();
				if(test.bplist[line] == null) {
					//add break point
					$(this).addClass("linenr_bp");
					test.bplist[line] = true;
				}
				else {
					//remove break point
					$(this).removeClass("linenr_bp");
					test.bplist[line] = null;
				}
			});

			test.fname = gft;
			var model = path.basename(gft, ".gft");
			model = path.basename(model, ".py");
			model = model.replace(".learn", "")
			$('#model').html(path.basename(gft, ".gft"));
			irt.cfg_set("gft_last", path.relative(cwd, gft));

			test.model = model;
			test.model_ok = false
			$('#model').css("color", "#ff0000");
			$('#model').attr("title", "setting of model '" + test.model + "' not found");
			irt.model_get(model, function(model) {
				$("#mask").hide();
				if(model == null) {
					return;
				}

				test.model_ok = true;
				$('#model').css("color", "#00ff00");
				$('#model').attr("title", "");
				model_sub_redraw(model.nrow, model.ncol, settings.mask);
			});
		}
	});
}

function update_uut_status(station, info) {
	var bgcolor = "#ffff00";
	state = info.status

	switch(info.status) {
	case "READY":
	case "PASS":
		bgcolor = "#00ff00";
		break;
	case "ERROR":
	case "FAIL":
		bgcolor = "#ff0000";
		break;
	case "WASTE":
		state = "FAIL"
		bgcolor = "#ff0000";
		break;
	default:
		break;
	}

	id_status = "#status"+station
	id_report = "#result"+station

	$(id_status).html(state);
	$(id_status).css("background-color", bgcolor);
	if(info.status.substring(0,4).toUpperCase() == "WAIT") {
		if ((info.barcode.length >= 0) && (info.ScanStart == 1)) {
			$(id_report).css("background-image", "url(../img/scan.gif)");
			$(id_report).css("background-size", "400px 250px");
			$(id_report).css("background-repeat", "no-repeat");
			$(id_report).css("background-position", "center top");
		}
		else {
			$(id_report).css('background', 'transparent');
		}
	}
	else if(info.status == "LOADING") {
		$(id_report).css("background-image", "url(img/up.gif)");
		$(id_report).css("background-size", "200px 150px");
		$(id_report).css("background-repeat", "no-repeat");
		$(id_report).css("background-position", "center top");
	}
	else if(info.status == "LOADED") {
		$(id_report).css("background-image", "url(img/start.png)");
		$(id_report).css("background-size", "400px 300px");
		$(id_report).css("background-repeat", "no-repeat");
		$(id_report).css("background-position", "center top");
	}
	else if(info.status == "WASTE") {
		$(id_report).css("background-image", "url(img/waste.gif)");
		$(id_report).css("background-size", "400px 300px");
		$(id_report).css("background-repeat", "no-repeat");
		$(id_report).css("background-position", "center top");
	}
	else {
		$(id_report).css('background', 'transparent');
	}
}

//for datafile modification monitoring
var datafile_crc = [];

function load_report(id, datafile) {
	if (datafile == null) {
		$(id).html("\n");
		return
	}


	fs.readFile(datafile, "ascii", function (err, content) {
		if(err) {
			content = ''
		}
		else {
			crc = crc32.str(content);
			if(crc == datafile_crc[id]) return;
			else datafile_crc[id] = crc;

			content = content.replace(/(\[PASS\])|(\[FAIL\])/gi, function(x) {
				if(x == "[PASS]") return "<span class='record_pass'>[PASS]</span>";
				else return "<span class='record_fail'>[FAIL]</span>";
			});
		}

		var obj = $(id);
		obj.html(content+"\n");
		//obj.scrollTop(obj[0].scrollHeight);
		div = obj.parent();
		div.scrollTop(div[0].scrollHeight);
	});
}

function update_status(status) {
	//var date = new Date();
	//var sdate = date.toLocaleDateString();
	//$("#time_cur").html(date.toTimeString().substr(0, 8));
	//$("#date").html(sdate);
	if(!status)
		return;

	$("#time_cur").html(status.time);
	$("#date").html(status.date);

	//fixture
	$("#fixture_id").html(status.fixture_id);
	$("#fixture_pressed").html(status.pressed);
	$("#wastes").html(status.wastes);
	$("#ims_saddr").html(status.ims_saddr);

	//run stm update
	$("#time_run").html(status.runtime+"s");
	$(".idleinput").attr("disabled", status.testing);
	$("#button_run").val((status.testing) ? "STOP" : "RUN");

	tests = status.test
	for(i = 0; i < 2; i ++) {
		if (i in tests) {
			test_info = tests[i]
			update_uut_status(i, test_info);
			$("#barcode"+i).html(test_info.barcode);
			$("#duration"+i).html(test_info.duration);
			if("TestStart" in test_info) {
				$("#TestStart"+i).html(test_info.TestStart);
				$("#ScanStart"+i).html(test_info.ScanStart);
			}
			else {
				$("#TestStart"+i).html("&nbsp;");
				$("#ScanStart"+i).html("&nbsp;");
			}
			load_report("#result"+i, test_info.datafile);
		}
	}

	MessageBox(status.emsg, status.ecode)

	if(test.uid) {
		if(status.estop != test.estop) {
			test.estop = status.estop;
			if(test.estop) {
				test.ims = null
				$("#estop_img").attr("src","img/estop.gif");
				$("#estop_txt").html("Emergency Stop!!! Release it, Then Press Reset Button to Continue..")
				$( "#dialog_estop" ).dialog("open");
			}
			else {
				$( "#dialog_estop" ).dialog("close");
			}
		}

		//ims stop?
		if(!test.estop) {
			if(status.ims != test.ims) {
				test.ims = status.ims
				if(test.ims == "StopOrder") {
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

function ecode_translate(src, ecodes) {
	lines = []
	ecodes_table = language_string.ecodes[src]

	line = "$src"
	line = line.replace("$src", src)
	lines.push(line)

	for(item in ecodes) {
		val = ecodes[item]
		if(val == 0) continue

		line = "$mem = 0x$val"
		line = line.replace("$mem", item)
		line = line.replace("$val", val.toString(16))
		//lines.push("")
		//lines.push(line)

		if (ecodes_table) {
			for(i = 0; i < 16; i ++) {
				bit = (val >> i) & 0x01
				if(bit) { //error bit founded
					emsg = ecodes_table[item][i]
					line = '$mem.$i: $emsg'
					line = line.replace("$mem", item)
					line = line.replace("$i", i)
					line = line.replace("$emsg", emsg)
					lines.push(line)
				}
			}
		}
	}

	emsg = lines.join("<br>")
	return emsg
}

function MessageBox(msg, ecode) {
	if(ecode) {
		msg = ecode_translate(msg, ecode);
	}

	if(msg != test.emsg) {
		if(test.emsg_alive > 0) return
		test.emsg = msg
		if(msg.length > 0) {
			$("#warn_txt").html(msg);
			$("#dialog_warn").dialog("open");
			test.emsg_alive = 1
		}
/* 		else {
			$("#dialog_warn").dialog("close");
		} */
	}
	else {
		if(msg.length > 0)
			test.emsg_alive = 1
	}
}

function timer_tick_update() {
	if(test.emsg_alive > 0) {
		test.emsg_alive -= 0.5
		if(test.emsg_alive <= 0) {
			$("#dialog_warn").dialog("close");
		}
	}

	irt.query("status", function(status) {
		test.tserv_ok = 5
		status = JSON.parse(status);
		update_status(status);
	});

	test.tserv_ok -= 1
	if (test.tserv_ok < 0) {
		test.tserv_ok = 0
		emsg = "Tester Died, Please Restart Or Check About Page For Details"
		MessageBox(emsg)
	}

	ready = test.uid != null
	ready &= test.tserv_ok > 0
	ready &= test.model_ok
	//ready |= test.mode == "LEARN"
	ready |= test.mode == "CAL"
	$("#button_run").attr("disabled", !ready);
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
	cwd = session.cwd
	if(session.test) {
		test = JSON.parse(session.test);
	}
	if(session.settings != null) {
		settings = JSON.parse(session.settings);
	}

	language_string = session.language_string
	language_string = JSON.parse(language_string)
	mode_string = language_string.mode

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

	$( "#dialog_uid" ).dialog({
		autoOpen: !test.uid,
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
		height: 280,
		width: 500,
		modal: false,
		hide: {
			effect: "puff",
			duration: 500
		}
	});

	$("#uid").dblclick(function(){
		$("#uid_input").val("");
		$( "#dialog_uid" ).dialog("open");
	})

	$("#uid_input").bind('keydown', function(event){
		var key = event.which;
		if (key == 13) {
			var uid = $("#uid_input").val();
			if(uid.length > 3) {
				test.uid = uid;
				$("#uid").html(test.uid);
				$("#dialog_uid").dialog("close");
			}
		}
	});

	$("#button_login").click(function(){
		var uid = $("#uid_input").val();
		if(uid.length > 3) {
			test.uid = uid;
			$("#uid").html(test.uid);
			$("#dialog_uid").dialog("close");
		}
	});

	var wcl_timer;
	$("#plc_status").dblclick(function(){
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
		cmdline = [];
		cmdline.push("plcw");
		cmdline.push("D1201")
		cmdline.push("0")
		cmdline = cmdline.join(" ");
		irt.query(cmdline, function(data) {});
	})
	$("#wcl_lock").click(function(){
		cmdline = [];
		cmdline.push("plcw");
		cmdline.push("D1201")
		cmdline.push("1")
		cmdline = cmdline.join(" ");
		irt.query(cmdline, function(data) {});
	})

	//$("#uid_input").val(test.uid);
	$("#uid").html(test.uid);

	$("#button_model").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.gft'],
			path: './gft'
		});

		Dialog.getFilePath(function (err, fname) {
			irt.query("reset", function(data) {});
			gft_load(fname);
		});
	});

	$("#button_mode").val(mode_string[test.mode]);
	if(test.mode == "STEP") $("#joystick").show();
	else $("#joystick").hide();

	$("#button_mode").click(function(){
		switch(test.mode) {
		case "AUTO":
			test.mode = "STEP"
			$("#joystick").show();
			//irt.query("wd 1007 1", function(){})
			break;
		case "STEP":
			test.mode = "LEARN"
			$("#joystick").show();
			//irt.query("wd 1007 1", function(){})
			break
		case "LEARN":
			test.mode = "CAL"
			$("#joystick").show();
			//irt.query("wd 1007 1", function(){})
			break
		default:
			test.mode = "AUTO"
			$("#joystick").hide();
			//irt.query("wd 1007 2", function(){})
			break
		}

		$(this).val(mode_string[test.mode]);
	});

	$(".plc").click(function(){
		//console.log("this.id")
		cmdline = [];
		cmdline.push("plcw");
		cmdline.push(this.id)
		cmdline.push("1")
		cmdline = cmdline.join(" ");
		irt.query(cmdline, function(data) {});
	})

	$("#button_run").click(function(){
		test.emsg = ""
		var run = $(this).val();
		if(run == "RUN") {
			irt.cfg_get('gft_last', function(fname) {
				fname = path.resolve(cwd, fname);
				var mask = 0
				for (var i in settings.mask) {
					mask += (settings.mask[i]) ? 0 : (1 << i);
				}

				var tname = "gft";
				var mode = "STEP";
				if(test.mode == "CAL") tname = "cal";
				else if(test.mode == "LEARN") tname = "learn";
				else mode = test.mode;

				cmdline = [];
				cmdline.push("test --test=" + tname);
				cmdline.push("--mode=" + mode);
				cmdline.push("--mask=" + mask);
				cmdline.push('--user="'+ test.uid + '"')
				cmdline.push('"'+fname+'"');
				cmdline = cmdline.join(" ");
				console.log(cmdline);
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

	test.emsg = null
	//MessageBox("fixture", {D98: 255, D99: 255})

	var timer_tick = setInterval("timer_tick_update()", 500);
	var stimer = setInterval("timer_statistics_update()", 1000);

	$(window).unload(function(){
		clearInterval(timer_tick);
		clearInterval(stimer);
		irt.exit();
		session.test = JSON.stringify(test);
	});
});