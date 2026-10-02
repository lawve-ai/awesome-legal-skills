#!/usr/bin/env bash
# Hostile fixtures must return HOSTILE (2); clean fixtures must return CLEAN (0).
set -u
D="$(cd "$(dirname "$0")" && pwd)"
python3 "$D/make_fixtures.py" >/dev/null
fail=0
for f in hostile.docx hostile.pdf hostile.html; do
  python3 "$D/../scan.py" "$D/fixtures/$f" >/dev/null; rc=$?
  [ $rc -eq 2 ] && echo "ok   $f HOSTILE" || { echo "FAIL $f expected 2 got $rc"; fail=1; }
done
for f in clean.docx clean.pdf; do
  python3 "$D/../scan.py" "$D/fixtures/$f" >/dev/null; rc=$?
  [ $rc -eq 0 ] && echo "ok   $f CLEAN" || { echo "FAIL $f expected 0 got $rc"; fail=1; }
done
# The emitted visible text of the hostile PDF must carry none of the planted lines.
out="$(mktemp)"; python3 "$D/../scan.py" --emit-visible "$out" "$D/fixtures/hostile.pdf" >/dev/null
if grep -qiE "ignore|assistant|guilty plea|evil\.example" "$out"; then echo "FAIL emit-visible leaks hidden text"; fail=1; else echo "ok   emit-visible clean"; fi
rm -f "$out"
python3 "$D/test_hook.py" || fail=1
exit $fail
