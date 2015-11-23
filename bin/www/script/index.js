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

function shutdown_timer_func() {
	var win = gui.Window.get();
	//irt.stop();
	win.close(true);
}

$(function() {
	var session = window.sessionStorage;
	delete(session.test);
	delete(session.server_error);

	var win = gui.Window.get();
	win.show();
	win.on('close', function() {
		// Pretend obama appears
		win.hide();

		//wait at most 1s
		setTimeout("shutdown_timer_func()", 1000);

		//inform tester server to shutdown
		irt.query("close", function(data) {
		});
	});

	irt.start(function(err){
		session.server_error = err;
		window.mainFrame.location.href = "about.html";
	});
});