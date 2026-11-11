"""Offline tests. No network and no model gateway."""

import importlib.util
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from ideascientist.loop import _normalize_report, _normalize_review, _schema_errors, check_run, evaluate, ideate, resume
from ideascientist.mcp import handle
from ideascientist.paths import load_vendor
from ideascientist.provider import ScriptedProvider
from ideascientist.sources import DictSource, register_sources
from ideascientist.store import RunStore, dump

from corpus import (
    ANSWER,
    GOAL,
    IDENTITY,
    MARKER,
    SEARCH,
    URL,
    baseline,
    candidate,
    digest,
    discovery,
    evaluation,
    gap,
    happy_steps,
    late_discovery,
    report,
    review,
    support,
)

PLUGIN = Path(__file__).resolve().parent


def run_happy(root):
    provider = ScriptedProvider(happy_steps())
    result = ideate(
        "SYNTHETIC offline test problem",
        cwd=root,
        provider=provider,
        source=DictSource({URL: "Synthetic note. The mechanism requires a stable signal. No measured outcome is stated."}),
        cutoff="2020-12-31",
        slug="synthetic",
        language="English",
    )
    return provider, result


class RunTests(unittest.TestCase):
    def test_report_hyperparameter_list_preserves_model_text(self):
        payload = report()["report"]
        values = ["Explanation order k", "Coalition sample budget M"]
        payload["model_details"]["training"]["key_hyperparameters"] = values
        normalized = _normalize_report(payload)
        self.assertEqual(list(normalized["model_details"]["training"]["key_hyperparameters"].values()), values)

    def test_report_invalid_evidence_type_is_not_accepted(self):
        steps = happy_steps()
        rejected = report()
        rejected["supports"][0]["kind"] = "definition"
        steps[-1] = ("report-writer", rejected)
        result = ideate(
            "SYNTHETIC offline test problem", cwd=self.root(),
            provider=ScriptedProvider(steps), source=DictSource({URL: "Synthetic note. The mechanism requires a stable signal."}),
            cutoff="2020-12-31", slug="invalid-evidence", language="English",
        )
        root = Path(result["run_dir"])
        self.assertEqual(result["status"], "blocked")
        self.assertFalse((root / "report.json").exists())
        self.assertEqual(json.loads((root / "report-attempt.json").read_text(encoding="utf-8"))["supports"][0]["kind"], "definition")

    def test_resume_repairs_saved_report_attempt(self):
        steps = happy_steps()
        rejected = report()
        rejected["supports"][0]["locator"] = "wrong locator"
        steps[-1] = ("report-writer", rejected)
        result = ideate(
            "SYNTHETIC offline test problem", cwd=self.root(),
            provider=ScriptedProvider(steps), source=DictSource({URL: "Synthetic note. The mechanism requires a stable signal."}),
            cutoff="2020-12-31", slug="report-retry", language="English",
        )
        root = Path(result["run_dir"])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(json.loads((root / "report-attempt.json").read_text(encoding="utf-8"))["supports"][0]["locator"], "wrong locator")
        provider = ScriptedProvider([("report-writer", report())])
        result = resume(root, "", provider=provider, source=DictSource({}))
        self.assertEqual(result["status"], "complete", result["content"])
        packet = json.loads(provider.calls[0]["messages"][1]["content"])
        self.assertEqual(packet["rejected_supports"][0]["locator"], "wrong locator")
        self.assertEqual(check_run(root), [])

    def test_review_with_unmatched_support_is_saved_and_repaired(self):
        steps = happy_steps()
        index = next(i for i, (role, _) in enumerate(steps) if role == "reviewer")
        rejected = review()
        rejected["artifact"]["supports"][0]["locator"] = "wrong locator"
        steps.insert(index, ("reviewer", rejected))
        result = ideate(
            "SYNTHETIC offline test problem", cwd=self.root(),
            provider=ScriptedProvider(steps), source=DictSource({URL: "Synthetic note. The mechanism requires a stable signal."}),
            cutoff="2020-12-31", slug="review-repair", language="English",
        )
        self.assertEqual(result["status"], "complete", result["content"])
        self.assertEqual(check_run(result["run_dir"]), [])
        attempts = list((Path(result["run_dir"]) / "attempts").glob("*.json"))
        self.assertTrue(any("wrong locator" in p.read_text(encoding="utf-8") for p in attempts))

    def test_innovator_can_discover_sources_before_candidate(self):
        steps = happy_steps()
        index = next(i for i, (role, _) in enumerate(steps) if role == "innovator")
        steps.insert(index, ("innovator", discovery()))
        result = ideate(
            "SYNTHETIC offline test problem", cwd=self.root(),
            provider=ScriptedProvider(steps), source=DictSource({URL: "Synthetic note. The mechanism requires a stable signal."}),
            cutoff="2020-12-31", slug="innovator-discovery", language="English",
        )
        self.assertEqual(result["status"], "complete", result["content"])
        self.assertEqual(check_run(result["run_dir"]), [])
        run = RunStore(result["run_dir"])
        task = next(t for t in run.data["tasks"] if t["role"] == "innovator" and t["output"].startswith("discoveries/"))
        self.assertEqual(task["status"], "done")

    def test_vendored_checker_accepts_plugin_fixture(self):
        spec = importlib.util.spec_from_file_location("native_fixture", PLUGIN / "native_fixture.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = module.create_run(self.fixture_dir())
        self.assertEqual(check_run(root), [])

    def test_checker_reads_utf8_on_windows(self):
        spec = importlib.util.spec_from_file_location("native_fixture_utf8", PLUGIN / "native_fixture.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = module.create_run(self.root() / "utf8")
        run = json.loads((root / "run.json").read_text(encoding="utf-8"))
        run["problem"] = "合成测试：稀疏奖励下的长程信用分配"
        run["challenge"] = "信用分配"
        (root / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (root / "plan.md").write_text("# 计划\n\n只检查编码。\n", encoding="utf-8")
        self.assertEqual(check_run(root), [])

    def test_happy_path_passes_checker(self):
        provider, result = run_happy(self.root())
        self.assertEqual(result["errors"], [], result["content"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(check_run(result["run_dir"]), [])
        baseline_calls = [call for call in provider.calls if call["role"] == "blind-baseline"]
        self.assertEqual(len(baseline_calls), 1)
        blob = json.dumps(baseline_calls[0]["messages"])
        self.assertNotIn(MARKER, blob)
        self.assertNotIn("Intuition", blob)

    def test_cutoff_registers_nothing(self):
        provider = ScriptedProvider([
            ("axes", {"challenge": "Late sources", "axes": ["Dates"]}),
            ("gap-finder", late_discovery()),
        ])
        result = ideate(
            "SYNTHETIC cutoff problem",
            cwd=self.root(),
            provider=provider,
            source=DictSource({}),
            cutoff="2020-12-31",
            slug="cutoff",
        )
        store = RunStore(result["run_dir"])
        self.assertEqual(store.data["papers"], [])
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(any(call["role"] == "paper-reader" for call in provider.calls))
        self.assertEqual(check_run(result["run_dir"]), [], result["content"])

    def test_budget_stops_before_the_next_role(self):
        provider = ScriptedProvider([("axes", {"challenge": "Budget", "axes": ["One axis"]})])
        result = ideate(
            "SYNTHETIC budget problem",
            cwd=self.root(),
            provider=provider,
            source=DictSource({}),
            slug="budget",
            max_role_calls=1,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(provider.calls), 1)
        self.assertTrue((Path(result["run_dir"]) / "problem.md").is_file())
        self.assertEqual(check_run(result["run_dir"]), [])

    def test_evaluate_completed_report(self):
        _provider, result = run_happy(self.root())
        graded = evaluate(result["run_dir"], provider=ScriptedProvider([("reviewer", evaluation())]))
        self.assertEqual(graded["errors"], [], graded["content"])
        self.assertEqual(graded["stage"], "evaluated")

    def test_register_sources_rejects_a_later_version(self):
        root = self.root() / "runs" / "ideascientist" / "unit"
        root.mkdir(parents=True)
        dump(root / "run.json", {
            "papers": [],
            "next_ids": {"paper": 1, "gap": 1, "candidate": 1, "task": 1},
        })
        (root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        store = RunStore(root)
        admitted, rejected = register_sources(store, late_discovery()["sources"], "2020-12-31")
        self.assertEqual(admitted, [])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(store.data["papers"], [])

    def test_resume_reads_registered_papers_without_searching_again(self):
        root = self.root() / "runs" / "ideascientist" / "partial"
        root.mkdir(parents=True)
        dump(root / "run.json", {
            "schema_version": 1,
            "slug": "partial",
            "problem": "SYNTHETIC offline test problem",
            "challenge": "Synthetic signal stability",
            "language": "English",
            "cutoff": "2020-12-31",
            "stage": "planned",
            "status": "active",
            "reason": "Resuming after a failed read.",
            "axes": [{"axis_id": "A001", "name": "Synthetic signal stability"}],
            "selected": {"axis_id": None, "gap_id": None, "candidate_id": None},
            "next_ids": {"paper": 2, "gap": 1, "candidate": 1, "task": 2},
            "budgets": {
                "role_calls": {"limit": 24, "spent": 2},
                "searches": {"limit": 40, "spent": 1},
                "reader_calls": {"limit": 18, "spent": 1},
            },
            "max_revisions": 2,
            "max_candidates_per_gap": 3,
            "blind_baseline": True,
            "papers": [{"paper_id": "P001", "identity": IDENTITY}],
            "tasks": [{
                "task_id": "T001",
                "role": "gap-finder",
                "target": "Gaps.",
                "output": "gaps/A001.json",
                "status": "done",
                "search_allowance": 8,
                "reader_allowance": 0,
            }],
        })
        (root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (root / "problem.md").write_text("# Problem\n\nSYNTHETIC offline test problem\n", encoding="utf-8")
        dump(root / "discoveries" / "T001.json", {
            "task_id": "T001",
            "role": "gap-finder",
            "sources": [{"identity": IDENTITY, "goals": [GOAL]}],
            "search": SEARCH,
        })
        provider = ScriptedProvider([
            ("paper-reader", digest()),
            ("gap-finder", gap()),
            ("blind-baseline", baseline()),
            ("innovator", candidate()),
            ("reviewer", review()),
            ("report-writer", report()),
        ])
        result = resume(
            root,
            "",
            provider=provider,
            source=DictSource({URL: "Synthetic note. The mechanism requires a stable signal."}),
        )
        self.assertEqual(result["errors"], [], result["content"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(provider.calls[0]["role"], "paper-reader")
        gap_calls = [call for call in provider.calls if call["role"] == "gap-finder"]
        self.assertEqual(len(gap_calls), 1)
        self.assertEqual(gap_calls[0]["tools"], [])
        store = RunStore(result["run_dir"])
        self.assertEqual(store.data["budgets"]["searches"]["spent"], 1)

    def test_resume_resubmits_a_gap_with_the_wrong_shape(self):
        root = self.root() / "runs" / "ideascientist" / "reshape"
        root.mkdir(parents=True)
        dump(root / "run.json", {
            "schema_version": 1,
            "slug": "reshape",
            "problem": "SYNTHETIC offline test problem",
            "challenge": "Synthetic signal stability",
            "language": "English",
            "cutoff": "2020-12-31",
            "stage": "gaps",
            "status": "no_gap",
            "reason": "The model used the wrong field names.",
            "axes": [{"axis_id": "A001", "name": "Synthetic signal stability"}],
            "selected": {"axis_id": "A001", "gap_id": None, "candidate_id": None},
            "next_ids": {"paper": 2, "gap": 1, "candidate": 1, "task": 2},
            "budgets": {
                "role_calls": {"limit": 24, "spent": 2},
                "searches": {"limit": 40, "spent": 1},
                "reader_calls": {"limit": 18, "spent": 1},
            },
            "max_revisions": 2,
            "max_candidates_per_gap": 3,
            "blind_baseline": True,
            "papers": [{"paper_id": "P001", "identity": IDENTITY}],
            "tasks": [],
        })
        (root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (root / "problem.md").write_text("# Problem\n\nSYNTHETIC offline test problem\n", encoding="utf-8")
        saved = digest()
        dump(root / "papers" / "P001.json", {
            "paper_id": "P001",
            "identity": IDENTITY,
            "access_level": "full_text",
            "read_status": "read",
            "results_masked": True,
            "views": saved["views"],
            "answers": saved["answers"],
            "limitations": saved["limitations"],
        })
        dump(root / "gaps" / "A001.json", {
            "axis_id": "A001",
            "axis": "Synthetic signal stability",
            "outcome": "gap_found",
            "method_summary": "Synthetic filter [P001].",
            "gaps": [{"gap": "Synthetic methods require a stable signal [P001].", "gap_id": "G001"}],
        })
        provider = ScriptedProvider([
            ("gap-finder", gap()),
            ("blind-baseline", baseline()),
            ("innovator", candidate()),
            ("reviewer", review()),
            ("report-writer", report()),
        ])
        result = resume(root, "", provider=provider, source=DictSource({}))
        self.assertEqual(result["errors"], [], result["content"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(provider.calls[0]["role"], "gap-finder")
        self.assertEqual(provider.calls[0]["tools"], [])
        self.assertEqual(RunStore(result["run_dir"]).data["budgets"]["searches"]["spent"], 1)

    def test_resume_resubmits_a_baseline_with_the_wrong_shape(self):
        root = self.root() / "runs" / "ideascientist" / "baseline"
        root.mkdir(parents=True)
        saved = digest()
        gap_artifact = gap()["artifact"]
        gap_artifact["axis_id"] = "A001"
        gap_artifact["axis"] = "Synthetic signal stability"
        gap_artifact["gaps"][0]["gap_id"] = "G001"
        gap_artifact["supports"][0]["answer_text"] = ANSWER
        dump(root / "run.json", {
            "schema_version": 1,
            "slug": "baseline",
            "problem": "SYNTHETIC offline test problem",
            "challenge": "Synthetic signal stability",
            "language": "English",
            "cutoff": "2020-12-31",
            "stage": "gaps",
            "status": "blocked",
            "reason": "innovator did not return a candidate",
            "axes": [{"axis_id": "A001", "name": "Synthetic signal stability"}],
            "selected": {"axis_id": "A001", "gap_id": "G001", "candidate_id": None},
            "next_ids": {"paper": 2, "gap": 2, "candidate": 2, "task": 2},
            "budgets": {
                "role_calls": {"limit": 24, "spent": 4},
                "searches": {"limit": 40, "spent": 1},
                "reader_calls": {"limit": 18, "spent": 1},
            },
            "max_revisions": 2,
            "max_candidates_per_gap": 3,
            "blind_baseline": True,
            "papers": [{"paper_id": "P001", "identity": IDENTITY}],
            "tasks": [],
        })
        (root / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (root / "problem.md").write_text("# Problem\n\nSYNTHETIC offline test problem\n", encoding="utf-8")
        dump(root / "papers" / "P001.json", {
            "paper_id": "P001",
            "identity": IDENTITY,
            "access_level": "full_text",
            "read_status": "read",
            "results_masked": True,
            "views": saved["views"],
            "answers": saved["answers"],
            "limitations": saved["limitations"],
        })
        dump(root / "gaps" / "A001.json", gap_artifact)
        dump(root / "baselines" / "G001.json", {
            "gap_id": "G001",
            "before_candidate": "C001",
            "status": "submitted",
            "mechanisms": [{"name": "Synthetic filter", "description": "A synthetic filter."}],
        })
        provider = ScriptedProvider([
            ("blind-baseline", baseline()),
            ("innovator", candidate()),
            ("reviewer", review()),
            ("report-writer", report()),
        ])
        result = resume(root, "", provider=provider, source=DictSource({}))
        self.assertEqual(result["errors"], [], result["content"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(provider.calls[0]["role"], "blind-baseline")
        self.assertEqual(provider.calls[0]["tools"], [])
        self.assertEqual(RunStore(result["run_dir"]).data["budgets"]["searches"]["spent"], 1)

    def test_resume_resubmits_a_report_once(self):
        _provider, result = run_happy(self.root())
        root = Path(result["run_dir"])
        dump(root / "report.json", {
            "title": "SYNTHETIC offline proposal",
            "problem_statement": "Synthetic assumptions require stable signals.",
            "limitations": "Synthetic test only.",
        })
        store = RunStore(root)
        store.data["status"] = "blocked"
        store.data["reason"] = "The report used the wrong field names."
        spent = store.data["budgets"]["role_calls"]["spent"]
        searches = store.data["budgets"]["searches"]["spent"]
        store.data["budgets"]["role_calls"]["limit"] = spent + 1
        store.save()
        provider = ScriptedProvider([("report-writer", report())])
        result = resume(root, "", provider=provider, source=DictSource({}))
        self.assertEqual(result["errors"], [], result["content"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual([call["role"] for call in provider.calls], ["report-writer"])
        self.assertEqual(provider.calls[0]["tools"], [])
        saved = RunStore(root)
        self.assertEqual(saved.data["budgets"]["role_calls"]["spent"], spent + 1)
        self.assertEqual(saved.data["budgets"]["searches"]["spent"], searches)
        rewritten = json.loads((root / "report.json").read_text(encoding="utf-8"))
        evidence = json.loads((root / "report-evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(rewritten["one_sentence_thesis"], "A synthetic filter may adapt to changing signals.")
        self.assertNotIn("problem_statement", rewritten)
        self.assertEqual(evidence["report_snapshot"], rewritten)

    def test_resume_does_not_repair_a_report_twice(self):
        _provider, result = run_happy(self.root())
        root = Path(result["run_dir"])
        original = {
            "title": "SYNTHETIC offline proposal",
            "problem_statement": "Synthetic assumptions require stable signals.",
            "limitations": "Synthetic test only.",
        }
        dump(root / "report.json", original)
        store = RunStore(root)
        store.data["status"] = "blocked"
        store.data["budgets"]["role_calls"]["limit"] = store.data["budgets"]["role_calls"]["spent"] + 1
        store.save()
        provider = ScriptedProvider([
            ("report-writer", {"action": "submit_report", "supports": [support()], "report": {"title": "still flat"}}),
            ("report-writer", report()),
        ])
        result = resume(root, "", provider=provider, source=DictSource({}))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(json.loads((root / "report.json").read_text(encoding="utf-8")), original)
        self.assertIn("schema", result["content"].lower() + RunStore(root).data["reason"].lower())
        self.assertTrue((root / "report-attempt.json").is_file())

    def test_report_strings_become_arrays_without_new_text(self):
        payload = report()["report"]
        payload["topic_relevance"]["sub_topic"] = "Synthetic signal"
        payload["topic_relevance"]["primary_focus"] = "Stability"
        payload["core_problem"]["why_it_matters"] = "Synthetic users see changing inputs."
        payload["key_novelty"]["explanations"] = payload["key_novelty"].pop("explanation")
        payload["method"]["high_level_flow"] = "Segment then filter."
        payload["method"]["modules"][0]["inputs"] = "Signal"
        payload["method"]["modules"][0]["outputs"] = "Windows"
        payload["limitations"] = "(1) Synthetic test only. (2) No experiment conducted. (3) No actual scientific novelty judgment."
        fixed = _normalize_report(payload)
        self.assertEqual(fixed["topic_relevance"]["sub_topic"], ["Synthetic signal"])
        self.assertEqual(fixed["topic_relevance"]["primary_focus"], ["Stability"])
        self.assertEqual(fixed["core_problem"]["why_it_matters"], ["Synthetic users see changing inputs."])
        self.assertEqual(fixed["key_novelty"]["explanation"], ["Use stable local windows.", "Adapt between windows."])
        self.assertNotIn("explanations", fixed["key_novelty"])
        self.assertEqual(fixed["method"]["high_level_flow"], ["Segment then filter."])
        self.assertEqual(fixed["method"]["modules"][0]["inputs"], ["Signal"])
        self.assertEqual(fixed["method"]["modules"][0]["outputs"], ["Windows"])
        self.assertEqual(fixed["limitations"], [
            "Synthetic test only.",
            "No experiment conducted.",
            "No actual scientific novelty judgment.",
        ])
        self.assertEqual(_schema_errors("report", fixed), [])
        short = report()["report"]
        short["key_novelty"]["explanation"] = ["Only one sentence."]
        self.assertEqual(_normalize_report(short)["key_novelty"]["explanation"], ["Only one sentence."])
        prose = report()["report"]
        prose["model_details"]["training"]["key_hyperparameters"] = "Neighborhood size, controls B, folds K, and threshold tau."
        fixed_hp = _normalize_report(prose)
        self.assertEqual(
            fixed_hp["model_details"]["training"]["key_hyperparameters"],
            {"text": "Neighborhood size, controls B, folds K, and threshold tau."},
        )
        self.assertEqual(_schema_errors("report", fixed_hp), [])
        prose["model_details"]["training"] = "Do not invent the missing training fields."
        self.assertIsInstance(_normalize_report(prose)["model_details"]["training"], str)
        cited = report()["report"]
        cited["method"]["pseudocode"] = "Use the downstream weight [P001 或 P002 式]."
        self.assertIn("[P001] 或 [P002] 式", _normalize_report(cited)["method"]["pseudocode"])
        self.assertNotIn("[P001 或 P002 式]", _normalize_report(cited)["method"]["pseudocode"])

    def test_resume_keeps_a_report_whose_arrays_were_strings(self):
        _provider, result = run_happy(self.root())
        root = Path(result["run_dir"])
        dump(root / "report.json", {"title": "SYNTHETIC flat report", "limitations": "Synthetic."})
        store = RunStore(root)
        store.data["status"] = "blocked"
        store.data["budgets"]["role_calls"]["limit"] = store.data["budgets"]["role_calls"]["spent"] + 1
        store.save()
        shaped = report()
        body = shaped["report"]
        body["topic_relevance"]["sub_topic"] = "Synthetic signal"
        body["topic_relevance"]["primary_focus"] = "Stability"
        body["core_problem"]["why_it_matters"] = "Synthetic users see changing inputs."
        body["key_novelty"]["explanations"] = body["key_novelty"].pop("explanation")
        body["method"]["high_level_flow"] = "Segment then filter."
        body["method"]["modules"][0]["inputs"] = "Signal"
        body["method"]["modules"][0]["outputs"] = "Windows"
        provider = ScriptedProvider([("report-writer", shaped)])
        result = resume(root, "", provider=provider, source=DictSource({}))
        self.assertEqual(result["errors"], [], result["content"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(provider.calls), 1)
        rewritten = json.loads((root / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(rewritten["method"]["modules"][0]["inputs"], ["Signal"])
        self.assertNotIn("explanations", json.dumps(rewritten))
        self.assertFalse((root / "report-attempt.json").exists())

    def test_review_checks_flatten_to_the_models_reason(self):
        flat = _normalize_review({
            "path": "reviews/C001.json",
            "target_id": "C001",
            "checks": {"novelty": {"status": "pass", "reason": "A substantive novelty note."}},
        })
        self.assertNotIn("path", flat)
        self.assertNotIn("target_id", flat)
        self.assertEqual(flat["checks"]["novelty"], "A substantive novelty note.")

    def test_pdf_worker_can_be_spawned(self):
        module = load_vendor("acquire_arxiv")
        self.assertEqual(module._download_worker.__module__, "acquire_arxiv")
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            target = handle.name
        worker = context.Process(
            target=module._download_worker,
            args=("http://127.0.0.1:1/not-a-pdf", target, sender),
        )
        worker.start()
        sender.close()
        self.assertTrue(receiver.poll(20))
        self.assertFalse(receiver.recv())
        worker.join(timeout=20)
        receiver.close()
        Path(target).unlink(missing_ok=True)

    def test_mcp_lists_tools_and_runs(self):
        notes = []
        init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, emit=notes.append)
        self.assertEqual(init["result"]["serverInfo"]["name"], "ideascientist")
        listed = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, emit=notes.append)
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(names, ["ideascientist", "ideascientist-reply"])
        root = self.root()
        response = handle({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "ideascientist",
                "arguments": {
                    "prompt": "SYNTHETIC offline test problem",
                    "cutoff": "2020-12-31",
                    "slug": "mcp",
                    "cwd": str(root),
                    "language": "English",
                },
                "_meta": {"progressToken": "tok"},
            },
        }, emit=notes.append, provider=ScriptedProvider(happy_steps()), source=DictSource({
            URL: "Synthetic note. The mechanism requires a stable signal.",
        }), state_dir=root / "state")
        self.assertFalse(response["result"].get("isError"))
        self.assertTrue(response["result"]["structuredContent"]["runId"])
        self.assertTrue(any(note.get("method") == "notifications/progress" for note in notes))
        self.assertEqual(check_run(response["result"]["structuredContent"]["runDir"]), [])

    def root(self):
        path = Path(self.id().split(".")[-1])
        # unittest runs from the cli directory when we set cwd. Use a temp under the test module.
        base = Path(__file__).resolve().parent / "_tmp" / self.id().split(".")[-1]
        if base.exists():
            import shutil
            shutil.rmtree(base)
        base.mkdir(parents=True)
        return base

    def fixture_dir(self):
        return self.root() / "plugin-fixture"


if __name__ == "__main__":
    unittest.main()
