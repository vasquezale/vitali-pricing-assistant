#!/usr/bin/env bash
set -euo pipefail

current_branch="$(git branch --show-current)"

echo "=== Proyecto Vitali: pre-push security check ==="
echo "Current branch: ${current_branch}"

if [[ "${current_branch}" == "main" ]]; then
  echo "ERROR: do not publish from 'main'. Use 'codex/public-ready' instead."
  exit 1
fi

if [[ "${current_branch}" != "codex/public-ready" ]]; then
  echo "WARNING: you are not on 'codex/public-ready'. Review carefully before pushing."
fi

echo "Checking tracked files..."
tracked_files="$(git ls-files)"
echo "${tracked_files}"

for blocked_path in "context/" "research/" "docs/" "notebooks/" "AGENTS.md" "CLAUDE.md"; do
  if grep -Eq "(^|/)$blocked_path" <<<"${tracked_files}"; then
    echo "ERROR: blocked documentation path is tracked: ${blocked_path}"
    exit 1
  fi
done

if grep -Eq '(^|/)(data/|secrets/|credentials/)' <<<"${tracked_files}"; then
  echo "ERROR: a protected local-only path is tracked."
  exit 1
fi

if grep -Eq '(^|/)\.env($|[.])' <<<"${tracked_files}"; then
  echo "ERROR: a real .env file is tracked."
  exit 1
fi

echo "Scanning tracked content for high-risk patterns..."
if git grep -n -I -E '(BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9]{20,}|api[_-]?key[[:space:]]*[:=][[:space:]]*[^[:space:]]+|token[[:space:]]*[:=][[:space:]]*[^[:space:]]+|password[[:space:]]*[:=][[:space:]]*[^[:space:]]+|passwd[[:space:]]*[:=][[:space:]]*[^[:space:]]+|secret[[:space:]]*[:=][[:space:]]*[^[:space:]]+|/Users/ale/Documents/Personal/)' -- $(git ls-files) >/tmp/proyecto_vitali_pre_push_matches.txt; then
  echo "ERROR: suspicious content found in tracked files."
  cat /tmp/proyecto_vitali_pre_push_matches.txt
  rm -f /tmp/proyecto_vitali_pre_push_matches.txt
  exit 1
fi
rm -f /tmp/proyecto_vitali_pre_push_matches.txt

echo "Checking worktree status..."
git status --short

echo "Pre-push security check passed."
