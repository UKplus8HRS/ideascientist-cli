"""Run directory, ids, and budgets. Counters never decrease."""

import json
import re
from pathlib import Path

PREFIXES = {"paper": "P", "gap": "G", "candidate": "C", "task": "T"}


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class RunStore:
    def __init__(self, path):
        self.path = Path(path)
        self.data = load_json(self.path / "run.json")

    def save(self):
        dump(self.path / "run.json", self.data)

    def log(self, text):
        # The checker treats [Pnnn] in markdown as a citation that needs a digest.
        safe = re.sub(r"\[(P\d+)\]", r"\1", text)
        with (self.path / "plan.md").open("a", encoding="utf-8") as handle:
            handle.write(safe.rstrip() + "\n")

    def reserve(self, kind, amount=1):
        budget = self.data["budgets"][kind]
        if budget["spent"] + amount > budget["limit"]:
            return False
        budget["spent"] += amount
        self.save()
        return True

    def alloc(self, kind):
        number = self.data["next_ids"][kind]
        self.data["next_ids"][kind] = number + 1
        self.save()
        return f"{PREFIXES[kind]}{number:03d}"

    def begin_task(self, role, target, output, search_allowance, reader_allowance):
        task_id = self.alloc("task")
        self.data["tasks"].append({
            "task_id": task_id,
            "role": role,
            "target": target,
            "output": output.replace("\\", "/"),
            "status": "active",
            "search_allowance": search_allowance,
            "reader_allowance": reader_allowance,
        })
        self.save()
        return task_id

    def finish_task(self, task_id, status="done"):
        for task in self.data["tasks"]:
            if task["task_id"] == task_id:
                task["status"] = status
                if status != "active":
                    task["output"] = task["output"].replace("\\", "/")
        self.save()

    def paper_map(self):
        return {paper["paper_id"]: paper for paper in self.data["papers"]}
