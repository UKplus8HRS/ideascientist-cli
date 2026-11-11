"""Regression tests for coordinator hardening and provider configuration. Offline."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ideascientist import cli
from ideascientist.loop import _bind_supports, _block
from ideascientist.provider import ProviderError, provider_from_env, resolve_settings
from ideascientist.sources import register_sources
from ideascientist.store import RunStore, dump


def _run(root):
    dump(root / "run.json", {
        "slug": root.name, "papers": [], "tasks": [],
        "next_ids": {"paper": 1, "gap": 1, "candidate": 1, "task": 1},
        "budgets": {"role_calls": {"limit": 2, "spent": 0}},
        "status": "active", "reason": "",
    })
    (root / "plan.md").write_text("# Plan\n", encoding="utf-8")
    return RunStore(root)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "r"
        self.root.mkdir()
        self.store = _run(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_interrupted_active_task_is_demoted(self):
        self.store.begin_task("gap-finder", "x", "gaps/A001.json", 1, 0)
        self.store.begin_task("gap-finder", "y", "gaps/A002.json", 1, 0)
        states = [t["status"] for t in self.store.data["tasks"]]
        self.assertEqual(states, ["blocked", "active"])

    def test_block_demotes_done_task_without_output(self):
        task = self.store.begin_task("reviewer", "x", "reviews/C001.json", 0, 0)
        self.store.finish_task(task, "done")
        _block(self.store, "supports did not bind")
        self.assertEqual(self.store.data["tasks"][0]["status"], "blocked")

    def test_bind_supports_rejects_malformed_shapes(self):
        self.assertFalse(_bind_supports(self.store, {"supports": "P001"}))
        self.assertFalse(_bind_supports(self.store, {"supports": ["P001"]}))
        self.assertTrue(_bind_supports(self.store, {"supports": []}))

    def test_register_sources_skips_non_objects(self):
        admitted, rejected = register_sources(self.store, ["arxiv:1234", {"identity": "x"}], None)
        self.assertEqual(admitted, [])
        self.assertEqual(len(rejected), 2)


class ProviderConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"IDEASCIENTIST_CONFIG": str(Path(self.tmp.name) / "c.json")}, clear=False)
        self.env.start()
        for key in ("IDEASCIENTIST_PROVIDER", "IDEASCIENTIST_BASE_URL", "IDEASCIENTIST_API_KEY", "IDEASCIENTIST_MODEL", "OPENAI_API_KEY"):
            os.environ.pop(key, None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_defaults_to_openai_preset(self):
        settings = resolve_settings()
        self.assertEqual(settings["provider"], "openai")
        self.assertEqual(settings["base_url"], "https://api.openai.com/v1")

    def test_env_overrides_config_and_flag_overrides_env(self):
        cli.main(["setup", "--non-interactive", "--provider", "custom", "--base-url", "http://h/v1", "--model", "m1", "--api-key", "k-secret-123"])
        os.environ["IDEASCIENTIST_MODEL"] = "m2"
        self.assertEqual(resolve_settings()["model"], "m2")
        self.assertEqual(resolve_settings("m3")["model"], "m3")
        provider = provider_from_env()
        self.assertEqual(provider.base_url, "http://h/v1")
        self.assertEqual(provider.api_key, "k-secret-123")
        self.assertNotIn("secret", json.dumps(provider.describe()))

    def test_custom_without_model_fails_clearly(self):
        os.environ["IDEASCIENTIST_PROVIDER"] = "custom"
        with self.assertRaises(ProviderError):
            provider_from_env()

    def test_unknown_provider(self):
        os.environ["IDEASCIENTIST_PROVIDER"] = "nope"
        with self.assertRaises(ProviderError):
            resolve_settings()


if __name__ == "__main__":
    unittest.main()
