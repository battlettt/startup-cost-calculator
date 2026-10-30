// Runs the demo's calculation code (docs/app.js) under Node and prints JSON
// results for each input file given on the command line, so the Python test
// suite can compare them with the CLI's numbers. Used by tests/test_parity.py.
"use strict";
const fs = require("fs");
const path = require("path");
const Calc = require(path.join(__dirname, "..", "..", "docs", "app.js"));

const out = {};
for (const file of process.argv.slice(2)) {
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  const res = Calc.check(data);
  const entry = { errors: res.errors, warnings: res.warnings, model: res.model };
  if (res.model) {
    entry.analysis = Calc.analyze(res.model);
    entry.comparison = Calc.compare(res.model);
  }
  out[file] = entry;
}
process.stdout.write(JSON.stringify(out));
