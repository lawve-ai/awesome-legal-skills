# Instalacja — PL, preview v1

ZIP to **bundle ewaluacyjny**, nie publikacja ani przyznanie licencji. Q11
pozostaje otwarte; używaj tylko w autoryzowanej ocenie, nie redystrybuuj jako
wydania open source. Zanim wgrasz pliki do hosta, przeczytaj
[ograniczenia](usage.pl.md) i [bramki](distribution.md).

## Sprawdzenie ZIP i Python

Python >=3.12, tylko stdlib. Nie trzeba pip, serwera ani instalacji OCR/PDF.
PowerShell, z katalogu źródłowego `legal-abduction`:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONHASHSEED = '0'
python -B -X utf8 --version
Get-FileHash '<ZIP-preview>' -Algorithm SHA256
python -B -X utf8 scripts/package_preview.py --check '<ZIP-preview>' --smoke
```

Porównaj SHA-256 z niezależnie zachowanym wynikiem budowania; manifest wewnątrz
ZIP nie jest podpisem ani dowodem pochodzenia. Jeśli nie masz zaufanego źródła
skryptu, najpierw obejrzyj ZIP bez wykonywania zawartego kodu. Po sprawdzeniu
rozpakuj przez interfejs archiwizera do **nowego katalogu staging**, nie nadpisuj
istniejącego skilla. ZIP ma jeden katalog `legal-abduction/` z `SKILL.md` w jego
korzeniu. Kopiuj ten katalog jako całość, nie sam Markdown.

## Claude Code

W wersji obsługującej Agent Skills:

- dla projektu: `<projekt>/.claude/skills/legal-abduction/`;
- dla użytkownika: `~/.claude/skills/legal-abduction/`
  (Windows: `$HOME/.claude/skills/legal-abduction/`).

Nie twórz `legal-abduction/legal-abduction/`. Uruchom nową sesję/wczytaj
konfigurację zgodnie z hostem, sprawdź listę dostępnych skills. Jeśli host
udostępnia komendy skillowe, wywołaj `/legal-abduction`; w przeciwnym razie
poproś o użycie skilla do **syntetycznego** pytania i sprawdź, że agent odczytał
lokalny `SKILL.md`. Nie zakładaj aktywacji na podstawie samej odpowiedzi modelu.

## VS Code / GitHub Copilot

W aktualnej wersji VS Code i Copilot z obsługą Agent Skills umieść katalog w
`<projekt>/.github/skills/legal-abduction/`. Dla instalacji osobistej hosty
Copilot mogą obsługiwać `~/.copilot/skills/legal-abduction/`; sprawdź dokumentację
konkretnej wersji przed użyciem tej ścieżki. Sprawdź w ustawieniach/diagnostyce
Copilot, czy Agent Skills są włączone i wykryto ten katalog. Wybierz tryb agenta
z dostępem do lokalnych plików i terminala; zatwierdzenia narzędzi pozostają
po stronie użytkownika. Nie utożsamiaj skilla z plikiem `.agent.md` lub
instrukcjami `.github/copilot-instructions.md`.

**Kompatybilność zależy od hosta, wersji, polityk organizacji, Workspace Trust,
uprawnień i modelu.** Nie przeprowadzono tu testu aktywacji rzeczywistego Claude
Code ani Copilot; test CLI po rozpakowaniu nie dowodzi wsparcia hosta.
Jeśli host nie wykrywa skills, można jawnie odczytać `SKILL.md` i pracować z
CLI, ale jest to ręczne zastosowanie procedury, nie certyfikowana integracja.
Nie usuwaj ograniczeń uprawnień, żeby wymusić działanie.

Oficjalne źródła (sprawdź aktualną wersję):
https://agentskills.io/specification,
https://code.claude.com/docs/en/skills,
https://code.visualstudio.com/docs/copilot/customization/agent-skills.

## Próba bez danych spraw

Z katalogu **zainstalowanego** skilla:

```powershell
python -B -X utf8 la.py --json version
python -B -X utf8 la.py --help
```

Do późniejszej oceny wybierz syntetyczny katalog sprawy poza katalogiem skilla
i poza `.github/skills`/`.claude/skills`. Każde polecenie pracy ze sprawą musi
otrzymać globalne `--case-dir <zewnętrzny-katalog>`. Nie uruchamiaj `init` w
korzeniu skilla. Przykład składni (plik profilu sporządza człowiek):

```powershell
python -B -X utf8 la.py --json --case-dir '<zewnętrzny-katalog>' init --profile-file '<profil-człowieka.json>'
python -B -X utf8 la.py --json --case-dir '<zewnętrzny-katalog>' doctor --declared-level A
```

Przy forbidden/braku zgody przerwij sesję przed wprowadzeniem akt: C/`none`
uruchamia człowiek poza agentem. Nie można tego naprawić zmianą adaptera.
Domyślna recenzja na lokalnym A to `human_via_agent`, nie `human_file`.
