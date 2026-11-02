# Výzkumná data a výstupy

## Struktura dossieru

Vstupní JSON používá `schema_version: "1.0"`. `schema.json` a příkaz `validate` popisují strojovou část; věcnou správnost zkontroluj samostatně.

| Kolekce | Účel |
|---|---|
| `project` | Zadání, území, otázky a datum založení; téma `landscape` |
| `entities` | Místa, krajinné prvky, budovy, organizace a jiné rozlišené objekty |
| `sources` | Použité a zkontrolované zdrojové záznamy s URL, institucí, přístupem a licencí |
| `claims` | Jednotlivá tvrzení s jistotou, konkrétní evidencí a časem |
| `events` | Události opřené o tvrzení; nepřidávat nedoložená fakta jen do časové osy |
| `links` | Pojmenované vztahy entit s odkazy na tvrzení |
| `research_log` | Hledání, kontrolovaný rozsah, výsledek a omezení |
| `open_questions` | Nevyřešené otázky a další kroky |

Všechna ID musí být jedinečná a odkazy musí mířit na existující záznam. ID nevytvářej z proměnlivého popisku; použij stálé označení, například `place-001`, které se po opravení názvu nezmění. Dossier ve veřejných příkladech používá popisná ID pro snazší čtení.

Zdroj `kind: primary` znamená původní záznam, úřední údaj o vlastní činnosti nebo obdobný primární doklad. Současný historický přehled bývá `secondary`, i když jej publikuje důvěryhodná instituce. `synthetic` vyhraď pro zřetelně umělé testy; nevyužívej jej v reálném výzkumu jako důkaz dějin.

Přístup `open` neznamená automaticky otevřenou licenci; `license: "unknown"` je poctivá hodnota, pokud další práva neznáš. `metadata`, `restricted` a `onsite` vystihují druh přístupu, nikoli neexistenci dokumentu.

## Tvrzení a evidence

Tvrzení potřebuje `id`, `entity_ids`, `text`, `status` a pole `evidence`. Jedna evidence má `source_id`, přesný `locator` a `kind`:

- `observation`: zaznamenané přímé pozorování obrazu nebo dat;
- `transcription`: přepis konkrétní pasáže;
- `paraphrase`: vlastní stručné vyjádření toho, co pramen uvádí;
- `context`: související podklad, který sám nedokazuje celý závěr.

`context` nenahrazuje přímou oporu silného tvrzení. Doplň původní znění jen v přiměřeném rozsahu. U fotografií, které nebyly načteny, nepoužívej `observation`.

Pro data používej `time: {"from": 1900, "to": 1910, "precision": "range"}`. Roky jsou celá čísla, neznámý konec `null`. Pro konkrétní rok mají oba konce stejnou hodnotu a `precision: "year"`. Přesný den lze zachovat v textu tvrzení a citaci; formát časových polí první verze pracuje s roky. Nevyráběj přesnou časovou osu z data přístupu.

## Geometrie

Entita může obsahovat `geometry` ve formátu GeoJSON a `location_accuracy_m`. Není povinné přiřadit geometrii každému nálezu. Aktuální reprezentativní bod obce není poloha zaniklého rybníka. Význam geometrie zapiš do `geometry_role` podle pravidel níže, aby se rozlišení skutečného objektu, přibližné polohy a středu území zachovalo i ve veřejném exportu. Zásadní význam bodu nesmí zůstat pouze v pracovních `notes`.

Pokud má objekt více časových geometrií, první verze umožňuje vytvořit samostatné entity jednotlivých doložených stavů a spojit je vztahy s datací. Neměň geometrii tak, že beze stopy přepíšeš starší stav. Pro náročnější analýzu uchovej i původní GIS soubory a transformační postup mimo dossier.

## Běžný pracovní cyklus

```bash
python3 skills/pamet-krajiny/scripts/badatel.py validate vyzkum.json
python3 skills/pamet-krajiny/scripts/badatel.py render vyzkum.json --format markdown --out vyzkum.md
python3 skills/pamet-krajiny/scripts/badatel.py render vyzkum.json --format html --out vyzkum.html --public
python3 skills/pamet-krajiny/scripts/badatel.py render vyzkum.json --format geojson --out vyzkum.geojson --public
```

Před přepsáním vlastní práce si ponech předchozí verzi. Editační dávky z více agentů nejprve porovnej s aktuálním souborem; zdejší datový model sám není databázový systém pro souběžné zápisy.

Markdown a HTML slouží ke čtení tvrzení, časové osy, evidence a nevyřešených otázek. HTML lze otevřít lokálně; externí odkazy na prameny vyžadují internet. GeoJSON umožňuje další zpracování doložených geometrií v GIS. Nástroj automaticky nevytvoří georeferenci ani prostorově přesnou mapu ze slovního popisu.

## Veřejné vydání

Označ citlivé entity/tvrzení `sensitive: true`. Příznak `--public` vytváří odvozený pohled podle těchto značek a navázaných záznamů. Před publikací však stále přečti výsledné texty a metadata: jméno nebo soukromý kontakt může být vložen i do titulku zdroje, URL, poznámky nebo volné otázky. Automatické filtrování samo nerozhoduje o oprávnění zveřejnit obsah.

Zkontroluj rovněž zdrojové soubory a adresář, který publikuješ. Soukromý JSON se nestává veřejným jen proto, že máš vedle něj filtrované HTML. Přílohy a snímky zveřejni pouze v dovoleném rozsahu a s atribucí.

Veřejný výsledek má výslovně odlišit doložené závěry, rozpory a hypotézy. Po technickém `validate` zůstává nutná kontrola správné identity míst a významu pramenů.

## Význam geometrie a stav ověření zdroje

K bodu přidej `geometry_role`: `site` pro ověřený objekt, `centroid` pro střed území, `approximate` pro přibližnou lokalizaci, `extent` pro plošný rozsah a `unknown`, pokud význam není určen. Toto pole přechází i do veřejného GeoJSON. Nevkládej zásadní význam bodu pouze do `notes`; pracovní poznámky veřejný filtr odstraní. Chybějící role se v exportu označí jako neověřená.

U zdroje používej `verification_status` (`content_checked`, `search_index_only`, `unavailable`). Samotná stopa z indexu nebo nedostupný obsah nepodpoří `documented` ani `supported`; založ hypotézu nebo další úkol. Podrobné příkazy a limity jsou v [nástrojích](nastroje.md).
