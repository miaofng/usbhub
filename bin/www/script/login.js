var irt = window.parent.require('./script/irt.js');

$(function() {
	var storage = window.sessionStorage;
	if(storage.getItem('cnt')) {
		storage['cnt'] = parseInt(storage['cnt']) + 1;
	}
	else {
		storage['cnt'] = 0;
	}
	console.log("login page: "+storage['cnt']);

	irt.init();
	$("#passwd").bind('keydown', function(event){
		$(this).css("border-color","black");
		var key = event.which;
		if (key == 13) {
			irt.cfg_get("passwd", function(passwd){
				var input = $("#passwd").val();
				if(passwd == input) {
					window.parent.topFrame.location.href = "header_admin.html";
					window.parent.mainFrame.location.href = "testing.html";
				}
				else {
					$("#passwd").css("border-color", "red");
				}
			});
		}
	});
});