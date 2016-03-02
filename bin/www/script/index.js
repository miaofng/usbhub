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
	session.cwd = process.cwd()
	delete(session.test);
	delete(session.server_error);

	var win = gui.Window.get();
	irt.init()
	irt.cfg_get("language", function(language) {
		switch(language) {
		case "cn":
			window.topFrame.location.href = "cn/header_admin.html";
			window.mainFrame.location.href = "cn/testing.html";
			document.title = cn.title
			session.language = "cn"
			session.language_string = JSON.stringify(cn);
			break
		default:
			window.topFrame.location.href = "en/header_admin.html";
			window.mainFrame.location.href = "en/testing.html";
			document.title = en.title
			session.language = "en"
			session.language_string = JSON.stringify(en);
			break
		}
	})

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
		window.mainFrame.location.href = session.language + "/about.html";
	});
});