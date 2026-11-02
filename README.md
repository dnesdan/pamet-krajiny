# Paměť krajiny

[![Tests](https://github.com/dnesdan/pamet-krajiny/actions/workflows/tests.yml/badge.svg)](https://github.com/dnesdan/pamet-krajiny/actions/workflows/tests.yml)

**Badatelský AI skill pro proměny míst v celé České republice.** Pomáhá zjistit, kudy vedla stará cesta, kde byl rybník nebo náhon, jak se změnilo sídlo, les, lom, pole či průmyslový areál — a u každého závěru uchovat konkrétní důkaz a jeho meze.

Paměť krajiny je sada instrukcí pro AI asistenta, otevřený katalog českých zdrojů a malé nástroje v Pythonu. Místo může ležet v kterémkoli ze 14 krajů. Regionální archiv se vybírá podle území a původce; pražské a brněnské portály jsou volitelné místní doplňky.

## Co dostaneš

- Badatelský postup od určení místa přes výběr map a písemností až po kontrolu závěrů.
- Obecný JSON dossier: místa a objekty, tvrzení, prameny, události, vztahy, výzkumný deník a otevřené otázky.
- Příkazy pro založení projektu, plán hledání, validaci a export do Markdownu, samostatného HTML a GeoJSON.
- Síťové pomocníky pro vybrané veřejné služby; jejich konkrétní operace uvádí `zdroje.py --help`. Katalog zahrnuje i prameny vyžadující ruční průzkum nebo badatelnu.
- Tři malé skutečné rešerše s citacemi a sadou zadání pro ověření přenositelnosti mezi kraji.
- Automatické testy jádra, exportů a síťového chování. Ověření dostupnosti živé služby je samostatný krok, nezaměňuje se s offline testy.

## Příklady zadání

> Použij Paměť krajiny. Zjisti, jak se měnila vodní soustava u mé obce mezi 19. a 20. stoletím. U každého závěru ukaž konkrétní mapu nebo písemný doklad a odděl nejisté možnosti.

> Prozkoumej staré cesty v okolí Klatov. Nejdřív vyber jednoznačné území a dostupné mapy, potom navrhni několik míst k ověření v terénu.

> Jak souvisí vznik jezera Most s předchozí těžbou? Udělej časovou osu a zachovej rozpory v údajích jednotlivých zdrojů.

> Mám fotografii a vzpomínku na zaniklý mlýn na Vysočině. Pomoz mi zjistit, který objekt to byl, a připrav další hledání podle fondu, nikoli jen dnešního kraje.

## Použití s AI asistentem

Hlavní instrukce jsou v [skills/pamet-krajiny/SKILL.md](skills/pamet-krajiny/SKILL.md). Zkopíruj **celou složku** `skills/pamet-krajiny`, včetně skriptů a referencí, do adresáře skillů určeného tvým AI klientem. Přesné umístění a způsob načtení ověř pro používanou verzi klienta. Samotné stažení repozitáře skill do účtu automaticky neinstaluje.

Asistent má před použitím přečíst `SKILL.md` a podle otázky příslušné reference. Pokud klient podporuje přímý výběr skillu, vyber **Paměť krajiny**; jinak odkaž na soubor v zadání. Nepotřebuješ mít předem hotový datový projekt.

## Rychlý start nástrojů

Vyžadován je Python 3.10 nebo novější. Běžné příkazy používají standardní knihovnu Pythonu. Následující příklady spouštěj z kořene repozitáře:

```bash
git clone https://github.com/dnesdan/pamet-krajiny.git
cd pamet-krajiny
python3 skills/pamet-krajiny/scripts/badatel.py --help
python3 skills/pamet-krajiny/scripts/zdroje.py --help
```

### Otevři skutečný příklad

```bash
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/most.json
python3 skills/pamet-krajiny/scripts/badatel.py render examples/most.json --format html --out most.html
python3 skills/pamet-krajiny/scripts/badatel.py render examples/most.json --format markdown --out most.md
```

Vytvořené HTML otevři v běžném prohlížeči. Přehled je samostatný; pro otevření citovaných webových pramenů je potřeba internet. Dodané příklady obsahují veřejné podklady a exportují se bez `--public`, aby zachovaly rozsah rešerše, badatelský deník a další kroky. U vlastního výzkumu `--public` použije označení citlivých dat; před publikací stále zkontroluj veškeré texty a přílohy.

### Začni vlastní výzkum

```bash
python3 skills/pamet-krajiny/scripts/badatel.py init --title "Cesty a náhony v okolí obce" --theme landscape --place "Vybraná obec, okres" --out vyzkum.json
python3 skills/pamet-krajiny/scripts/badatel.py plan --place "Klatovy" --region "Plzeňský kraj" --topic "staré cesty a mlýny" --out plan.json
python3 skills/pamet-krajiny/scripts/badatel.py sources --theme landscape
```

Návrh plánu ještě neobsahuje nalezené důkazy. Teprve po prohlédnutí pramene přidej zdroj a tvrzení do `vyzkum.json`. Podrobnosti jsou v [datovém postupu](skills/pamet-krajiny/references/data-a-vystupy.md).

## Co pokrývají zdroje

| Oblast | Typické zdroje |
|---|---|
| Současná identita místa | RÚIAN, ČÚZK, identifikátory obce a katastru |
| Mapy a snímky | Archiv ČÚZK, CENIA včetně roků snímkování, MZK, VÚGTK, místní geoportály |
| Písemná historie | Regionální a městské archivy, kroniky, hospodářské a vodoprávní spisy |
| Literatura a tisk | Kramerius, Bibliografie dějin Českých zemí, ANNO, regionální publikace |
| Specializovaná krajina | ČGS, HEIS, NZM, NPÚ, AMČR, ČHMÚ |
| Sídla a pomístní názvy | ČSÚ, ÚJČ, místní historie, odborné a komunitní rozcestníky |

Přehled s omezeními a krajským směrováním je v [rozcestníku](skills/pamet-krajiny/references/archivy-a-zdroje.md). Licence a rozsah přístupu se posuzují u konkrétního dokumentu. Prohlížení na webu neznamená právo hromadně stahovat či přebírat obrázky.

## Příklady a jejich rozsah

| Příklad | Co ověřuje |
|---|---|
| [Uherský Brod](examples/uhersky-brod.json) | Městská struktura, opevnění a zeleň; oddělení neurčené lokality od konkrétního parku a projektového záměru od provedení |
| [Most](examples/most.json) | Těžba a hydrická rekultivace; časové milníky a uchování skutečného rozporu dvou institucionálních údajů |
| [Rožmberk](examples/rozmberk.json) | Mokřady, povodeň a následné úpravy vodní soustavy; rozlišení primárního úředního dokladu od odborného přehledu a vyhlášení ochrany od vzniku mokřadu |
| [Zadání pro 14 krajů](examples/overeni-prenositelnosti.md) | Přenos postupu na jiné území a typ pramene; nejsou vydávána za provedených 14 rešerší |

Tři dossierové příklady byly vytvořeny z otevřených institucionálních webových záznamů s datem přístupu 2. listopadu 2026. Obsahují citace a výzkumný deník. Nemají vymyšlenou geometrii a nevydávají textovou rešerši za hotové srovnání map. Důvod absence geometrie je zaznamenán, GeoJSON export proto může mít prázdné `features`. Přehledy a reprodukční příkazy jsou v [examples/README.md](examples/README.md).

## Testování

```bash
python3 -m unittest discover -s tests -v
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/uhersky-brod.json
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/most.json
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/rozmberk.json
```

Automatické testy ověřují strukturu dat, referenční vazby, chování exportů a izolované síťové situace. Nenahrazují paleografickou kontrolu, odbornou interpretaci map ani novou kontrolu dostupnosti všech portálů. Pro nezávislé vyzkoušení postupu použij konkrétní zadání z příkladů a ukaž agentovi jen zadání, skill a surové podklady.

## Návaznost na ostatní skilly

Projekt navazuje na [Rodokmen](https://github.com/sarsonj/rodokmen-skill), [Paměť rodu](https://github.com/thejanhromek/pamet-rodu) a [Dějiny domu](https://github.com/vzoha/dejiny-domu-skill). Přehled použitelných nástrojů a konkrétních podnětů z PR je v [návaznosti](skills/pamet-krajiny/references/navaznost.md). Výzkum výroby pokračuje v [Dějinách podniku a řemesla](https://github.com/dnesdan/dejiny-podniku-a-remesla).

Vlastní kód a texty se řídí licencí repozitáře; práva externích map, skenů a fotografií zůstávají u jejich zdrojů. Příručky `playbook.md` vyjmuté z licencí původních projektů nebyly převzaty.

## Meze první verze

Přesná georeference, automatická detekce změn na rastru a kompletní interaktivní mapa všech časových řezů nejsou automatickými funkcemi těchto skriptů. Skill vede badatele k jejich řádnému provedení v odpovídajícím GIS či obrazovém prostředí. Řada archiválií vyžaduje ruční čtení, přihlášení nebo návštěvu badatelny.

U stejného názvu místa se vždy rozhoduje podle dalších údajů. Mapové „nenalezeno“ není automaticky zánik, dnešní číslo parcely není historická identita a větší počet odkazů sám nezvyšuje jistotu závěru.

## Implementované klienty a ověření

Součástí balíku je **62 popsaných zdrojů** a **7 síťových příkazů**: registr Krameriů, kandidáti RÚIAN, vyhledávání Kramerius v5/v7, seznam WMS vrstev, jednotlivý mapový výřez, inspekce IIIF manifestu a ARES. Kompletní příklady příkazů, limity a zacházení s chybami jsou v [referenci nástrojů](skills/pamet-krajiny/references/nastroje.md).

Původ návrhu a vyhodnocení **všech 25 upstream PR** najdeš v [UPSTREAM.md](UPSTREAM.md). Konkrétní lokální, nezávislé a živé ověření zaznamenává [TESTING.md](TESTING.md). Externí podklady mají [vlastní licenční podmínky](THIRD_PARTY_NOTICES.md).

Další dokončené příklady: [Rožmberk a povodňové změny](examples/rozmberk.md), [skutečný mapový výřez Uherského Brodu](examples/mapovy-vyrez.md). Rožmberk vznikl při nezávislém průchodu skillu. Každý JSON má čitelný Markdown a samostatné HTML ve stejné složce.
