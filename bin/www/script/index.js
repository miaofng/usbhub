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
		win = this
		irt.query("close", function(data) {
			//debug mode, irt.stop will fail,
			//exe won't exit
			irt.stop();
			win.hide(); // Pretend to be closed already
			win.close(true);
		});
	});

	irt.start(function(err){
		session.server_error = err;
		window.mainFrame.location.href = "about.html";
	});
});