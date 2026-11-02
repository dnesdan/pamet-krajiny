"""Check the shipped skill, real dossiers and nationwide source selection."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SKILL = next((ROOT / "skills").glob("*/SKILL.md")).parent
spec = importlib.util.spec_from_file_location("package_badatel", SKILL / "scripts/badatel.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class PackageTests(unittest.TestCase):
    def test_shipped_dossiers_are_valid_and_exportable(self):
        paths = sorted((ROOT / "examples").glob("*.json"))
        dossiers = []
        for path in paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            if "project" in value and "schema_version" in value:
                dossiers.append((path, value))
        self.assertGreaterEqual(len(dossiers), 2)
        expected_theme = "landscape" if SKILL.name == "pamet-krajiny" else "enterprise"
        for path, data in dossiers:
            with self.subTest(file=path.name):
                self.assertEqual(b.validate(data), [])
                self.assertEqual(data["project"]["theme"], expected_theme)
                self.assertTrue(data["claims"])
                self.assertTrue(data["sources"])
                self.assertNotIn("example.org", json.dumps(data))
                page = b.render_html(data)
                self.assertIn("<!doctype html", page.lower())
                self.assertIn(data["project"]["title"], page)
                self.assertEqual(b.render_geojson(data)["type"], "FeatureCollection")

    def test_real_catalogue_routes_every_region_to_a_regional_archive(self):
        catalogue = b.load_catalogue()
        by_id = {s["id"]: s for s in catalogue}
        regions = ["Praha", "Středočeský", "Jihočeský", "Plzeňský", "Karlovarský", "Ústecký", "Liberecký", "Královéhradecký", "Pardubický", "Vysočina", "Jihomoravský", "Olomoucký", "Zlínský", "Moravskoslezský"]
        for region in regions:
            with self.subTest(region=region):
                result = b.plan("Libovolná jednoznačně určená obec", region, "historie", catalogue=catalogue)
                chosen = [by_id[q["source_id"]] for q in result["queries"]]
                self.assertTrue(any("archiv" in s["topics"] and "CZ" not in s["regions"] for s in chosen))
                if region != "Jihomoravský":
                    self.assertFalse(any(s["id"] == "brno-maps" for s in chosen))
                self.assertEqual(result["status"], "plan_only")

    def test_catalogue_records_capabilities_and_limits(self):
        catalogue = b.load_catalogue()
        ids = [s["id"] for s in catalogue]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(catalogue), 40)
        for source in catalogue:
            with self.subTest(source=source["id"]):
                self.assertIn(urlparse(source["url"]).scheme, ("https", "http"))
                self.assertTrue(source["limitations"])
                self.assertTrue(source["description"])
                self.assertTrue(source["automation"])
                self.assertTrue(source["regions"])

    def test_skill_references_are_portable_inside_package(self):
        # A user installs the skill folder, not the whole GitHub repository.
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertLess(len(text.splitlines()), 500)
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in link or link.startswith("#"):
                continue
            target = (SKILL / link.split("#", 1)[0]).resolve()
            self.assertTrue(target.exists(), f"Missing skill resource: {link}")
            self.assertTrue(target.is_relative_to(SKILL.resolve()), f"Skill requires an unbundled file: {link}")

    def test_installable_folder_works_without_repository_root(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / SKILL.name
            shutil.copytree(SKILL, installed, ignore=shutil.ignore_patterns("__pycache__"))
            command = [sys.executable, str(installed / "scripts/badatel.py"), "plan", "--place", "Liberec", "--region", "Liberecký", "--topic", "textil"]
            result = subprocess.run(command, cwd=directory, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "plan_only")
            self.assertTrue(any(q["source_id"] == "soa-litomerice" for q in data["queries"]))


if __name__ == "__main__":
    unittest.main()
