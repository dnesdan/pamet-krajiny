"""No network or listening sockets: deterministic HTTP and process-lock tests."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = next(ROOT.glob("skills/*/scripts/http_client.py")).parent
sys.path.insert(0, str(SCRIPT_DIR))
import http_client as h


class Response(BytesIO):
    def __init__(self, data=b'{"ok": true}', url="https://example.org/data", status=200, headers=None):
        super().__init__(data)
        self.url, self.status = url, status
        self.headers = headers if headers is not None else {"Content-Type": "application/json"}
    def geturl(self):
        return self.url


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = []
    def client(self, response_factory=None, **options):
        def transport(request, timeout):
            self.calls.append((request, timeout))
            return response_factory(request, timeout) if response_factory else Response(url=request.full_url)
        return h.HttpClient(cache_dir=self.temp.name, min_interval=0, transport=transport, **options)

    def test_second_client_reuses_complete_response(self):
        first=self.client().fetch("https://example.org/data")
        second=self.client().fetch("https://example.org/data")
        self.assertFalse(first.from_cache)
        self.assertTrue(second.from_cache)
        self.assertEqual(second.json(), {"ok":True})
        self.assertEqual(first.retrieved_at,second.retrieved_at)
        self.assertEqual(len(self.calls),1)
        self.assertIn("CeskeBadatelskeSkilly",self.calls[0][0].get_header("User-agent"))

    def test_full_query_string_is_part_of_cache_key(self):
        client=self.client()
        client.fetch("https://example.org/data?q=Brno")
        client.fetch("https://example.org/data?q=Plzen")
        self.assertEqual(len(self.calls),2)
        self.assertEqual(len(list((Path(self.temp.name)/"responses").glob("*.json"))),2)

    def test_refresh_fetches_again(self):
        client=self.client()
        client.fetch("https://example.org/data")
        self.assertFalse(client.fetch("https://example.org/data",refresh=True).from_cache)
        self.assertEqual(len(self.calls),2)

    def test_corrupt_body_is_not_reused(self):
        client=self.client(); client.fetch("https://example.org/data")
        path=next((Path(self.temp.name)/"responses").glob("*.json"))
        cache=json.loads(path.read_text()); cache["sha256"]="wrong"
        path.write_text(json.dumps(cache))
        self.assertFalse(client.fetch("https://example.org/data").from_cache)
        self.assertEqual(len(self.calls),2)

    def test_failure_status_is_never_cached_or_retried(self):
        def transport(req,timeout):
            raise HTTPError(req.full_url,500,"error",{},None)
        client=self.client(transport)
        with self.assertRaisesRegex(h.FetchError,"HTTP 500"):
            client.fetch("https://example.org/data")
        self.assertEqual(len(self.calls),1)
        self.assertEqual(list(Path(self.temp.name).glob("responses/*.json")),[])

    def test_access_errors_stop_and_share_cooldown(self):
        for status in (401,403,429,503):
            with self.subTest(status=status),tempfile.TemporaryDirectory() as cache:
                calls=[]
                def transport(req,timeout):
                    calls.append(req)
                    raise HTTPError(req.full_url,status,"blocked",{"Retry-After":"120"},None)
                client=h.HttpClient(cache_dir=cache,min_interval=0,transport=transport)
                with self.assertRaises(h.AccessBlocked) as caught:
                    client.fetch("https://example.org/data")
                self.assertEqual(caught.exception.status,status)
                with self.assertRaises(h.CooldownError):
                    h.HttpClient(cache_dir=cache,min_interval=0,transport=transport).fetch("https://example.org/other")
                self.assertEqual(len(calls),1)
                self.assertEqual(list(Path(cache).glob("responses/*.json")),[])

    def test_status_returned_without_http_error_still_blocks(self):
        client=self.client(lambda req,timeout:Response(status=429,url=req.full_url))
        with self.assertRaises(h.AccessBlocked):
            client.fetch("https://example.org/data")
        self.assertEqual(len(self.calls),1)

    def test_bounded_body_without_content_length(self):
        client=self.client(lambda req,timeout:Response(b"01234567890",url=req.full_url),max_bytes=10)
        with self.assertRaisesRegex(h.FetchError,"byte limit"):
            client.fetch("https://example.org/data")
        self.assertEqual(list(Path(self.temp.name).glob("responses/*.json")),[])

    def test_content_length_is_checked_before_read(self):
        client=self.client(lambda req,timeout:Response(b"small",url=req.full_url,headers={"Content-Length":"100"}),max_bytes=10)
        with self.assertRaisesRegex(h.FetchError,"byte limit"):
            client.fetch("https://example.org/data")

    def test_truncated_body_is_not_cached(self):
        client=self.client(lambda req,timeout:Response(b"short",url=req.full_url,headers={"Content-Length":"10"}))
        with self.assertRaisesRegex(h.FetchError,"Incomplete response"):
            client.fetch("https://example.org/data")
        self.assertEqual(list(Path(self.temp.name).glob("responses/*.json")),[])

    def test_broken_transfer_is_not_cached(self):
        class Broken(Response):
            def read(self,size=-1):
                raise OSError("connection lost")
        client=self.client(lambda req,timeout:Broken(url=req.full_url))
        with self.assertRaisesRegex(h.FetchError,"connection lost"):
            client.fetch("https://example.org/data")
        self.assertEqual(list(Path(self.temp.name).glob("responses/*.json")),[])

    def test_invalid_json_is_not_an_empty_search_result(self):
        result=self.client(lambda req,timeout:Response(b"<html>login</html>",url=req.full_url)).fetch("https://example.org/data")
        with self.assertRaisesRegex(h.FetchError,"not UTF-8 JSON"):
            result.json()

    def test_unapproved_url_forms_rejected_before_transport(self):
        for url in ("file:///tmp/data", "https://user:pass@example.org/", "http://127.0.0.1/", "http://[::1]/", "http://localhost/", "https://example.org/\nX:bad"):
            with self.subTest(url=url),self.assertRaises(h.FetchError):
                self.client().fetch(url)
        self.assertEqual(self.calls,[])

    def test_cross_host_final_response_rejected(self):
        client=self.client(lambda req,timeout:Response(url="https://elsewhere.example/data"))
        with self.assertRaisesRegex(h.FetchError,"cross-host"):
            client.fetch("https://example.org/data")
        self.assertEqual(list(Path(self.temp.name).glob("responses/*.json")),[])

    def test_cross_process_lock_and_release(self):
        path=Path(self.temp.name)/"host.lock"
        code="""import sys
sys.path.insert(0,sys.argv[1])
from pathlib import Path
from http_client import _lock, CooldownError
try:
    with _lock(Path(sys.argv[2])):
        print('acquired')
except CooldownError:
    print('busy')
"""
        with h._lock(path):
            result=subprocess.run([sys.executable,"-c",code,str(SCRIPT_DIR),str(path)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),"busy")
        result=subprocess.run([sys.executable,"-c",code,str(SCRIPT_DIR),str(path)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.stdout.strip(),"acquired")
        self.assertTrue(path.exists(),"persistent lock files avoid unlink/inode races")

    def test_url_fragment_does_not_duplicate_resource(self):
        client=self.client()
        client.fetch("https://example.org/data#page1")
        self.assertTrue(client.fetch("https://example.org/data#page2").from_cache)
        self.assertEqual(len(self.calls),1)


if __name__ == "__main__":
    unittest.main()
