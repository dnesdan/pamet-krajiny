# Co bylo skutečně otestováno

Stav při přípravě verze **0.1.0, 2. listopadu 2026**. Výsledky živých služeb jsou časový snímek; jejich aktuální dostupnost se může změnit.

## Automatické kontroly

**74 lokálních testů prošlo.** Samostatně prošel také validátor metadat skillu, UI metadat, JSON Schema, šablony a všech 3 přibalených dossierů. Běžné testy nevyužívají síť ani uživatelská přihlášení. Runtime používá jen standardní knihovnu Pythonu 3.10+; PyYAML a jsonschema jsou vývojové závislosti.

Z kořene repozitáře:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/verify.py
```

[GitHub Actions](https://github.com/dnesdan/pamet-krajiny/actions/workflows/tests.yml) spouští při pushi a pull requestu pět kombinací: Ubuntu a Windows s Pythonem 3.10/3.12 a macOS s Pythonem 3.12. Konkrétní stav jednotlivého commitu je v odkazovaném běhu; samotná existence workflow není důkaz úspěšného běhu.

| Oblast | Co kontrolujeme |
|---|---|
| Důkazy a datový model | Jedinečná ID, odkazy mezi záznamy, citace a lokátory, míra jistoty, časové rozsahy, validita geometrie |
| Přenositelnost | Směrování všech 14 krajů na odpovídající regionální archiv, absence pevného brněnského výchozího místa, samostatně zkopírovaná složka skillu |
| Plán rešerše | Téma a území, výchozí limit 15 prioritních zdrojů, zdůvodněné pořadí a zachování dalších pramenů v rezervě |
| Exporty | Citace a časové nejistoty v HTML/Markdown/GeoJSON, bezpečné vykreslení textů, vztahy a význam geometrie |
| Veřejný pohled | Odstranění označených citlivých záznamů i závislostí; pracovní poznámky a neznámá rozšíření nepřecházejí do veřejného výstupu |
| Síťový klient | Omezená velikost a čas, kontrola délky odpovědi, atomická cache a hash, sdílený zámek mezi procesy, stop stavy a čekací lhůta, žádné slepé opakování |
| Zdroje | RÚIAN a nejednoznačné názvy; Kramerius v5/v7; IIIF v2/v3; ARES; dědičnost WMS parametrů, osy, formát a rozměry obrázku |
| Přenos mezi systémy | Čeština na stdout/stderr i při vynuceném ASCII prostředí; sdílené zámky pro POSIX a Windows |

První skutečný běh na Windows odhalil chybu samotného testu načítání HTML: výchozí CP1252 neumělo přečíst správně vytvořený UTF-8 soubor. Test nyní výslovně používá UTF-8; nebyl vypnut ani obejit změnou prostředí. Linux a macOS prošly již v prvním běhu. Aktuální výsledek celé matice je ověřitelný přes výše uvedené Actions.

## Nezávislé použití a opravy z kontroly

Rožmberk: nový agent dostal téma, skill a dostupné zdroje bez předem připravené odpovědi. Založil projekt, vytvořil čtyři tvrzení, validoval data a vyexportoval Markdown i HTML. Výsledkem je [rozmberk.json](examples/rozmberk.json), se zdroji AOPK a původní povodňovou zprávou. Nedostupné služby nebyly vydávány za prázdný archiv.

Samostatná kontrola kódu našla tři ztráty informací při exportu: časovou platnost vztahů, konkrétní vazbu tvrzení na důkaz v GeoJSON a význam geometrického bodu. Všechny byly opraveny a mají regresní testy. Pole `geometry_role` nyní rozlišuje skutečný objekt, centroid, přibližnou lokalizaci a další případy. `verification_status` brání tomu, aby samotný vyhledávací úryvek nebo nedostupný zdroj podpíral tvrzení označené jako doložené či podpořené.

Nezávislý průchod také vedl ke zkrácení příliš širokého výchozího plánu. Další relevantní zdroje se nezahazují, zůstávají v `reserve_sources`.

## Živé ověření společných klientů

Podrobné URL, parametry, čas načtení a stručné výsledky jsou v [docs/live-checks.json](docs/live-checks.json). Bylo provedeno **osm úspěšných malých kontrol**:

| Operace | Skutečně pozorovaný výsledek |
|---|---|
| Registr Krameriů | Načteno 56 záznamů aktuálního registru knihoven |
| RÚIAN: Uherský Brod | Jeden kandidát, kód obce 592731 |
| RÚIAN: Horní Lhota | Dva kandidáti, žádný automatický výběr prvního |
| Kramerius MZK v7 | Doslovná OCR fráze „Uherský Brod“, filtr veřejných záznamů, 3 záznamy z 4 318 hlášených výsledků; explicitní příznak zkrácení |
| CENIA WMS | Přečteny capabilities historické ortofotomapy, vrstva `orto`, WMS 1.1.1 |
| ARES | IČO 46345965, současná identita České zbrojovky; bez odvození historického nástupnictví |
| Manuscriptorium IIIF | Skutečný manifest v2, 932 pláten, zobrazeny údaje prvních 2; žádné obrazy se nestahovaly |
| CENIA GetMap | Skutečný JPEG 800 × 600, EPSG:5514, 134 847 bajtů; ověřena signatura, rozměry a SHA-256 |

Jeden výsledek Krameria může být například stránka, nikoli samostatná publikace. Počet výsledků vyhledávání není počet nezávislých důkazů. Přečtení manifestu neznamená přečtení rukopisu. Přesný rok snímkování konkrétního mapového výřezu nebyl ověřen a nebyl odhadnut podle názvu vrstvy.

### Pozorované překážky

- Kramerius NFA v5 vrátil HTTP **403**. Klient skončil bez obcházení přístupu a bez automatického opakování. Živá dostupnost této instance tedy není potvrzena; v5 je pokryta řízenými testy odpovědí.
- CENIA na požadovaný PNG v jednom pokusu vrátila JPEG. Kontrola odmítla nesoulad formátu. Následný výslovný požadavek na JPEG uspěl.
- Živým testem neprošlo všech 62 záznamů katalogu. Část katalogu jsou metodické rozcestníky, portály pro ruční práci nebo odkazy na nástroje jiných projektů, nikoli implementované adaptéry.

### Zopakování jednotlivých síťových dotazů

Příkazy prováděj jednotlivě a respektuj případné odmítnutí služby. Výsledky se mohou lišit od uloženého protokolu.

```bash
python skills/pamet-krajiny/scripts/zdroje.py registry
python skills/pamet-krajiny/scripts/zdroje.py ruian --query "Horní Lhota" --kind municipality
python skills/pamet-krajiny/scripts/zdroje.py kramerius-search --library mzk --query "Uherský Brod" --rows 3 --public-only
python skills/pamet-krajiny/scripts/zdroje.py wms --url https://gis.cenia.cz/mapcache/ortofotomapa_historicka/wms
python skills/pamet-krajiny/scripts/zdroje.py ares --ico 46345965
python skills/pamet-krajiny/scripts/zdroje.py iiif --url https://collectiones.manuscriptorium.com/assorted/NKCR__/NKCR__/2/NKCR__-NKCR__14_J_000094_3I6VGS2-cs/ --limit 2
```

Přesný postup pro mapový výřez, včetně licence, původu souřadnic a reprodukčního příkazu, je v [mapovém příkladu Paměti krajiny](https://github.com/dnesdan/pamet-krajiny/blob/main/examples/mapovy-vyrez.md).

## Příklady a vizuální kontrola

V obou projektech je dohromady sedm malých citovaných rešerší ze šesti různých míst a samostatný mapový příklad. Ukázky nejsou úplné místní monografie. Rozpory a neověřené možnosti jsou záměrně zachovány. Zadání pro všech 14 krajů jsou návrhy dalších zkoušek; netvrdíme, že už proběhlo 14 archivních studií.

Dodané HTML/Markdown vznikly přímo z JSON. Veřejné příklady byly obsahově zkontrolovány a vyrenderovány bez `--public`, aby zůstaly viditelné výzkumné meze, deník a další kroky. U vlastních pracovních dat používej označení citlivosti a zkontroluj výsledný veřejný výstup.

Byl vizuálně prohlédnut skutečný mapový výřez a statické tiskové vykreslení ukázek Most a Plzeň. Nebyl dokončen automatický test v reálném prohlížeči: stažení jeho binárního balíku v testovacím prostředí selhalo. Statické HTML má testy obsahu a exportu; netvrdíme ověření ve všech prohlížečích.

## Co úspěšné testy nezaručují

Testy neprokazují úplnost digitalizace, pravdivost každého citovaného historického přehledu ani právní kontinuitu podniků. Neprovádějí automatickou georeferenci, plošné čtení rukopisů nebo rozpoznání všech změn krajiny. `--public` je filtr označených údajů, ne automatická anonymizace. Aktuální práva, dostupnost a význam každého použitého pramene je nutné posoudit při konkrétní rešerši.
