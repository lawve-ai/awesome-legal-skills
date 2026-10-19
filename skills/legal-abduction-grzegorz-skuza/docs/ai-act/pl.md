# Dokumentacja wdrażającego — PL, preview v1

Wersja dokumentu `deployer-preview/1`; związana z kodem i SHA-256 manifestu
bundle, nie z deklaracją zgodności. **Ocena prawna i kwalifikacja nie zostały
wykonane.** Q10 (rola dostawcy), Q11 (licencja), Q12 (exhibit/etyka),
LEGAL_VERIFICATION pozostają otwarte. Nie potwierdzamy numerów ani terminów
nowelizacji przywołanych w PRD.

## Przeznaczenie i granice

Wsparcie pełnomocników, obrońców i compliance w analizie dokumentów i
konkurencyjnych wyjaśnień ograniczonego zdarzenia. Preview tylko dla
realistycznych spraw syntetycznych. Planowane konteksty `internal_employee`
i `law_enforcement` uruchamiają zabezpieczenia wysokiego ryzyka; sama bramka
nie upoważnia do wdrożenia. Sąd, arbitraż i ADR (`judicial`) są wyłączone.
Raport strony nie jest narzędziem sądu, ustaleniem lub opinią biegłego.
Zakazane są oceny osób, winy, wiarygodności, skłonności i przyszłego zachowania.

## Instrukcja i zgoda

Stosuj [instrukcję](../usage.pl.md). Człowiek wybiera profil, jurysdykcję,
podstawę użycia i `model_processing`. Przy forbidden/braku zgody na A/B
trzeba przerwać pracę i przejść na C poza sesją, nie tylko ustawić `none`.
Wdrażający przyjmuje dokumentację przez własne `deployer_ack` w `case.json`
dla kontekstów wysokiego ryzyka. Agent nie może go nadać ani uznać za
ocenę zgodności. Brak ack → `E_HIGH_RISK_ACK`; judicial →
`E_CONTEXT_UNSUPPORTED`. Nie udzielono tu żadnego ack.

## Nadzór, logi i ograniczenia

H jest propozycją, O rzeczywistą oceną człowieka poza agentem. Triage,
próba, budżet i tempo recenzji nie mogą być omijane. Domyślne lokalne A ma
`human_via_agent`; `human_file` wymaga zaobserwowanej odmowy zapisu.
Klasy podpisu/roli są przyszłe P1. Raport pokazuje udział klas, hasze,
wersję kodu, głowę łańcucha i braki. Logi/provenance pozwalają odtworzyć
kroki, ale pełna kompletność dziennika i testy na realnych hostach są
niezamknięte (m.in. czas kroków w aktualnej implementacji).

Hash dowodzi zgodności bajtów, nie autentyczności. SQLite z dostępem do dysku
nie jest tamper-proof. Instrukcje w źródłach są danymi, jednak ryzyko
wstrzyknięcia wymaga testów agentowych. OCR, znaczenie, predykcje, pokrycie
i brak Raportu ograniczają ocenę. Nie ma dowodu kosztu ani skuteczności.

Wdrażający z prawnikiem ocenia obowiązki ochrony danych, tajemnicy,
kwalifikacji, nadzoru i przechowywania logów według obowiązującego prawa.
Pakiety/propozycje zawierają tekst; `.lacase` bez oryginałów nie jest anonimowy.
Nie przesyłaj ich w telemetrii. Retencja/purge to P1, nie automatyczna kasacja
w preview. [Profil prawny](../../references/legal-profile.md) to kolejka
do urzędowej weryfikacji, nie jej wynik.
