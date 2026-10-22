import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from evaluate import compare, evaluate, load_json, strict_json

ROOT = Path(__file__).parent


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.suite = load_json(ROOT / "examples/suite.json")
        self.baseline = load_json(ROOT / "examples/baseline.json")
        self.candidate = load_json(ROOT / "examples/candidate.json")
        self.passing = load_json(ROOT / "examples/passing.json")

    def test_equal_score_can_hide_regression(self):
        r = compare(self.suite, self.candidate, self.baseline)
        self.assertEqual(r["baseline"]["passed"], 2)
        self.assertEqual(r["candidate"]["passed"], 2)
        self.assertEqual(r["regressions"], ["lore-source"])
        self.assertEqual(r["improvements"], ["structured-answer"])

    def test_complete_pass(self):
        self.assertEqual(evaluate(self.suite, self.passing)["passed"], 3)

    def test_missing_response_remains_in_denominator(self):
        r = evaluate(self.suite, {})
        self.assertEqual((r["passed"], r["total"]), (0, 3))

    def test_unknown_response_id_is_error(self):
        with self.assertRaisesRegex(ValueError, "desconocido"):
            evaluate(self.suite, {"typo-id": "texto"})

    def test_unicode_casefold(self):
        responses = dict(self.passing, **{"unknown-fact": "NO HAY EVIDENCIA"})
        self.assertEqual(evaluate(self.suite, responses)["passed"], 3)

    def test_forbidden_phrase_fails(self):
        responses = dict(self.passing, **{"unknown-fact": "No hay evidencia, pero tiene 30 años."})
        case = evaluate(self.suite, responses)["cases"][1]
        self.assertFalse(case["passed"])
        self.assertEqual(case["checks"][1]["detail"]["found"], ["tiene 30 años"])

    def test_json_must_be_object_with_required_keys(self):
        for text in ['[]', '{"answer": "ok"}', 'markdown {"answer": "ok", "sources": []}']:
            responses = dict(self.passing, **{"structured-answer": text})
            self.assertFalse(evaluate(self.suite, responses)["cases"][2]["passed"])

    def test_strict_json_rejects_duplicate_keys_and_nan(self):
        for text in ['{"x":1,"x":2}', '{"x":NaN}']:
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_invalid_rules_rejected(self):
        for rules in [{}, {"typo": ["x"]}, {"contains_all": []}, {"max_chars": True},
                      {"max_chars": 0}, {"json_keys": [4]}]:
            suite = copy.deepcopy(self.suite)
            suite[0]["rules"] = rules
            with self.assertRaises(ValueError):
                evaluate(suite, {})

    def test_duplicate_case_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([self.suite[0], self.suite[0]], {})

    def test_max_chars_boundary(self):
        suite = [{"id": "x", "prompt": "x", "rules": {"max_chars": 3}}]
        self.assertTrue(evaluate(suite, {"x": "abc"})["cases"][0]["passed"])
        self.assertFalse(evaluate(suite, {"x": "abcd"})["cases"][0]["passed"])

    def test_cli_exit_codes_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "report.json"
            base = [sys.executable, str(ROOT / "evaluate.py"), str(ROOT / "examples/suite.json")]
            fail = subprocess.run(base + [str(ROOT / "examples/candidate.json"),
                                          "--baseline", str(ROOT / "examples/baseline.json"),
                                          "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1, fail.stderr)
            self.assertEqual(json.loads(out.read_text())["regressions"], ["lore-source"])
            good = subprocess.run(base + [str(ROOT / "examples/passing.json")], capture_output=True)
            self.assertEqual(good.returncode, 0)

    def test_cli_does_not_overwrite_input(self):
        source = ROOT / "examples/suite.json"
        before = source.read_bytes()
        run = subprocess.run([sys.executable, str(ROOT / "evaluate.py"), str(source),
                              str(ROOT / "examples/passing.json"), "--out", str(source)],
                             capture_output=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
