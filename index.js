/*
 * Christmas lights controller - Tim Poulsen
 * License MIT
 *
 *
 */

var rpio = require('rpio'),
	fs = require("fs"),
	path = require("path");

const OFF = rpio.HIGH;
const ON = rpio.LOW;

var pins = [3, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24];
var turnOffShowAt;
var initialized;
var show;
var showPositionCounter = 0;

turnOffAllRelays();

// process the command line arguments to turn relays on/off or start the show
if (process.argv[2]) {
	var showToRun = process.argv[2];
	if (showToRun === 'off') {
		turnOffAllRelays();
	} else if (showToRun === 'on') {
		turnOnAllRelays();
	} else {
		runShow(process.argv[2]);
	}
} else {
	var fields = require("fields");
	var shows = fs.readdirSync('shows');
	fields.set([
		fields.select({
			promptLabel: 'Which show would you like to run?',
			options: shows,
			numbered: true
		})
	]).prompt(function (err, value) {
		if (err) {
			console.error('There was an error!\n' + err);
		} else {
			runShow(value[0]);
		}
	});
}

// if present, process the turn-off-show argument
// turn off the show after x hours
if (process.argv[3] && !isNaN(process.argv[3])) {
	var now = new Date();
	var futureMS = Math.round(parseFloat(process.argv[3]) * 60 * 60 * 1000);
	turnOffShowAt = now.getTime() + futureMS;
}

/*
 * Main function to kick off the show, which marshalls off to a looping function
 */
function runShow(showName) {
	var filePath = path.join('shows', showName);
	if (!fs.existsSync(filePath)) {
		console.error('No show file by the name ' + showName);
		process.exit(1);
	}
	var showFile = fs.readFileSync(filePath, 'utf8');
	show = JSON.parse(showFile);
	showPositionCounter = 0;
	doShowLoop();
}

/*
 * doShowLoop processes one row of the show file, and if appropriate calls
 * itself to process the next (or back to first) row of the show file
 */
function doShowLoop() {
	if (showPositionCounter < show.show.length) {
		drawRow(show.show[showPositionCounter]);
		showPositionCounter++;
	} else {
		// we're at the end of the show file, do we repeat?
		if (show.loop && (!turnOffShowAt || (turnOffShowAt && (new Date()).getTime() < turnOffShowAt))) {
			showPositionCounter = 0;
			setTimeout(doShowLoop, show.interval);
		} else {
			endShow();
		}
	}
}

function endShow() {
	turnOffAllRelays();
	rpio.sleep(10);
	console.log('Good night');
}

function drawRow(arr) {
	arr.forEach(function (pinValue, index) {
		rpio.write(pins[index], pinValue ? ON : OFF);
	});
}

function turnOffAllRelays() {
	if (!initialized) {
		for (var i = 0, j = pins.length; i < j; i++) {
			rpio.open(pins[i], rpio.OUTPUT, OFF);
		}
		initialized = true;
	} else {
		pins.forEach(function (pin) {
			rpio.write(pin, OFF);
		});
	}
}

function turnOnAllRelays() {
	if (!initialized) {
		for (var i = 0, j = pins.length; i < j; i++) {
			rpio.open(pins[i], rpio.OUTPUT, ON);
		}
		initialized = true;
	} else {
		pins.forEach(function (pin) {
			rpio.write(pin, ON);
		});
	}
}