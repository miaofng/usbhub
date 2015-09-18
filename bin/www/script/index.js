/*
	called once when nw.exe start
	store routine static record, such as
	subpage user settings and etc
*/
var gui = require('nw.gui');
var irt = require('./script/irt.js');

//global var init
storage = window.sessionStorage;
storage.testing_status = "BOOTING";

$(function() {
	var session = window.sessionStorage;
	delete(session.test);
	delete(session.server_error);

	var win = gui.Window.get();
	win.show();
	win.on('close', function() {
		this.hide(); // Pretend to be closed already
		console.log("We're closing...");
		this.close(true);
	});

	irt.start(function(err){
		session.server_error = err;
		window.mainFrame.location.href = "about.html";
	});

	$(window).unload(function(){
		irt.stop();
	});
});