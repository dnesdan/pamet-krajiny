#!/usr/bin/env python3
"""Verify installable skill metadata, examples and JSON schema; no network."""
import importlib.util
import json
from pathlib import Path
import sys
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
skill_dirs = [p.parent for p in (ROOT / "skills").glob("*/SKILL.md")]
assert len(skill_dirs) == 1, "A repository must contain exactly one skill"
skill = skill_dirs[0]
text = (skill / "SKILL.md").read_text(encoding="utf-8")
assert text.startswith("---\n"), "Missing frontmatter"
front = yaml.safe_load(text.split("---", 2)[1])
assert set(front) == {"name", "description"}, "Only name and description belong in skill frontmatter"
assert front["name"] == skill.name and isinstance(front["description"], str) and front["description"].strip()
ui = yaml.safe_load((skill / "agents/openai.yaml").read_text(encoding="utf-8"))["interface"]
assert "$" + skill.name in ui["default_prompt"]
assert 25 <= len(ui["short_description"]) <= 64
schema = json.loads((skill / "schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(schema)
spec = importlib.util.spec_from_file_location("verify_badatel", skill / "scripts/badatel.py")
badatel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(badatel)
files = [skill / "assets/template.json"] + sorted((ROOT / "examples").glob("*.json"))
count = 0
for path in files:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "schema_version" not in data or "project" not in data:
        continue
    Draft202012Validator(schema).validate(data)
    errors = badatel.validate(data)
    assert not errors, str(path) + ": " + "; ".join(errors)
    count += 1
print(f"OK: skill metadata, UI metadata, JSON schema and {count} dossiers")
