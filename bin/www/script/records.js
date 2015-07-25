var irt = window.parent.require('./script/irt.js');
var fs = window.parent.require('fs');
var path = window.parent.require('path');
var fdialogs = window.parent.require('node-webkit-fdialogs')

//to be stored in browser's session
var records = {
	s_start: "",
	s_end: "",
	s_model: "",
	s_barcode: "",
	searched: false,
	id: null,
};

//for datafile modification monitoring
var datafile = '';
var datafile_size = 0;
var dat_dir = "";

function test_load(id) {
	irt.test_get(id, function (test) {
		$('#model').val(test.model);
		$('#barcode').val(test.barcode);
		$('#date').html(test.time.substr(0,10));
		$('#time_cur').html(test.time.substr(10));
		$('#time_run').html(parseInt(test.runtime));
		$('#time_test').html(parseInt(test.duration));
		result_load(test.datafile);

		irt.model_get(test.model, function(model) {
			$("#mask").hide();
			//update sub board display for mask purpose
			if(model == null) {
				//alert("Model is Not Found in Database!!!");
				test.status = 'MODEL NOT FOUND';
				return;
			}
			//console.dir(model);
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
			});

			var w = 100/model.ncol + "%";
			var h = 100/model.nrow + "%";
			$("#mask div").removeAttr("width").removeAttr("height").css({"width":w, "height":h});
			$("#mask").show();
			irt_show_status((test.failed)?"FAIL":"PASS", test.failed, model);
		});
	});
}

function result_load(datafile) {
	//console.time("result_load");
	datafile = path.normalize(dat_dir + datafile);
	datafile = path.resolve(process.cwd(), "www/script", datafile);
	fs.readFile(datafile, "ascii", function (err, content) {
		if(err) {
			alert(err.message);
		}
		else {
			content = content.replace(/\[(\w+)\]/gi, function(x) {
				if(x == "[PASS]") return "<span class='record_pass'>[PASS]</span>";
				else return "<span class='record_fail'>[FAIL]</span>";
			});
			var ctrl_table = $("#table");
			ctrl_table.html(content+"\n");
			//ctrl_table.scrollTop(ctrl_table[0].scrollHeight);
			//console.timeEnd("result_load");
		}
	});
}

function irt_show_status(status, ecode, model) {

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

	for(var i = 0; i < model.nsub; i ++) {
		//border color?
		var border_color = "#00ff00";
		if((1 << i) & ecode) {
			border_color = "red";
		}

		var target = "#mask" + i + " label";
		$(target).css("border-color", border_color);
	}
}

function test_list() {
	var cnds = {};
	cnds.date_start = records.s_start;
	cnds.date_end = records.s_end;
	cnds.model = records.s_model.trim();
	cnds.barcode = records.s_barcode.trim();
	cnds.max_records = 128;

	irt.test_enum(cnds, function(rows){
		var html = [];
		rows.forEach(function(row, index){
			var ul = [];
			ul.push('<ul title="'+row.datafile+'">');
			ul.push('<li>');
			ul.push('<a href="#'+row.id+'">'+row.time+'</a>');
			ul.push('</li>');

			ul.push('<li>' + row.model +'</li>');
			ul.push('<li class="'+((row.failed) ? "record_fail" : "record_pass") +'">' + row.barcode +'</li>');
			ul.push('</ul>');
			html.push(ul.join(' '));
		});
		html.push('<ul>&nbsp;</ul>');
		$('#s_result').html(html.join('\r\n'));
		$("#s_result ul li a").click(function(){
			var id = this.href.substr(this.href.search('#') + 1);
			records.id = parseInt(id);
			test_load(records.id);
			return false;
		});
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.records != null) {
		records = JSON.parse(session.records);
	}

	irt.cfg_get("dat_dir", function(value){
		dat_dir = value;
	});

	$("#search").click(function(){
		records.s_start = $("#s_start").val();
		records.s_end = $("#s_end").val();
		records.s_model = $("#s_model").val();
		records.s_barcode = $("#s_barcode").val();
		records.searched = true;
		test_list();
	});

	$( "#mask input" ).button({ disabled: true,});
		$( "#s_start, #s_end" ).datepicker({
		dateFormat: 'yy-mm-dd',
		showWeek: true,
		firstDay: 1
	});

	$( "#s_model" ).autocomplete({
		source: function( request, response ) {
			irt.model_enum("%"+request.term.trim()+"%", function(rows){
				var values = [];
				rows.forEach(function(row, index){
					values.push(row.name);
				});
				response(values);
			});
		}
	});

	$( "#s_barcode" ).autocomplete({
		source: function( request, response ) {
			var cnds = {};
			cnds.barcode = request.term.trim()+"%";
			cnds.max_records = 64;
			irt.test_enum(cnds, function(rows){
				var values = [];
				rows.forEach(function(row, index){
					values.push(row.barcode);
				});
				response(values);
			});
		}
	});

	var date=new Date();
	var sdate = date.toLocaleDateString().replace(/\//g, "-");
	sdate = sdate.replace(/\d+/g, function(m){
		return "0".substr(m.length - 1) + m;
	});

	$("#s_start").val(sdate);
	$("#s_end").val(sdate);

	//load settings saved in session
	if(records.searched) {
		$("#s_start").val(records.s_start);
		$("#s_end").val(records.s_end);
		$("#s_model").val(records.s_model);
		$("#s_barcode").val(records.s_barcode);
		test_list();
	}
	else {
		test_list();
	}

	if(records.id != null) {
		test_load(records.id);
	}

	$(window).unload(function(){
		irt.exit();
		session.records = JSON.stringify(records);
	});
});