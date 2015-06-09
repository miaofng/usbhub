var fs = require('fs');
var sqlite3 = require('sqlite3').verbose();
var net = require('net');
var spawn = require('child_process').spawn;

var host = '127.0.0.1';
var port = 10003;

exports.cfg_get = function(name, cb) {
	db.get("SELECT * FROM cfg WHERE name=?", name, function(err, row) {
		cb(row['value']);
	});
};

exports.cfg_set = function(name, value) {
	db.run("UPDATE cfg SET value=? WHERE name = ?", value, name, function(err) {
		if(err) {
			console.log("cfg: "+name+"="+value+" "+err);
		}
	});
};

exports.model_get = function(model, cb) {
	db.get("SELECT * FROM model WHERE name = ?", model, function(err, row) {
		if(err) {
		}
		else {
			cb(row);
		}
	});
};

exports.start = function() {
	var server = net.createServer();
	server.once('error', function(err) {
		if (err.code === 'EADDRINUSE') {
			console.log("external server ran already");
		}
	});

	server.listen(port, host, function() {
		server.close();
		console.log("starting server tester.py ...");
		tester = spawn('python', ['tester.py'], { stdio: 'pipe', cwd: 'www/tester/'});
		tester.stdout.on('data', function(data) {
			console.log(data.toString());
		});
		tester.stderr.on('data', function (data) {
			console.error(data.toString());
		});
	});
};

exports.stop = function() {
	tester.kill();
}

exports.query = function(cmdline, callback) {
	var tester = new net.Socket();
	tester.connect(port, host, function() {
		tester.write(cmdline);
	});

	tester.on('data', function(data) {
		tester.destroy();
		callback(data);
	});
};

exports.init = function() {
	db = new sqlite3.Database('www/tester/irt.db', function(err){
		if(err) {
			console.log("open database, err: "+err);
		}
	});
};

exports.exit = function() {
	db.close();
};