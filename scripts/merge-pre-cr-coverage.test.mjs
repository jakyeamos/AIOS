import assert from "node:assert/strict";
import test from "node:test";

import { mergeLcovReports } from "./merge-pre-cr-coverage.mjs";

test("merges complete LCOV records without rewriting paths", () => {
  const python = "SF:services/example.py\nDA:1,1\nend_of_record\n";
  const node = "SF:tools/example.mjs\nDA:1,1\nend_of_record\n";

  assert.equal(
    mergeLcovReports([python, node]),
    "SF:services/example.py\nDA:1,1\nend_of_record\nSF:tools/example.mjs\nDA:1,1\nend_of_record\n",
  );
});

test("rejects empty or incomplete reports", () => {
  assert.throws(() => mergeLcovReports([""]), /must contain LCOV records/);
  assert.throws(() => mergeLcovReports(["SF:tools/example.mjs\nDA:1,1\n"]), /end_of_record/);
});
