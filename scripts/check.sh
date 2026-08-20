#!/usr/bin/env bash
# Structural checks for the greenfield plugin.
#
# No dependencies beyond bash, grep, sed, and python3 (for JSON parsing).
# Run from the repository root:  ./scripts/check.sh
#
# Run this after adding or editing a command, skill, or subagent.
# The guard check is the important one — see "Why the guard check" in AGENTS.md.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

fail=0
note() { printf "  %-52s %s\n" "$1" "$2"; }
bad()  { fail=1; note "$1" "FAIL"; }

echo "== JSON =="
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json .mcp.json; do
  if python3 -c "import json,sys; json.load(open('$f'))" 2>/dev/null; then
    note "$f" "ok"
  else
    bad "$f"
  fi
done

echo "== Frontmatter =="
for f in skills/*/SKILL.md agents/*.md; do
  [ -n "$(sed -n '2s/^name: //p' "$f")" ] && note "$f" "ok" || bad "$f (missing name:)"
done
for f in commands/*.md; do
  [ -n "$(sed -n '2s/^description: //p' "$f")" ] && note "$f" "ok" || bad "$f (missing description:)"
done

echo "== Skill cross-references resolve =="
ls skills/ | sort > /tmp/gf_have.$$
grep -rhoE '`[a-z][a-z-]+`' commands/ skills/ agents/ AGENTS.md \
  | tr -d '`' | sort -u | grep -Fxf /tmp/gf_have.$$ > /dev/null
missing=$(grep -rhoE '`(greenfield-delivery|discovery|requirements-gate|architecture-design|build-standards|tracker-conventions|tracker-jira|tracker-azure-devops|progress-reporting|handoff|business-test-cases|qe|build-loop)`' \
  commands/ skills/ agents/ AGENTS.md | tr -d '`' | sort -u | comm -13 /tmp/gf_have.$$ -)
rm -f /tmp/gf_have.$$
[ -z "$missing" ] && note "all referenced skills exist" "ok" || bad "referenced but missing: $missing"

echo "== Step numbering (no duplicates) =="
for f in commands/*.md; do
  d=$(grep -oE '^## [0-9]+\.' "$f" | sort | uniq -d)
  [ -z "$d" ] && note "$f" "ok" || bad "$f (duplicate: $d)"
done

echo "== Guards: every command must stop on missing or invalid input =="
for f in commands/*.md; do
  g=$(grep -ciE 'stop and (say|ask)|Stop if|Stop and say|refuse|do not (infer|guess|invent|fall back|produce)' "$f")
  if [ "$g" -gt 0 ]; then
    note "$f" "$g guard(s)"
  else
    bad "$f (no guard — see AGENTS.md)"
  fi
done

echo "== Dashboard =="
if python3 -m py_compile scripts/dashboard/*.py scripts/conform.py scripts/features.py 2>/dev/null; then
  note "scripts/*.py compiles" "ok"
else
  bad "scripts/*.py (syntax error)"
fi
# Named by discovery, not hardcoded: this line used to say test_dashboard.py
# and would have kept saying it after a second test file was added.
found=$(ls scripts/test_*.py 2>/dev/null | wc -l | tr -d ' ')
if python3 -m unittest discover -s scripts -p 'test_*.py' -q >/dev/null 2>&1; then
  note "$found test file(s)" "ok"
else
  bad "scripts/test_*.py (failing tests)"
fi

echo "== Docs and code agree =="
# The plugin IS its markdown, and until now nothing checked that the formats
# the skills TEACH are the formats the parser ACCEPTS. A drifted table means
# every artifact produced by following the docs is unreadable to the tooling,
# which then blames the user for doing what they were told.
if python3 -m unittest discover -s scripts -p 'test_docs.py' -q >/dev/null 2>&1; then
  note "documented formats parse; vocabularies match" "ok"
else
  bad "docs/code drift (run: cd scripts && python3 -m unittest test_docs)"
fi

echo "== Conformance fixtures still discriminate =="
if python3 -m unittest discover -s scripts -p 'test_conform.py' -q >/dev/null 2>&1; then
  note "examples/conformance/*" "ok"
else
  bad "examples/conformance/* (a fixture stopped failing its rule)"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS"
else
  echo "FAIL — fix the above before committing."
fi
exit "$fail"
