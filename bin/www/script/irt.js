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
		if(err != null) {
			console.log("cfg: "+name+"="+value+" "+err);
		}
	});
};

exports.model_get = function(model, cb) {
	db.get("SELECT * FROM model WHERE name = ?", model, function(err, row) {
		if(err != null) {
		}
		else {
			if(cb != null) {
				cb(row);
			}
		}
	});
};

exports.model_set = function(model, cb) {
	var sql = "UPDATE model SET name=$name, nrow=$nrow, \
		ncol=$ncol, nsub=$nsub, points=$points, \
		offset=$offset, barcode=$barcode \
		WHERE id=$id \
	";

	if(isNaN(model.id) || (model.id == null)) {
		sql = "INSERT INTO model(name, nrow, ncol, nsub, points, offset, barcode) \
			VALUES($name, $nrow, $ncol, $nsub, $points, $offset, $barcode) \
		";
	}

	para = {};
	Object.keys(model).forEach(function(key){
		para["$"+key] = model[key];
	});
	db.run(sql, para, function(err) {
		if(cb != null) {
			cb(err, this.lastID);
		}
	});
};


exports.model_get_by_id = function(model_id, cb) {
	db.get("SELECT * FROM model WHERE id = ?", model_id, function(err, row) {
		if(err != null) {
			alert(err.message);
		}
		else {
			if(cb != null) {
				cb(row);
			}
		}
	});
};

exports.model_del = function(model_id, cb) {
	db.run("DELETE FROM model WHERE id = ?", model_id, function(err) {
		if(err != null) {
			alert(err.message);
		}
		else {
			if(cb != null) {
				cb();
			}
		}
	});
};

exports.test_get = function(id, cb) {
	db.get("SELECT * FROM test WHERE id = ?", id, function(err, row) {
		if(err) {
		}
		else {
			if(cb != null) {
				cb(row);
			}
		}
	});
};

exports.test_enum = function(cnds, cb) {
	var where = [];
	var cnd;

	if(!isNaN(cnds.date_start)) {
		var sdate = cnds.date_start.trim();
		if(sdate.length > 0) {
			cnd = 'strftime("%s", time) > strftime("%s", "{date}")';
			cnd = cnd.replace("{date}", sdate);
			where.push(cnd);
		}
	}

	if(!isNaN(cnds.date_end)) {
		var edate = cnds.date_end.trim();
		if(edate.length > 0) {
			cnd = 'strftime("%s", time) < strftime("%s", "{date}")';
			cnd = cnd.replace("{date}", edate);
			where.push(cnd);
		}
	}

	if(!isNaN(cnds.model)) {
		var model = cnds.model.trim();
		if(model.length > 0) {
			model = model.replace(/\*/g, "%");
			cnd = 'model like "{name}"';
			cnd = cnd.replace("{name}", model);
			where.push(cnd);
		}
	}

	if(!isNaN(cnds.barcode)) {
		var barcode = cnds.barcode.trim();
		if(barcode.length > 0) {
			barcode = barcode.replace(/\*/g, "%");
			cnd = 'barcode like "{name}"';
			cnd = cnd.replace("{name}", barcode);
			where.push(cnd);
		}
	}

	if(where.length > 0) {
		var WHERE = " WHERE " + where.join(" AND ");
	}
	if(!isNaN(cnds.max_records)) {
		var LIMIT = ' LIMIT ' + cnds.max_records;
	}

	var sql = "SELECT * FROM test " + WHERE + LIMIT;
	console.log(sql);
	db.all(sql, function(err, rows) {
		if(err) {
		}
		else {
			cb(rows);
		}
	});
};

exports.model_enum = function(name) {
	var max_records = (arguments.length > 2) ? arguments[1] : 10;
	var cb = (arguments.length > 2) ? arguments[2] : arguments[1];
	var model = name.replace(/\*/g, "%");
	db.all('SELECT * FROM model WHERE name like ? LIMIT ?', [model, max_records], function(err, rows) {
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