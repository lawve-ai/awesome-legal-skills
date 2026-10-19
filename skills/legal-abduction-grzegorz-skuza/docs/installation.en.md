# Installation — EN, preview v1

This ZIP is an **evaluation bundle**, not publication or a license grant.
Q11 remains unresolved: use only for authorized evaluation, not redistribution
as an open-source release. Read [limits](usage.en.md) and
[gates](distribution.md) before loading it into a host.

## ZIP and Python verification

Python >=3.12, stdlib only; no pip, server or PDF/OCR installation needed.
PowerShell, from the source `legal-abduction` directory:

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONHASHSEED = '0'
python -B -X utf8 --version
Get-FileHash '<preview-ZIP>' -Algorithm SHA256
python -B -X utf8 scripts/package_preview.py --check '<preview-ZIP>' --smoke
```

Compare SHA-256 with an independently retained build result. An internal
manifest is not a signature or proof of origin. Without a trusted script
source, inspect the archive before executing its code. After verification,
extract using an archive UI into a **new staging directory**, never overwrite
an existing skill. The ZIP has one `legal-abduction/` directory with `SKILL.md`
at its root. Copy the entire directory, not only the Markdown file.

## Claude Code

With a version supporting Agent Skills:

- project installation: `<project>/.claude/skills/legal-abduction/`;
- personal installation: `~/.claude/skills/legal-abduction/`
  (Windows: `$HOME/.claude/skills/legal-abduction/`).

Avoid a nested `legal-abduction/legal-abduction/`. Start/reload a session as
documented by the host, and inspect available skills. Where skill commands
are supported, invoke `/legal-abduction`; otherwise request use of this skill
on a **synthetic** question and verify the agent read the local `SKILL.md`.
An agent's verbal claim alone does not establish activation.

## VS Code / GitHub Copilot

With current VS Code and Copilot versions supporting Agent Skills, copy to
`<project>/.github/skills/legal-abduction/`. Copilot hosts may support personal
skills at `~/.copilot/skills/legal-abduction/`; check the specific version's
documentation before using that location. Check Copilot settings/diagnostics
for enabled skills and discovery of this directory. Select agent mode with
local file/terminal access; tool permissions remain controlled by the user.
A skill is not a `.agent.md` file or `.github/copilot-instructions.md`.

**Compatibility varies by host, version, organization policy, Workspace Trust,
permissions and model.** Actual Claude Code/Copilot activation was not tested
here; an extracted CLI smoke test does not prove host integration.
If native discovery is absent, explicitly reading `SKILL.md` and using the CLI
is a manual procedure, not a certified integration. Do not remove permission
boundaries to force compatibility.

Official sources (check current versions):
https://agentskills.io/specification,
https://code.claude.com/docs/en/skills,
https://code.visualstudio.com/docs/copilot/customization/agent-skills.

## No-case smoke

From the **installed** directory:

```powershell
python -B -X utf8 la.py --json version
python -B -X utf8 la.py --help
```

For later evaluation select a synthetic case directory outside the skill and
`.github/skills`/`.claude/skills`. All case-processing commands need global
`--case-dir <external-directory>`. Never run `init` inside the skill root.
Syntax example (a human supplies the profile file):

```powershell
python -B -X utf8 la.py --json --case-dir '<external-directory>' init --profile-file '<human-profile.json>'
python -B -X utf8 la.py --json --case-dir '<external-directory>' doctor --declared-level A
```

Missing/forbidden consent: stop the session before introducing documents; the
human runs C/`none` outside the agent. Adapter switching is insufficient.
Default local A review is `human_via_agent`, not `human_file`.
