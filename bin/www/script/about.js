var require = window.parent.require
var irt = require('./script/irt.js');
var fs = require('fs');
var path = require('path');
var fdialogs = require('node-webkit-fdialogs')
var crc32 = require('crc-32')

$(function() {
	var session = window.sessionStorage;
	if (session.server_error) {
		$("#error").html(session.server_error);
		$("#error").css("border-color", "red");
		$("#photo").attr("src","../img/ohno.jpg");
	}
});