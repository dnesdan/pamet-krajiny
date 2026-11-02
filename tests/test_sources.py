"""Protocol fixtures, not live archive claims. All data below are synthetic."""
from copy import deepcopy
import json
import os
from pathlib import Path
import struct
import sys
import subprocess
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = next(ROOT.glob("skills/*/scripts/zdroje.py")).parent
sys.path.insert(0, str(SCRIPT_DIR))
from http_client import FetchResult, FetchError
import zdroje as z


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []
    def fetch(self, url, refresh=False):
        self.urls.append(url)
        value = self.responses.pop(0)
        if isinstance(value, tuple):
            data, mime = value
        else:
            data, mime = json.dumps(value).encode("utf-8"), "application/json"
        return FetchResult(data, mime, url, "2026-11-02T12:00:00+00:00", False)


def registry_fixture(version="7.2.2.4"):
    return [{"code":"fixture", "name":"Synthetic library", "url":"https://example.org", "version":version,
             "alive":True, "new_client_url":"https://viewer.example.org/fixture"}]


def wms_fixture(version="1.3.0", crs="EPSG:4326"):
    return f'''<WMS_Capabilities xmlns="http://www.opengis.net/wms" xmlns:xlink="http://www.w3.org/1999/xlink" version="{version}">
    <Service><Title>Synthetic map service</Title></Service><Capability><Request><GetMap>
    <Format>image/png</Format><Format>image/jpeg</Format><DCPType><HTTP><Get><OnlineResource xlink:href="https://example.org/wms?"/></Get></HTTP></DCPType>
    </GetMap></Request><Layer queryable="1"><Title>Parent</Title><CRS>{crs}</CRS>
    <Style><Name>default</Name><Title>Default</Title></Style><BoundingBox CRS="{crs}" minx="1" miny="2" maxx="3" maxy="4"/>
    <Layer><Name>test-layer</Name><Title>Child layer</Title></Layer></Layer></Capability></WMS_Capabilities>'''.encode()


def png(width=32, height=16):
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress((b"\x00"+b"\x00\x00\x00"*width)*height))+chunk(b"IEND",b"")


class RegistryAndSearchTests(unittest.TestCase):
    def test_cli_argument_error_is_utf8_under_forced_ascii(self):
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / "zdroje.py"), "ares", "--ico", "00000019", "--neznámý-přepínač"],
                                capture_output=True, env=dict(os.environ, PYTHONIOENCODING="ascii"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("--neznámý-přepínač", result.stderr.decode("utf-8"))
        self.assertNotIn(b"UnicodeEncodeError", result.stderr)

    def test_registry_has_explicit_provenance_and_code_resolution(self):
        out=z.registry(Client([registry_fixture()]),"FIXTURE")
        self.assertEqual(out["count"],1)
        for field in ("request_url","retrieved_at","from_cache","limitations"):
            self.assertIn(field,out)
        with self.assertRaises(FetchError):
            z.registry(Client([registry_fixture()]),"missing")

    def test_k7_uses_verified_ocr_field_and_literal_phrase(self):
        response={"response":{"numFound":8,"start":0,"numFoundExact":False,"docs":[{
            "pid":"uuid:page","root.pid":"uuid:book","titles.search":["227"],"root.title":"Fixture newspaper","date.str":"1900","accessibility":"public","model":"page"}]}}
        client=Client([registry_fixture(),response])
        out=z.kramerius_search(client,"fixture",'Brod" OR *:*',rows=2,public_only=True)
        params=parse_qs(urlsplit(client.urls[-1]).query)
        self.assertEqual(params["q"],['text_ocr:"Brod\\" OR *:*"'])
        self.assertEqual(params["fq"],["accessibility:public"])
        self.assertIn("/search/api/client/v7.0/search",client.urls[-1])
        self.assertTrue(out["truncated"])
        self.assertFalse(out["count_exact"])
        self.assertEqual(out["documents"][0]["viewer_url"],"https://viewer.example.org/fixture/view/uuid:page")
        self.assertEqual(out["documents"][0]["title"],"227")
        self.assertEqual(out["documents"][0]["root_title"],"Fixture newspaper")

    def test_k5_endpoint_fields_and_access_filter_are_distinct(self):
        response={"response":{"numFound":1,"docs":[{"PID":"uuid:p","root_title":"Fixture", "dostupnost":"public","datum_str":"1901"}]}}
        client=Client([registry_fixture("5.8.4"),response])
        out=z.kramerius_search(client,"fixture","Brod",public_only=True)
        params=parse_qs(urlsplit(client.urls[-1]).query)
        self.assertEqual(params["fq"],["dostupnost:public"])
        self.assertIn("/search/api/v5.0/search",client.urls[-1])
        self.assertEqual(out["documents"][0]["date"],"1901")

    def test_provider_error_is_not_empty_search(self):
        with self.assertRaisesRegex(FetchError,"Provider returned an error"):
            z.kramerius_search(Client([registry_fixture(),{"error":{"msg":"unknown field"}}]),"fixture","Brod")
        with self.assertRaises(FetchError):
            z.kramerius_search(Client([registry_fixture(),{"message":"login"}]),"fixture","Brod")

    def test_empty_search_preserves_coverage_caveat(self):
        out=z.kramerius_search(Client([registry_fixture(),{"response":{"numFound":0,"docs":[]}}]),"fixture","missing")
        self.assertEqual(out["documents"],[])
        self.assertIn(z.EMPTY_WARNING,out["limitations"])

    def test_search_bounds_before_network(self):
        client=Client([])
        for kwargs in ({"rows":51},{"start":-1}):
            with self.assertRaises(ValueError):
                z.kramerius_search(client,"fixture","Brod",**kwargs)
        self.assertEqual(client.urls,[])


class RuianTests(unittest.TestCase):
    def test_duplicate_names_return_candidates_and_truncation(self):
        data={"features":[{"attributes":{"kod":i,"nazev":"Nová Ves","okres":i},"centroid":{"x":16+i/100,"y":49}} for i in (1,2,3)]}
        client=Client([data])
        out=z.ruian(client,"Nová Ves",limit=2)
        self.assertEqual(len(out["candidates"]),2)
        self.assertTrue(out["truncated"])
        self.assertIsNone(out["selected"])
        self.assertIn("representative_point",out["candidates"][0])
        self.assertNotIn("geometry",out["candidates"][0])
        self.assertEqual(parse_qs(urlsplit(client.urls[0]).query)["returnGeometry"],["false"])

    def test_sql_quotes_escaped_and_address_field_correct(self):
        client=Client([{"features":[]}])
        z.ruian(client,"O'Brien 1",kind="address")
        params=parse_qs(urlsplit(client.urls[0]).query)
        self.assertEqual(params["where"],["UPPER(adresa) LIKE '%O''BRIEN 1%'"])
        self.assertIn("/1/query",client.urls[0])
        for query in ("%","Br_o","*","A","X\nY"):
            with self.assertRaises(ValueError):
                z.ruian(Client([]),query)

    def test_invalid_ruian_response_and_wrong_projection_fail(self):
        with self.assertRaises(FetchError):
            z.ruian(Client([{"error":{"message":"bad field"}}]),"Brno")
        with self.assertRaises(FetchError):
            z.ruian(Client([{"features":[{"attributes":{"kod":1,"adresa":"Fixture"},"geometry":{"x":-600000,"y":-1100000}}]}]),"Brno",kind="address")


class WmsTests(unittest.TestCase):
    def test_inherited_crs_styles_boxes_and_queryable(self):
        result=z.parse_wms(wms_fixture())
        layer=result["layers"][0]
        self.assertEqual(layer["crs"],["EPSG:4326"])
        self.assertEqual(layer["styles"],[{"name":"default","title":"Default"}])
        self.assertEqual(layer["bounding_boxes_native_axis_order"]["EPSG:4326"],[1,2,3,4])
        self.assertTrue(layer["queryable"])

    def test_axis_orders_and_native_czech_crs(self):
        common=("test-layer",[16,49,17,50])
        p=z.map_parameters(*common,"1.3.0","EPSG:4326",100,100,"image/png")
        self.assertEqual(p["BBOX"],"49,16,50,17"); self.assertEqual(p["CRS"],"EPSG:4326")
        p=z.map_parameters(*common,"1.1.1","EPSG:4326",100,100,"image/png")
        self.assertEqual(p["BBOX"],"16,49,17,50"); self.assertIn("SRS",p)
        p=z.map_parameters(*common,"1.3.0","CRS:84",100,100,"image/png")
        self.assertEqual(p["BBOX"],"16,49,17,50")
        p=z.map_parameters("layer",[-600000,-1200000,-590000,-1190000],"1.1.1","EPSG:5514",100,100,"image/png")
        self.assertEqual(p["BBOX"],"-600000,-1200000,-590000,-1190000")
        with self.assertRaisesRegex(ValueError,"requires --version 1.1.1"):
            z.map_parameters("layer",[-600000,-1200000,-590000,-1190000],"1.3.0","EPSG:5514",100,100,"image/png")

    def test_invalid_bbox_and_oversize_image_dimensions(self):
        for box in ("nan,49,17,50","17,49,16,50","16,49,17,149","16,49,17"):
            with self.assertRaises(ValueError): z.parse_bbox(box)
        with self.assertRaises(ValueError):
            z.map_parameters("x",[16,49,17,50],"1.3.0","EPSG:4326",10000,100,"image/png")

    def test_old_wms_parameters_are_removed_between_operations(self):
        url=z.wms_url("https://example.org/wms?SRS=EPSG%3A5514&bbox=wrong&service=WMS&provider=fixture",{"CRS":"EPSG:4326","REQUEST":"GetMap"})
        params=parse_qs(urlsplit(url).query)
        self.assertNotIn("SRS",params)
        self.assertNotIn("bbox",params)
        self.assertEqual(params["provider"],["fixture"])

    def test_xml_entities_and_service_exception_rejected(self):
        for body in (b'<!DOCTYPE x [<!ENTITY boom "bad">]><x>&boom;</x>',b'<ServiceExceptionReport><ServiceException>Wrong CRS</ServiceException></ServiceExceptionReport>'):
            with self.assertRaises(FetchError): z.parse_wms(body)

    def test_map_saves_verified_bytes_and_exact_sidecar(self):
        body=png()
        client=Client([(wms_fixture(),"text/xml"),(body,"image/png")])
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"map.png"
            metadata=z.wms_map(client,"https://example.org/wms","test-layer","16,49,17,50",out,width=32,height=16)
            self.assertEqual(out.read_bytes(),body)
            sidecar=json.loads(Path(str(out)+".json").read_text())
            self.assertEqual(metadata["sha256"],sidecar["sha256"])
            self.assertEqual(sidecar["bbox_request"],"49,16,50,17")
            self.assertEqual(sidecar["crs"],"EPSG:4326")
            with self.assertRaisesRegex(ValueError,"already exists"):
                z.wms_map(client,"https://example.org/wms","test-layer","16,49,17,50",out,width=32,height=16)

    def test_error_or_wrong_dimensions_never_saved_as_image(self):
        for body,mime in ((b"<html>error</html>","text/html"),(b"not png","image/png"),(png(64,16),"image/png")):
            client=Client([(wms_fixture(),"text/xml"),(body,mime)])
            with tempfile.TemporaryDirectory() as td:
                out=Path(td)/"map.png"
                with self.assertRaises(FetchError):
                    z.wms_map(client,"https://example.org/wms","test-layer","16,49,17,50",out,width=32,height=16)
                self.assertFalse(out.exists())

    def test_unsupported_layer_crs_fails_before_map_request(self):
        client=Client([(wms_fixture(crs="EPSG:5514"),"text/xml")])
        with tempfile.TemporaryDirectory() as td,self.assertRaisesRegex(ValueError,"does not advertise"):
            z.wms_map(client,"https://example.org/wms","test-layer","16,49,17,50",Path(td)/"map.png")
        self.assertEqual(len(client.urls),1)

    def test_same_host_advertised_http_does_not_downgrade_https(self):
        caps=wms_fixture().replace(b'https://example.org/wms?',b'http://example.org/maps?')
        client=Client([(caps,"text/xml"),(png(),"image/png")])
        with tempfile.TemporaryDirectory() as td:
            z.wms_map(client,"https://example.org/wms","test-layer","16,49,17,50",Path(td)/"map.png",width=32,height=16)
        self.assertTrue(client.urls[-1].startswith("https://example.org/maps?"))


class IiifAndAresTests(unittest.TestCase):
    def test_iiif_v2_preserves_canvas_and_service_ids(self):
        data={"@type":"sc:Manifest","@id":"https://example.org/manifest","label":"Fixture","license":"https://example.org/rights","sequences":[{"canvases":[{
            "@id":"https://example.org/canvas/1","label":"1","images":[{"resource":{"@type":"dctypes:Image","@id":"https://example.org/image.jpg","service":{"@id":"https://example.org/iiif/image","profile":"http://iiif.io/api/image/2/level1.json"}}}]}]}]}
        client=Client([data]); out=z.iiif(client,"https://example.org/manifest")
        self.assertEqual(out["presentation_version"],2)
        self.assertEqual(out["canvases"][0]["images"][0]["services"][0]["id"],"https://example.org/iiif/image")
        self.assertEqual(len(client.urls),1,"manifest inspection must not fetch linked images")

    def test_iiif_v3_choice_and_referenced_pages(self):
        data={"type":"Manifest","id":"https://example.org/manifest","label":{"en":["English"],"cs":["Česky"]},"rights":"https://example.org/rights","items":[{
            "type":"Canvas","id":"https://example.org/canvas/1","items":[{"id":"https://example.org/page"},{"type":"AnnotationPage","items":[{"motivation":"painting","body":{"type":"Choice","items":[{"type":"Image","id":"https://example.org/one.jpg"},{"type":"Image","id":"https://example.org/two.jpg"}]}}]}]}]}
        out=z.parse_iiif(data)
        self.assertEqual(out["label"],"Česky")
        self.assertEqual(len(out["canvases"][0]["images"]),2)
        self.assertTrue(out["warnings"])
        data["items"].append({"type":"Canvas","id":"https://example.org/canvas/2","items":[]})
        self.assertTrue(z.parse_iiif(data,limit=1)["truncated"])
        with self.assertRaises(FetchError): z.parse_iiif({"type":"Collection","items":[]})

    def test_malformed_iiif_is_an_error_not_a_successful_empty_manifest(self):
        cases=[{"type":"Manifest","items":[{"id":[]} ]},
               {"type":"Manifest","items":[{"id":"https://example.org/c","items":None}]},
               {"@type":"sc:Manifest","sequences":[{"canvases":None}]}]
        for data in cases:
            with self.assertRaises(FetchError): z.parse_iiif(data)

    def test_ares_keeps_leading_zeros_and_does_not_claim_history(self):
        client=Client([{"ico":"00000019","obchodniJmeno":"Syntetický test","datumVzniku":"1990-01-01"}])
        out=z.ares(client,"00000019")
        self.assertTrue(client.urls[0].endswith("/00000019"))
        self.assertEqual(out["interpretation"],"current_registry_identity")
        for ico in ("19","0000001x","123456789","１２３４５６７８"):
            with self.assertRaises(ValueError): z.ares(Client([]),ico)
        with self.assertRaises(FetchError):
            z.ares(Client([{"ico":"00000001","obchodniJmeno":"Wrong entity"}]),"00000019")


if __name__ == "__main__":
    unittest.main()
