---
name: pamet-krajiny
description: "Zkoumej proměny krajiny a sídel v celé České republice z historických map, leteckých snímků, kronik, tisku a veřejných dat. Použij pro otázky, kudy vedla stará cesta, kde býval rybník, mlýn, důl nebo zaniklá obec, jak se změnila čtvrť, vodní tok, les či zemědělská krajina; vytvářej doložené časové osy, karty míst a podklady pro historickou vycházku."
---

# Paměť krajiny

Veď výzkum zvoleného místa v Čechách, na Moravě i ve Slezsku. Ptej se, **kterou změnu lze doložit, ve kterém období a s jakou polohovou jistotou**. Pracuj s jednotlivými tvrzeními a konkrétními prameny. Nespolehlivou stopu uchovej jako hypotézu.

## Začni místem a otázkou

1. Zjisti obec, katastr nebo jiné rozlišující okolí. Je-li název nejednoznačný, předlož kandidáty s okresem či souřadnicemi; první výsledek geokódování nevybírej automaticky. Když místo lze určit ze zadání, pokračuj bez zbytečných otázek.
2. Vymez území bodem s okolím, úsekem trasy nebo polygonem. Při nedostatku přesných podkladů zůstaň u popisu území; souřadnice nevymýšlej. Rozliš aktuální obec, historické sídlo, katastr a samotný krajinný prvek.
3. Sepiš dvě až pět otázek, například „Kdy náhon přestal být zobrazován a co dokládá jeho zrušení?“ Období zvol podle zadání a dostupných pramenů.
4. Najdi starší české a německé názvy, případně další jazyky. Každou variantu spoj s pramenem a dobou použití; podobný název neslučuj automaticky.

## Založ dohledatelný výzkum

Příkazy spouštěj z kořene repozitáře; v instalovaném skillu použij odpovídající absolutní cestu ke `scripts/badatel.py`.

```bash
python3 skills/pamet-krajiny/scripts/badatel.py init --title "Proměny vybraného údolí" --theme landscape --place "Obec, okres" --out vyzkum.json
python3 skills/pamet-krajiny/scripts/badatel.py plan --place "Obec, okres" --region "Zlínský kraj" --topic "náhony a staré cesty" --out plan.json
python3 skills/pamet-krajiny/scripts/badatel.py sources --theme landscape
```

`plan` připravuje návrh hledání. Jeho odkazy a dotazy nejsou provedenou rešerší ani nalezenými důkazy. `sources` vypisuje katalog zdrojů; rozsah skutečné automatizace určuje `scripts/zdroje.py --help`.

Pracuj s JSON podle [datového postupu](references/data-a-vystupy.md). Výzkumná data ukládej mimo veřejný repozitář skillu, pokud uživatel výslovně nechce veřejný výsledek.

## Vyber prameny pro celé Česko

Použij nejprve dva až tři zdroje, které odpovídají otázce; další přidávej podle zjištěných mezer.

- **Identita místa:** RÚIAN, Archiv ČÚZK, historické názvy a místní topografie.
- **Proměny povrchu:** stabilní katastr, vojenská mapování, letecké měřické snímky, historické a současné ortofoto. Ověř skutečné pokrytí území.
- **Důvod a průběh změny:** obecní a školní kroniky, vodoprávní, stavební, lesní a pozemkové spisy, noviny, odborná literatura.
- **Specializovaný kontext:** ČGS, HEIS, lesní mapy, NPÚ, AMČR, ČSÚ, ČHMÚ, muzejní sbírky; viz [tematické postupy](references/temata.md).
- **Místní prameny:** zvol archiv podle původce a fondu, s krajem jako výchozím vodítkem. Použij [celorepublikový rozcestník](references/archivy-a-zdroje.md). Brněnské a pražské portály připojuj pouze pro jejich skutečné území.

Vyhledávač a OCR používej k nalezení kandidátů. Před přijetím historického tvrzení otevři konkrétní záznam, stránku či snímek. Z katalogové anotace tvrď jen to, co anotace skutečně říká; nepopisuj obsah nepřečtené archiválie.

## Čti mapy jako pramen

Před porovnáním čti [pravidla práce s mapami](references/mapy.md).

1. U každého podkladu zaznamenej zvlášť zaměření, aktualizaci, vydání, snímkování a digitalizaci, pokud jsou známé. Rok vydání není automaticky rok terénního stavu.
2. U CENIA „50. léta“ zjisti místní rok snímkování. U mozaiky může hranice let protínat zkoumané území.
3. Zaznamenej měřítko, legendu, list, souřadnicový systém a přesný výřez. Před WMS požadavkem přečti capabilities, identifikátor vrstvy, podporované CRS a pořadí os pro zvolenou verzi.
4. Srovnávej stejnou oblast a dosažitelnou úroveň detailu. U ruční georeference zaznamenej kontrolní body, metodu a odhad chyby. Starou cestu zakresli jako nejistý koridor, když přesnou trasu nelze obhájit.
5. Nezobrazení objektu samo nedokazuje zánik. Zvaž měřítko, účel mapy, vegetaci, stín, neúplný výřez a převzaté starší podklady. Datum změny ohranič nejpozdějším spolehlivým dokladem starého stavu a prvním spolehlivým dokladem nového stavu; nejistotu výslovně uveď.

Nevydávej jazykový popis webu za vizuální prohlídku snímku. Pokud obraz nelze načíst, zaznamenej omezení a pokračuj textovými prameny.

## Přijímej nálezy a zachovej rozpory

Pro každý přijatý nález ulož:

- stabilní ID místa/prvku a samostatné ID tvrzení;
- krátké tvrzení, stav `documented`, `supported`, `hypothesis` nebo `disputed`;
- zdrojový odkaz, instituci, datum přístupu, signaturu/list/stranu/oddíl a druh důkazu;
- dobové znění nebo vlastní přepis oddělený od výkladu;
- časový interval a prostorovou nejistotu, pokud je lze určit;
- co zatím chybí a jaký další pramen by to mohl rozhodnout.

Stav `documented` znamená dohledatelný doklad konkrétního tvrzení, nikoli neomylnost pramene. Odbornou syntézu, úřední plán, dobový zápis a vzpomínku rozlišuj. Dva weby přebírající stejný text nepovažuj za dvě nezávislá potvrzení. Při rozporu uchovej obě verze a jejich kontext; nedopočítávej smyšlený kompromis. Podrobnosti obsahuje [metodika](references/metodika.md).

Zapisuj i neúspěšné hledání včetně dotazu a prohledaného rozsahu. „Nenalezeno v OCR tohoto ročníku“ nepřepisuj na „nestalo se“.

## Pracuj šetrně a podle skutečných oprávnění

Používej společnou cache a omezování požadavků z `http_client.py`. Další agent na stejném hostiteli nesmí založit nezávislou rychlou smyčku. Při 401/403/429/503 zastav stahování, popiš překážku a přejdi k jinému povolenému zdroji. Nevypínej TLS ani neobcházej přihlášení. Dávky a opakování omez na potřebné položky.

U digitálního dokumentu odděl možnost prohlížet, uložit a zveřejnit. DNNT neoznačuj za volně stažitelný obsah. U fotografií, map a komunitních příspěvků ověř práva konkrétního záznamu. Cituj i materiály, které nepřebíráš jako soubor.

## Ověř a předej výsledek

```bash
python3 skills/pamet-krajiny/scripts/badatel.py validate vyzkum.json
python3 skills/pamet-krajiny/scripts/badatel.py render vyzkum.json --format markdown --out vyzkum.md
python3 skills/pamet-krajiny/scripts/badatel.py render vyzkum.json --format html --out vyzkum.html --public
python3 skills/pamet-krajiny/scripts/badatel.py render vyzkum.json --format geojson --out mista.geojson --public
```

Předej odpověď na otázky, karty doložených míst, časovou osu, citace a otevřené otázky. Automatický export nesupluje kontrolu věcné správnosti. GeoJSON obsahuje jen doložené geometrie; prázdná mapa je poctivější než vymyšlené body. Zdejší HTML je přenosný badatelský přehled, nikoli automaticky georeferencovaná mapa „tehdy/dnes“.

Před veřejným vydáním projdi i volné texty, názvy, URL, metadata a přílohy. `--public` filtruje označené citlivé záznamy, ale samo nerozpozná všechny soukromé údaje. Výzkum nesmí bez souhlasu zveřejnit rodinné nahrávky nebo osobní kontakty. U archeologických či jinak citlivých lokalit může být vhodná jen obecná poloha.

Navrhne-li uživatel historickou vycházku, sestav seznam zastavení s důkazy a zvlášť ověř aktuální veřejnou průchodnost. Historická cesta ani mapa nejsou oprávněním vstupu.

## Návaznost a příklady

Pro konkrétní dům navazuj na **Dějiny domu**, pro doložené obyvatele na **Rodokmen/Paměť rodu**, pro výrobní areál na **Dějiny podniku a řemesla**. Předávej ID, citace a nejistoty; neslučuj různé entity podle stejného jména. Otevřený PR nepovažuj za vydanou funkci.

Použij [přehled návazných nástrojů](references/navaznost.md), potřebuješ-li archivní klienty původních projektů. Tyto volitelné nástroje nejsou součástí zdejšího příkazu `zdroje.py`, pokud to výslovně neuvádí jeho nápověda.

V repozitáři `examples/` jsou dva malé skutečné výzkumy: **Uherský Brod – městská struktura a zeleň** a **Most – lom a jezero**. Ukazují evidenci textových pramenů a reálný rozpor; netvrdí, že proběhla kartografická analýza všech map. Při novém území použij stejný postup a vlastní prameny.

## Nástroje a hranice získání důkazu

Před síťovým dotazem čti [přehled přibalených nástrojů](references/nastroje.md). U zdrojů zapisuj, zda byl prohlédnut jejich obsah (`verification_status`), nebo je znám pouze úryvek z indexu. Samotný úryvek nesmí být jediným podkladem tvrzení `documented` či `supported`. U geometrie zachovej strukturovaný význam bodu v `geometry_role`; neukládej toto rozlišení jen do pracovních poznámek.
