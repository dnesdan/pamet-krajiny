# Návaznost na původní skilly a všechny jejich PR

Stav ověřen 2. listopadu 2026. Nové skilly nejsou forkem kompletního rodokmenového webu. Jejich Python jádro, datový model a protokoloví klienti jsou nová implementace. Následující projekty poskytly konkrétní vzory, zdroje, odhalené chyby a ověřitelné návaznosti. Otevřený PR zde není vydaná funkce upstreamu.

| Projekt | Zkoumaný commit | Převzatá myšlenka / použití |
|---|---|---|
| [Rodokmen](https://github.com/sarsonj/rodokmen-skill) | [`2b65713`](https://github.com/sarsonj/rodokmen-skill/tree/2b657135f9dbe6843cc7515883252ad799fb40c9) | české archivní portály, přesné odkazy na snímky, badatelský deník, ověřování výřezů, společné omezování dotazů |
| [Paměť rodu](https://github.com/thejanhromek/pamet-rodu) | [`d40b651`](https://github.com/thejanhromek/pamet-rodu/tree/d40b6512efb247859773f4cd4e273a1299d26f22) | důkazy u jednotlivých tvrzení, stabilní identifikátory, nezamlčené rozpory, oddělení pracovního a veřejného výstupu, samostatné offline HTML |
| [Dějiny domu](https://github.com/vzoha/dejiny-domu-skill) | [`240bed4`](https://github.com/vzoha/dejiny-domu-skill/tree/240bed4ddf2490ebb59f31aad50c1a0e2dc67648) | propojení katastru, RÚIAN, starých map, držitelů a obyvatel; místní kontext; výběr podle fondu a období |

Paměť rodu a Dějiny domu v době kontroly neměly upstream PR. Rodokmen měl 25 PR: 4 sloučené a 21 otevřených. Strojově čitelný úplný seznam včetně tehdejších commitů je v [docs/upstream-prs.json](docs/upstream-prs.json).

## Co z jednotlivých PR ovlivnilo tyto dva skilly

| PR Rodokmenu | Stav při kontrole | Rozhodnutí v nových skillech |
|---|---|---|
| [#2](https://github.com/sarsonj/rodokmen-skill/pull/2) Windows, Praha, Plzeň, FTB | merged | návazné nástroje pro Prahu a Porta fontium; UTF-8 a Windows v testech; rodokmenový import FTB není potřeba |
| [#7](https://github.com/sarsonj/rodokmen-skill/pull/7) smazané osoby | merged | validátor odmítá osiřelé odkazy mezi všemi entitami, tvrzeními a zdroji |
| [#8](https://github.com/sarsonj/rodokmen-skill/pull/8) permalink a výřez | merged | důkaz vyžaduje lokátor konkrétní položky; URL prohlížeče nestačí; obrazový výřez nesmí ztratit odkaz na celek |
| [#10](https://github.com/sarsonj/rodokmen-skill/pull/10) zálohy aktualizace | merged | vlastní výzkum se ukládá mimo balík; init neexistujícího projektu nepřepisuje soubor; aktualizace balíku není aktualizace dat |
| [#13](https://github.com/sarsonj/rodokmen-skill/pull/13) celý rodinný graf | open | stabilní entity a vztahy s důkazem; rodinný strom neimplementován |
| [#19](https://github.com/sarsonj/rodokmen-skill/pull/19) domy, statistiky a tvary jmen | open | historické aliasy a GeoJSON; žádné automatické přiřazení neurčité adresy nejčastější obci |
| [#20](https://github.com/sarsonj/rodokmen-skill/pull/20) strom předků | open | čistě genealogické UI, mimo rozsah |
| [#22](https://github.com/sarsonj/rodokmen-skill/pull/22) ARON správný snímek | open | pokyn ověřit permalink snímku, rozlišit jednotku a obraz; nezaměňovat index knihy s PID snímku |
| [#23](https://github.com/sarsonj/rodokmen-skill/pull/23) významné osobnosti | open | profesní a biografické stopy jako kandidáti, nikoli důkaz shodné osoby |
| [#26](https://github.com/sarsonj/rodokmen-skill/pull/26) YAML | open | citovaný description, standardní frontmatter a validační test |
| [#28](https://github.com/sarsonj/rodokmen-skill/pull/28) pomocníci a vedlejší nálezy | open | otevřené otázky a předání výzkumu; síťový zámek sdílený procesy i přes paralelní práci |
| [#29](https://github.com/sarsonj/rodokmen-skill/pull/29) nové archivy | open | rozšíření katalogu a návodů: MZA, Litoměřice, VadeMeCum, Brno, válečné databáze; PR není vydaná verze 0.8.0, jeho klienti nejsou potichu přibalení |
| [#41](https://github.com/sarsonj/rodokmen-skill/pull/41) čas aktualizace a prostředí | open | datum přístupu u každého zdroje a přesná dokumentace prostředí; Node není potřeba |
| [#42](https://github.com/sarsonj/rodokmen-skill/pull/42) Codex / OMP | open | přenosný SKILL.md a agents/openai.yaml; žádná závislost na jediném agentovi |
| [#46](https://github.com/sarsonj/rodokmen-skill/pull/46) předávání výzkumu | open | výzkumný deník, neprohledané mezery, další krok a stav důkazů zůstávají v dossieru |
| [#47](https://github.com/sarsonj/rodokmen-skill/pull/47) archivní pokyny a opakování | open | přístupový problém není prázdný výsledek; stop po 401/403/429/503 a sdílený cooldown |
| [#48](https://github.com/sarsonj/rodokmen-skill/pull/48) Třeboň krajní dlaždice | open | přímo nerealizujeme Zoomify stitching; pro upstream Třeboň upozornění na okraje a úplnost snímku |
| [#49](https://github.com/sarsonj/rodokmen-skill/pull/49) více příběhů | open | nezávislé dossiers pro více lokalit/podniků; žádná pevná vazba na rodovou větev |
| [#52](https://github.com/sarsonj/rodokmen-skill/pull/52) Cursor | open | instalace celého přenosného skill adresáře; hostitelské prostředí volí uživatel |
| [#53](https://github.com/sarsonj/rodokmen-skill/pull/53) Windows a síťová brzda | open | Windows/POSIX OS zámky a CI; nové jádro nepřebírá shell hooky závislé na PATH/CRLF |
| [#55](https://github.com/sarsonj/rodokmen-skill/pull/55) výkon vějíře | open | genealogický vějíř mimo rozsah; export HTML bez velké JS závislosti |
| [#56](https://github.com/sarsonj/rodokmen-skill/pull/56) nginx | open | webserver a přihlašovací proxy nejsou součástí offline exportu |
| [#59](https://github.com/sarsonj/rodokmen-skill/pull/59) YAML | open | stejný námět jako #26, nezapočítán jako další funkce |
| [#60](https://github.com/sarsonj/rodokmen-skill/pull/60) cache | open | atomická cache s hashem a zámkem hostitele; cache se po získání zámku znovu ověřuje; neúplná odpověď se neukládá |
| [#62](https://github.com/sarsonj/rodokmen-skill/pull/62) vrchnost, zemské desky, mlýny | open | rozšíření metodiky a zdrojů pro mlýny/velkostatky; původní PR má jen dokumentaci, ne nový klient |

## Přímá použitelnost a hranice

Přibalení nativní klienti jsou uvedeni v README a `zdroje.py --help`. V katalogu má položka `automation: upstream` význam „specializovaný nástroj lze hledat v původním projektu“, nikoli „tento repozitář obsahuje a otestoval jeho stahovač“. Ověř přesný commit a závislosti před použitím. Hlavní nástroje:

- Rodokmen: `aron_search.py`, `aron_img.py`, `ebadatelna.py`, `portafontium.py`, `trebon.py`, `ahmp_parse.py`, `ahmp_scan.py`, `soal_zoomify.py`, `policie_prihlasky.py`, `anno.py`, `anno_snap.py`, `vyrez.py`, `ramecek.py`.
- Dějiny domu navíc: `cuzk_archiv.py`, `ipr_praha.py`, `mza.py`; `mista.py` dokládá práci s RÚIAN. Nový klient zde vrací kandidáty, nepřebírá automatickou volbu prvního výsledku.
- Otevřený PR #29: `litomerice.py`, `vademecum.py`, `mza.py`, `brno_encyklopedie.py`, `arolsen.py`, `mauthausen.py`, `obeti.py`, `vezni.py`, `matricula.py`. Tyto návrhy mají oddělené síťové řízení; před větší sérií vyžadují samostatné ověření.
- Paměť rodu: datový kontrakt a `tools/mza-crop.js` jako inspirace pro vazbu snímku na důkaz; ukázková genealogie se nepřebírá jako skutečná data.

Pro klienty v upstreamu platí jejich vlastní licence a omezení. Soubory `reference/playbook.md` Rodokmenu a Dějin domu mají výslovnou licenční výjimku a do těchto repozitářů se nekopírují. Nepřebíráme ani externí fonty, obrázky, mapové dlaždice nebo historické skeny. Odkaz a metadata zdroje neposkytují licenci k jeho plné reprodukci. MIT těchto repozitářů se vztahuje na nový kód a vlastní dokumentaci, nikoli na cizí podklady.
