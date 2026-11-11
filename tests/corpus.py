"""Synthetic artifacts. They are not evidence about any real paper."""

GOAL = "What assumption does the synthetic mechanism require?"
ANSWER = "This synthetic note requires a stable signal."
LOCATOR = "Section synthetic mechanism"
MARKER = "UNIQUE_CANDIDATE_MARKER_9f3a"
URL = "https://example.invalid/offline-note-v1"

IDENTITY = {
    "title": "SYNTHETIC offline mechanism note",
    "authors": ["Offline fixture"],
    "url": URL,
    "doi": None,
    "version": "synthetic v1",
    "publication_date": "2020-01-01",
    "date_basis": "Synthetic fixture date, not a publication claim",
}

SEARCH = {
    "queries": ["synthetic offline query"],
    "coverage": "SYNTHETIC offline search trace, no web retrieval.",
    "status": "searched",
    "block_reason": None,
}


def support():
    return {
        "paper_id": "P001",
        "goal": GOAL,
        "locator": LOCATOR,
        "claim": "Synthetic mechanism requires a stable signal.",
        "kind": "mechanism",
        "answer_text": "",
    }


def axes():
    return {"challenge": "SYNTHETIC signal instability", "axes": ["Synthetic signal stability"]}


def discovery():
    return {
        "action": "submit_discovery",
        "sources": [{"identity": IDENTITY, "goals": [GOAL]}],
        "search": SEARCH,
    }


def late_discovery():
    identity = dict(IDENTITY)
    identity["publication_date"] = "2026-01-02"
    identity["url"] = "https://example.invalid/late-note-v2"
    return {
        "action": "submit_discovery",
        "sources": [{"identity": identity, "goals": [GOAL]}],
        "search": SEARCH,
    }


def digest():
    return {
        "action": "submit_digest",
        "access_level": "full_text",
        "read_status": "read",
        "views": {
            "problem_definition": "Synthetic stable-signal task.",
            "challenge": "Synthetic instability.",
            "intuition": "Synthetic stabilizer.",
            "solution": "Synthetic signal filter, no claimed outcome.",
        },
        "answers": [{
            "goal": GOAL,
            "answer": ANSWER,
            "locator": LOCATOR,
            "status": "answered",
            "access_level": "full_text",
        }],
        "limitations": ["Synthetic evidence only."],
    }


def gap():
    return {"action": "submit_artifact", "artifact": {
        "what_has_been_done": "Synthetic filter [P001].",
        "gaps": [{
            "Gap": "Synthetic methods require a stable signal [P001].",
            "Near-miss methods and coverage": "Synthetic filter is a narrow near miss [P001].",
            "Methodological deficiency": "Synthetic assumption fails under a changing signal [P001].",
            "Why it matters": "Synthetic downstream users need changing signals.",
            "Evidence route": "Observe consistency under synthetic signal change.",
            "near_miss_ids": ["P001"],
            "narrow_search_rationale": "SYNTHETIC narrow fixture has one source only.",
        }],
        "search": SEARCH,
        "supports": [support()],
        "outcome": "grounded",
        "reason": "Synthetic fixture.",
    }}


def baseline():
    return {"action": "submit_artifact", "artifact": {
        "mechanisms": [{
            "mechanism": "Synthetic filter [P001].",
            "derivation": "Synthetic derivation from a stable signal.",
        }],
        "supports": [support()],
    }}


def candidate():
    return {"action": "submit_artifact", "artifact": {
        "Intuition": f"Adapt the synthetic filter to a changing signal. {MARKER}",
        "Gap it attacks": "Synthetic stability assumption.",
        "Source inspiration": "Synthetic filter [P001].",
        "How it maps to this problem": "Signal corresponds to the changing input.",
        "Why it could work / feasibility": "Stable windows may satisfy the synthetic condition [P001].",
        "Novelty vs. closest in-domain work": "Synthetic comparison extends the stable case [P001].",
        "Main risk": "No stable window exists.",
        "novelty_type": "reinforcing-a-weak-connection",
        "source_ids": ["P001"],
        "closest_in_domain_ids": ["P001"],
        "search": SEARCH,
        "supports": [support()],
    }}


def review():
    return {"action": "submit_artifact", "artifact": {
        "verdict": "survive",
        "focus": None,
        "reason": "Synthetic structural verdict only.",
        "strongest_objection": "Synthetic assumption may fail.",
        "checks": {key: "SYNTHETIC fixture rationale." for key in (
            "novelty", "coherence", "feasibility", "clarity", "mapping", "grounding", "methodological_contribution",
        )},
        "search": SEARCH,
        "supports": [support()],
    }}


def report():
    return {"action": "submit_report", "supports": [support()], "report": {
        "title": "SYNTHETIC offline proposal",
        "topic_relevance": {"sub_topic": ["Synthetic signal"], "primary_focus": ["Stability"]},
        "one_sentence_thesis": "A synthetic filter may adapt to changing signals.",
        "core_problem": {
            "problem_statement": "Synthetic assumptions require stable signals [P001].",
            "why_it_matters": ["Synthetic users see changing inputs."],
            "concrete_example": "A synthetic signal changes halfway through a window.",
        },
        "key_novelty": {"main_idea": "Synthetic adaptive filter", "explanation": ["Use stable local windows.", "Adapt between windows."]},
        "problem_definition": {"formal_setting": "Synthetic sequential scalar input.", "inputs": "Synthetic signal.", "outputs": "Synthetic filtered signal."},
        "key_terms": {"window": "A local synthetic interval."},
        "related_work": [{"sub_area": "Synthetic filters", "what_it_does": "Assumes stable signals [P001].", "open_gap": "Synthetic signal changes.", "citations": ["P001"]}],
        "method": {
            "high_level_flow": ["Segment then filter."],
            "modules": [{
                "module": "Synthetic segmenter",
                "role": "Find local windows.",
                "model": "Synthetic rule.",
                "inputs": ["Signal"],
                "outputs": ["Windows"],
                "notes": "Proposed synthetic design.",
            }],
            "novel_architectural_elements": ["Adaptive segmentation."],
            "pseudocode": "For each proposed stable window, apply a filter.",
            "design_choices": ["Local windows may approximate stability."],
            "theoretical_grounding": "A synthetic untested stability hypothesis.",
        },
        "model_details": {
            "base_model": "No learned model in this synthetic proposal.",
            "training": {
                "method": "No training.",
                "objective_functions": ["Synthetic consistency criterion."],
                "adaptation": "No parameter training.",
                "key_hyperparameters": {},
            },
        },
        "comparison_to_sota": {
            "related_methods": ["Synthetic stable filter [P001]."],
            "key_differences": ["Adds synthetic local windows."],
        },
        "proposed_evaluation": {
            "evaluation_setting": "Proposed synthetic changing signals.",
            "benchmarks": [{"name": "New synthetic signal set.", "task_type": "Filtering", "newly_constructed": True}],
            "baselines": ["Synthetic stable filter [P001]."],
            "main_metrics": ["Proposed signal consistency."],
            "ablations": ["Remove synthetic segmentation."],
        },
        "falsifiable_predictions": [{
            "pillar": "Local stability",
            "prediction": "Synthetic local windows may preserve consistency.",
            "kill_condition": "Consistency fails despite stable local windows.",
        }],
        "limitations": ["Synthetic test only.", "No experiment conducted.", "No actual scientific novelty judgment."],
    }}


def evaluation():
    qualities = ("actionability", "specificity", "clarity", "impact", "soundness", "relevance")
    return {"action": "submit_artifact", "artifact": {
        "quality": {name: {"score": 3, "rationale": "Synthetic structural score only."} for name in qualities},
        "novelty": {"scope": "live", "coverage": "Synthetic coverage only.", "judgment": "Not a claim of novelty."},
        "nonobviousness": {"status": "unavailable", "baseline_file": None, "rationale": "Coordinator records the frozen baseline."},
        "search": SEARCH,
        "supports": [],
    }}


def happy_steps():
    return [
        ("axes", axes()),
        ("gap-finder", discovery()),
        ("paper-reader", digest()),
        ("gap-finder", gap()),
        ("blind-baseline", baseline()),
        ("innovator", candidate()),
        ("reviewer", review()),
        ("report-writer", report()),
    ]
