# Mapy, ortofota a geometrie

## Vyber podklad podle otázky

| Podklad | Co může pomoci zjistit | Co sám neurčuje |
|---|---|---|
| Stabilní katastr a jeho písemné operáty | Parcely, půdorysy, dobové využití ploch, místní názvy | Automatickou shodu dnešního a historického parcelního čísla |
| Vojenské a topografické mapy | Síť cest, sídla, vody, terén a větší provozy | Přesný půdorys drobného objektu nebo každou změnu v roce vydání |
| Letecký měřický snímek | Vzhled povrchu v konkrétním okamžiku | Bez ortorektifikace přesnou polohu na moderní mapě |
| Ortofoto | Srovnání pokryvu a objektů při známé přesnosti a místním datu | Funkci budovy, vlastníka ani příčinu změny |
| DMR 5G / odvozený stínovaný reliéf | Terénní tvary, které stojí za další ověření | Stáří, původ ani bezpečnost terénního útvaru |
| Lesní, vodní, báňský nebo regulační plán | Tematické členění a zamýšlené zásahy | Automaticky realizaci navrženého stavu |

Začni v [Archivu ČÚZK](https://ags.cuzk.gov.cz/archiv/) a ověř druh podkladu v [popisu ÚAZK](https://www.cuzk.gov.cz/Urady/Zememericky-urad/Dalsi-informace/UAZK/Prohlizeni-archivalii,-archivni-mapy.aspx). Další listy a edice hledej přes [MZK](https://www.mzk.cz/katalogy-zdroje/mapy-v-mzk), [Mapseries](https://mapseries.mzk.cz/) a [VÚGTK](https://www.vugtk.cz/virtualni-mapova-sbirka/). Katalog není záruka volné licence ani úplného digitálního pokrytí.

## Uchovej všechna známá data mapy

Do `sources.notes` zapisuj odděleně:

```text
zamereni: rok nebo interval / nezjištěno
revize: rok nebo interval / nezjištěno
vydani: rok / nezjištěno
snimkovani: datum konkrétního snímku / netýká se
digitalizace: datum / nezjištěno
list_a_edice: katalogové označení
meritko: jmenovité měřítko původní mapy
CRS: identifikátor souřadnicového systému nebo nezjištěno
vyrez: bbox a jeho CRS, případně soubor + pixelový rámeček
georeference: původní/služba/ruční; metoda a polohová nejistota
stav: původní mapa / aktualizovaný otisk / návrh / rekonstrukce
```

Zapsání neznámé hodnoty je přijatelné. Bez potvrzeného zaměření nepřenášej datum vydání na každou budovu. V jedné mapě mohou současně zůstávat staré i aktualizované prvky.

## Historické ortofoto CENIA

[CENIA uvádí](https://cenia.gov.cz/2022/02/17/historicka-ortofotomapa-z-50-let-se-otevira/) převahu snímků 1952–1954 a doplnění z jiných let včetně roku 1996. Název vrstvy „50. léta“ proto neslouží jako jednotné datum celého území.

Vyhledej [vrstvu roků snímkování](https://geoportal.gov.cz/php/micka/record/basic/57873306-f280-43d0-9a39-3fddc0a80153), zkontroluj její aktuální metadatový záznam a překrytí s použitým rastrem. Rozděl území, pokud protíná více let. Nezaměň referenční datum aktualizace metadat s datem fotografování. Pokud vrstva rok neurčí jednoznačně, ponech neznámý nebo interval a zaznamenej rozpor.

Při publikaci použitého výřezu dodrž CC BY 4.0 a atribuci poskytovatele; přesné znění převzít z aktuálního licenčního oznámení. Licence obrázku a licence textového článku na stejném webu se mohou lišit.

## WMS, WMTS a souřadnice

1. Zjisti endpoint z oficiálních metadat, nikoli odhadováním URL. Načti `GetCapabilities` a ulož zdroj, datum přístupu a verzi.
2. Vyber skutečný `Name` vrstvy. `Title` je čitelný popisek a nemusí být použitelný v požadavku.
3. Zvol podporovaný CRS a zkontroluj jeho jednotky. Stupně WGS84 nelze vložit místo metrů S-JTSK.
4. U WMS 1.3.0 respektuj pořadí os zvoleného CRS; EPSG:4326 používá pořadí zeměpisná šířka, délka, zatímco CRS:84 délka, šířka. U WMS 1.1.1 se EPSG:4326 v bbox používá jako délka, šířka. Nespoléhej na to, že knihovna udělá transformaci či změnu os sama.
5. Zkontroluj typ odpovědi. XML chybová zpráva může mít HTTP 200; není to obraz mapy. Prázdný výřez může znamenat rozsah, měřítko či nevhodné parametry.
6. WMTS má vlastní matici dlaždic, měřítka a CRS. Neskládej dvě vrstvy jen proto, že čísla dlaždic vypadají podobně.

Autoritativní specifikace: [OGC WMS](https://www.ogc.org/standards/wms/). Zdejší adaptér popisuje možnosti služby; následnou kartografickou analýzu proveď v prostředí, které transformaci a georeferenci skutečně podporuje.

Výstupní GeoJSON tohoto skillu používá WGS84 a pořadí **zeměpisná délka, zeměpisná šířka**, viz [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946). Před exportem proveď skutečnou transformaci z jiného CRS, ne pouhé přepsání názvu systému. Zaokrouhli souřadnice podle dosažitelné jistoty a přidej `location_accuracy_m`, pokud ji lze odhadnout.

## Srovnání a georeference

Vyber trvalé kontrolní body rozložené po území: výrazné křižovatky, kostely, kamenné mosty nebo rohy doloženě dochovaných staveb. Ověř, že nebyly přesunuty či přestavěny. Kontrolní body na jediné přímce nemusí stabilizovat transformaci v celém výřezu.

Zaznamenej použité body, metodu, výslednou chybu a místo, kde už je srovnání nespolehlivé. Přesná hodnota rezidua v kontrolních bodech sama nezaručuje přesnost celé mapy. U menšího měřítka nezaměň kartografickou generalizaci se skutečným posunem cesty.

Před tvrzením o změně se ptej: vidím ji přímo, nebo pouze interpretuji značku? Je podklad dostatečně podrobný? Jde o dvě nezávislá zaměření? Znám lokální datum obou stavů? Mám jiný pramen, který vysvětluje funkci a příčinu?

Pokud neproběhlo načtení a vizuální porovnání obrazů, předej textový výzkum s plánem mapové kontroly. Nevytvářej ozdobnou „historickou mapu“ generátorem obrázků jako náhradu pramene.
