# Práce v repozitáři

Zachovej celostátní použitelnost skillu. Názvy míst v příkladech nesmějí být pevnou podmínkou kódu. Každé faktické tvrzení v příkladu naváž na otevřený zdroj a konkrétní lokátor. Nezaměňuj plán hledání, úspěšný HTTP požadavek a ověření historického obsahu.

Spouštěj `python -m unittest discover -s tests -v` a `python tools/verify.py`. Běžné testy nesmějí potřebovat síť ani přihlašovací údaje. Živé ověření prováděj jednotlivými malými dotazy přes `HttpClient`, se zachováním cache, časových odstupů, podmínek zdroje a stop stavů. Přihlášení a omezení automaticky neobcházej.

Společné runtime skripty a katalog zdrojů mají sourozenecký repozitář; při jejich změně uveď kompatibilitu datového formátu a přenes opravu i tam. Nekopíruj licenčně vyňaté upstream playbooky. Případová data ukládej mimo balík skillu. Veřejný filtr je pomoc k redakci, ne automatická anonymizace.
