"""Check synthetic fixture integrity; this does not execute or evaluate an LLM."""

import json
from pathlib import Path


def expected_zone(case):
    a = case["assumptions"]
    score = case["candidate_expected"]["score"]
    if not a["internal_use_permitted"]:
        return "不使用"
    if not a["publication_scope_allowed"]:
        return "内部研究（仅许可范围）"
    if not a["within_requested_window"]:
        return "内部观察"
    if not a["research_value"]:
        return "排除"
    if not a["source_read"] or not a["source_traceable"] or score is None:
        return "内部观察" if a["source_traceable"] else "排除"
    if score >= 75 and a["core_facts_verified"] and a["inspiration_clear"]:
        return "正式信号"
    if (case["kind"] == "case" and 70 <= score <= 75
            and a["research_conditions_met"] and a["mechanism_supported"]):
        return "案例研究区"
    return "内部观察"


def check(data):
    if not data["all_material_is_synthetic"]:
        raise ValueError("Fixtures must be synthetic")
    provenance = data["provenance"]
    for name in ("candidate_model_run", "boundary_cases_model_run",
                 "official_pyyaml_validation_passed", "runtime_installation_tested"):
        if provenance[name] is not False:
            raise ValueError("Unverified execution claim: " + name)
    cases = data["historical_nine_adapted"] + data["new_boundary_cases"]
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)) or len(data["historical_nine_adapted"]) != 9:
        raise ValueError("Missing or duplicate historical case")
    maxima = data["dimension_maxima"]
    if maxima != [30, 25, 20, 15, 10] or sum(maxima) != 100:
        raise ValueError("Invalid scoring weights")
    for case in cases:
        ident = case["id"]
        exp = case["candidate_expected"]
        dims = case["candidate_score_dimensions"]
        if dims is not None:
            if len(dims) != 5 or any(type(n) is not int or not 0 <= n <= cap
                                     for n, cap in zip(dims, maxima)):
                raise ValueError(ident + ": invalid dimensions")
            if sum(dims) != exp["score"]:
                raise ValueError(ident + ": total differs from dimensions")
        elif exp["score"] is not None:
            raise ValueError(ident + ": unsupported exact score")
        if case["candidate_model_execution"] != "not_run":
            raise ValueError(ident + ": fixture must not claim a model run")
        zone = expected_zone(case)
        if zone != exp["zone"]:
            raise ValueError(ident + ": zone conflicts with declared assumptions")
        expected_counts = (int(zone == "正式信号"), int(zone == "案例研究区"))
        if (exp["formal_count"], exp["case_research_count"]) != expected_counts:
            raise ValueError(ident + ": counts conflict with zone")
        if exp["qualified_daily_count_default"] != exp["formal_count"]:
            raise ValueError(ident + ": daily count differs from documented default")
        if exp["score"] is not None and exp["score"] < 70 and any(expected_counts):
            raise ValueError(ident + ": sub-70 case was counted")
        for dim_key, score_key in (("before_update_dimensions", "before_update_score"),
                                   ("superseded_research_dimensions", "superseded_research_score")):
            if dim_key in case and sum(case[dim_key]) != case[score_key]:
                raise ValueError(ident + ": update arithmetic mismatch")
        if "input_records" in case:
            if case["expected_unique_events"] != 1 or case["input_records"] != 2:
                raise ValueError(ident + ": duplicate event contract mismatch")
            if sum(expected_counts) > case["expected_unique_events"]:
                raise ValueError(ident + ": same event counted across zones")
    # Preserve observations separately from the corrected contract.
    historical = {c["id"]: c["historical_observation"] for c in data["historical_nine_adapted"]}
    for ident, score in (("T1", 74), ("T2", 69), ("T4", 63), ("T6", 64), ("T7", 74)):
        if historical[ident]["score"] != score:
            raise ValueError(ident + ": historical score overwritten")
    return len(cases)


if __name__ == "__main__":
    fixture_path = Path(__file__).with_name("synthetic-cases.json")
    count = check(json.loads(fixture_path.read_text(encoding="utf-8")))
    print(f"{count} synthetic fixture integrity checks passed; no model or runtime test performed.")
