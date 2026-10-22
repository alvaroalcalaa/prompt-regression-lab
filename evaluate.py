"""Compare saved AI responses against deterministic rules. Python 3.10+."""
import argparse
import json
from pathlib import Path

RULES = {"contains_all", "forbidden_any", "max_chars", "json_keys"}


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("clave JSON duplicada: " + key)
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("constante JSON no válida: " + value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)


def load_json(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def validate_suite(suite):
    if not isinstance(suite, list) or not suite:
        raise ValueError("la suite debe ser una lista no vacía")
    seen = set()
    for case in suite:
        if not isinstance(case, dict) or set(case) != {"id", "prompt", "rules"}:
            raise ValueError("cada caso necesita exactamente id, prompt y rules")
        cid = case["id"]
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise ValueError("id vacío, duplicado o no textual")
        seen.add(cid)
        if not isinstance(case["prompt"], str):
            raise ValueError(f"{cid}: prompt debe ser texto")
        rules = case["rules"]
        if not isinstance(rules, dict) or not rules or set(rules) - RULES:
            raise ValueError(f"{cid}: reglas vacías o no reconocidas")
        for key, value in rules.items():
            if key == "max_chars":
                if type(value) is not int or value < 1:
                    raise ValueError(f"{cid}: max_chars debe ser un entero positivo")
            elif (not isinstance(value, list) or not value
                  or any(not isinstance(s, str) or not s for s in value)):
                raise ValueError(f"{cid}: {key} necesita una lista de textos no vacíos")
    return suite


def evaluate(suite, responses):
    validate_suite(suite)
    if not isinstance(responses, dict) or any(not isinstance(v, str) for v in responses.values()):
        raise ValueError("las respuestas deben ser un objeto id: texto")
    ids = {case["id"] for case in suite}
    unknown = set(responses) - ids
    if unknown:
        raise ValueError("respuestas con id desconocido: " + ", ".join(sorted(unknown)))
    results = []
    for case in suite:
        cid, rules = case["id"], case["rules"]
        checks = []
        if cid not in responses:
            checks.append({"rule": "response_present", "passed": False,
                           "detail": "respuesta ausente"})
        else:
            text = responses[cid]
            folded = text.casefold()
            for rule, expected in rules.items():
                if rule == "contains_all":
                    missing = [s for s in expected if s.casefold() not in folded]
                    passed, detail = not missing, {"missing": missing}
                elif rule == "forbidden_any":
                    found = [s for s in expected if s.casefold() in folded]
                    passed, detail = not found, {"found": found}
                elif rule == "max_chars":
                    passed, detail = len(text) <= expected, {"actual": len(text), "limit": expected}
                else:
                    try:
                        parsed = strict_json(text)
                        missing = [s for s in expected if not isinstance(parsed, dict) or s not in parsed]
                        passed = isinstance(parsed, dict) and not missing
                        detail = {"missing_keys": missing}
                    except ValueError:
                        passed, detail = False, {"error": "respuesta no es JSON estricto"}
                checks.append({"rule": rule, "passed": passed, "detail": detail})
        results.append({"id": cid, "passed": all(c["passed"] for c in checks), "checks": checks})
    passed = sum(r["passed"] for r in results)
    return {"total": len(results), "passed": passed,
            "pass_rate": round(passed / len(results), 4), "cases": results}


def compare(suite, candidate, baseline=None):
    report = {"candidate": evaluate(suite, candidate), "regressions": [], "improvements": []}
    if baseline is not None:
        report["baseline"] = evaluate(suite, baseline)
        old = {c["id"]: c["passed"] for c in report["baseline"]["cases"]}
        for case in report["candidate"]["cases"]:
            if old[case["id"]] and not case["passed"]:
                report["regressions"].append(case["id"])
            if not old[case["id"]] and case["passed"]:
                report["improvements"].append(case["id"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--out", type=Path, help="Informe JSON detallado")
    args = parser.parse_args()
    inputs = [p.resolve() for p in (args.suite, args.candidate, args.baseline) if p]
    if args.out and args.out.resolve() in inputs:
        parser.error("--out no puede sobrescribir una entrada")
    try:
        report = compare(load_json(args.suite), load_json(args.candidate),
                         load_json(args.baseline) if args.baseline else None)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.write_text(payload, encoding="utf-8")
        print(payload, end="")
    except (OSError, ValueError) as error:
        parser.exit(2, f"Error: {error}\n")
    parser.exit(0 if report["candidate"]["passed"] == report["candidate"]["total"] else 1)


if __name__ == "__main__":
    main()
