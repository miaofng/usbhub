var irt = window.parent.require('./script/irt.js');
var fs = window.parent.require('fs');
var path = window.parent.require('path');
var fdialogs = window.parent.require('node-webkit-fdialogs');

var datafile = '';
var datafile_size = 0;

function gft_load(gft) {
	if(gft.length < 1) {
		return;
	}

	fs.readFile(gft, "ascii", function (err, content) {
		if(err) {
		}
		else {
			$('#gft').val(content);
			$('#fname').val(path.basename(gft, ".gft"));
			irt.cfg_set("gft_last", gft);
		}
	});
}

function result_load(datafile) {
	console.time("result_load");
		fs.readFile(datafile, "ascii", function (err, content) {
			if(err) {
			}
			else {
				content = content.replace(/\[(\w+)\]/g, function(x) {
					if(x == "[PASS]") return "<span class='record_pass'>[PASS]</span>";
					else return "<span class='record_fail'>[FAIL]</span>";
				});
				var ctrl_table = $("#table");
				ctrl_table.html(content);
				ctrl_table.scrollTop(ctrl_table[0].scrollHeight);
				console.timeEnd("result_load");
			}
		});
}

function irt_show_status(status) {
	$("#panel_result").html(status);
	switch(status) {
	case "PASS": $("#panel_result").css("background-color", "#00ff00"); break;
	case "ERROR":
		$("#button_run").attr("disabled", true);
	case "FAIL":
		$("#panel_result").css("background-color", "#ff0000");
		break;
	default:
		$("#panel_result").css("background-color", "#c0c0c0");
	}
}

function timer_tick_update() {
	var d=new Date();
	$("#time_cur").html(d.toTimeString().substr(0, 8));
	$("#date").html(d.toLocaleDateString());
	irt.query("status", function(data) {
		var result = JSON.parse(data);
		//console.dir(result);

		if(result.testing) {
			$("#button_run").val("STOP");
			$("#button_mode").attr("disabled", true);
			$("#button_model").attr("disabled", true);
		}
		else {
			$("#button_run").val("RUN");
			$("#button_mode").attr("disabled", false);
			$("#button_model").attr("disabled", false);
		}

		var status = result["status"];
		if(status != storage.testing_status) {
			storage.testing_status = status;
			irt_show_status(status);
		}

		$("#num_pass").html(result["nr_ok"]);
		$("#num_fail").html(result["nr_ng"]);
		var total = parseInt(result["nr_ok"]) + parseInt(result["nr_ng"]);
		$("#num_total").html(total);
		var passrate = parseFloat(result["nr_ok"])/total;
		var failrate = 1 - passrate;
		$("#passrate").html(passrate.toString().substr(0, 5));
		$("#failrate").html(failrate.toString().substr(0, 5));
		$("#time_run").html(result["runtime"]+"s");
		if(result.testtime != null) $("#time_test").html(result.testtime+"s");
		var barcode = result["barcode"].trim();
		if (barcode.length > 0) {
			$("#barcode").val(barcode);
		}

		if(result.datafile != null) {
			if(result.datafile != datafile) {
				datafile = result.datafile;
				datafile_size = 0;
				result_load(result.datafile);
			}
			else fs.stat(datafile, function(err, stats) {
				if(stats.size != datafile_size) {
					datafile_size = stats.size;
					result_load(result.datafile);
				}
			});
		}
	});
}

$(function() {
	irt.init();
	irt.cfg_get('gft_last', function(gft_file) {
		gft_load(gft_file);
	});

	//load settings saved in session
	storage = window.sessionStorage;
	if(storage.testing_mode == null) {
		storage.testing_mode = "AUTO";
	}

	//load storage settings
	$("#button_mode").val(storage["testing_mode"]+" MODE");
	irt_show_status(storage.testing_status);

	$("#button_mode").click(function(){
		if(storage["testing_mode"] == "AUTO") storage["testing_mode"] = "STEP";
		else storage["testing_mode"] = "AUTO";
		$(this).val(storage["testing_mode"]+" MODE");
	});

	$("#button_model").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.gft'],
			path: './gft'
		});

		Dialog.getFilePath(function (err, gft_file) {
			gft_load(gft_file);
		});
	});

	$("#button_run").click(function(){
		var run = $(this).val();
		if(run == "RUN") {
			irt.cfg_get('gft_last', function(gft_file) {
				cmdline = 'test "' + gft_file + '"';
				irt.query(cmdline, function(data) {
				});
			});
		}
		else {
			irt.query("stop", function(data) {
			});
		}
	});

	var timer_tick = setInterval("timer_tick_update()", 100);
	$(window).unload(function(){
		clearInterval(timer_tick);
		irt.exit();
	});
});