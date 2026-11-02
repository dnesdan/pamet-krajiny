"""Domain regression checks over real, source-backed examples; no network."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "landscape_badatel", ROOT / "skills/pamet-krajiny/scripts/badatel.py"
)
badatel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(badatel)


def dossier(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text(encoding="utf-8"))


class LandscapeExamplesTest(unittest.TestCase):
    def test_real_disagreement_is_not_lost_in_public_output(self):
        data = dossier("most")
        conflict = next(c for c in data["claims"] if c["id"] == "most-c-area")
        self.assertEqual(conflict["status"], "disputed")
        self.assertEqual(len({e["source_id"] for e in conflict["evidence"]}), 2)
        public = badatel.public_projection(data)
        report = badatel.render_html(public)
        for value in ("309,09", "309,4", "Rozporné údaje"):
            self.assertIn(value, report)
        for evidence in conflict["evidence"]:
            url = next(s["url"] for s in data["sources"] if s["id"] == evidence["source_id"])
            self.assertIn(url, report)

    def test_unresolved_park_identity_is_not_silently_merged(self):
        data = dossier("uhersky-brod")
        entities = {e["id"]: e for e in data["entities"]}
        self.assertIn("ub-tyrsovy", entities)
        self.assertIn("ub-north-park", entities)
        claim = next(c for c in data["claims"] if c["id"] == "ub-c-northpark")
        self.assertNotIn("ub-tyrsovy", claim["entity_ids"])
        self.assertTrue(any("Který konkrétní park" in q for q in data["open_questions"]))
        self.assertEqual(badatel.validate(data), [])

    def test_unmeasured_examples_do_not_gain_fake_coordinates(self):
        for name in ("most", "uhersky-brod"):
            with self.subTest(example=name):
                data = dossier(name)
                self.assertEqual(badatel.validate(data), [])
                exported = badatel.render_geojson(data)
                if isinstance(exported, str):
                    exported = json.loads(exported)
                self.assertEqual(exported["features"], [])


if __name__ == "__main__":
    unittest.main()
