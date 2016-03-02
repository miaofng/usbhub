var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')
var sprintf = require('sprintf-js').sprintf
var async = require('async')

//to be stored in browser's session
var test = {};
var settings = {
	"mask": {},
};

function gcfg_load(){
	async.eachSeries($(".gcfg"), function (dom, callback) {
		irt.cfg_get(dom.id, function(value){
			$(dom).val(value);
			callback();
		});
	});
}

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
			//disabled: true,
		});

		var w = 100/ncol + "%";
		var h = 100/nrow + "%";
		$("#mask div").removeAttr("width").removeAttr("height").css({"width":w, "height":h});
		$("#mask").show();
}

function model_load() {
	rule_list_all();
	model_sub_redraw(1,1,{1: true});
	if(test.model == null) {
		$("#mcfg_save").attr("disabled", true);
		return;
	}

	$("#mcfg_save").css("disabled", false);
	$("#m_model").html(test.model);

	sql = 'SELECT * FROM model WHERE name = "$model"';
	sql = sql.replace("$model", test.model);
	console.log(sql);
	irt.db().get(sql, function(err, row){
		if(row == null)
			return;

		$("#m_nrow").val(row.nrow);
		$("#m_ncol").val(row.ncol);
		$("#m_npts").val(row.npts);
		$("#m_nofs").val(row.nofs);
		$("#m_barcode").val(row.barcode);
		model_sub_redraw(row.nrow, row.ncol, settings.mask);
		if(row.zpl.length > 2)
			$("#m_zpl").html(JSON.parse(row.zpl));

		$("#m_track").val(row.track);
		row.printlabel = (row.printlabel == "1") ? "1" : "0";
		$("#m_printlabel").val(row.printlabel);
		$("#m_barcode").attr("disabled", row.printlabel == "1");
		$("#m_openzpl").attr("disabled", row.printlabel != "1");
		$("#m_zpl").attr("disabled", row.printlabel != "1");
	});
}

function rule_list_all()
{
	var html = []
	header = irt.mlstring(function(){/*
		<ul class="list_head">
			<li>$type</li>
			<li>$i</li>
			<li>$typical</li>
			<li>$min</li>
			<li>$max</li>
			<li><a class="rule" href="#" title="Create New Rule">+</a>&nbsp;$name<input type="checkbox" id="rule_checkall"/></li>
		</ul>
	*/});
	header = header.replace("$type", language_string.type)
	header = header.replace("$i", language_string.i)
	header = header.replace("$typical", language_string.typical)
	header = header.replace("$min", language_string.min)
	header = header.replace("$max", language_string.max)
	header = header.replace("$name", language_string.name)
	html.push(header);
	irt.db().all("SELECT * FROM rule", function(err, rows){
		if(err) {
			return;
		}

		rows.forEach(function(row){
			dict_mA = {
				"0"	: 10,
				"1"	: 20,
				"2"	: 50,
				"3"	: 100,
				"4"	: 200,
				"5"	: 500,
				"6"	: 750,
				"7"	: 1000,
				//#newly added
				"8"	: 1500,
				"9"	: 2000,
			}
			dict_range = {
				"0"	: "<",
				"1"	: ">",
				"2"	: 0.01, //#+/-1%
				"3"	: 0.03,
				"4"	: 0.05,
				"5"	: 0.10,
				"6"	: 0.20,
				"7"	: 0.30,
				"8"	: 0.40,
				"9"	: 0.50,
			}

			mA = dict_mA[row.i]
			typ = value = row.value
			range = dict_range[row.range]
			switch (range) {
			case "<":
				min = ''
				max = value
				break
			case ">":
				min = value
				max = ''
				break
			default:
				min = value * (1 - range)
				max = value * (1 + range)

				min = min.toFixed(1)
				max = max.toFixed(1)
			}

			ul = [];
			ul.push("<ul>");
			ul.push("<li>type</li>".replace("type", row.type));
			ul.push("<li>ia</li>".replace("ia", mA));
			ul.push("<li>typ</li>".replace("typ", typ));
			ul.push("<li>min</li>".replace("min", min));
			ul.push("<li>max</li>".replace("max", max));
			var li = '<li> <a class="rule" id=$id href="#">$name</a> <input class="rule_check" type="checkbox" id="check_$id"/> </li>';
			li = li.replace("$id", row.id);
			li = li.replace("$id", row.id);
			li = li.replace("$name", row.name);
			ul.push(li);
			ul.push("</ul>");
			html.push(ul.join(' '));
		});

		$('#list').html(html.join('\r\n'));

		if(test.model) {
			sql = 'SELECT rules FROM model WHERE name = "$model"';
			sql = sql.replace("$model", test.model);
			console.log(sql);
			irt.db().get(sql, function(err, row){
				if(row == null)
					return;

				var rules = JSON.parse(row.rules);
				for(id in rules) {
					$("#check_"+rules[id]).prop("checked", true);
				}
			});
		}

		$('#rule_checkall').change(function(){
			var checked = $(this).is(':checked');
	 		var checkboxs = $(".rule_check");
			for(var i = 0; i < checkboxs.length; i ++) {
				var cb = checkboxs[i];
				$(cb).prop("checked", checked);
			}
		});

		$(".rule").click(function(){
			//var id = this.href.substr(this.href.search('#') + 1);
			var id = $(this).attr("id");
			sql = "SELECT * FROM rule WHERE id = $id";
			sql = sql.replace("$id", id);
			console.log(sql);
			irt.db().get(sql, function(err, rule){
				if(rule == null) {
					//to create a new rule
					rule = {}
					rule.type = "R";
					rule.name = "?";
					rule.min = rule.max = "";
					rule.i = "1";
					$('#rule_set').attr('disabled', true);
					$('#rule_del').attr('disabled', true);
				}
				else {
					$('#rule_set').attr('disabled', false);
					$('#rule_del').attr('disabled', false);
				}

				$("#rule_type").val(rule.type);
				$("#rule_name").val(rule.name);
				$("#rule_value").val(rule.value);
				$("#rule_range").val(rule.range);
				$("#rule_i").val(rule.i);
				$("#rule_dlg").data('id', id).dialog('open');
			});
		});
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.settings != null) {
		settings = JSON.parse(session.settings);
	}
	if(session.test) {
		test = JSON.parse(session.test);
	}

	language_string = session.language_string
	language_string = JSON.parse(language_string)

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

	$( "#dialog_warn" ).dialog({
		autoOpen: false,
		closeOnEscape: true,
		height: 280,
		width: 500,
		modal: false,
		hide: {
			effect: "explode",
			duration: 500
		}
	});

	$("#warn_ok").click(function(){
		irt.db().run("DELETE FROM test", function(err){
			if(err) alert(err);
			else $("#dialog_warn").dialog("close");
		})
	});

	$("#gcfg_save").click(function(){
		async.eachSeries($(".gcfg"), function (dom, callback) {
			irt.cfg_set(dom.id, $(dom).val());
			callback();
		});
	});

	$("#gcfg_clear").click(function(){
		$("#dialog_warn").dialog("open");
	});

	$("#m_nrow, #m_ncol").change(function(){
		nrow = $("#m_nrow").val();
		ncol = $("#m_ncol").val();
		model_sub_redraw(nrow, ncol, settings.mask);
	});

	$("#m_openzpl").click(function(){
		var Dialog = new fdialogs.FDialog({
			type: 'open',
			accept: ['.prn'],
			path: ''
		});

		Dialog.getFilePath(function (err, fname) {
			fs.readFile(fname, "ascii", function (err, content) {
				$("#m_zpl").html(content);
			});
		});
	});

	$("#mcfg_save").click(function(){
		nrow = $("#m_nrow").val();
		ncol = $("#m_ncol").val();
		npts = $("#m_npts").val();
		nofs = $("#m_nofs").val();
		barcode = $("#m_barcode").val().trim()
		printlabel = $("#m_printlabel").val();

		zpl = $("#m_zpl").html();
		zpl = JSON.stringify(zpl);

		nrow = parseInt(nrow);
		ncol = parseInt(ncol);
		npts = parseInt(npts);
		nofs = parseInt(nofs);

		var err = isNaN(nrow + ncol + npts + nofs);
		err |= nrow <= 0;
		err |= ncol <= 0;
		err |= npts <= 0;
		err |= nofs < 0;
		if(err) {
			alert("Illegal input value !!!");
			return;
		}

		var checked_ids = [];
		var ctrls = $("#list :checked");
		for(var i = 0; i < ctrls.length; i ++) {
			 var id = ctrls[i].id.substr(6);
			 id = parseInt(id);
			 if(!isNaN(id))
				checked_ids.push(id);
		}
		rules = JSON.stringify(checked_ids);
		console.log("checked rules: "+rules);

		var sql = 'SELECT * FROM model WHERE name = "$model"';
		sql = sql.replace("$model", test.model);
		console.log(sql);
		irt.db().get(sql, function(err, row){
			var sql_upd = irt.mlstring(function(){/*
				UPDATE model SET nrow = $nrow, ncol = $ncol,
				npts = $npts, nofs = $nofs, zpl = '$zpl',
				rules = '$rules', printlabel = '$printlabel', barcode = '$barcode'
				WHERE id = $id
			*/});

			var sql_ins = irt.mlstring(function(){/*
				INSERT INTO model(nrow, ncol, npts, nofs, printlabel, zpl, barcode, rules, name)
				VALUES($nrow, $ncol, $npts, $nofs, '$printlabel', '$zpl', '$barcode', '$rules', '$model')
			*/});

			var sql = sql_ins;
			if(row) {
				sql = sql_upd;
				sql = sql.replace("$id", row.id);
			}

			sql = sql.replace("$nrow", nrow);
			sql = sql.replace("$ncol", ncol);
			sql = sql.replace("$npts", npts);
			sql = sql.replace("$nofs", nofs);
			sql = sql.replace("$rules", rules);
			sql = sql.replace("$printlabel", printlabel);
			sql = sql.replace("$zpl", zpl);
			sql = sql.replace("$barcode", barcode);
			sql = sql.replace("$model", test.model);
			console.log(sql);

 			irt.db().run(sql, function(err){
				if(err) alert(err);
				else {
					//save unmasks
					var mask = {};
					var ctrls = $(".mask_checkbox");
					for(var i = 0; i < ctrls.length; i ++) {
						var ctrl = ctrls[i];
						var id = ctrl.id.substr(5); //mask_n
						mask[id] = ctrl.checked;
					}
					console.log("settings.mask = " + JSON.stringify(mask));
					settings.mask = mask;

					model_load();
				}
			});
		});
	});

	$( "#rule_dlg" ).dialog({
		autoOpen: false,
		height: 450,
		width: 500,
		modal: true,
		hide: {
			effect: "explode",
			duration: 500
		},
		close: function(){
		}
	});

	$("#rule_set").click(function(){
		var id = $("#rule_dlg").data("id");
		var inputs = $(".rule_input")
		var pairs = [];
		for(var i = 0; i < inputs.length; i ++) {
			var input = inputs[i]
			var col = input.id.substr(5);
			var val = input.value;
			pairs.push(col+'="$val"'.replace("$val", val));
		}

		var sql = "UPDATE rule SET $pairs WHERE id = $id";
		sql = sql.replace("$pairs", pairs.join(","));
		sql = sql.replace("$id", id);
		console.log(sql);
		irt.db().run(sql, function(err){
			if(err) alert(err);
			else {
				rule_list_all();
				$("#rule_dlg").dialog("close");
			}
		});
	});

	$("#rule_add").click(function(){
		var id = $("#rule_dlg").data("id");
		var inputs = $(".rule_input")
		var cols = [];
		var vals = [];
		for(var i = 0; i < inputs.length; i ++) {
			var input = inputs[i]
			var col = input.id.substr(5);
			var val = input.value;
			cols.push(col);
			vals.push('"$val"'.replace("$val", val));
		}

		cols = cols.join(",");
		vals = vals.join(",");
		var sql = "INSERT INTO rule($cols) VALUES($vals)";
		sql = sql.replace("$cols", cols);
		sql = sql.replace("$vals", vals);
		console.log(sql);
		irt.db().run(sql, function(err){
			if(err) alert(err);
			else {
				rule_list_all();
				$("#rule_dlg").dialog("close");
			}
		});
	});

	$("#rule_del").click(function(){
		var id = $("#rule_dlg").data("id");
		var sql = "DELETE FROM rule WHERE id=$id";
		sql = sql.replace("$id", id);
		console.log(sql);
		irt.db().run(sql, function(err){
			if(err) alert(err);
			else {
				rule_list_all();
				$("#rule_dlg").dialog("close");
			}
		});
	});

	$("#m_printlabel").change(function() {
		$("#m_barcode").attr("disabled", this.value == "1");
		$("#m_openzpl").attr("disabled", this.value != "1");
		$("#m_zpl").attr("disabled", this.value != "1");
	})

	gcfg_load();
	model_load();

	$(window).unload(function(){
		irt.exit();
		session.settings = JSON.stringify(settings);
	});
});
