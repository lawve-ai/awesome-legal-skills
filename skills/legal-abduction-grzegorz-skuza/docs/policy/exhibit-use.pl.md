# Polityka użycia raportu w postępowaniu (profil `exhibit`) — wersja robocza 1

> **Tekst roboczy do czasu rozstrzygnięcia Q12.** Skopiowano normatywną treść z PRD v1.0 (sekcja „Polityka użycia raportu w postępowaniu”). Nie jest to potwierdzenie statusu prawnego raportu, opinia prawna ani zgoda na publikację; ocena statusu prawnego i zasad etyki zawodowej należy do człowieka (Q12).

Identyfikator wersji polityki: `exhibit-use/1-working`.

**Raport w profilu `exhibit` może być załącznikiem do pisma procesowego jako materiał strony — nie jako opinia biegłego, ustalenie faktów ani miara prawdopodobieństwa.** Polityka wiąże użytkownika; skill egzekwuje jej część techniczną (R17).

## Status raportu (ocena robocza, do potwierdzenia — Q12)

- **Postępowanie cywilne.** Raport podpisany przez pełnomocnika jest dokumentem prywatnym (art. 245 k.p.c.): dowodzi, że podpisujący złożył zawarte w nim oświadczenie. Sąd ocenia go swobodnie (art. 233 § 1 k.p.c.). Nie jest opinią biegłego (art. 278 k.p.c.), a porządek hipotez nie jest domniemaniem faktycznym (art. 231 k.p.c.).
- **Obowiązek prawdy.** Art. 3 k.p.c. każe dawać wyjaśnienia zgodnie z prawdą i bez zatajania. Stąd zakaz cichego wyciągu: pominięcie hipotez lub ocen musi być jawne.
- **Postępowanie karne.** Obrońca lub pełnomocnik może złożyć raport jako dokument z wnioskiem dowodowym; organ ocenia go swobodnie (art. 7 k.p.k.). Raport wytworzony na potrzeby organu ścigania podlega trybowi wysokiego ryzyka (R12), a raport dla sądu jest w v1 wyłączony.

## Zasady

1. **Źródło.** Załącznikiem może być wyłącznie wynik `la.py report --profile exhibit`. Hasz raportu trafia do pakietu odtworzeniowego; ręczna edycja treści merytorycznej po renderze odbiera mu status `exhibit`.
2. **Odpowiedzialność.** Raport zawiera oświadczenie odpowiedzialnego prawnika: przejrzał podstawy wniosków, zna ograniczenia metody i przedstawia raport jako stanowisko strony. Skill zostawia pole puste; wypełnia je człowiek.
3. **Ujawnienie metody.** Nagłówek podaje nazwę i wersję skilla, model, poziom hosta, datę, udział klas dowodu oraz zdanie, że raport nie zawiera ustaleń faktycznych ani prawdopodobieństw.
4. **Kompletność.** Raport obejmuje pełny zestaw hipotez i macierz dla zadanego pytania. Wyciąg jest dopuszczalny tylko jako jawny: liczba pominiętych rekordów, `approved_set_hash` pełnej analizy i powód pominięcia (np. tajemnica, dane osób trzecich).
5. **Statusy na początku.** `unstable` lub `underdetermined` stoją w pierwszym akapicie. Porządku hipotez nie przedstawia się jako szansy, wiarygodności ani stopnia udowodnienia.
6. **Nadzór.** Podstawy raportu mają klasę `human_file`, `human_signed` lub (P1) `human_role`. Raport z `human_via_agent` nie jest załącznikiem.
7. **Dane i tajemnica.** Przed złożeniem prawnik ocenia, czy cytowane fragmenty nie ujawniają danych osób trzecich ani informacji objętych tajemnicą ponad potrzebę. Narzędziem jest jawny wyciąg z pkt 4.
8. **Odtwarzalność.** Do raportu dołącza się manifest haszy i informację, że pakiet odtworzeniowy (`.lacase` bez oryginałów + wersja kodu) zostanie udostępniony na żądanie sądu lub strony przeciwnej. Oryginały — według reguł postępowania.
9. **Zakazy.** Nie przedstawia się raportu jako opinii biegłego ani „opinii prywatnej”; nie używa się go jako narzędzia sądu lub sądu polubownego; nie łączy się go z ocenami osób fizycznych spoza raportu.
10. **Wersjonowanie.** Zmiana polityki = nowa wersja szablonu `exhibit`; raport podaje wersję, według której powstał.

Obowiązki wynikające z zasad etyki zawodowej adwokatów i radców prawnych co do ujawniania użycia narzędzi AI w pismach — Q12 (nierozstrzygnięte).
