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

exports.test_get = function(id, cb) {
	db.get("SELECT * FROM test WHERE id = ?", id, function(err, row) {
		if(err) {
		}
		else {
			cb(row);
		}
	});
};

exports.test_enum = function(cnds, cb) {
	var date_start = cnds.date_start.trim();
	var date_end = cnds.date_end.trim();
	var model = cnds.model.replace(/\*/g, "%");
	var barcode = cnds.barcode.replace(/\*/g, "%");
	var nrecords = cnds.max_records;
	var scnd = ecnd = nlim = "";

	if(date_start.length > 0) {
		scnd = 'AND strftime("%s", time) > strftime("%s", "'+date_start+'")';
	}
	if(date_end.length > 0) {
		ecnd = 'AND strftime("%s", time) < strftime("%s", "'+date_end+'", "+1 day")';
	}
	if(nrecords != null) {
		nlim = 'LIMIT ' + nrecords;
	}

	model = (model.length == 0) ? "%" : model;
	barcode = (barcode.length == 0) ? "%" : barcode;
	var where = 'WHERE model LIKE "' +model+ '" AND barcode LIKE "' +barcode+ '"';
	where = where + " " + scnd + " " + ecnd + " " + nlim;
	var sql = "SELECT * FROM test " + where;

	db.all(sql, function(err, rows) {
		if(err) {
		}
		else {
			cb(rows);
		}
	});
};

exports.model_enum = function(name, cb) {
	db.all('SELECT * FROM model WHERE name like "%'+name+'%" LIMIT 10', function(err, rows) {
		if(err) {
		}
		else {
			cb(rows);
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