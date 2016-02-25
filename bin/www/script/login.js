var irt = window.parent.require('./script/irt.js');

$(function() {
	var session = window.sessionStorage;
	if(session.getItem('cnt')) {
		session['cnt'] = parseInt(session['cnt']) + 1;
	}
	else {
		session['cnt'] = 0;
	}
	console.log("login page: "+session['cnt']);

	irt.init();
	$("#passwd").bind('keydown', function(event){
		$(this).css("border-color","black");
		var key = event.which;
		if (key == 13) {
			irt.cfg_get("passwd", function(passwd){
				var input = $("#passwd").val();
				if(passwd == input) {
					window.parent.topFrame.location.href = session.language + "/header_admin.html";
					window.parent.mainFrame.location.href = session.language + "/testing.html";
				}
				else {
					$("#passwd").css("border-color", "red");
				}
			});
		}
	});
});