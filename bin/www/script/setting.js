var irt = window.parent.require('./script/irt.js');
var fs = window.parent.require('fs');
var path = window.parent.require('path');
var fdialogs = window.parent.require('node-webkit-fdialogs')

//to be stored in browser's session
var settings = {
	s_model: "",
	id: null,
	model: {},
};

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

function model_load(id) {
	if(id == null) { //hide model
		settings.model = {};
		model_show();
		return;
	}

	irt.model_get_by_id(id, function(model) {
		settings.model = model;
		model_show(model);
	});
}

function model_list(s_model) {
	var model = s_model.trim();
	var max_settings = 128;

	irt.model_enum(model, max_settings, function(rows){
		var html = [];
		html.push('<ul class="list_head"><li>NAME</li><li>ROWS</li><li>COLS</li><li>POINTS</li><li>OFFSET</li></ul>');
		rows.forEach(function(row, index){
			var ul = [];
			ul.push('<ul>');
			ul.push('<li>');
			ul.push('<a href="#'+row.id+'">'+row.name+'</a>');
			ul.push('</li>');

			ul.push('<li>' + row.nrow +'</li>');
			ul.push('<li>' + row.ncol +'</li>');
			ul.push('<li>' + row.points +'</li>');
			ul.push('<li>' + row.offset +'</li>');

			ul.push('</ul>');
			html.push(ul.join(' '));
		});
		html.push('<ul>&nbsp;</ul>');
		$('#s_result').html(html.join('\r\n'));
		$("#s_result ul li a").click(function(){
			var id = this.href.substr(this.href.search('#') + 1);
			model_load(parseInt(id));
			return false;
		});
	});
}

function prn_load(prn) {
	if(prn.length < 1) {
		return;
	}

	fs.readFile(prn, "ascii", function (err, content) {
		if(err) {
		}
		else {
			settings.model.barcode = JSON.stringify(content);
			$("#m_prn").html(content);
		}
	});
}

function gcfg_load(){
	irt.cfg_get("nr_ok", function(value){
		$("#g_nr_ok").val(value);
	});
	irt.cfg_get("nr_ng", function(value){
		$("#g_nr_ng").val(value);
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.settings != null) {
		settings = JSON.parse(session.settings);
	}

	var editor = ace.edit("editor");
	editor.setTheme("ace/theme/chrome");
	editor.getSession().setMode("ace/mode/python");
	editor.setAutoScrollEditorIntoView(true);
	editor.setOption("showPrintMargin", false);

	$("#s_model").keydown(function(e){
		if(e.keyCode == 13) {
			settings.s_model = $("#s_model").val();
			model_list(settings.s_model);
		}
	});

	$("#m_nrow, #m_ncol, #m_nsub").change(function(){
		settings.model[this.id.substr(2)] = this.value;
		model_sub_redraw(settings.model.nrow, settings.model.ncol, settings.model.nsub);
	});

	$("#m_name, #m_points, #m_offset").change(function(){
		settings.model[this.id.substr(2)] = this.value;
	});

	$("#m_openprn").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.prn'],
		});

		Dialog.getFilePath(function (err, prn_file) {
			prn_load(prn_file);
		});
	});

	$("#m_apply").click(function(){
		irt.model_set(settings.model, function(err, id){
			if(err != null) alert(err.message);
			else model_list(settings.s_model);
		});
	});

	$("#m_add").click(function(){
		var model = settings.model;
		delete(model.id);
		irt.model_set(model, function(err, id){
			if(err != null) alert(err.message);
			else {
				model_load(id);
				model_list(settings.s_model);
			}
		});
	});

	$("#m_del").click(function(){
		irt.model_get_by_id(settings.model.id, function(model){
			var msg = 'Delete model "$name" ?';
			msg = msg.replace("$name", model.name);
			if(confirm(msg)) {
				irt.model_del(model.id, function(){
					model_load();
					model_list(settings.s_model);
				});
			}
		});
	});

	$( "#mask input" ).button({ disabled: true,});
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

	gcfg_load();

	//load settings saved in session
	settings.s_model = isNaN(settings.s_search) ? "*" : settings.s_model;
	$("#s_model").val(settings.s_model);
	model_list(settings.s_model);

	if(settings.model != null) {
		//model_show(settings.model);
		//reload correct model data to avoid confuse the user
		if(!isNaN(settings.model.id)) {
			model_load(settings.model.id);
		}
	}

	$(window).unload(function(){
		irt.exit();
		session.settings = JSON.stringify(settings);
	});
});