# legal-abduction — instrukcja użytkownika PL, preview v1

## Co robi i czym różni się od jednego promptu

Skill prowadzi agenta przez wersjonowany proces: zamrożone źródła → dosłowne
cytaty z lokalizatorami → propozycje → recenzja człowieka → konkurencyjne
hipotezy, macierz, luki i testy rozróżniające. Skrypt wykonuje kontrole
deterministyczne; model proponuje treść; człowiek ocenia i zatwierdza poza agentem.

Jednorazowy prompt może dać dobry opis, ale sam nie zapewnia walidatora,
oddzielnej kolejki propozycji, kontroli cytatu, łańcucha integralności, rodzin
źródeł, budżetu recenzji czy aktualizacji delta. Skill dostarcza te mechanizmy
i trwałą instrukcję ich użycia. To **przewaga konstrukcji**, nie jeszcze dowód
lepszej jakości lub niższego kosztu. Model może się mylić, instrukcja może być
pominięta przez host, a agent z dostępem do dysku może manipulować bazą.
Ocena porównawcza jest [zaproponowana i uruchamialna](evaluation/protocol.md);
nie przeprowadzono jeszcze eksperymentu skill kontra goły LLM.

**Tylko realistyczne sprawy syntetyczne w tym preview.** Nie wkładaj akt,
danych osobowych, sekretów ani wyników do katalogu skilla.

## Start

1. [Zainstaluj](installation.pl.md), sprawdź wersję Python >=3.12 i aktywację.
2. Przed otwarciem akt wybierz PL/EN, pytanie, okres, zakres, jurysdykcję, cel,
   perspektywy i kontekst. Profil oraz zgoda pochodzą od człowieka.
3. Jeśli `model_processing` jest forbidden lub nie podano go na A/B, przerwij
   analizę w sesji. Człowiek musi uruchomić C/`none` poza sesją agenta;
   samo `--model-id none` w agencie nie wystarczy.
4. `init` i `doctor` dla zewnętrznego katalogu sprawy, jawne pliki do `ingest`,
   następnie `extract`, `families`. Nie instaluj PDF/OCR; `needs_text`
   wymaga jawnej pochodnej i przeglądu. Przerwanie wznawialnego kroku:
   globalne `--resume` przed komendą, przy niezmienionych wejściach.
5. Według [mapy poleceń](../references/workflow.md) przygotowuj propozycje,
   eksportuj recenzję, czekaj na rzeczywistą decyzję człowieka, importuj ją.
   Agent nie jest recenzentem. Cytat jest wycinkiem Passage i pozostaje dosłowny.
6. Wybierz obserwacje, przeprowadź udokumentowane poszukiwania, hipotezy
   alternatywne, macierz i plan testów. Porównanie czyta tylko zatwierdzone rekordy.

## Jak czytać wynik

- `partial` / incomplete: braki ocen lub materiału; brakująca para to
  `not_assessed`, nie neutralna.
- `underdetermined`: materiał/reguły nie wyznaczają jednego wyjaśnienia;
  remis nie jest rozstrzygany po ID.
- `unstable`: lider zmienia się po pominięciu rodziny źródeł.
- Porządek profilowy nie jest sumą punktów, prawdopodobieństwem lub oceną osoby.
- SHA-256 wiąże bajty; nie dowodzi autentyczności, autorstwa ani daty.
  Integralność jest wykrywalna, nie „tamper-proof”.
- Domyślny lokalny host A ma `human_via_agent`. Silniejszej klasy nie można
  nadać deklaracją; wymagany jest rzeczywisty kanał i kontrola `doctor`.
- Budżet i triage służą nadzorowi: klasa I pojedynczo, klasa II z próbą.
  Błąd w próbie eskaluje partię; nie omijaj odmowy budżetowej.

Raport `working` służy roboczej analizie. `exhibit` ma ostrzejsze bramki,
ale jego status prawny i etyczny jest **nierozstrzygnięty**:
[polityka robocza](policy/exhibit-use.pl.md). To materiał strony, nie narzędzie
sądu/ADR, ustalenie faktów ani opinia biegłego. Oświadczenie prawnika wypełnia
człowiek. Preview nie upoważnia do składania raportów w postępowaniu.

## Aktualizacja i ciągłość

`update run` przetwarza nowy/dotknięty materiał; stare zatwierdzenia pozostają,
rekordy stale wymagają ponownej oceny. Lista `revisit` (oraz `update revisit`) wskazuje
każdą wcześniejszą ocenę do ponownego rozważenia, jej dotychczasową treść i zmianę, która
ją podważyła. Gdy powiesz agentowi, że twierdzenie lub obserwacja zostały wycofane,
skorygowane albo znów obowiązują, zapisze to przez `update withdraw|change|reinstate`
z Twoim uzasadnieniem. Oznaczane są tylko wyjaśnienia, których ocena tego faktu brzmiała
supports/conflicts; komórki wycofanego faktu przestają się liczyć; zamiennik skorygowanego
faktu trzeba ocenić. O każdej oznaczonej ocenie decydujesz w pliku ponownej oceny; agent
go nie wypełnia. Skutki możesz obejrzeć przed decyzją: `--dry-run` pokazuje, co zostałoby oznaczone,
unieważnione i do oceny, i niczego nie zapisuje.
Te zmiany mają klasę `human_via_agent` i blokują profil `exhibit`.
Nie edytuj SQLite ani triggerów.
Na host B przed końcem sesji `status --session-end`, `case export`, pobierz
pacz­kę `.lacase`; w kolejnej sesji import do świeżego katalogu. Paczka może
zawierać poufną treść także bez oryginałów. Nie myl jej z instalacyjnym ZIP.
Na B nie obiecujemy G2.

## Ograniczenia i bramki

[Dokumentacja wdrażającego](ai-act/pl.md), [profil prawny](../references/legal-profile.md)
i [bramki dystrybucji](distribution.md) opisują Q10/Q11/Q12, brak Raportu,
LEGAL_VERIFICATION oraz późniejsze testy i pomiary. Predykcje i znaczące pokrycie
pozostają częściowo nieokreślone. PostgreSQL, API, solver, scoring, podpisana
recenzja, MCP/DMS to przyszłe P1/P2, nie gotowe funkcje preview.
Zgłaszaj faktyczne błędy i odmowy, nie zamieniaj ich na narrację „sukcesu”.

## Dokumenty i historia odrzuceń (0.3.0)

Plan testów wskazuje niepewność, konkretny dokument lub jego typ, podstawę
wskazania i następne działanie człowieka. Dokument obecny w korpusie,
wzmiankowany i niepozyskany oraz dokument o niepotwierdzonym istnieniu mają
odrębne oznaczenia. Starsze testy zachowują jawne braki; testy niezgodne
z aktualnym zakresem wymagają ponownej oceny. Nowe pakiety stosują
`task_tests/v2`; opis pól znajduje się w [workflow](../references/workflow.md).

Eksport recenzji zawiera osobną historię odrzuceń z dokładną ocenioną wersją,
źródłem i uzasadnieniem człowieka. Nie wypełniaj decyzji w historii. Raport
zawiera tabelę zatwierdzonych działań i załącznik audytowy całej sprawy.
Odrzucone treści nie uczestniczą w analizie. Czas importu nie jest czasem
decyzji; brakujące dane historyczne pozostają widoczne.
