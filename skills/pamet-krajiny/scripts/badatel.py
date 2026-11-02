#!/usr/bin/env python3
"""Portable, dependency-free research dossiers with claim-level evidence.

This program organizes evidence. It never upgrades a hypothesis automatically,
deduces disappearance from a failed search, or equates a firm with its building.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import html
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit, quote

SKILL_ROOT = Path(__file__).resolve().parents[1]
ARRAYS = ("entities", "sources", "claims", "events", "links", "research_log", "open_questions")
ENTITY_TYPES = {"place", "landscape_feature", "building", "organization", "person", "craft", "product", "infrastructure", "brand"}
ENTITY_TYPE_CZ = {"place": "Místo", "landscape_feature": "Krajinný prvek", "building": "Budova / provozovna",
                  "organization": "Podnik / instituce", "person": "Osoba", "craft": "Řemeslo", "product": "Výrobek",
                  "infrastructure": "Infrastruktura", "brand": "Značka"}
STATUSES = {"documented", "supported", "hypothesis", "disputed"}
PRECISIONS = {"exact", "year", "range", "approximate", "unknown"}
GEOMETRY_ROLES = {"site", "centroid", "approximate", "extent", "unknown"}
GEOMETRY_ROLE_CZ = {"site": "poloha zkoumaného objektu podle pramene", "centroid": "centroid území; není polohou objektu", "approximate": "přibližná poloha", "extent": "rozsah území", "unknown": "význam geometrie neověřen; nepovažovat za přesnou polohu"}
PRECISION_CZ = {"exact": "přesně", "year": "rok", "range": "interval", "approximate": "přibližně", "unknown": "neznámá"}
VERIFICATION_STATES = {"content_checked", "search_index_only", "unavailable"}
VERIFICATION_CZ = {"content_checked": "obsah zkontrolován", "search_index_only": "pouze vyhledávací index nebo úryvek", "unavailable": "obsah nedostupný"}
STATUS_CZ = {"documented": "Doloženo v uvedeném prameni", "supported": "Podpořeno prameny", "hypothesis": "Hypotéza", "disputed": "Rozporné údaje"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _year(value):
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and -9999 <= value <= 9999)


def _date(value):
    try:
        return isinstance(value, str) and len(value) == 10 and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _url(value):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        return False
    try:
        url = urlsplit(value)
        return url.scheme in ("http", "https") and bool(url.hostname) and not url.username and not url.password
    except ValueError:
        return False


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(data):
    """Return actionable errors without throwing on malformed input."""
    errors = []
    def err(path, message):
        errors.append(f"{path}: {message}")
    if not isinstance(data, dict):
        return ["root: dossier must be a JSON object"]
    if data.get("schema_version") != "1.0":
        err("schema_version", "must be '1.0'")
    project = data.get("project")
    if not isinstance(project, dict):
        err("project", "must be an object")
        project = {}
    for key in ("id", "title", "place", "scope"):
        if not isinstance(project.get(key), str) or (key != "scope" and not _text(project.get(key))):
            err(f"project.{key}", "must be text" + (" (nonempty)" if key != "scope" else ""))
    if not isinstance(project.get("theme"), str) or project.get("theme") not in ("landscape", "enterprise"):
        err("project.theme", "must be landscape or enterprise")
    if not _date(project.get("created")):
        err("project.created", "must be an ISO date YYYY-MM-DD")
    if not isinstance(project.get("research_questions"), list) or any(not _text(v) for v in project.get("research_questions", [])):
        err("project.research_questions", "must be an array of nonempty strings")
    collections = {}
    for key in ARRAYS:
        value = data.get(key)
        if not isinstance(value, list):
            err(key, "must be an array")
            value = []
        collections[key] = value
    if any(not _text(v) for v in collections["open_questions"]):
        err("open_questions", "must contain nonempty strings")
    all_ids, by_kind = {}, {}
    pid = project.get("id")
    if isinstance(pid, str):
        if not ID_RE.fullmatch(pid):
            err("project.id", "must be a stable identifier without spaces")
        all_ids[pid] = "project"
    for kind in ("entities", "sources", "claims", "events", "links"):
        by_kind[kind] = set()
        for index, obj in enumerate(collections[kind]):
            path = f"{kind}[{index}]"
            if not isinstance(obj, dict):
                err(path, "must be an object")
                continue
            ident = obj.get("id")
            if not isinstance(ident, str) or not ID_RE.fullmatch(ident):
                err(path + ".id", "must be a stable identifier without spaces")
            else:
                if ident in all_ids:
                    err(path + ".id", f"duplicate ID {ident!r} already used by {all_ids[ident]}")
                all_ids[ident] = path
                by_kind[kind].add(ident)
            if "sensitive" in obj and not isinstance(obj["sensitive"], bool):
                err(path + ".sensitive", "must be true or false")

    def refs(value, kind, path, nonempty=False):
        if not isinstance(value, list):
            err(path, "must be an array of IDs")
            return
        if nonempty and not value:
            err(path, "must not be empty")
        seen = set()
        for ref in value:
            if not isinstance(ref, str) or ref not in by_kind[kind]:
                err(path, f"unknown {kind} ID {ref!r}")
            elif ref in seen:
                err(path, f"duplicate reference {ref!r}")
            else:
                seen.add(ref)

    def when(value, path, precision=True):
        if not isinstance(value, dict):
            err(path, "must be a time object")
            return
        if precision and (not isinstance(value.get("precision"), str) or value.get("precision") not in PRECISIONS):
            err(path + ".precision", "must be exact, year, range, approximate or unknown")
        for bound in ("from", "to"):
            if bound not in value or not _year(value.get(bound)):
                err(path + "." + bound, "must be an integer year or null")
        a, b = value.get("from"), value.get("to")
        if _year(a) and _year(b) and a is not None and b is not None and a > b:
            err(path, "start year must not exceed end year")
        if value.get("precision") in ("exact", "year") and (a is None or b is None or a != b):
            err(path, "exact/year precision requires equal known bounds")
        if value.get("precision") == "unknown" and (a is not None or b is not None):
            err(path, "unknown precision requires null bounds")

    def geometry(value, path):
        if not isinstance(value, dict):
            err(path, "must be a GeoJSON geometry object")
            return
        typ, coords = value.get("type"), value.get("coordinates")
        if "crs" in value:
            err(path, "use WGS84 longitude/latitude, not an alternate CRS")
        def point(p, pth):
            if not isinstance(p, list) or len(p) not in (2, 3) or any(not _number(v) for v in p):
                err(pth, "position must contain 2 or 3 finite numbers")
            elif not (-180 <= p[0] <= 180 and -90 <= p[1] <= 90):
                err(pth, "WGS84 longitude/latitude out of range; check coordinate order")
        def line(points, pth, ring=False):
            if not isinstance(points, list) or len(points) < (4 if ring else 2):
                err(pth, "not enough positions")
                return
            for i, p in enumerate(points):
                point(p, f"{pth}[{i}]")
            if ring and points[0] != points[-1]:
                err(pth, "polygon ring must be closed")
        def polygon(rings, pth):
            if not isinstance(rings, list) or not rings:
                err(pth, "polygon must contain at least one ring")
            else:
                for i, ring in enumerate(rings):
                    line(ring, f"{pth}[{i}]", True)
        if typ == "Point":
            point(coords, path + ".coordinates")
        elif typ == "LineString":
            line(coords, path + ".coordinates")
        elif typ == "Polygon":
            polygon(coords, path + ".coordinates")
        elif typ in ("MultiPoint", "MultiLineString", "MultiPolygon"):
            if not isinstance(coords, list) or not coords:
                err(path + ".coordinates", "must be a nonempty array")
            else:
                function = {"MultiPoint": point, "MultiLineString": line, "MultiPolygon": polygon}[typ]
                for i, part in enumerate(coords):
                    function(part, f"{path}.coordinates[{i}]")
        else:
            err(path + ".type", "supported geometries: Point, LineString, Polygon and their Multi variants")

    for i, obj in enumerate(collections["entities"]):
        if not isinstance(obj, dict):
            continue
        path = f"entities[{i}]"
        if not isinstance(obj.get("type"), str) or obj.get("type") not in ENTITY_TYPES:
            err(path + ".type", "unknown entity type")
        if not _text(obj.get("label")):
            err(path + ".label", "must be nonempty text")
        if "geometry" in obj:
            geometry(obj["geometry"], path + ".geometry")
        if "geometry_role" in obj and (not isinstance(obj["geometry_role"], str) or obj["geometry_role"] not in GEOMETRY_ROLES):
            err(path + ".geometry_role", "must be site, centroid, approximate, extent or unknown")
        if "location_accuracy_m" in obj and (not _number(obj["location_accuracy_m"]) or obj["location_accuracy_m"] < 0):
            err(path + ".location_accuracy_m", "must be a finite nonnegative number")
        aliases = obj.get("aliases", [])
        if not isinstance(aliases, list):
            err(path + ".aliases", "must be an array")
        else:
            for n, alias in enumerate(aliases):
                apath = f"{path}.aliases[{n}]"
                if not isinstance(alias, dict):
                    err(apath, "must be an object")
                    continue
                if not _text(alias.get("name")):
                    err(apath + ".name", "must be nonempty text")
                when(alias, apath, False)
                refs(alias.get("source_ids", []), "sources", apath + ".source_ids")

    for i, obj in enumerate(collections["sources"]):
        if not isinstance(obj, dict):
            continue
        path = f"sources[{i}]"
        for key in ("title", "publisher", "license"):
            if not _text(obj.get(key)):
                err(path + "." + key, "must be nonempty text; use 'unknown' for unverified license")
        if not _url(obj.get("url")):
            err(path + ".url", "must be an absolute HTTP(S) URL without credentials")
        if not _date(obj.get("accessed")):
            err(path + ".accessed", "must be an ISO date YYYY-MM-DD")
        if obj.get("kind") not in ("primary", "secondary", "synthetic"):
            err(path + ".kind", "must be primary, secondary or synthetic")
        if obj.get("access") not in ("open", "metadata", "restricted", "onsite"):
            err(path + ".access", "must be open, metadata, restricted or onsite")
        if "verification_status" in obj and (not isinstance(obj["verification_status"], str) or obj["verification_status"] not in VERIFICATION_STATES):
            err(path + ".verification_status", "must be content_checked, search_index_only or unavailable")

    source_verification = {obj.get("id"): obj.get("verification_status") for obj in collections["sources"]
                           if isinstance(obj, dict) and isinstance(obj.get("id"), str)}
    for i, obj in enumerate(collections["claims"]):
        if not isinstance(obj, dict):
            continue
        path = f"claims[{i}]"
        if not _text(obj.get("text")):
            err(path + ".text", "must be nonempty text")
        if not isinstance(obj.get("status"), str) or obj.get("status") not in STATUSES:
            err(path + ".status", "unknown evidence status")
        refs(obj.get("entity_ids"), "entities", path + ".entity_ids", True)
        evidence = obj.get("evidence")
        if not isinstance(evidence, list):
            err(path + ".evidence", "must be an array")
            evidence = []
        if obj.get("status") in ("documented", "supported", "disputed") and not evidence:
            err(path + ".evidence", "a documented/supported/disputed claim needs cited evidence")
        if obj.get("status") in ("documented", "supported") and evidence:
            usable = any(isinstance(item, dict) and isinstance(item.get("source_id"), str)
                         and item["source_id"] in source_verification
                         and source_verification[item["source_id"]] not in ("search_index_only", "unavailable")
                         for item in evidence)
            if not usable:
                err(path + ".evidence", "search-index-only/unavailable evidence cannot support documented/supported status; keep a hypothesis until content is checked")
        for n, item in enumerate(evidence):
            epath = f"{path}.evidence[{n}]"
            if not isinstance(item, dict):
                err(epath, "must be an object")
                continue
            refs([item.get("source_id")], "sources", epath + ".source_id")
            if not _text(item.get("locator")):
                err(epath + ".locator", "must identify the page, section or record")
            if item.get("kind") not in ("observation", "transcription", "paraphrase", "context"):
                err(epath + ".kind", "unknown evidence kind")
            if "excerpt" in item and not isinstance(item["excerpt"], str):
                err(epath + ".excerpt", "must be text")
        if "time" in obj:
            when(obj["time"], path + ".time")
    for kind in ("events", "links"):
        for i, obj in enumerate(collections[kind]):
            if not isinstance(obj, dict):
                continue
            path = f"{kind}[{i}]"
            refs(obj.get("claim_ids"), "claims", path + ".claim_ids", True)
            if kind == "events":
                for key in ("type", "label"):
                    if not _text(obj.get(key)):
                        err(path + "." + key, "must be nonempty text")
                refs(obj.get("entity_ids"), "entities", path + ".entity_ids", True)
                when(obj.get("time"), path + ".time")
            else:
                refs([obj.get("from"), obj.get("to")], "entities", path)
                if not _text(obj.get("relation")):
                    err(path + ".relation", "must be nonempty text")
                if "time" in obj:
                    when(obj["time"], path + ".time")
    for i, obj in enumerate(collections["research_log"]):
        path = f"research_log[{i}]"
        if not isinstance(obj, dict):
            err(path, "must be an object")
            continue
        if not _date(obj.get("date")):
            err(path + ".date", "must be an ISO date")
        for key in ("query", "result", "limitations"):
            if not isinstance(obj.get(key), str) or (key != "limitations" and not _text(obj.get(key))):
                err(path + "." + key, "must be text")
        refs([obj.get("source_id")], "sources", path + ".source_id")
    return errors


def new_dossier(title, theme, place):
    return {"schema_version": "1.0", "project": {"id": "project-1", "title": title,
            "theme": theme, "place": place, "scope": "", "research_questions": [],
            "created": date.today().isoformat()}, **{name: [] for name in ARRAYS}}


def public_projection(data):
    """Remove flagged records and their dependent graph, then free-form work notes.

    This is a conservative filter, not an anonymizer. A human must review text
    that was never marked sensitive, and verify reuse rights before publishing.
    """
    # Whitelist the public structure: unknown extension fields may contain work
    # notes and must not leak merely because the validator permits extensions.
    result = {key: deepcopy(data[key]) for key in ("schema_version", "project", *ARRAYS)}
    result["entities"] = [o for o in result["entities"] if not o.get("sensitive", False)]
    entity_ids = {o["id"] for o in result["entities"]}
    source_ids = {o["id"] for o in result["sources"] if not o.get("sensitive", False)}
    result["claims"] = [o for o in result["claims"] if not o.get("sensitive", False)
                        and set(o["entity_ids"]) <= entity_ids
                        and all(e["source_id"] in source_ids for e in o["evidence"])]
    claim_ids = {o["id"] for o in result["claims"]}
    result["events"] = [o for o in result["events"] if not o.get("sensitive", False)
                        and set(o["entity_ids"]) <= entity_ids and set(o["claim_ids"]) <= claim_ids]
    result["links"] = [o for o in result["links"] if not o.get("sensitive", False)
                       and o["from"] in entity_ids and o["to"] in entity_ids and set(o["claim_ids"]) <= claim_ids]
    needed_sources = {e["source_id"] for o in result["claims"] for e in o["evidence"]}
    for entity in result["entities"]:
        entity.pop("notes", None)
        if "aliases" in entity:
            entity["aliases"] = [alias for alias in entity["aliases"]
                                 if set(alias.get("source_ids", [])) <= source_ids and not alias.get("sensitive", False)]
            for alias in entity["aliases"]:
                needed_sources.update(alias.get("source_ids", []))
    result["sources"] = [o for o in result["sources"] if o["id"] in needed_sources and o["id"] in source_ids]
    for source in result["sources"]:
        source.pop("notes", None)
    public_fields = {
        "entities": {"id", "type", "label", "aliases", "geometry", "geometry_role", "location_accuracy_m"},
        "sources": {"id", "title", "url", "publisher", "accessed", "kind", "access", "license", "locator", "verification_status"},
        "claims": {"id", "entity_ids", "text", "status", "evidence", "time"},
        "events": {"id", "type", "label", "entity_ids", "claim_ids", "time"},
        "links": {"id", "from", "to", "relation", "claim_ids", "time"},
    }
    for kind, allowed in public_fields.items():
        result[kind] = [{key: value for key, value in obj.items() if key in allowed} for obj in result[kind]]
    for entity in result["entities"]:
        if "geometry" in entity:
            entity["geometry"] = {key: value for key, value in entity["geometry"].items() if key in {"type", "coordinates"}}
        if "aliases" in entity:
            entity["aliases"] = [{key: value for key, value in alias.items() if key in {"name", "from", "to", "source_ids"}}
                                 for alias in entity["aliases"]]
    for claim in result["claims"]:
        claim["evidence"] = [{key: value for key, value in item.items() if key in {"source_id", "locator", "kind"}}
                             for item in claim["evidence"]]
    for kind in ("claims", "events", "links"):
        for obj in result[kind]:
            if "time" in obj:
                obj["time"] = {key: value for key, value in obj["time"].items() if key in {"from", "to", "precision"}}
    result["research_log"] = []
    result["open_questions"] = []
    result["project"] = {key: value for key, value in result["project"].items()
                         if key in {"id", "title", "theme", "place", "created"}}
    result["project"]["scope"] = ""
    result["project"]["research_questions"] = []
    return result


def time_label(when):
    if not when:
        return "nedatováno"
    a, b, precision = when.get("from"), when.get("to"), when.get("precision")
    if a is None and b is None:
        return "datum neznámé"
    text = str(a) if a == b else f"{a if a is not None else '?'}–{b if b is not None else '?'}"
    return ("přibližně " if precision == "approximate" else "") + text


def time_detail(when):
    if not when:
        return "čas neuveden; nelze předpokládat trvalou platnost"
    return time_label(when) + " (přesnost: " + PRECISION_CZ.get(when.get("precision"), "neznámá") + ")"


def geometry_detail(entity):
    role = entity.get("geometry_role", "unknown")
    description = GEOMETRY_ROLE_CZ.get(role, GEOMETRY_ROLE_CZ["unknown"])
    if "location_accuracy_m" in entity:
        description += f"; uvedená polohová nejistota {entity['location_accuracy_m']} m"
    return description


def related_status(claim_ids, claims):
    """An event or relation must not hide uncertainty in the claims it cites."""
    statuses = {c["status"] for c in claims if c["id"] in claim_ids}
    for status in ("disputed", "hypothesis", "supported", "documented"):
        if status in statuses:
            return STATUS_CZ[status]
    return "Bez podkladového tvrzení"


def _md(value):
    # Escape raw HTML and Markdown syntax from imported data.
    value = html.escape(str(value), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def _link(label, url):
    safe = quote(url, safe=":/?#[]@!$&'*+,;=%")
    return f"[{_md(label)}](<{safe}>)"


def render_markdown(data):
    project = data["project"]
    lines = [f"# {_md(project['title'])}", "", f"**Místo:** {_md(project['place'])}", "",
             "Stav tvrzení vyjadřuje práci s uvedenými prameny; není automatickou zárukou historické pravdy.", ""]
    if project["scope"]:
        lines += [_md(project["scope"]), ""]
    if project["research_questions"]:
        lines += ["## Badatelské otázky", ""] + [f"- {_md(v)}" for v in project["research_questions"]] + [""]
    lines += ["## Objekty výzkumu", ""]
    for entity in data["entities"]:
        lines += [f"- **{_md(entity['label'])}** (`{entity['id']}`), {_md(entity['type'])}"]
        if "geometry" in entity:
            lines += [f"  - Geometrie: {_md(geometry_detail(entity))}."]
        if entity.get("notes"):
            lines += [f"  - Poznámka: {_md(entity['notes'])}"]
        for alias in entity.get("aliases", []):
            lines += [f"  - Varianta názvu: {_md(alias['name'])}; {_md(time_label(alias))}; prameny: {_md(', '.join(alias.get('source_ids', [])) or 'neurčeny')}"]
    lines += ["", "## Tvrzení a důkazy", ""]
    sources = {o["id"]: o for o in data["sources"]}
    for claim in data["claims"]:
        lines += [f"### {claim['id']} · {STATUS_CZ[claim['status']]}", "", _md(claim["text"]), ""]
        if "time" in claim:
            lines += [f"**Čas:** {_md(time_label(claim['time']))}", ""]
        if not claim["evidence"]:
            lines += ["Bez přímého dokladu; ověřit před použitím jako fakt.", ""]
        for evidence in claim["evidence"]:
            source = sources[evidence["source_id"]]
            lines += [f"- {_link(source['title'], source['url'])} ({source['id']}), {_md(evidence['locator'])}; {_md(evidence['kind'])}."]
        lines += [""]
    lines += ["## Časová osa", ""]
    for event in sorted(data["events"], key=lambda o: (o["time"].get("from") is None, o["time"].get("from") or 0, o["id"])):
        status = related_status(event["claim_ids"], data["claims"])
        lines += [f"- **{_md(time_label(event['time']))}:** {_md(event['label'])} — {_md(status)}; tvrzení {_md(', '.join(event['claim_ids']))}."]
    if data["links"]:
        lines += ["", "## Vztahy", ""]
        for item in data["links"]:
            status = related_status(item["claim_ids"], data["claims"])
            lines += [f"- `{item['from']}` → {_md(item['relation'])} → `{item['to']}`; {_md(time_detail(item.get('time')))}; {_md(status)}; tvrzení {_md(', '.join(item['claim_ids']))}."]
    if data["open_questions"]:
        lines += ["", "## Co zbývá ověřit", ""] + [f"- {_md(v)}" for v in data["open_questions"]]
    lines += ["", "## Soupis pramenů", ""]
    for source in data["sources"]:
        checked = VERIFICATION_CZ.get(source.get("verification_status"), "stav ověření neuveden")
        lines += [f"- **{source['id']}**: {_link(source['title'], source['url'])}. {_md(source['publisher'])}; přístup {_md(source['accessed'])}; {_md(source['access'])}; {_md(checked)}; licence: {_md(source['license'])}."]
    if data["research_log"]:
        lines += ["", "## Badatelský deník", ""]
        for item in data["research_log"]:
            lines += [f"- **{_md(item['date'])} · {_md(item['source_id'])}:** {_md(item['query'])}. Výsledek: {_md(item['result'])}. Omezení: {_md(item['limitations'])}."]
    return "\n".join(lines) + "\n"


def render_html(data):
    e = lambda value: html.escape(str(value), quote=True)
    p = data["project"]
    sources = {s["id"]: s for s in data["sources"]}
    claims = []
    for c in data["claims"]:
        evidence = "".join(f'<li><a href="{e(sources[item["source_id"]]["url"])}" rel="noreferrer">{e(sources[item["source_id"]]["title"])}</a> — {e(item["locator"])} <small>({e(item["kind"])})</small></li>' for item in c["evidence"])
        if not evidence:
            evidence = "<li>Bez přímého dokladu; ověřit před použitím jako fakt.</li>"
        claims.append(f'<article id="{e(c["id"])}"><span class="status {e(c["status"])}">{e(STATUS_CZ[c["status"]])}</span><h3>{e(c["text"])}</h3><p class="meta">{e(c["id"])} · {e(time_label(c.get("time")))}</p><ul>{evidence}</ul></article>')
    event_parts = []
    for event in sorted(data["events"], key=lambda o: (o["time"].get("from") is None, o["time"].get("from") or 0)):
        anchors = " · ".join('<a href="#' + e(k) + '">' + e(k) + '</a>' for k in event["claim_ids"])
        status = related_status(event["claim_ids"], data["claims"])
        event_parts.append(f'<li><time>{e(time_label(event["time"]))}</time><div><strong>{e(event["label"])}</strong><small>{e(status)}</small><p>{anchors}</p></div></li>')
    events = "".join(event_parts)
    entity_parts = []
    for entity in data["entities"]:
        detail = '<small>Geometrie: ' + e(geometry_detail(entity)) + '</small>' if "geometry" in entity else ""
        notes = '<p>Poznámka: ' + e(entity["notes"]) + '</p>' if entity.get("notes") else ""
        entity_parts.append(f'<li id="{e(entity["id"])}"><strong>{e(entity["label"])}</strong><small>{e(ENTITY_TYPE_CZ[entity["type"]])}</small>{detail}{notes}</li>')
    entity_html = "".join(entity_parts)
    source_html = "".join(f'<li id="{e(v["id"])}"><a href="{e(v["url"])}" rel="noreferrer">{e(v["title"])}</a><small>{e(v["publisher"])} · přístup {e(v["accessed"])} · {e(v["access"])} · {e(VERIFICATION_CZ.get(v.get("verification_status"), "stav ověření neuveden"))} · licence: {e(v["license"])}</small></li>' for v in data["sources"])
    questions = "".join(f"<li>{e(v)}</li>" for v in data["open_questions"])
    research = "".join(f'<li><strong>{e(v["date"])} · {e(v["source_id"])}</strong><p>{e(v["query"])} → {e(v["result"])}</p><small>{e(v["limitations"])}</small></li>' for v in data["research_log"])
    links = "".join(f'<li>{e(v["from"])} → {e(v["relation"])} → {e(v["to"])}; {e(time_detail(v.get("time")))}; {e(related_status(v["claim_ids"], data["claims"]))}; {e(", ".join(v["claim_ids"]))}</li>' for v in data["links"])
    style = """*{box-sizing:border-box}body{margin:0;background:#f4f1e9;color:#18342f;font:17px/1.65 system-ui,sans-serif}header{background:#173d35;color:#f8f3e8;padding:3rem max(6vw,1.25rem)}main{max-width:1080px;margin:auto;padding:1.5rem}h1{max-width:900px;font:700 clamp(2rem,5vw,3.4rem)/1.12 Georgia,serif}h2{font:700 1.8rem Georgia,serif;margin-top:2.7rem}h3{font-size:1.1rem;line-height:1.5}a{color:#166154;overflow-wrap:anywhere}header a{color:#d0e2d8}nav{display:flex;gap:1.4rem;flex-wrap:wrap}small,.meta{display:block;color:#536861;font-size:.86rem}article{background:#fffdf8;padding:1.3rem 1.6rem;margin:1rem 0;border-left:4px solid #267359;border-radius:5px;break-inside:avoid}ul{padding-left:1.3rem}li{margin:.6rem 0}.status{font-size:.76rem;text-transform:uppercase;font-weight:750;letter-spacing:.06em;border-radius:3px;padding:.3rem .6rem;background:#e3eee5}.hypothesis{background:#fff0c4}.disputed{background:#f8dcd4}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.8rem;list-style:none;padding:0}.cards li{padding:1rem;border:1px solid #cbd2c7;border-radius:5px}.timeline{list-style:none;padding:0}.timeline li{display:flex;gap:1.5rem;border-top:1px solid #cbd2c7;padding:.8rem 0}.timeline time{min-width:9rem;font-weight:bold}footer{margin-top:3rem;border-top:1px solid #cbd2c7;padding:2rem 0;font-size:.85rem}@media(max-width:600px){.timeline li{display:block}header{padding:2rem 1.25rem}}@media print{body{background:white;color:black}header{background:white;color:black;padding:0}nav{display:none}main{padding:0}a{color:inherit}article{border:1px solid #aaa}}"""
    return f'''<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{e(p['title'])}</title><style>{style}</style></head>
<body><header><p>BADATELSKÝ DOSSIER · {e(p['place'])}</p><h1>{e(p['title'])}</h1><p>{e(p['scope'])}</p><nav><a href="#doklady">Tvrzení a důkazy</a><a href="#cas">Časová osa</a><a href="#prameny">Prameny</a></nav></header><main>
<p>Stav tvrzení vyjadřuje práci s uvedenými prameny; není automatickou zárukou historické pravdy. Mapa ani výsledek vyhledávání samy neprokazují totožnost nebo zánik objektu.</p>
<h2>Objekty výzkumu</h2><ul class="cards">{entity_html}</ul>
<h2 id="doklady">Tvrzení a důkazy</h2>{''.join(claims)}
<h2 id="cas">Časová osa</h2><ol class="timeline">{events or '<li>Žádné doložené události.</li>'}</ol>
{'<h2>Vztahy</h2><ul>'+links+'</ul>' if links else ''}
{'<h2>Co zbývá ověřit</h2><ul>'+questions+'</ul>' if questions else ''}
<h2 id="prameny">Soupis pramenů</h2><ul>{source_html}</ul>
{'<h2>Badatelský deník</h2><ul>'+research+'</ul>' if research else ''}
<footer>Vytvořeno z otevřeného datového modelu 1.0. Obsah je uložen v tomto souboru; odkazy na prameny vyžadují internet. Texty a práva k dalšímu zveřejnění zkontroluj samostatně.</footer></main></body></html>'''


def render_geojson(data):
    features = []
    source_by_id = {v["id"]: v for v in data["sources"]}
    for entity in data["entities"]:
        if "geometry" not in entity:
            continue
        claims = [c for c in data["claims"] if entity["id"] in c["entity_ids"]]
        sources = sorted({e["source_id"] for c in claims for e in c["evidence"]})
        features.append({"type": "Feature", "id": entity["id"], "geometry": deepcopy(entity["geometry"]),
                         "properties": {"label": entity["label"], "entity_type": entity["type"],
                                        "geometry_role": entity.get("geometry_role", "unknown"),
                                        "geometry_meaning": geometry_detail(entity),
                                        "location_accuracy_m": entity.get("location_accuracy_m"),
                                        "claims": [{"id": c["id"], "text": c["text"], "status": c["status"],
                                                    "time": {k: c["time"].get(k) for k in ("from", "to", "precision")} if "time" in c else None,
                                                    "evidence": [{k: e[k] for k in ("source_id", "locator", "kind", "excerpt") if k in e} for e in c["evidence"]]} for c in claims],
                                        "sources": [{k: source_by_id[sid][k] for k in ("id", "title", "url", "publisher", "accessed", "kind", "access", "license", "locator", "verification_status") if k in source_by_id[sid]} for sid in sources]}})
    return {"type": "FeatureCollection", "features": features}


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c))).strip("-")


REGIONS = {
    "CZ010": ("Praha", "Hlavní město Praha", "praha"),
    "CZ020": ("Středočeský kraj", "stredocesky"),
    "CZ031": ("Jihočeský kraj", "jihocesky"),
    "CZ032": ("Plzeňský kraj", "plzensky"),
    "CZ041": ("Karlovarský kraj", "karlovarsky"),
    "CZ042": ("Ústecký kraj", "ustecky"),
    "CZ051": ("Liberecký kraj", "liberecky"),
    "CZ052": ("Královéhradecký kraj", "kralovehradecky"),
    "CZ053": ("Pardubický kraj", "pardubicky"),
    "CZ063": ("Kraj Vysočina", "Vysočina", "vysocina"),
    "CZ064": ("Jihomoravský kraj", "jihomoravsky"),
    "CZ071": ("Olomoucký kraj", "olomoucky"),
    "CZ072": ("Zlínský kraj", "zlinsky"),
    "CZ080": ("Moravskoslezský kraj", "moravskoslezsky"),
}


def region_tokens(region):
    token = normalize(region)
    for code, names in REGIONS.items():
        variants = {normalize(code), *(normalize(v) for v in names)}
        if token in variants:
            return variants
    raise ValueError("Unknown region; use a Czech region name or code CZ010–CZ080 from the source catalogue")


def load_catalogue(path=None):
    path = Path(path) if path else SKILL_ROOT / "references" / "sources.json"
    if not path.exists():
        raise ValueError(f"Source catalogue is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    sources = value.get("sources") if isinstance(value, dict) else value
    if not isinstance(sources, list) or any(not isinstance(v, dict) for v in sources):
        raise ValueError("Source catalogue must contain an array of source objects")
    return sources


# Small, inspectable topic groups: this is routing guidance, not historical NLP.
TOPIC_GROUPS = (
    (("textil", "tkalc", "tkad", "souken", "pradel", "bavln", "hedvab", "lnar", "barvir"),
     {"podnik", "firma", "prumysl", "tovarna", "remeslo", "vyrobek", "inzerat", "adresar", "cech", "zivnost"}),
    (("stroj", "prumysl", "tovarn", "pivov", "sklar", "hut", "automobil", "podnik"),
     {"podnik", "firma", "prumysl", "tovarna", "technika", "vyrobek", "adresar", "archiv"}),
    (("rybnik", "vod", "reka", "rekou", "mlyn", "povod"),
     {"voda", "rybnik", "mlyn", "krajina", "mapa", "ortofoto", "povoden"}),
    (("les", "park", "zahrad"), {"les", "zahrada", "park", "krajina", "mapa", "ortofoto"}),
    (("dul", "dol", "lom", "tezb", "uhli", "rekultiv"),
     {"dul", "lom", "tezba", "geologie", "poddolovani", "rekultivace", "jezero", "prumysl"}),
    (("zelezn", "silnic", "cest", "trat", "most"), {"cesta", "mapa", "ortofoto", "krajina", "archiv"}),
    (("zanik", "vesnic", "obec", "sidlo", "vysidl"), {"zanikle-misto", "obec", "krajina", "mapa", "ortofoto", "kronika"}),
    (("patent", "znack", "vynalez"), {"patent", "ochranna-znamka", "vynalez", "vyrobek", "vestnik"}),
)
COMMON_PRIORITY = {"ruian": 100, "archives-portal": 92, "ndb": 88, "kramerius-registry": 86,
                   "kramerius": 84, "biblio": 78, "cuzk-archiv": 75, "nkp-open": 65, "anno": 60, "ujc": 55}
THEME_PRIORITY = {
    "landscape": {"cenia-ortho": 85, "cenia-years": 84, "csu-lexicon": 72, "cuzk-open": 65,
                  "mzk-maps": 60, "chartae": 58, "pamatkovy-katalog": 55, "historical-atlas": 50},
    "enterprise": {"industrial-topography": 80, "ntm-archive": 70, "justice": 66, "ares": 65,
                   "pamatkovy-katalog": 60, "rzp": 58, "esbirky": 56},
}


def source_priority(source, place, topic, theme, regional):
    ident = source.get("id", "")
    normalized = normalize(topic)
    words = normalized.split("-")
    has = lambda stems: any(word.startswith(stem) for word in words for stem in stems)
    tags = {normalize(value) for value in source.get("topics", [])}
    expanded = {normalized, *words}
    for stems, additions in TOPIC_GROUPS:
        if has(stems):
            expanded.update(additions)
    matches = sorted(tags & expanded)
    score = max(COMMON_PRIORITY.get(ident, 0), THEME_PRIORITY[theme].get(ident, 0))
    reasons = ["základní pramen pro identifikaci nebo kontext"] if score else []
    if regional:
        score += 120 if "archiv" in tags else 50
        reasons.append("odpovídá zvolenému kraji; ověř konkrétní fond a historickou působnost")
    if matches:
        score += min(48, 12 * len(matches))
        reasons.append("tematická shoda: " + ", ".join(matches))
    reserve_reason = None
    war = has(("valk", "voj", "legion", "nacist", "holocaust", "aryzac", "nucen", "koncentr", "internac"))
    repression = has(("znarodn", "perzek", "komunis", "stb", "represe"))
    if ident in {"vua", "holocaust", "arolsen"} and not war:
        reserve_reason = "specializovaný válečný pramen; zařaď při otázce na válku, arizaci či nucenou práci"
    elif ident == "abs" and not (war or repression):
        reserve_reason = "specializovaný pramen k represím; zařaď při doložené tematické souvislosti"
    elif ident.startswith("brno-") and "brno" not in normalize(place).split("-"):
        reserve_reason = "městský zdroj pro Brno; samotná shoda kraje neprokazuje místní působnost"
    if reserve_reason:
        score = -1000
        reasons = [reserve_reason]
    elif ident in {"vua", "holocaust", "arolsen", "abs"}:
        score += 100
        reasons.append("výslovná otázka na válku nebo represi")
    if not reasons:
        reasons = ["doplňkový pramen; použij podle zjištěných souvislostí"]
    return score, reasons, matches, reserve_reason


def plan(place, region, topic, name=None, from_year=None, to_year=None, catalogue=None, theme=None, max_sources=15):
    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("The start year must not exceed the end year")
    if not isinstance(max_sources, int) or isinstance(max_sources, bool) or not 1 <= max_sources <= 60:
        raise ValueError("max_sources must be an integer from 1 to 60")
    tokens = region_tokens(region)
    sources = load_catalogue() if catalogue is None else catalogue
    topic_key = normalize(topic)
    enterprise_topics = {"enterprise", "podnik", "firma", "remeslo", "dejiny-podniku-a-remesla"}
    landscape_topics = {"landscape", "krajina", "pamet-krajiny"}
    if theme is not None and theme not in ("landscape", "enterprise"):
        raise ValueError("Theme must be landscape or enterprise")
    if theme is None:
        theme = "enterprise" if topic_key in enterprise_topics else "landscape" if topic_key in landscape_topics else ("enterprise" if SKILL_ROOT.name == "dejiny-podniku-a-remesla" else "landscape")
    ranked = []
    for source in sources:
        regions = source.get("regions", ["CZ"])
        if isinstance(regions, str):
            regions = [regions]
        stokens = {normalize(v) for v in regions}
        if stokens and not (stokens & {"cz", "all", "national", "ceska-republika", "cele-cesko"}) and not (stokens & tokens):
            continue
        regional = bool(stokens & tokens) and not bool(stokens & {"cz", "all", "national", "ceska-republika", "cele-cesko"})
        themes = source.get("themes", ["landscape", "enterprise"])
        if theme and theme not in themes:
            continue
        url = source.get("url", source.get("homepage", ""))
        text = " ".join(v for v in (name, place, topic) if v)
        if from_year is not None or to_year is not None:
            text += f" {from_year if from_year is not None else '?'}–{to_year if to_year is not None else '?'}"
        score, reasons, matched_topics, reserve_reason = source_priority(source, place, topic, theme, regional)
        ranked.append({"source_id": source.get("id", ""), "source": source.get("title", source.get("name", "")),
                        "url": url, "query": text, "access": source.get("access", "check"),
                        "automation": source.get("automation", "manual"),
                        "instruction": source.get("notes", source.get("limitations", "Ověř rozsah fondu a dostupnost dokumentu.")),
                        "priority": score, "priority_reasons": reasons, "matched_topics": matched_topics,
                        "reserve_reason": reserve_reason})
    ranked.sort(key=lambda item: -item["priority"])
    queries, reserve = [], []
    for item in ranked:
        if len(queries) < max_sources and item["reserve_reason"] is None:
            queries.append(item)
        else:
            if item["reserve_reason"] is None:
                item["reserve_reason"] = "za hranicí prvních priorit; dostupné pro navazující hledání"
            reserve.append(item)
    return {"place": place, "region": region, "topic": topic, "theme": theme, "name": name,
            "period": {"from": from_year, "to": to_year}, "queries": queries, "reserve_sources": reserve,
            "max_sources": max_sources, "eligible_source_count": len(ranked), "catalogue_source_count": len(sources),
            "before_search": ["Urči jednoznačně obec, okres a katastr; kandidáty neslučuj automaticky.",
                              "Zapiš historické názvy a tehdejší správní příslušnost podle pramene.",
                              "Dnešní kraj je navigační pomůcka; fond může být uložen jinde.",
                              "U map rozliš datum měření, revize a vydání; u fotografie datum pořízení.",
                              "U firmy rozliš právní subjekt, značku, provozovnu, budovu a vlastníka."],
            "status": "plan_only", "warning": "Dotazy nebyly spuštěny. Prázdný výsledek ani neviditelný objekt nejsou důkazem zániku nebo neexistence."}


def write_output(content, out=None):
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="" if text.endswith("\n") else "\n")


def main(argv=None):
    # Windows redirected streams can otherwise use a legacy code page. Limit
    # this change to CLI execution; importing the module must not alter callers.
    for stream in (sys.stdout, sys.stderr):
        if callable(getattr(stream, "reconfigure", None)):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Evidence-led Czech historical research dossiers (Python standard library).")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="Create an empty dossier; does not invent findings")
    for key in ("title", "place", "out"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--theme", choices=("landscape", "enterprise"), required=True)
    p = sub.add_parser("validate", help="Check evidence, references, dates and coordinates")
    p.add_argument("file")
    p = sub.add_parser("render", help="Render a valid dossier without network requests")
    p.add_argument("file")
    p.add_argument("--format", choices=("markdown", "html", "geojson"), required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--public", action="store_true", help="Remove flagged records and dependent evidence; review unflagged text manually")
    p = sub.add_parser("plan", help="Prepare source queries for any Czech region; does not execute them")
    for key in ("place", "region", "topic"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--name")
    p.add_argument("--theme", choices=("landscape", "enterprise"), help="Defaults to this skill's theme unless topic names one explicitly")
    p.add_argument("--max-sources", type=int, default=15, help="Primary source priorities, 1–60; other eligible sources remain in reserve_sources")
    p.add_argument("--from-year", type=int)
    p.add_argument("--to-year", type=int)
    p.add_argument("--out")
    p = sub.add_parser("sources", help="List national and regional source capabilities")
    p.add_argument("--theme", choices=("landscape", "enterprise"))
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            if Path(args.out).exists():
                raise ValueError("Output already exists; choose a new path")
            write_output(new_dossier(args.title, args.theme, args.place), args.out)
        elif args.command in ("validate", "render"):
            data = json.loads(Path(args.file).read_text(encoding="utf-8"))
            errors = validate(data)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            if args.command == "validate":
                print(f"OK: {args.file} ({len(data['claims'])} claims, {len(data['sources'])} sources)")
            else:
                if Path(args.out).resolve() == Path(args.file).resolve():
                    raise ValueError("Export must not overwrite the input dossier")
                if args.public:
                    data = public_projection(data)
                    print("Public filter applied. Review unflagged text, rights and location sensitivity before publishing.", file=sys.stderr)
                output = {"markdown": render_markdown, "html": render_html, "geojson": render_geojson}[args.format](data)
                write_output(output, args.out)
        elif args.command == "plan":
            write_output(plan(args.place, args.region, args.topic, args.name, args.from_year, args.to_year, theme=args.theme, max_sources=args.max_sources), args.out)
        else:
            sources = load_catalogue()
            if args.theme:
                sources = [s for s in sources if args.theme in s.get("themes", ["landscape", "enterprise"])]
            write_output(sources)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
