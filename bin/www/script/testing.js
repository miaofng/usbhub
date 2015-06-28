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
	"status": 'INIT', //irt-ui itself status
};

//for datafile modification monitoring
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
			irt.cfg_set("gft_last", gft);

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
				//update sub board display for mask purpose
				if(model == null) {
					//alert("Model is Not Found in Database!!!");
					test.status = 'MODEL NOT FOUND';
					return;
				}

				test.model = model;
				console.dir(model);
				var html = [];
				var nsubs = model.nrow * model.ncol;
				for(var i = 0; i < nsubs; i ++) {
					var subname = String.fromCharCode("A".charCodeAt()+i);
					var checked = (test.mask & (1 << i)) ? "" : 'checked = "checked"';
					html[i] = '<div id="mask'+i+'"><input id="'+i+'" type="checkbox" ' + checked + ' />' +
					'<label for="'+i+'">'+subname+'</label></div>';
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

				var w = 100/model.ncol + "%";
				var h = 100/model.nrow + "%";
				$("#mask div").removeAttr("width").removeAttr("height").css({"width":w, "height":h});
				$("#mask").show();
				test.status = "READY";
			});
		}
	});
}

function result_load(datafile) {
	//console.time("result_load");
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

function irt_show_status(status) {
	var ecode = arguments[1] ? arguments[1] : 0;

	$("#panel_result").html(status);
	switch(status) {
	case "TESTING":
		$("#panel_result").css("background-color", "#ffff00");
		break;
	case "READY":
	case "PASS":
		$("#panel_result").css("background-color", "#00ff00");
		break;

	case "INIT":
	case "LOADING":
		$("#panel_result").css("background-color", "#c0c0c0");
		break;

	case "ERROR":
		$("#button_run").attr("disabled", true);
	case "FAIL":
	default:
		$("#panel_result").css("background-color", "#ff0000");
		break;
	}

	if(test.model != null) {
		for(var i = 0; i < test.model.nsub; i ++) {
			//border color?
			var border_color = "gray";
			if((1 << i) & ecode) {
				border_color = "red";
			}

			var target = "#mask" + i + " label";
			$(target).css("border-color", border_color);
		}
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
			$("#mask input").attr("disabled", true);
		}
		else {
			$("#button_run").val("RUN");
			$("#button_mode").attr("disabled", false);
			$("#button_model").attr("disabled", false);
			$("#mask input").attr("disabled", false);
		}

		if(test.status == 'READY') {
			$("#button_run").attr("disabled", false);
		}
		else {
			$("#button_run").attr("disabled", true);
		}


		if(test.status != "READY") {
			irt_show_status(test.status);
		}
		else {
			irt_show_status(result.status, result.ecode);
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
	var session = window.sessionStorage;
	if(session.test != null) {
		test = JSON.parse(session.test);
	}

	//init status display
	$("#button_mode").val(test.mode+" MODE");
	irt_show_status(test.status);

	$( "#mask input" ).button({
		//disabled: true,
	});

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
			test.status = 'LOADING';
			irt.query("reset", function(data) {});
			gft_load(gft_file);
		});
	});

	$("#button_run").click(function(){
		var run = $(this).val();
		if(run == "RUN") {
			irt.cfg_get('gft_last', function(gft_file) {
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

	var timer_tick = setInterval("timer_tick_update()", 100);
	$(window).unload(function(){
		clearInterval(timer_tick);
		irt.exit();
		session.test = JSON.stringify(test);
	});
});