# Návaznost na existující projekty a PR

Tento skill používá vlastní obecný JSON model a malé samostatné nástroje. Původní projekty nabízejí další archivní klienty a zkušenosti; jejich instalace není nutná pro zdejší offline evidenci a export. Před spuštěním nástroje z jiného repozitáře ověř jeho současnou nápovědu, závislosti a síťové chování.

## Co má smysl připojit

| Projekt / nástroj | Vhodné použití | Co ověřit |
|---|---|---|
| [Dějiny domu – `cuzk_archiv.py`](https://github.com/vzoha/dejiny-domu-skill/blob/240bed4ddf2490ebb59f31aad50c1a0e2dc67648/skills/dejiny-domu/tools/cuzk_archiv.py) | Dohledání listů a rastrů katastrálních map | Vybranou lokalitu, druh mapy, datování a podmínky konkrétní služby |
| Dějiny domu – [`mista.py`](https://github.com/vzoha/dejiny-domu-skill/blob/240bed4ddf2490ebb59f31aad50c1a0e2dc67648/skills/dejiny-domu/tools/mista.py) | Současná adresa, katastr, okolí | Kandidáty kontrolovat ručně; první geokódovaný výsledek není důkaz historické identity |
| Dějiny domu – [`ipr_praha.py`](https://github.com/vzoha/dejiny-domu-skill/blob/240bed4ddf2490ebb59f31aad50c1a0e2dc67648/skills/dejiny-domu/tools/ipr_praha.py) | Srovnatelné mapové výřezy v Praze | Skutečné pokrytí jednotlivých vrstev; nepoužívat mimo Prahu |
| Rodokmen/Dějiny domu – Třeboň, ARON, eBadatelna, Porta fontium | Kroniky, knihy, sčítání a další archiválie podle portálu | Katalogové zařazení, správný snímek a jeho trvalý odkaz |
| [Paměť rodu – datový kontrakt](https://github.com/thejanhromek/pamet-rodu/blob/d40b6512efb247859773f4cd4e273a1299d26f22/docs/data-contract.md) | Oddělení osoby, místa, tvrzení, dokladů, konfliktů a badatelských úkolů | Formáty nejsou automaticky kompatibilní; přenos vyžaduje mapování ID a citací |
| [Dějiny podniku a řemesla](https://github.com/dnesdan/dejiny-podniku-a-remesla) | Mlýn, továrna, huť, pivovar, lom či dílna v krajině | Oddělit areál, právní subjekt, provozovatele a vlastníka pozemku |

Konkrétní soubor ve výše připnutém snapshotu znamená existující implementaci v tomto snapshotu, nikoli zde provedenou zkoušku všech jeho internetových operací.

## Podněty z PR Rodokmenu

Stav auditu je 2. listopadu 2026. Otevřený PR nejprve zkontroluj; jeho číslo není verze vydaného produktu.

- [#22](https://github.com/sarsonj/rodokmen-skill/pull/22): správný permalink snímku ARON. Při přenosu vždy ověř, že odkaz ukazuje skutečně citovaný snímek.
- [#29](https://github.com/sarsonj/rodokmen-skill/pull/29): rozšířené archivní klienty a další databáze. Použij konkrétní relevantní nástroj až po sjednocení limitů a ověření; neinstaluj celý otevřený návrh jen kvůli jednomu zdroji.
- [#46](https://github.com/sarsonj/rodokmen-skill/pull/46) a [#47](https://github.com/sarsonj/rodokmen-skill/pull/47): předávání výzkumu a chování při nedostupných archivech. Zde se odrážejí v deníku, otevřených otázkách a šetrném síťovém klientu.
- [#48](https://github.com/sarsonj/rodokmen-skill/pull/48): skládání okrajových obrazových dlaždic. Před čtením skenu ověř úplnost obrazu; chybějící pruh není prázdný obsah archiválie.
- [#53](https://github.com/sarsonj/rodokmen-skill/pull/53) a [#60](https://github.com/sarsonj/rodokmen-skill/pull/60): přenositelné omezování rychlosti a cache. Souběžní agenti musí sdílet stav hostitele, nestačí nezávislé pauzy.
- [#62](https://github.com/sarsonj/rodokmen-skill/pull/62): vrchnostenské prameny, zemské desky a mlýny. Jde o metodický podnět, nikoli hotové API všech mlýnů.
- [#19](https://github.com/sarsonj/rodokmen-skill/pull/19): objekty a mapová prezentace. Geometrii je však nutné spojit s prokázanou identitou, ne s nejčastější obcí v datech.

Úplný audit všech PR a přesný původ komponent je veden v dokumentaci repozitáře. Není třeba přebírat vizualizace rodokmenu nebo genealogický datový model, které zdejší otázku neřeší.

## Licence a bezpečný přenos

[Rodokmen](https://github.com/sarsonj/rodokmen-skill/blob/2b657135f9dbe6843cc7515883252ad799fb40c9/LICENSE) a [Dějiny domu](https://github.com/vzoha/dejiny-domu-skill/blob/240bed4ddf2490ebb59f31aad50c1a0e2dc67648/LICENSE) mají výjimku pro `playbook.md`. Tyto příručky sem nekopírovat pod označením MIT. Při převzetí kódu uchovat požadované autorské a licenční údaje. Licence programu nikdy neuděluje práva k mapám, skenům a fotografiím, které program získá.

Připojený archivní klient nesmí obcházet zdejší zastavení při odmítnutém přístupu. Neexportuj přihlašovací cookies ani DNNT obsah do veřejného výzkumného balíčku.
