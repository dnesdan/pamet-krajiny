# Přibalené nástroje a skutečné datové operace

## Obsah

1. Dossier a výstupy
2. Identita místa a zdrojů
3. Tisk a firemní registry
4. Mapy a IIIF
5. Síťové podmínky
6. Důkazní kontrola

Příkazy níže spouštěj z kořene repozitáře. Při instalaci samotného balíku uprav předponu `skills/pamet-krajiny/` podle umístění jeho `SKILL.md`. Výzkumné výstupy ukládej mimo instalovaný balík. Python 3.10+; provozní kód nemá závislosti mimo standardní knihovnu.

## 1. Dossier a výstupy

```bash
python3 skills/pamet-krajiny/scripts/badatel.py --help
python3 skills/pamet-krajiny/scripts/badatel.py validate work/vyzkum.json
python3 skills/pamet-krajiny/scripts/badatel.py render work/vyzkum.json --format html --out work/vyzkum.html
python3 skills/pamet-krajiny/scripts/badatel.py render work/vyzkum.json --format geojson --out work/vyzkum.geojson --public
```

`init` založí prázdný projekt, nikoli smyšlené nálezy. `validate` kontroluje strukturu a vazby, nikoli historickou pravdivost. `plan` připravuje prioritizované dotazy a rezervní zdroje; nic nevyhledává automaticky. `sources` vypíše úplný katalog. `render` neprovádí žádné síťové požadavky. HTML je samostatné, bez externích skriptů; odkazované prameny samozřejmě potřebují internet.

Pro nejednoznačné tematické zadání použij explicitní `plan --theme landscape` nebo `--theme enterprise`. Aktuální nápověda obsahuje i omezení délky prioritního seznamu. `--public` odstraňuje označené citlivé záznamy a závislé vazby; nepozná citlivost neoznačeného textu. Veřejný export proto vždy přečti.

## 2. Identita místa a zdrojů

```bash
python3 skills/pamet-krajiny/scripts/zdroje.py registry --out work/knihovny.json
python3 skills/pamet-krajiny/scripts/zdroje.py registry --code mzk
python3 skills/pamet-krajiny/scripts/zdroje.py ruian --query "Horní Lhota" --kind municipality --out work/kandidati.json
python3 skills/pamet-krajiny/scripts/zdroje.py ruian --query "Uherský Brod" --kind cadastral
```

`registry` čte oficiální seznam instancí Krameria, nikoli pevný seznam několika knihoven. Záznamy mohou obsahovat staré i nové instance, zahraniční sbírky nebo výpadek. Počet instancí neznamená počet nezávislých korpusů.

`ruian` podporuje `municipality`, `part`, `cadastral`, `address`. Vrací kandidáty, kódy a dnešní atributy; `selected` zůstává `null`. U obce a katastru rozlišuje reprezentativní centroid od přesné polohy místa. Historickou adresu ani zaniklou obec automaticky nepřiřazuj k prvnímu kandidátovi. Výsledek může být zkrácen; použij `--limit` a konkrétnější dotaz. `total_count: null` je přiznaný neznámý celkový počet.

## 3. Tisk a firemní registry

```bash
python3 skills/pamet-krajiny/scripts/zdroje.py kramerius-search --library mzk --query "Uherský Brod" --rows 5 --public-only --out work/tisk.json
python3 skills/pamet-krajiny/scripts/zdroje.py ares --ico 46345965 --out work/ares.json
```

Vyhledávání Krameria použije verzi 5 nebo 7 podle registru; `--api-version` dovolí vědomou volbu po ověření serveru. Dotaz je **doslovná fráze v OCR**, nikoli libovolný Solr příkaz. Zkus pravopisné a jazykové varianty v dalších cílených dotazech. Nástroj vrací pouze metadata a odkazy, včetně samostatného názvu stránky a kořenového titulu. Nečte automaticky sken a neskládá z výsledků potvrzená historická tvrzení. `--public-only` filtruje dostupnost, ne autorská práva. Pro složité časové filtry použij oficiální klient knihovny nebo dokumentovaný odborný dotaz mimo tento malý adaptér.

ARES vyžaduje přesné osmimístné IČO včetně počátečních nul. Zjišťuje současnou evidenční identitu a údaje zdrojových registrů. Registrační datum není automaticky vznik historické továrny, řemesla nebo značky. Osobní údaje živnostníků automaticky nepřenášej do veřejného výstupu.

## 4. Mapy a IIIF

```bash
python3 skills/pamet-krajiny/scripts/zdroje.py wms --url https://gis.cenia.cz/mapcache/ortofotomapa_historicka/wms --out work/vrstvy.json
python3 skills/pamet-krajiny/scripts/zdroje.py wms-map --url https://gis.cenia.cz/mapcache/ortofotomapa_historicka/wms --layer orto --crs EPSG:5514 --version 1.1.1 --bbox=-525389,-1187795,-523789,-1186595 --width 800 --height 600 --out work/vyrez.jpg
python3 skills/pamet-krajiny/scripts/zdroje.py iiif --url https://collectiones.manuscriptorium.com/assorted/NKCR__/NKCR__/2/NKCR__-NKCR__14_J_000094_3I6VGS2-cs/ --limit 2 --out work/manifest.json
```

WMS nejprve načte capabilities a ověří vrstvu, formát a souřadnicový systém. `wms-map` stáhne jediný malý obraz a vedle něj JSON s celou URL požadavku, CRS, bbox, rozměry, datem přístupu a hashem. Kontroluje deklarovaný MIME, obrazovou signaturu a skutečné rozměry; HTML přihlašovací stránky nebo obrázek v jiném formátu nepřejmenuje na platnou mapu. Přípona `.jpg` znamená požadavek JPEG, `.png` PNG.

Výchozí bbox je `minlon,minlat,maxlon,maxlat` v EPSG:4326. Nástroj řeší prohození os WMS 1.3.0/EPSG:4326 a odlišuje CRS:84. **EPSG:5514 vyžaduje WMS 1.1.1 a nativní metry easting,northing. Reprojekce není implementována.** Záporný bbox předávej s rovnítkem jako v příkladu, aby jej argparse nezaměnil za přepínač. U jiného místa přepočítej výřez v ověřeném GIS nebo vyžádej body z poskytovatele v potřebném CRS.

IIIF podporuje manifesty Presentation API 2 a 3. Vypíše canvas ID, odkazy na obrázky/služby, dostupná práva a případné zkrácení. **Nestahuje obrazy, neprochází kolekce ani stránkované annotation pages.** Chybějící vložený obraz tedy není důkazem, že rukopis nemá snímek. Odkaz manifestu ber z poskytovatele, neodhaduj jeho ID.

## 5. Síťové podmínky

Všechny adaptéry používají stejné `HttpClient`: identifikační User-Agent, zděděnou proxy a ověření TLS, časový odstup, sdílený zámek po hostiteli, omezený počet bajtů a timeout. Úspěšná celá odpověď má atomickou cache s hashem. Výchozí cache je v dočasném adresáři daného uživatele, společná oběma skillům. Vlastní `--cache-dir` musí mít stejné umístění pro všechny spolupracující procesy; měnit jej za účelem obejití pauzy je nepřípustné.

Po 401, 403, 429 nebo 503 se požadavek neopakuje a další proces uvidí společnou pauzu. `--refresh` ruší jen použití uložené odpovědi, nikoli pauzu hostitele. Při přesměrování na jiný hostitel ověř nový oficiální cíl a použij jeho kanonickou URL samostatně. Žádné přihlašování, CAPTCHA ani režim DNNT se neobchází. Pro hromadný výzkum nejprve hledej oficiální export nebo podmínky poskytovatele.

## 6. Důkazní kontrola

Úspěšný požadavek dokládá získání dat, nikoli pravdivost interpretace. `retrieved_at` není datum historické události. Nenulové `num_found` není počet správně identifikovaných osob či nezávislých pramenů. Prázdný seznam, výpadek a neúplný index mají odlišný význam.

Ke zdroji používej `verification_status`: `content_checked`, `search_index_only` nebo `unavailable`. Výsledek vyhledávače slouží k objevení kandidáta. Dokud není příslušný obsah otevřen a prohlédnut, nepovažuj jej sám za podklad pro `documented` či `supported`; ulož stopu do deníku, mezi otázky nebo jako výslovnou hypotézu. Prohlédnutí katalogového popisu potvrzuje jeho obsah, nikoli automaticky obsah všech archiválií uvedených ve fondu.

Vlastní přesný význam bodu ukládej do `geometry_role` (`site`, `centroid`, `approximate`, `extent`, `unknown`), spolu s odůvodněnou `location_accuracy_m`. Podstatnou veřejnou mez historické identity uveď také v textu tvrzení; nespoléhej jen na pracovní `notes`, které veřejný filtr odstraní.
