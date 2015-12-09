var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')
var sprintf = require('sprintf-js').sprintf
var async = require('async')

//to be stored in browser's session
var settings = {
	model: {},
};

function gcfg_load(){
	async.eachSeries($(".gcfg"), function (dom, callback) {
		irt.cfg_get(dom.id, function(value){
			$(dom).val(value);
			callback();
		});
	});
}

function rules_load() {
}

function model_sub_redraw(nrow, ncol, nsub) {
		$("#mask").hide();

		var html = [];
		var nsubs = nrow * ncol;
		for(var i = 0; i < nsubs; i ++) {
			var subname = String.fromCharCode("A".charCodeAt()+i);
			var checked = 'checked = "checked"';
			html[i] = '<div id="mask'+i+'"><input id="'+i+'" type="checkbox" ' + checked + ' />' +
			'<label for="'+i+'">'+subname+'</label></div>';
		}
		html = html.join("\n");
		$("#mask").html(html);
		$( "#mask input" ).button({
			//disabled: true,
		});

		var w = 100/ncol + "%";
		var h = 100/nrow + "%";
		$("#mask div").removeAttr("width").removeAttr("height").css({"width":w, "height":h});
		$("#mask").show();
}

function model_show(model) {
	if(model == null) {
		model = {};
		model.name = "";
		model.nrow = "";
		model.ncol = "";
		model.nsub = "";
		model.points = "";
		model.offset = "";
		model.barcode = '""';
	}

	$("#m_name").val(model.name);
	$("#m_nrow").val(model.nrow);
	$("#m_ncol").val(model.ncol);
	$("#m_nsub").val(model.nsub);
	$("#m_points").val(model.points);
	$("#m_offset").val(model.offset);
	model_sub_redraw(model.nrow, model.ncol, model.nsub);
	$("#m_prn").html(JSON.parse(model.barcode));
	$("#m_del").attr("disabled", model.id == null);
}

function model_load(fname) {
	fs.readFile(fname, "ascii", function (err, content) {
		if (err) throw err;

		var editor = ace.edit("editor");
		editor.session.setValue(content);

		var model = path.basename(fname, ".py");
		$('#m_model').html(model);
		$('#m_model').attr("title", fname)

		settings.fname = fname;
		$("#m_save, #m_saveas").attr("disabled", false);
	});
}

function model_save(fname) {
	var editor = ace.edit("editor");
	content = editor.session.getValue();
	fs.writeFile(fname, content, function (err) {
		if (err) throw err;
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.settings != null) {
		settings = JSON.parse(session.settings);
	}

/* 	var editor = ace.edit("editor");
	editor.setTheme("ace/theme/chrome");
	editor.getSession().setMode("ace/mode/python");
	editor.setAutoScrollEditorIntoView(true);
	editor.setOption("showPrintMargin", false); */

	gcfg_load();
	if(settings.fname) {
		model_load(settings.fname);
	}

	model_sub_redraw(1,1,1);
	$("#m_nrow, #m_ncol, #m_nsub").change(function(){
		settings.model[this.id.substr(2)] = this.value;
		model_sub_redraw(settings.model.nrow, settings.model.ncol, settings.model.nsub);
	});

	$("#gcfg_save").click(function(){
		async.eachSeries($(".gcfg"), function (dom, callback) {
			irt.cfg_set(dom.id, $(dom).val());
			callback();
		});
	});

	$("#g_admin_confirm").bind('keydown', function(event){
		var key = event.which;
		if (key == 13) {
			confirm = $(this).val();
			passwd = $("#g_admin_passwd").val();
			if((confirm.length > 3) && (confirm == passwd)) {
				irt.cfg_set("passwd", passwd);
				alert("Password Changed Successfully");
			}
			else alert("Password Too Short Or Not Equal, Please Retry");
		}
	});

	$("#g_waste_confirm").bind('keydown', function(event){
		var key = event.which;
		if (key == 13) {
			confirm = $(this).val();
			passwd = $("#g_waste_passwd").val();
			if((confirm.length > 3) && (confirm == passwd)) {
				irt.cfg_set("waste_passwd", passwd);
				alert("Password Changed Successfully");
			}
			else alert("Password Too Short Or Not Equal, Please Retry");
		}
	});

	$("#m_openzpl").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.zpl'],
			path: ''
		});

		Dialog.getFilePath(function (err, fname) {
			//model_load(fname);
		});
	});

	$("#m_save").click(function(){
		model_save(settings.fname);
	});

	$("#m_saveas").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'save',
			accept: ['.py'],
			path: './gft'
		});

		Dialog.getFilePath(function (err, fname) {
			//test.ui_status = 'LOADING';
			//irt.query("reset", function(data) {});
			model_save(fname);
		});
	});

	$(window).unload(function(){
		irt.exit();
		session.settings = JSON.stringify(settings);
	});
});