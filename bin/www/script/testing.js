var irt = window.parent.require('./script/irt.js');
var fs = window.parent.require('fs');
var path = window.parent.require('path');
var fdialogs = window.parent.require('node-webkit-fdialogs')

//to be stored in browser's session
var test = {
	"model": null,
	"mode":"AUTO",
	"mask": 0,
	"bplist":{},

	"ui_status": 'INIT', //'LOADING', 'READY', 'XXX ERROR'
	//show irt server status only when ui_status = 'READY'
};

function model_sub_redraw(nrow, ncol, nsub) {
		$("#mask").hide();

		var html = [];
		var nsubs = nrow * ncol;
		for(var i = 0; i < nsubs; i ++) {
			var subname = String.fromCharCode("A".charCodeAt()+i);
			var masked = test.mask & (1 << i);
			var checked = (masked) ? '' : 'checked = "checked"';

			var div = '\
				<div id = "mask$i"> \
					<input id="$i" type="checkbox" $checked /> \
					<label for="$i">$name</label> \
				</div> \
			';

			div = div.replace(/\$i/g, i);
			div = div.replace(/\$checked/g, checked);
			div = div.replace(/\$name/g, subname);
			//console.log(div);
			html.push(div);
		}

		html = html.join("\n");
		$("#mask").html(html);

		$( "#mask input" ).button({
			//disabled: true,
		}).click(function(){
			//alert(this.id + "=" + this.checked);
			var sub = parseInt(this.id);
			var checked = (this.checked) ? 0 : 1;
			test.mask = (test.mask & ~(1 << sub)) | (checked << sub);
		});

		var w = 100/ncol + "%";
		var h = 100/nrow + "%";
		$("#mask div").removeAttr("width").removeAttr("height").css({"width":w, "height":h});
		$("#mask").show();
}

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
			var i = 0;
			content = content.replace(/\r/g, '');
			content = content.replace(/^/gm, function(x) {
				var span = "<span class='linenr'>"+i+"</span>  "
				var span_bp = "<span class='linenr linenr_bp'>"+i+"</span>  "
				span = (test.bplist[i.toString()]) ? span_bp : span;
				i ++;
				return span;
			});
			$('#gft').html(content+"\n\n");
			var model = path.basename(gft, ".gft");
			$('#fname').val(model);
			irt.cfg_set("gft_last", path.relative(process.cwd(), gft));

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

			irt.model_get(model, function(model) {
				$("#mask").hide();
				if(model == null) {
					test.ui_status = 'MODEL UNSUPPORTED';
					return;
				}

				test.model = model;
				model_sub_redraw(model.nrow, model.ncol, model.nsub);
				test.ui_status = "READY";
			});
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

	$("#panel_result").html(state);
	$("#panel_result").css("background-color", bgcolor);

	//subboard state display
	if(test.model != null) {
		for(var i = 0; i < test.model.nsub; i ++) {
			//border color?
			var border_color = "gray";
			if(status == "PASS" || status == "FAIL") {
				border_color = "#00ff00";
			}

			if((1 << i) & ecode) {
				border_color = "red";
			}

			var target = "#mask" + i + " label";
			$(target).css("border-color", border_color);
		}
	}
}

//for datafile modification monitoring
var datafile_save = '';
var datafile_size = 0;

function load_report(datafile) {
	fs.readFile(datafile, "ascii", function (err, content) {
		if(err) {
		}
		else {
			content = content.replace(/\[(\w+)\]/gi, function(x) {
				if(x == "[PASS]") return "<span class='record_pass'>[PASS]</span>";
				else return "<span class='record_fail'>[FAIL]</span>";
			});
			var ctrl_table = $("#table");
			ctrl_table.html(content+"\n");
			ctrl_table.scrollTop(ctrl_table[0].scrollHeight);
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
		$("#barcode").val(barcode);
	}

	//state update
	$(".idleinput").attr("disabled", status.testing);
	$("#button_run").val((status.testing) ? "STOP" : "RUN");
	$("#button_run").attr("disabled", test.ui_status != "READY");
	update_state(status.status, status.ecode);

	//report update
	var datafile = status.datafile;
	if(datafile != null) {
		if(datafile_save != datafile) {
			datafile_save = datafile;
			datafile_size = 0;
			load_report(status.datafile);
		}
		else fs.stat(datafile, function(err, stats) {
			if(stats.size != datafile_size) {
				datafile_size = stats.size;
				load_report(status.datafile);
			}
		});
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

	$("#button_mode").click(function(){
		if(test.mode == "AUTO") test.mode = "STEP";
		else test.mode = "AUTO";
		$(this).val(test.mode + " MODE");
	});

	$("#button_model").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.gft'],
			path: './gft'
		});

		Dialog.getFilePath(function (err, gft_file) {
			test.ui_status = 'LOADING';
			test.mask = 0;
			irt.query("reset", function(data) {});
			gft_load(gft_file);
		});
	});

	$("#button_run").click(function(){
		var run = $(this).val();
		if(run == "RUN") {
			irt.cfg_get('gft_last', function(gft_file) {
				gft_file = path.resolve(process.cwd(), gft_file);
				cmdline = [];
				cmdline.push("test");
				cmdline.push("--mode=" + test.mode);
				cmdline.push("--mask=" + test.mask);
				cmdline.push('"'+gft_file+'"');
				cmdline = cmdline.join(" ");
				irt.query(cmdline, function(data) {});
			});
		}
		else {
			irt.query("stop", function(data) {
			});
		}
	});

	irt.cfg_get('gft_last', function(gft_file) {
		gft_load(gft_file);
	});

	var timer_tick = setInterval("timer_tick_update()", 100);
	$(window).unload(function(){
		clearInterval(timer_tick);
		irt.exit();
		session.test = JSON.stringify(test);
	});
});