#!/usr/bin/env bash
set -euo pipefail

current_branch="$(git branch --show-current)"

echo "=== Proyecto Vitali: pre-push security check ==="
echo "Current branch: ${current_branch}"

if [[ "${current_branch}" == "codex/prepublish-backup" ]]; then
  echo "ERROR: do not push from 'codex/prepublish-backup'. It is a local safety branch."
  exit 1
fi

if [[ "${current_branch}" == "main" ]]; then
  echo "INFO: pushing from 'main' is acceptable once feature work has been reviewed and merged."
elif [[ "${current_branch}" == "codex/public-ready" ]]; then
  echo "INFO: 'codex/public-ready' is the legacy clean publication branch."
else
  echo "INFO: topic branch detected. Push only if you intentionally want the branch on the remote."
fi

echo "Checking tracked files..."
tracked_files="$(git ls-files)"
echo "${tracked_files}"
scan_files="$(printf '%s\n' "${tracked_files}" | grep -v '^scripts/pre_push_security_check\.sh$' || true)"

for blocked_path in "context/" "research/" "docs/" "notebooks/" "AGENTS.md" "CLAUDE.md"; do
  if grep -Eq "(^|/)$blocked_path" <<<"${tracked_files}"; then
    echo "ERROR: blocked documentation path is tracked: ${blocked_path}"
    exit 1
  fi
done

if grep -Eq '^(data/|secrets/|credentials/)' <<<"${tracked_files}"; then
  echo "ERROR: a protected local-only path is tracked."
  exit 1
fi

echo "Checking tracked env files..."
bad_env_files="$(printf '%s\n' "${tracked_files}" | grep -E '(^|/)\.env($|\.)' | grep -vE '(^|/)\.env\.example$' || true)"

if [[ -n "${bad_env_files}" ]]; then
  echo "ERROR: a real .env file is tracked."
  echo "${bad_env_files}"
  exit 1
fi

echo "Scanning tracked content for high-risk patterns..."
if [[ -n "${scan_files}" ]] && git grep -n -I -E '(BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9]{20,}|api[_-]?key[[:space:]]*[:=][[:space:]]*[^[:space:]]+|token[[:space:]]*[:=][[:space:]]*[^[:space:]]+|password[[:space:]]*[:=][[:space:]]*[^[:space:]]+|passwd[[:space:]]*[:=][[:space:]]*[^[:space:]]+|secret[[:space:]]*[:=][[:space:]]*[^[:space:]]+|/Users/ale/Documents/Personal/)' -- ${scan_files} >/tmp/proyecto_vitali_pre_push_matches.txt; then
  echo "ERROR: suspicious content found in tracked files."
  cat /tmp/proyecto_vitali_pre_push_matches.txt
  rm -f /tmp/proyecto_vitali_pre_push_matches.txt
  exit 1
fi
rm -f /tmp/proyecto_vitali_pre_push_matches.txt

echo "Checking worktree status..."
git status --short

echo "Pre-push security check passed."
