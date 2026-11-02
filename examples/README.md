# Tři doložené příklady a nová zadání

Příklady jsou malé, skutečné rešerše, které mají ukázat práci s důkazy. Nevytvářejí dojem úplných dějin tří zkoumaných míst. Výchozím podkladem byly otevřené texty konkrétních institucí; každý použitý záznam má URL, datum přístupu, locator a záznam omezení.

| Soubor | Obsah | Zdrojové instituce |
|---|---|---|
| `uhersky-brod.json` | 4 entity, 6 tvrzení, 2 události; opevnění, půdorys a parky | NPÚ, městské informační centrum, MMR/DotaceEU |
| `most.json` | 2 entity, 6 tvrzení, 3 události; lom a jezero, 1 rozpor | DIAMO; dva záznamy stejné instituce, nikoli dva nezávislé prameny |
| `rozmberk.json` | 5 entit, 4 tvrzení, 4 události; ochrana mokřadů, povodeň a následné úpravy vodní soustavy | Povodí Vltavy (zpráva na DIBAVOD/VÚV TGM), registr AOPK a odborný časopis Ochrana přírody |

Hotové čitelné přehledy: [Uherský Brod](uhersky-brod.md), [Most](most.md), [Rožmberk](rozmberk.md). Samostatné soubory [uhersky-brod.html](uhersky-brod.html), [most.html](most.html) a [rozmberk.html](rozmberk.html) lze po stažení otevřít v prohlížeči.

Žádný příklad neobsahuje soukromé rodinné údaje. Geometrie nebyly doplněny, protože nebylo provedeno mapové ověření. To je součást předvedeného postupu: geometrie má být doložený výsledek, ne povinná ozdoba.

## Reprodukuj výstup

Z kořene repozitáře. Veřejné příklady exportuj bez `--public`, aby ve výstupech zůstaly rozsah rešerše, badatelský deník a další kroky:

```bash
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/uhersky-brod.json
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/most.json
python3 skills/pamet-krajiny/scripts/badatel.py validate examples/rozmberk.json
python3 skills/pamet-krajiny/scripts/badatel.py render examples/uhersky-brod.json --format html --out uhersky-brod.html
python3 skills/pamet-krajiny/scripts/badatel.py render examples/uhersky-brod.json --format markdown --out uhersky-brod.md
python3 skills/pamet-krajiny/scripts/badatel.py render examples/most.json --format html --out most.html
python3 skills/pamet-krajiny/scripts/badatel.py render examples/most.json --format markdown --out most.md
python3 skills/pamet-krajiny/scripts/badatel.py render examples/rozmberk.json --format html --out rozmberk.html
python3 skills/pamet-krajiny/scripts/badatel.py render examples/rozmberk.json --format markdown --out rozmberk.md
```

HTML zobrazuje chronologii a tvrzení s citacemi. Zkopírování příkladu do jiné obce nestačí: nový výzkum musí vybrat odpovídající prameny a ověřit jejich obsah.

## Co zkontrolovat při čtení

V Uherském Brodě jsou **Tyršovy sady** a **park v severní části města uváděný NPÚ** samostatné entity. Použitá citace neopravňuje jejich automatické sloučení. Úřední záznam projektu zachycuje plán a evidované období; skutečnou podobu dokončeného díla je třeba ověřit jinde.

V Mostě se dvě stránky DIAMO rozcházejí v údaji o ploše jezera. Záznam uchovává obě hodnoty jako `disputed` a nabízí další ověření. Tvrzení o ukončení těžby, začátku napouštění a dosažení provozní hladiny zůstávají oddělená.

Rožmberk vznikl při nezávislém průchodu skillu. Odděluje rybník, přírodní rezervaci, hráz a dělicí jezy. Datum vyhlášení rezervace nedatuje vznik mokřadů. Záznam o povodni vychází z původní zprávy Povodí Vltavy, zatímco tvrzení o následných opravách a modernizaci mají stav `supported`, protože vycházejí z odborného přehledu bez kontroly stavební dokumentace.

## Pokračuj praktickým bádáním

Pro Brod dohledat datované mapy a snímky, vymezit jednotlivé parky a otevřít příslušné městské fondy. Pro Most dohledat geometrie starších těžebních stavů a technický podklad k rozloze jezera. Pro Rožmberk porovnat datované mapové podklady a dohledat původní dokumentaci provedených oprav. Aktuální dostupnost a obsah těchto navazujících pramenů příklady zatím neověřují.

Další [zadání pro všech 14 krajů](overeni-prenositelnosti.md) slouží k nezávislému vyzkoušení skillu. Jejich uvedení není záznam provedených rešerší.
