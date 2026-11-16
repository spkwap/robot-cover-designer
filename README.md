# Industrial Robot Protective Cover Designer

Aplikacja webowa do projektowania pokrowców ochronnych na roboty: dane robota → środowisko → **jeden** materiał → konstrukcja →
wykroje (PDF 1:1 / DXF / SVG) → zużycie materiału → nić/igła/maszyna → BOM → dokumentacja produkcyjna → walidacja (zielony/żółty/czerwony).

## Uruchomienie
    ./run.sh            # http://127.0.0.1:8000   (Python 3.10+)
    python3 -m pytest tests   # 25 testów obliczeń i API
Przycisk „Otwórz projekt demonstracyjny” ładuje FIKCYJNEGO robota 6-osiowego (wymiary poglądowe).

## Architektura (moduły = pliki w rcd/engines)
| Moduł | Plik |
|---|---|
| Dane robotów / baza | `data/catalog.py`, `db.py` |
| Geometria (obwody, kinematyka planarna, przemiatanie kolizji) | `geometry.py` |
| Analiza środowiska (61 czynników, pytania uzupełniające) | `environment.py` |
| Dobór materiału | `materials.py` |
| Konstrukcja (moduły, plisy harmonijkowe, zakładki, zapięcia) | `construction.py`, `sewing_base.py` |
| Wykroje | `pattern.py` |
| Rozmieszczenie na beli + zużycie | `nesting.py` |
| Szycie, maszyny, dodatki, BOM | `sewing.py` |
| Walidacja | `validation.py` |
| Dokumentacja + eksporty | `documentation.py`, `export/` |
Backend: FastAPI + SQLite. Frontend: czysty JS (bez builda), PL/EN. Cała logika liczbowa jest deterministyczna.

## Zasady dotyczące danych (ważne)
* Żaden rekord bazy NIE pochodzi z karty TDS/SDS konkretnego produktu. Wszystkie mają `confidence: typical/unverified`
  (zakresy typowe dla rodziny materiałowej). Dlatego walidacja materiału daje najwyżej ŻÓŁTY.
* Status `verified` ustawia się w module „Baza danych” – API odrzuca go bez `tds_url`/`source_document`.
* Wartości potwierdzone przez dostawcę (gramatura, grubość, skurcz) wpisuje się w „Dobór materiału”; nadpisują zakresy typowe w obliczeniach.
* Roboty w bazie: tylko zasięg/udźwig/osie (niezweryfikowane), bez wymiarów segmentów – te wprowadza użytkownik.

## Znane ograniczenia wersji 1
* Brak pobierania danych z internetu (dokumentacja producentów) – wyszukiwanie tylko w lokalnej bazie.
* Import 3D: STL/OBJ/DXF → tylko prostopadłościan otaczający (informacyjnie). STEP – tylko zapis pliku (wymaga jądra CAD).
* Kolizje: model PŁASKI (osie zginane współpłaszczyznowe, segmenty jako kapsuły) – badanie przesiewowe, nie zastępuje próby 3D.
* Nesting po prostokątach otaczających (wynik zachowawczy); stożki dzielone na sektory wg szerokości beli; otwory w stożkach nie są układane automatycznie.
* Wizualizacja jest schematyczna (opisana tak w UI), nie jest modelem CAD.
* Asystent tekstowy środowiska działa słownikowo (bez LLM) i tylko sugeruje.
* Baza projektów: SQLite (warstwa `db.py` odizolowana; PostgreSQL = podmiana repozytorium).
* Pokrowiec to wyposażenie dodatkowe maszyny: wymagana ocena ryzyka i próby na stanowisku; aplikacja nie deklaruje zgodności z normami.

## Import danych z dokumentu / internetu (Baza danych → „Import…”)

* Wgraj PDF/HTML/TXT karty katalogowej (TDS) **lub** podaj URL. Aplikacja wyciąga tekst (pypdf / pdftotext) i proponuje wartości:
  materiał — gramatura, grubość, zakres temperatur, wytrzymałość N/50 mm, szerokość beli, wymienione normy (jako deklaracje);
  robot — zasięg, udźwig, liczba osi, masa, powtarzalność.
* Każda propozycja ma **cytat z dokumentu**; do bazy trafia tylko to, co zaznaczysz (wartości można poprawić). Tylko te pola dostają status
  „zweryfikowane" (`verified_fields`), rekord ma status „częściowo z dokumentu"; reszta pozostaje „typowa". Dokument jest zapisywany w `var/docs/` z SHA-256.
* Oceny odporności chemicznej (0–3) **wpisuje użytkownik** na podstawie tabel w dokumencie — nie są wyciągane automatycznie.
* Rekord można zapisać jako nowy produkt (rodzina materiałowa pozostaje bez zmian).
* Ograniczenia: ekstrakcja oparta na wyrażeniach regularnych (nie AI) — zawsze sprawdź cytat; skany/obrazy wymagają OCR (niewspierane);
  pobieranie z URL wymaga dostępu sieciowego serwera; adresy prywatne/loopback są blokowane (`RCD_ALLOW_PRIVATE_URLS=1` zmienia to na zaufanym hoście);
  wyłącznie http/https, max 3 przekierowania, limit 30 MB. Normy wymienione w dokumencie nie oznaczają, że aplikacja deklaruje zgodność.
