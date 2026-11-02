#!/usr/bin/env python3
"""Small read-only adapters for public Czech research sources.

Only the requested page, query or map is retrieved. A provider error is never
converted to an empty successful search. No login, bulk harvesting or OCR/image
rights circumvention is implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from http_client import HttpClient, FetchError, validate_url

REGISTRY_URL = "https://api.registr.digitalniknihovna.cz/libraries.json"
RUIAN_URL = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer"
ARES_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/"
LAYERS = {"municipality": 12, "part": 11, "cadastral": 7, "address": 1}
EMPTY_WARNING = "Prázdný výsledek není důkazem historické neexistence; ověř rozsah zdroje, varianty názvu a OCR."


def request_url(base, params):
    """Replace parameters case-insensitively, preserving other public parameters."""
    parts = urlsplit(validate_url(base))
    replaced = {key.lower() for key in params}
    values = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in replaced]
    values.extend(params.items())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(values, doseq=True), ""))


def wms_url(base, params):
    """Drop stale WMS operation parameters; retain provider-specific arguments."""
    parts = urlsplit(validate_url(base))
    controls = {"service", "request", "version", "layers", "styles", "bbox", "srs", "crs", "width", "height", "format", "transparent", "exceptions"}
    values = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in controls]
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(values), ""))
    return request_url(clean, params)


def provenance(result, url, limitations):
    return {"request_url": url, "response_url": result.url, "retrieved_at": result.retrieved_at,
            "from_cache": result.from_cache, "limitations": limitations}


def read_json(client, url, refresh=False):
    result = client.fetch(url, refresh=refresh)
    data = result.json()
    if isinstance(data, dict) and data.get("error"):
        error = data["error"]
        if isinstance(error, dict):
            message = str(error.get("message", error.get("msg", "Provider error")))
            details = error.get("details")
            if details:
                message += "; " + str(details)
        else:
            message = str(error)
        raise FetchError(f"Provider returned an error for {url}: {message}")
    return result, data


def registry(client, code=None, refresh=False):
    result, data = read_json(client, REGISTRY_URL, refresh)
    if isinstance(data, dict):
        data = data.get("libraries")
    if not isinstance(data, list) or any(not isinstance(v, dict) or not v.get("code") or not v.get("url") for v in data):
        raise FetchError("Unexpected digital-library registry structure")
    if code is not None:
        data = [entry for entry in data if entry["code"].casefold() == code.casefold()]
        if not data:
            raise FetchError(f"Library code {code!r} is not in the current registry; run registry without --code")
    records = [{key: item.get(key) for key in ("code", "name", "sigla", "url", "version", "alive", "new_client_url", "library_url")} for item in data]
    return {**provenance(result, REGISTRY_URL, ["Registr může obsahovat staré i nové instance a zahraniční knihovny; není deduplikovaným soupisem českých dokumentů.", "Příznak alive nenahrazuje právě provedený test rozhraní."]), "libraries": records, "count": len(records)}


def ruian(client, query, kind="municipality", limit=20, refresh=False):
    if kind not in LAYERS:
        raise ValueError("Unknown RÚIAN kind")
    if not 1 <= limit <= 50:
        raise ValueError("RÚIAN limit must be 1–50")
    query = query.strip()
    if not 2 <= len(query) <= 200 or re.search(r"[%_*?\x00-\x1f]", query):
        raise ValueError("Use 2–200 characters of a literal name/address, without wildcard or control characters")
    field = "adresa" if kind == "address" else "nazev"
    quoted = query.upper().replace("'", "''")
    params = {"f": "json", "where": f"UPPER({field}) LIKE '%{quoted}%'", "outFields": "*",
              "outSR": "4326", "returnGeometry": "true" if kind in ("part", "address") else "false",
              "returnCentroid": "true" if kind in ("municipality", "cadastral") else "false",
              "orderByFields": field + " ASC,kod ASC", "resultRecordCount": limit + 1}
    url = request_url(f"{RUIAN_URL}/{LAYERS[kind]}/query", params)
    result, data = read_json(client, url, refresh)
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise FetchError("Unexpected RÚIAN query response; missing features")
    features = data["features"]
    candidates = []
    for feature in features[:limit]:
        if not isinstance(feature, dict) or not isinstance(feature.get("attributes"), dict):
            raise FetchError("Malformed RÚIAN feature")
        attrs = feature["attributes"]
        candidate = {"code": attrs.get("kod"), "name": attrs.get(field), "kind": kind,
                     "municipality_code": attrs.get("obec"), "district_code": attrs.get("okres"),
                     "attributes": attrs}
        point = feature.get("centroid") if kind in ("municipality", "cadastral") else feature.get("geometry")
        if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(point.get("y"), (int, float)):
            if not (-180 <= point["x"] <= 180 and -90 <= point["y"] <= 90):
                raise FetchError("RÚIAN returned coordinates outside WGS84 range despite requested outSR=4326")
            candidate["representative_point" if kind in ("municipality", "cadastral") else "registry_point"] = {
                "type": "Point", "coordinates": [point["x"], point["y"]],
                "meaning": "centroid of current administrative geometry, not an exact site" if kind in ("municipality", "cadastral") else "current RÚIAN definition/address point"}
        candidates.append(candidate)
    return {**provenance(result, url, ["Dnešní údaje registru nejsou důkazem historické totožnosti místa, adresy nebo budovy.",
                                       "Kandidáty ověř podle obce, okresu a katastru; žádný se automaticky nevybírá.", EMPTY_WARNING]),
            "query": query, "kind": kind, "candidates": candidates, "selected": None,
            "truncated": bool(data.get("exceededTransferLimit")) or len(features) > limit,
            "returned_count": len(candidates), "total_count": None}


def literal_phrase(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 500 or any(ord(c) < 32 for c in text):
        raise ValueError("Search phrase must contain 1–500 characters without control characters")
    return '"' + text.strip().replace("\\", "\\\\").replace('"', '\\"') + '"'


def kramerius_search(client, library, query, api_version=None, rows=20, start=0, public_only=False, refresh=False):
    if not 1 <= rows <= 50 or not 0 <= start <= 100000:
        raise ValueError("Use rows 1–50 and start 0–100000; narrow broad searches instead of harvesting")
    phrase = literal_phrase(query)
    registration = registry(client, library, refresh)
    if len(registration["libraries"]) != 1:
        raise FetchError("Ambiguous registry code; choose one explicit current library")
    record = registration["libraries"][0]
    if api_version is None:
        version = str(record.get("version") or "").split(".")[0]
        if version not in ("5", "7"):
            raise FetchError("Registry version is unknown/unsupported; verify documentation and pass --api-version 5 or 7")
        api_version = int(version)
    if api_version not in (5, 7):
        raise ValueError("Supported API versions are 5 and 7")
    base = validate_url(record["url"]).rstrip("/")
    if urlsplit(base).query:
        raise FetchError("Registry API base URL unexpectedly contains query parameters")
    if base.endswith("/search"):
        base = base[:-7]
    endpoint = base + ("/search/api/client/v7.0/search" if api_version == 7 else "/search/api/v5.0/search")
    fields = "pid,root.pid,titles.search,root.title,date.str,accessibility,model" if api_version == 7 else "PID,root_pid,root_title,datum_str,dostupnost,fedora.model,details"
    params = {"q": "text_ocr:" + phrase, "rows": rows, "start": start, "wt": "json", "fl": fields}
    if public_only:
        params["fq"] = "accessibility:public" if api_version == 7 else "dostupnost:public"
    url = request_url(endpoint, params)
    result, data = read_json(client, url, refresh)
    response = data.get("response") if isinstance(data, dict) else None
    if not isinstance(response, dict) or not isinstance(response.get("docs"), list) or not isinstance(response.get("numFound"), int) or isinstance(response.get("numFound"), bool) or response["numFound"] < 0:
        raise FetchError("Unexpected Kramerius search response; no valid response/docs/numFound")
    documents = []
    for item in response["docs"][:rows]:
        if not isinstance(item, dict):
            raise FetchError("Malformed Kramerius result")
        pid = item.get("pid") if api_version == 7 else item.get("PID")
        if not isinstance(pid, str):
            raise FetchError("Kramerius result lacks a persistent document ID")
        titles = item.get("titles.search") if api_version == 7 else None
        title = (titles[0] if isinstance(titles, list) and titles else titles) or item.get("root.title", item.get("root_title"))
        client_url = validate_url(record.get("new_client_url") or record["url"])
        documents.append({"pid": pid, "root_pid": item.get("root.pid", item.get("root_pid")),
                          "title": title, "root_title": item.get("root.title", item.get("root_title")),
                          "date": item.get("date.str", item.get("datum_str")),
                          "accessibility": item.get("accessibility", item.get("dostupnost")),
                          "model": item.get("model", item.get("fedora.model")),
                          "viewer_url": client_url.rstrip("/") + "/view/" + quote(pid, safe=":")})
    count = response["numFound"]
    return {**provenance(result, url, ["Vyhledává se doslovná fráze v OCR; chyby rozpoznávání a staré pravopisné podoby mohou nález skrýt.",
                                      "Vrácena jsou metadata, nikoli přepis stránky nebo potvrzený historický fakt.",
                                      "Public označuje přístup v knihovně, nikoli automatickou licenci k dalšímu zveřejnění.", EMPTY_WARNING]),
            "library": record["code"], "api_version": api_version, "query": query, "public_only": public_only,
            "registry_provenance": {k: registration[k] for k in ("request_url", "retrieved_at", "from_cache")},
            "num_found": count, "count_exact": response.get("numFoundExact", True), "start": response.get("start", start),
            "documents": documents, "truncated": start + len(documents) < count}


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def children(element, name):
    return [child for child in element if local_name(child) == name]


def child_text(element, name, default=""):
    found = children(element, name)
    return (found[0].text or "").strip() if found else default


def parse_wms(data):
    if re.search(br"<!ENTITY\s", data, re.I):
        raise FetchError("Entity declarations are not accepted in WMS XML")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise FetchError("Response is not valid WMS XML") from exc
    if local_name(root) not in ("WMS_Capabilities", "WMT_MS_Capabilities"):
        messages = [" ".join(node.itertext()).strip() for node in root.iter() if local_name(node) in ("ServiceException", "ExceptionText")]
        raise FetchError("Not a WMS capabilities response" + (": " + "; ".join(messages) if messages else ""))
    version = root.attrib.get("version", "")
    if version not in ("1.1.1", "1.3.0", "1.1.0"):
        raise FetchError(f"Unsupported WMS version {version!r}")
    capabilities = children(root, "Capability")
    if not capabilities:
        raise FetchError("WMS response lacks Capability")
    capability = capabilities[0]
    formats, endpoint = [], None
    requests = children(capability, "Request")
    if requests:
        maps = children(requests[0], "GetMap")
        if maps:
            formats = [(v.text or "").strip() for v in children(maps[0], "Format")]
            for node in maps[0].iter():
                if local_name(node) == "OnlineResource":
                    endpoint = node.attrib.get("{http://www.w3.org/1999/xlink}href") or node.attrib.get("href")
                    if endpoint:
                        break
    layers = []
    def walk(node, inherited_crs, inherited_boxes, inherited_styles, inherited_queryable=False, depth=0):
        if depth > 64:
            raise FetchError("WMS layer tree is unreasonably deep")
        crs = set(inherited_crs)
        for kind in ("CRS", "SRS"):
            for value in children(node, kind):
                crs.update((value.text or "").split())
        boxes = deepcopy_json(inherited_boxes)
        for box in children(node, "BoundingBox"):
            coordinate_system = box.attrib.get("CRS", box.attrib.get("SRS"))
            try:
                bounds = [float(box.attrib[key]) for key in ("minx", "miny", "maxx", "maxy")]
                if coordinate_system and all(math.isfinite(v) for v in bounds):
                    boxes[coordinate_system] = bounds
            except (KeyError, ValueError):
                pass
        styles = dict(inherited_styles)
        for style in children(node, "Style"):
            name = child_text(style, "Name")
            if name:
                styles[name] = child_text(style, "Title", name)
        queryable = node.attrib.get("queryable", "1" if inherited_queryable else "0") == "1"
        name = child_text(node, "Name")
        if name:
            layers.append({"name": name, "title": child_text(node, "Title", name), "abstract": child_text(node, "Abstract"),
                           "crs": sorted(crs), "bounding_boxes_native_axis_order": boxes,
                           "styles": [{"name": k, "title": v} for k, v in styles.items()], "queryable": queryable})
        for child in children(node, "Layer"):
            walk(child, crs, boxes, styles, queryable, depth + 1)
    for layer in children(capability, "Layer"):
        walk(layer, set(), {}, {})
    service = children(root, "Service")
    return {"version": version, "title": child_text(service[0], "Title") if service else "", "get_map_url": endpoint,
            "map_formats": formats, "layers": layers}


def deepcopy_json(value):
    return json.loads(json.dumps(value))


def wms(client, url, version=None, refresh=False):
    params = {"SERVICE": "WMS", "REQUEST": "GetCapabilities"}
    if version:
        params["VERSION"] = version
    url = wms_url(url, params)
    result = client.fetch(url, refresh=refresh)
    return {**provenance(result, url, ["Capabilities popisují službu, nikoli dataci každého snímku nebo historickou přesnost mapy.",
                                      "CRS a styly se dědí z nadřazených vrstev. Nativní BoundingBox používá osy podle uvedené verze WMS."]), **parse_wms(result.data)}


def parse_bbox(value, crs="EPSG:4326"):
    try:
        values = [float(v.strip()) for v in value.split(",")] if isinstance(value, str) else list(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Bbox requires four comma-separated finite numbers") from exc
    if len(values) != 4 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in values):
        raise ValueError("Bbox requires four finite numbers")
    a, b, c, d = values
    if a >= c or b >= d:
        raise ValueError("Bbox minimum must be smaller than maximum")
    if crs in ("EPSG:4326", "CRS:84") and not (-180 <= a < c <= 180 and -90 <= b < d <= 90):
        raise ValueError("Longitude/latitude bbox is outside WGS84 bounds")
    return values


def map_parameters(layer, bbox, version, crs, width, height, mime):
    if version not in ("1.1.1", "1.3.0"):
        raise ValueError("Map download supports WMS 1.1.1 or 1.3.0")
    if crs not in ("EPSG:4326", "CRS:84", "EPSG:5514"):
        raise ValueError("Supported CRS: EPSG:4326, CRS:84, EPSG:5514")
    if crs == "EPSG:5514" and version != "1.1.1":
        raise ValueError("EPSG:5514 requires --version 1.1.1 and a native easting/northing bbox in metres; no implicit reprojection")
    if not 16 <= width <= 1024 or not 16 <= height <= 1024:
        raise ValueError("Map dimensions must be between 16 and 1024 pixels")
    bbox = parse_bbox(bbox, crs)
    sent = [bbox[1], bbox[0], bbox[3], bbox[2]] if version == "1.3.0" and crs == "EPSG:4326" else bbox
    params = {"SERVICE": "WMS", "VERSION": version, "REQUEST": "GetMap", "LAYERS": layer, "STYLES": "",
              "BBOX": ",".join(format(v, ".12g") for v in sent), "WIDTH": width, "HEIGHT": height, "FORMAT": mime,
              "TRANSPARENT": "FALSE", "CRS" if version == "1.3.0" else "SRS": crs}
    return params


def image_dimensions(data, mime):
    if mime == "image/png":
        if len(data) < 33 or not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR" or b"IEND" not in data[-16:]:
            raise FetchError("WMS response is not a complete PNG")
        return struct.unpack(">II", data[16:24])
    if mime == "image/jpeg":
        if len(data) < 4 or not data.startswith(b"\xff\xd8\xff") or not data.endswith(b"\xff\xd9"):
            raise FetchError("WMS response is not a complete JPEG")
        pos = 2
        while pos + 4 <= len(data):
            if data[pos] != 255:
                break
            while pos < len(data) and data[pos] == 255:
                pos += 1
            if pos >= len(data):
                break
            marker = data[pos]; pos += 1
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(data):
                break
            length = struct.unpack(">H", data[pos:pos + 2])[0]
            if length < 2 or pos + length > len(data):
                break
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and length >= 7:
                height, width = struct.unpack(">HH", data[pos + 3:pos + 7])
                return width, height
            pos += length
        raise FetchError("JPEG dimensions could not be verified")
    raise FetchError("WMS map response must have image/png or image/jpeg MIME type")


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def wms_map(client, url, layer, bbox, out, width=800, height=600, version=None, crs="EPSG:4326", refresh=False):
    path = Path(out)
    extension = path.suffix.lower()
    if extension not in (".png", ".jpg", ".jpeg"):
        raise ValueError("Map output filename must end in .png, .jpg or .jpeg")
    sidecar = Path(str(path) + ".json")
    if path.exists() or sidecar.exists():
        raise ValueError("Map or sidecar already exists; choose new output paths")
    mime = "image/png" if extension == ".png" else "image/jpeg"
    # Validate coordinate interpretation and dimensions before any network call.
    map_parameters(layer, bbox, version or "1.3.0", crs, width, height, mime)
    caps = wms(client, url, version, refresh)
    negotiated = caps["version"]
    if version and negotiated != version:
        raise FetchError(f"WMS did not negotiate requested version {version}; got {negotiated}")
    matches = [record for record in caps["layers"] if record["name"] == layer]
    if len(matches) != 1:
        raise ValueError("Select an exact, unique layer name from the wms command")
    if crs not in matches[0]["crs"]:
        raise ValueError(f"Layer does not advertise {crs}; available: {', '.join(matches[0]['crs'])}. No coordinates were reprojected.")
    if mime not in caps["map_formats"]:
        raise ValueError(f"WMS does not advertise requested image format {mime}")
    endpoint = caps.get("get_map_url") or url
    ep, original = urlsplit(validate_url(endpoint)), urlsplit(validate_url(url))
    if ep.hostname != original.hostname:
        raise FetchError("Advertised GetMap uses another host; inspect and supply its canonical service URL explicitly")
    if original.scheme == "https" and ep.scheme == "http":
        endpoint = urlunsplit(("https", ep.netloc, ep.path, ep.query, ""))
    params = map_parameters(layer, bbox, negotiated, crs, width, height, mime)
    map_url = wms_url(endpoint, params)
    result = client.fetch(map_url, refresh=refresh)
    actual_mime = result.content_type.split(";", 1)[0].strip().lower()
    if actual_mime != mime:
        raise FetchError(f"WMS returned {actual_mime}, expected {mime}; image was not saved")
    dimensions = image_dimensions(result.data, actual_mime)
    if dimensions != (width, height):
        raise FetchError(f"WMS returned dimensions {dimensions}, expected {(width, height)}")
    metadata = {**provenance(result, map_url, ["Jde o vyžádaný mapový výřez, nikoli automaticky datovaný důkaz změny krajiny.",
                                             "Ověř licenci vrstvy, datum měření/snímku a vhodnost měřítka; neuvedené datum nedoplňuj odhadem.",
                                             "Příkaz neprovádí reprojekci. EPSG:5514 používá nativní metry a jen WMS 1.1.1."]),
                "capabilities": {key: caps[key] for key in ("request_url", "retrieved_at", "from_cache")},
                "layer": layer, "layer_title": matches[0]["title"], "version": negotiated, "crs": crs,
                "bbox_input": parse_bbox(bbox, crs), "bbox_input_order": "easting,northing" if crs == "EPSG:5514" else "longitude,latitude",
                "bbox_request": params["BBOX"], "width": width, "height": height, "mime": actual_mime,
                "sha256": hashlib.sha256(result.data).hexdigest(), "bytes": len(result.data), "file": str(path), "sidecar": str(sidecar)}
    atomic_write(path, result.data)
    atomic_write(sidecar, (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return metadata


def label_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " / ".join(label_text(v) for v in value)
    if isinstance(value, dict):
        if "@value" in value:
            return label_text(value["@value"])
        for language in ("cs", "en", "none", "@none"):
            if language in value:
                return label_text(value[language])
        return label_text(next(iter(value.values()), ""))
    return ""


def as_list(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def image_bodies(body):
    for item in as_list(body):
        if not isinstance(item, dict):
            continue
        typ = item.get("type", item.get("@type", ""))
        if typ in ("Choice", "oa:Choice"):
            yield from image_bodies(item.get("items", item.get("item", [])))
            yield from image_bodies(item.get("default"))
        elif typ == "SpecificResource":
            yield from image_bodies(item.get("source"))
        elif typ in ("Image", "dctypes:Image") or str(item.get("format", "")).startswith("image/"):
            yield item


def parse_iiif(data, limit=500):
    if not isinstance(data, dict):
        raise FetchError("IIIF response must be a manifest object")
    typ = data.get("type", data.get("@type"))
    if typ not in ("Manifest", "sc:Manifest"):
        raise FetchError("Supply one IIIF v2/v3 Manifest, not a Collection or image info.json")
    version = 3 if typ == "Manifest" else 2
    raw_canvases, warnings = [], []
    if version == 3:
        raw_canvases = data.get("items", [])
    else:
        sequences = data.get("sequences", [])
        if not isinstance(sequences, list):
            raise FetchError("Invalid IIIF v2 sequences")
        for sequence in sequences:
            if isinstance(sequence, dict):
                values = sequence.get("canvases", [])
                if not isinstance(values, list):
                    raise FetchError("Invalid IIIF v2 canvas list")
                raw_canvases.extend(values)
    if not isinstance(raw_canvases, list):
        raise FetchError("Invalid IIIF canvas list")
    canvases, seen = [], set()
    for canvas in raw_canvases:
        if not isinstance(canvas, dict):
            raise FetchError("Invalid IIIF canvas")
        ident = canvas.get("id", canvas.get("@id"))
        if not isinstance(ident, str) or not ident:
            raise FetchError("IIIF Canvas lacks a string identifier")
        if ident in seen:
            continue
        seen.add(ident)
        if len(canvases) >= limit:
            continue
        annotations = []
        if version == 2:
            annotations = canvas.get("images", [])
        else:
            pages = canvas.get("items", [])
            if not isinstance(pages, list):
                raise FetchError("IIIF Canvas items must be an array")
            for page in pages:
                if not isinstance(page, dict):
                    continue
                if "items" not in page:
                    warnings.append(f"Canvas {ident}: referenced AnnotationPage not fetched")
                values = page.get("items", [])
                if not isinstance(values, list):
                    raise FetchError("IIIF AnnotationPage items must be an array")
                annotations.extend(values)
        if not isinstance(annotations, list):
            raise FetchError("IIIF annotations must be an array")
        images = []
        for annotation in annotations:
            if not isinstance(annotation, dict):
                continue
            motivation = annotation.get("motivation", "painting" if version == 3 else "sc:painting")
            if not any(v in ("painting", "sc:painting") for v in as_list(motivation)):
                continue
            for body in image_bodies(annotation.get("body" if version == 3 else "resource")):
                image_url = body.get("id", body.get("@id"))
                services = []
                for service in as_list(body.get("service")):
                    if isinstance(service, dict):
                        services.append({"id": service.get("id", service.get("@id")), "type": service.get("type", service.get("@type")), "profile": service.get("profile")})
                images.append({"url": image_url, "format": body.get("format"), "width": body.get("width"), "height": body.get("height"),
                               "services": services, "rights": body.get("rights", body.get("license"))})
        canvases.append({"id": ident, "label": label_text(canvas.get("label")), "width": canvas.get("width"), "height": canvas.get("height"), "images": images})
    return {"presentation_version": version, "id": data.get("id", data.get("@id")), "label": label_text(data.get("label")),
            "rights": data.get("rights", data.get("license")), "attribution": label_text(data.get("attribution", data.get("requiredStatement", {}).get("value") if isinstance(data.get("requiredStatement"), dict) else "")),
            "canvases": canvases, "canvas_count": len(seen), "truncated": len(seen) > len(canvases), "warnings": warnings}


def iiif(client, url, limit=500, refresh=False):
    if not 1 <= limit <= 5000:
        raise ValueError("IIIF canvas limit must be 1–5000")
    url = validate_url(url)
    result, data = read_json(client, url, refresh)
    return {**provenance(result, url, ["Přečten je pouze manifest. Obrázky, vzdálené AnnotationPages a autorizační služby se nestahují.",
                                      "Uvedený obrázek nebo licence manifestu nezaručuje právo publikovat každý snímek; ověř práva konkrétní položky."]), **parse_iiif(data, limit)}


def ares(client, ico, refresh=False):
    if not re.fullmatch(r"[0-9]{8}", ico):
        raise ValueError("IČO must contain exactly eight ASCII digits, including leading zeros")
    url = ARES_URL + ico
    result, data = read_json(client, url, refresh)
    if not isinstance(data, dict) or str(data.get("ico", "")).zfill(8) != ico or not data.get("obchodniJmeno"):
        raise FetchError("ARES did not return the requested identified economic subject")
    return {**provenance(result, url, ["ARES poskytuje současnou evidenční identitu a údaje registrů; nezjišťuje celou historii podniku nebo značky.",
                                      "Shoda názvu nebo adresy není důkazem právního nástupnictví. Registrační datum není automaticky počátkem řemesla či provozu.",
                                      "Veřejnost registru neznamená, že máš bez dalšího zveřejnit osobní údaje živnostníka."]),
            "ico": ico, "name": data["obchodniJmeno"], "legal_form": data.get("pravniForma"), "address": data.get("sidlo"),
            "registry_dates": {key: data.get(key) for key in ("datumVzniku", "datumZaniku", "datumAktualizace") if key in data},
            "cz_nace": data.get("czNace"), "status": data.get("seznamRegistraci"), "interpretation": "current_registry_identity"}


def main(argv=None):
    # Use deterministic UTF-8 even when Windows redirects a legacy-code-page
    # console. Imports retain the host application's original stream settings.
    for stream in (sys.stdout, sys.stderr):
        if callable(getattr(stream, "reconfigure", None)):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Read-only Czech source adapters with provenance and bounded requests.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("registry", help="Discover current Kramerius library codes and API versions")
    p.add_argument("--code")
    p = sub.add_parser("ruian", help="Return present-day place/address candidates without auto-selection")
    p.add_argument("--query", required=True); p.add_argument("--kind", choices=tuple(LAYERS), default="municipality")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("kramerius-search", help="Search a literal phrase in OCR; metadata only")
    p.add_argument("--library", required=True); p.add_argument("--query", required=True)
    p.add_argument("--api-version", type=int, choices=(5, 7)); p.add_argument("--rows", type=int, default=20)
    p.add_argument("--start", type=int, default=0); p.add_argument("--public-only", action="store_true")
    p = sub.add_parser("wms", help="List layers with inherited CRS, styles and native bounds")
    p.add_argument("--url", required=True)
    p = sub.add_parser("wms-map", help="Fetch one small map image and its provenance sidecar")
    p.add_argument("--url", required=True); p.add_argument("--layer", required=True)
    p.add_argument("--bbox", required=True, help="minlon,minlat,maxlon,maxlat; EPSG5514 uses native XY metres")
    p.add_argument("--crs", choices=("EPSG:4326", "CRS:84", "EPSG:5514"), default="EPSG:4326")
    p.add_argument("--version", choices=("1.1.1", "1.3.0")); p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p = sub.add_parser("iiif", help="Inspect a v2/v3 manifest without downloading images")
    p.add_argument("--url", required=True); p.add_argument("--limit", type=int, default=500)
    p = sub.add_parser("ares", help="Read current economic-subject metadata by exact IČO")
    p.add_argument("--ico", required=True)
    for name, command in sub.choices.items():
        command.add_argument("--cache-dir", help="Shared cache/host-gate directory; default is per-user temporary cache")
        command.add_argument("--refresh", action="store_true", help="Refresh response, still respecting host cooldown")
        command.add_argument("--out", required=name == "wms-map", help="JSON output; wms-map instead writes this image and FILE.json provenance")
    args = parser.parse_args(argv)
    client = HttpClient(cache_dir=args.cache_dir)
    try:
        if args.command == "registry":
            value = registry(client, args.code, args.refresh)
        elif args.command == "ruian":
            value = ruian(client, args.query, args.kind, args.limit, args.refresh)
        elif args.command == "kramerius-search":
            value = kramerius_search(client, args.library, args.query, args.api_version, args.rows, args.start, args.public_only, args.refresh)
        elif args.command == "wms":
            value = wms(client, args.url, refresh=args.refresh)
        elif args.command == "wms-map":
            value = wms_map(client, args.url, args.layer, args.bbox, args.out, args.width, args.height, args.version, args.crs, args.refresh)
        elif args.command == "iiif":
            value = iiif(client, args.url, args.limit, args.refresh)
        else:
            value = ares(client, args.ico, args.refresh)
        output = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if args.out and args.command != "wms-map":
            atomic_write(args.out, output.encode("utf-8"))
        else:
            print(output, end="")
    except (FetchError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
