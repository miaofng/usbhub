var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')
var sprintf = require('sprintf-js').sprintf

//to be stored in browser's session
var diagnosis = {
	s_model: "",
	id: null,
	model: {},
};

function update_status(status)
{
	sensors = status.sensors;
	control = status.control;

	$(".indicators").each(function(){
		switch(this.id) {
		case "LID": //3.07-3.04
			regv = (sensors[3] >> 4) & 0x0f;
			$(this).html(sprintf("%02d", regv));
			break;
		case "RID": //3.03-3.00
			regv = (sensors[3] >> 0) & 0x0f;
			$(this).html(sprintf("%02d", regv));
			break;
		default:
			idx = Math.round(this.id);
			bit = Math.round(this.id * 100) % 100;
			regv = (sensors[idx] >> bit) & 0x01;
			if(regv) $(this).css("backgroundColor", "#00ff00");
			else $(this).css("backgroundColor", "white");
		}
	});

	$(".buttons").each(function(){
		switch(this.id) {
		case "TLDOOR": //100.00(open) 100.01(close) 100.05(lamp)
			regv = (control[0] >> 5) & 0x01;
			break;
		case "TRDOOR": //100.02(open) 100.03(close) 100.04(lamp)
			regv = (control[0] >> 4) & 0x01;
			break;
		case "TLPSFL": //103.02(R) 103.03(G)
			regv = (control[3] >> 2) & 0x01;
			break;
		case "TRPSFL": //103.00(R) 103.01(G)
			regv = (control[3] >> 0) & 0x01;
			break;
		default:
			idx = Math.round(this.id) % 100;
			bit = Math.round(this.id * 100) % 100;
			regv = (control[idx] >> bit) & 0x01;
		}

		if(regv) {
			//$(this).css("background-image", "url(img/fan.gif)");
			//$(this).css("background-repeat","no-repeat");
			//$(this).css("background-size","32px 32px");
			//$(this).css("background-position","center left");
			$(this).css("background-color", "#00ff00");
			//$(this).css("color", "#00ff00");
		}
		else {
			//$(this).css("background", "transparent");
			$(this).css("background-color", "#ccc");
			//$(this).css("color", "black");
		}
	});
}

function tick_update()
{
	irt.query("plc", function(data) {
		data = JSON.parse(data);
		update_status(data);
	});
}

$(function() {
	irt.init();
	var session = window.sessionStorage;
	if(session.diagnosis != null) {
		diagnosis = JSON.parse(session.diagnosis);
	}

	$(".buttons").click(function(){
		//console.log(this.id);
		cmdline = [];
		cmdline.push("plc");
		cmdline.push(this.id)
		cmdline = cmdline.join(" ");
		irt.query(cmdline, function(data) {});
	});

	var tick = setInterval("tick_update()", 500);
	$(window).unload(function(){
		clearInterval(tick);
		irt.exit();
		session.diagnosis = JSON.stringify(diagnosis);
	});
});