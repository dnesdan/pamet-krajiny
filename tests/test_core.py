"""Offline regression tests: evidence integrity, public export and Czech routing."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = next(ROOT.glob("skills/*/scripts/badatel.py"))
sys.path.insert(0, str(SCRIPT.parent))
import badatel as b


def sample():
    d = b.new_dossier("Ukázka testu", "landscape", "Česká republika")
    d["entities"] = [{"id": "place-1", "type": "place", "label": "Veřejné místo",
                      "geometry": {"type": "Point", "coordinates": [16.61, 49.20]},
                      "location_accuracy_m": 500}]
    d["sources"] = [{"id": "source-1", "title": "Syntetický testovací záznam", "url": "https://example.org/item/1",
                     "publisher": "Test fixture", "accessed": "2026-11-02", "kind": "synthetic", "access": "open", "license": "unknown"}]
    d["claims"] = [{"id": "claim-1", "entity_ids": ["place-1"], "text": "Testovací tvrzení, nikoli historický nález.",
                    "status": "documented", "evidence": [{"source_id": "source-1", "locator": "Syntetický odstavec 1", "kind": "paraphrase"}],
                    "time": {"from": 1900, "to": 1900, "precision": "year"}}]
    d["events"] = [{"id": "event-1", "type": "test", "label": "Testovací událost", "entity_ids": ["place-1"],
                    "claim_ids": ["claim-1"], "time": {"from": 1900, "to": 1900, "precision": "year"}}]
    d["research_log"] = [{"date": "2026-11-02", "query": "test", "source_id": "source-1", "result": "fixture", "limitations": "not a live archive"}]
    return d


class EvidenceTests(unittest.TestCase):
    def test_valid_fixture_and_empty_project(self):
        self.assertEqual(b.validate(sample()), [])
        self.assertEqual(b.validate(b.new_dossier("Nový", "enterprise", "Plzeň")), [])

    def test_documented_claim_requires_localized_evidence(self):
        d = sample(); d["claims"][0]["evidence"] = []
        self.assertTrue(any("needs cited evidence" in e for e in b.validate(d)))
        d = sample(); d["claims"][0]["evidence"][0]["locator"] = " "
        self.assertTrue(any("locator" in e for e in b.validate(d)))

    def test_hypothesis_can_remain_unproven(self):
        d = sample(); d["claims"][0].update(status="hypothesis", evidence=[])
        self.assertEqual(b.validate(d), [])
        self.assertIn("Bez přímého dokladu", b.render_markdown(d))

    def test_cross_record_integrity(self):
        mutations = [lambda d: d["entities"][0].update(id="source-1"),
                     lambda d: d["claims"][0].update(entity_ids=["missing"]),
                     lambda d: d["claims"][0]["evidence"][0].update(source_id="missing"),
                     lambda d: d["events"][0].update(claim_ids=["missing"])]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                d = sample(); mutation(d)
                self.assertTrue(b.validate(d))

    def test_dates_reject_reversed_or_invented_precision(self):
        for when in ({"from": 1950, "to": 1900, "precision": "range"},
                     {"from": 1900, "to": 1901, "precision": "exact"},
                     {"from": True, "to": 1900, "precision": "year"},
                     {"from": 1900, "to": 1900, "precision": "unknown"}):
            d = sample(); d["claims"][0]["time"] = when
            self.assertTrue(b.validate(d), when)
        d = sample(); d["claims"][0]["time"] = {"from": 1890, "to": None, "precision": "range"}
        self.assertEqual(b.validate(d), [])
        d["sources"][0]["accessed"] = "2026-02-30"
        self.assertTrue(b.validate(d))

    def test_coordinates_and_polygon_closure(self):
        geometries = [{"type": "Point", "coordinates": [16, 149]},
                      {"type": "Point", "coordinates": [float("nan"), 49]},
                      {"type": "Point", "coordinates": [True, 49]},
                      {"type": "Polygon", "coordinates": [[[16,49],[17,49],[17,50],[16,50]]]},
                      {"type": "Point", "coordinates": [16,49], "crs": "EPSG:5514"}]
        for geometry in geometries:
            d = sample(); d["entities"][0]["geometry"] = geometry
            self.assertTrue(b.validate(d))
        d = sample(); d["entities"][0]["geometry"] = {"type": "Polygon", "coordinates": [[[16,49],[17,49],[17,50],[16,49]]]}
        self.assertEqual(b.validate(d), [])

    def test_malformed_shapes_report_errors_without_crashing(self):
        malformed = [None, [], {"schema_version": "1.0"}]
        for field in b.ARRAYS:
            d = sample(); d[field] = "wrong"; malformed.append(d)
        for collection in ("entities", "sources", "claims", "events", "links", "research_log"):
            d = sample(); d[collection] = [None]; malformed.append(d)
        d = sample(); d["claims"][0]["status"] = []; malformed.append(d)
        d = sample(); d["entities"][0]["type"] = {}; malformed.append(d)
        d = sample(); d["claims"][0]["entity_ids"] = [[]]; malformed.append(d)
        for d in malformed:
            self.assertTrue(b.validate(d))

    def test_unsafe_source_urls_rejected(self):
        for url in ("javascript:alert(1)", "file:///etc/passwd", "https://user:password@example.org/", "https://example.org/\nfoo"):
            d = sample(); d["sources"][0]["url"] = url
            self.assertTrue(b.validate(d), url)

    def test_brand_is_separate_from_organization(self):
        d = sample(); d["entities"].append({"id": "brand-1", "type": "brand", "label": "Značka"})
        self.assertEqual(b.validate(d), [])

    def test_index_only_or_unavailable_source_cannot_substantiate_a_claim(self):
        for verification in ("search_index_only", "unavailable"):
            for status in ("documented", "supported"):
                d = sample(); d["sources"][0]["verification_status"] = verification
                d["claims"][0]["status"] = status
                self.assertTrue(any("until content is checked" in e for e in b.validate(d)))
            d["claims"][0]["status"] = "hypothesis"
            self.assertEqual(b.validate(d), [])
            exported = b.public_projection(d)
            self.assertEqual(exported["sources"][0]["verification_status"], verification)
            self.assertEqual(b.render_geojson(exported)["features"][0]["properties"]["sources"][0]["verification_status"], verification)
        d = sample(); d["sources"][0]["verification_status"] = "content_checked"
        self.assertEqual(b.validate(d), [])
        d["sources"][0]["verification_status"] = "invented"
        self.assertTrue(b.validate(d))


class ExportTests(unittest.TestCase):
    def test_html_and_markdown_escape_imported_text(self):
        d = sample(); payload = '<script>alert("x")</script> [click](javascript:bad)'
        d["claims"][0]["text"] = payload; d["project"]["title"] = payload
        rendered = b.render_html(d)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        md = b.render_markdown(d)
        self.assertNotIn("<script>", md)
        self.assertIn(r"\[click\]", md)
        self.assertNotIn("<script src", rendered)

    def test_geojson_preserves_evidence_and_accuracy(self):
        out = b.render_geojson(sample())
        self.assertEqual(out["features"][0]["geometry"]["coordinates"], [16.61, 49.20])
        props = out["features"][0]["properties"]
        self.assertEqual(props["location_accuracy_m"], 500)
        self.assertEqual(props["claims"][0]["status"], "documented")
        self.assertEqual(props["sources"][0]["url"], "https://example.org/item/1")

    def test_geojson_keeps_claim_specific_evidence_and_time(self):
        d = sample()
        source = deepcopy(d["sources"][0]); source.update(id="source-2", title="Second fixture", url="https://example.org/item/2", verification_status="content_checked")
        claim = deepcopy(d["claims"][0]); claim.update(id="claim-2", text="A later event", time={"from":1950,"to":1959,"precision":"range"}, evidence=[{"source_id":"source-2","locator":"Page 42, paragraph 3","kind":"transcription"}])
        d["sources"].append(source); d["claims"].append(claim)
        props = b.render_geojson(d)["features"][0]["properties"]
        claims = {c["id"]: c for c in props["claims"]}
        self.assertEqual(claims["claim-1"]["evidence"][0]["source_id"], "source-1")
        self.assertEqual(claims["claim-2"]["evidence"][0]["source_id"], "source-2")
        self.assertEqual(claims["claim-2"]["evidence"][0]["locator"], "Page 42, paragraph 3")
        self.assertEqual(claims["claim-2"]["time"], {"from":1950,"to":1959,"precision":"range"})
        self.assertEqual(props["sources"][1]["verification_status"], "content_checked")

    def test_relation_exports_retain_dates_and_precision(self):
        d = sample(); d["entities"].append({"id":"org-1","type":"organization","label":"Fixture organization"})
        d["claims"][0]["entity_ids"].append("org-1")
        d["links"] = [{"id":"link-1","from":"org-1","to":"place-1","relation":"provozovala",
                       "claim_ids":["claim-1"],"time":{"from":1873,"to":1887,"precision":"approximate"}}]
        for content in (b.render_markdown(d), b.render_html(d)):
            self.assertIn("1873–1887", content)
            self.assertIn("přibližně", content)
            self.assertIn("přesnost", content)

    def test_geometry_role_survives_public_export_and_unknown_is_labelled(self):
        d = sample(); d["entities"][0].update(geometry_role="centroid", notes="PRIVATE annotation explaining position")
        self.assertEqual(b.validate(d), [])
        for content in (b.render_markdown(d), b.render_html(d)):
            self.assertIn("centroid", content)
            self.assertIn("PRIVATE annotation", content)
        public = b.public_projection(d)
        self.assertEqual(public["entities"][0]["geometry_role"], "centroid")
        self.assertNotIn("PRIVATE", b.render_html(public))
        self.assertEqual(b.render_geojson(public)["features"][0]["properties"]["geometry_role"], "centroid")
        del d["entities"][0]["geometry_role"]
        self.assertIn("význam geometrie neověřen", b.render_html(d))
        self.assertEqual(b.render_geojson(d)["features"][0]["properties"]["geometry_role"], "unknown")
        d["entities"][0]["geometry_role"] = "exact-by-default"
        self.assertTrue(b.validate(d))

    def test_public_filter_drops_private_graph_and_work_notes(self):
        d = sample(); d["entities"].append({"id":"person-1", "type":"person", "label":"SECRET PERSON", "sensitive":True})
        private = deepcopy(d["claims"][0]); private.update(id="claim-private", entity_ids=["place-1", "person-1"], text="SECRET CLAIM")
        d["claims"].append(private)
        d["links"] = [{"id":"link-private", "from":"person-1", "to":"place-1", "relation":"SECRET RELATION", "claim_ids":["claim-private"]}]
        event = deepcopy(d["events"][0]); event.update(id="event-private", label="SECRET EVENT", claim_ids=["claim-private"])
        d["events"].append(event)
        d["entities"][0]["notes"] = "SECRET NOTE"
        d["sources"][0]["notes"] = "SECRET SOURCE NOTE"
        d["project"].update(scope="SECRET SCOPE", research_questions=["SECRET QUESTION"])
        d["open_questions"] = ["SECRET QUESTION"]
        d["research_log"][0]["query"] = "SECRET LOG"
        result = b.public_projection(d)
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertEqual(b.validate(result), [])
        self.assertEqual(len(result["claims"]), 1)
        self.assertEqual(len(d["claims"]), 2, "projection must not mutate original")

    def test_sensitive_source_removes_dependent_claim_event_alias(self):
        d = sample(); d["sources"][0]["sensitive"] = True
        d["entities"][0]["aliases"] = [{"name":"PRIVATE ALIAS", "from":None, "to":None, "source_ids":["source-1"]}]
        result = b.public_projection(d)
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["events"], [])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["entities"][0]["aliases"], [])
        self.assertEqual(b.validate(result), [])

    def test_public_filter_drops_unknown_extension_fields(self):
        d = sample(); d["private_extension"] = "SECRET ROOT"
        d["project"]["private_extension"] = "SECRET PROJECT"
        for kind in ("entities", "sources", "claims", "events"):
            d[kind][0]["private_extension"] = "SECRET RECORD"
        d["claims"][0]["evidence"][0]["private_extension"] = "SECRET EVIDENCE"
        d["claims"][0]["time"]["private_extension"] = "SECRET TIME"
        d["entities"][0]["geometry"]["private_extension"] = "SECRET GEOMETRY"
        self.assertNotIn("SECRET", json.dumps(b.public_projection(d)))

    def test_timeline_keeps_hypothesis_status(self):
        d = sample(); d["claims"][0]["status"] = "hypothesis"
        timeline = b.render_html(d).split('<h2 id="cas">', 1)[1].split('<h2 id="prameny">', 1)[0]
        self.assertIn("Hypotéza", timeline)

    def test_time_order_and_unknown_bounds(self):
        d = sample(); old = deepcopy(d["events"][0]); old.update(id="event-old", label="Earlier", time={"from":1800,"to":1800,"precision":"year"})
        d["events"].append(old)
        self.assertLess(b.render_html(d).index("Earlier"), b.render_html(d).index("Testovací událost"))
        self.assertEqual(b.time_label({"from":None,"to":None,"precision":"unknown"}), "datum neznámé")


class RoutingAndCliTests(unittest.TestCase):
    def test_redirected_cli_uses_utf8_under_forced_ascii_environment(self):
        environment = dict(os.environ, PYTHONIOENCODING="ascii")
        result = subprocess.run([sys.executable, str(SCRIPT), "plan", "--place", "Žďár nad Sázavou",
                                 "--region", "Vysočina", "--topic", "krajina"],
                                capture_output=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        output = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(output["place"], "Žďár nad Sázavou")
        self.assertIn("Vysočina".encode("utf-8"), result.stdout)
        # Error messages containing a Czech path must also remain UTF-8.
        result = subprocess.run([sys.executable, str(SCRIPT), "validate", "neexistující-soubor.json"],
                                capture_output=True, env=environment)
        self.assertEqual(result.returncode, 2)
        self.assertIn("neexistující-soubor.json", result.stderr.decode("utf-8"))

    def test_every_czech_region_resolves_without_brno_default(self):
        for code, names in b.REGIONS.items():
            region = names[0]
            catalogue = [{"id":"national", "title":"National", "url":"https://example.org", "regions":["CZ"]},
                         {"id":"local", "title":"Local", "url":"https://example.org/local", "regions":[region]}]
            result = b.plan("Zadané místo", code, "landscape", catalogue=catalogue)
            self.assertCountEqual([v["source_id"] for v in result["queries"]], ["national", "local"])
            self.assertEqual(result["status"], "plan_only")
        self.assertEqual(b.region_tokens("Jihomoravský"), b.region_tokens("CZ064"))
        self.assertEqual(b.region_tokens("Ústecký"), b.region_tokens("Ústecký kraj"))

    def test_unknown_region_and_reversed_period_raise(self):
        with self.assertRaisesRegex(ValueError, "Unknown region"):
            b.plan("Místo", "Vymyšlený kraj", "landscape", catalogue=[])
        with self.assertRaisesRegex(ValueError, "start year"):
            b.plan("Místo", "Praha", "landscape", from_year=2000, to_year=1900, catalogue=[])

    def test_plan_filters_theme_and_region(self):
        cat=[{"id":"local-wrong", "regions":["Plzeňský"], "themes":["enterprise"]},
             {"id":"maps", "regions":["CZ"], "themes":["landscape"]},
             {"id":"ares", "regions":["CZ"], "themes":["enterprise"]}]
        result=b.plan("Uherský Brod", "Zlínský", "enterprise", catalogue=cat)
        self.assertEqual([v["source_id"] for v in result["queries"]], ["ares"])
        self.assertTrue(any("fond" in v for v in result["before_search"]))

    def test_actual_textile_plan_is_bounded_relevant_and_keeps_reserves(self):
        result = b.plan("Liberec", "Liberecký", "textil", theme="enterprise")
        primary = {v["source_id"] for v in result["queries"]}
        reserve = {v["source_id"] for v in result["reserve_sources"]}
        self.assertLessEqual(len(primary), 15)
        self.assertIn("soa-litomerice", primary)
        self.assertIn("kramerius", primary)
        self.assertNotIn("arolsen", primary)
        self.assertNotIn("holocaust", primary)
        self.assertNotIn("vua", primary)
        self.assertIn("arolsen", reserve)
        self.assertEqual(len(primary | reserve), result["eligible_source_count"])
        self.assertFalse(primary & reserve)
        focused = b.plan("Liberec", "Liberecký", "nucená práce za války", theme="enterprise")
        self.assertIn("arolsen", {v["source_id"] for v in focused["queries"]})

    def test_max_sources_is_explicit_and_invalid_values_rejected(self):
        result = b.plan("Liberec", "Liberecký", "textil", theme="enterprise", max_sources=3)
        self.assertEqual(len(result["queries"]), 3)
        self.assertGreater(len(result["reserve_sources"]), 3)
        for count in (0, 61, True):
            with self.assertRaises(ValueError):
                b.plan("Liberec", "Liberecký", "textil", max_sources=count)

    def test_cli_round_trip_and_input_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"dossier.json"; out=Path(td)/"report.html"
            command=[sys.executable,str(SCRIPT)]
            result=subprocess.run(command+["init","--title","Test","--theme","enterprise","--place","Plzeň","--out",str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            for arguments in (["validate",str(path)], ["render",str(path),"--format","html","--out",str(out)]):
                result=subprocess.run(command+arguments,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('<html lang="cs">',out.read_text())
            original=path.read_bytes()
            result=subprocess.run(command+["render",str(path),"--format","html","--out",str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(path.read_bytes(),original)


if __name__ == "__main__":
    unittest.main()
