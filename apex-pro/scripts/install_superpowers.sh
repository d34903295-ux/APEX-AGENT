#!/usr/bin/env bash
# ============================================================================
# Install the Superpowers skills library for your coding agent.
# Superpowers (MIT, by Jesse Vincent / obra) gives Claude Code a full software
# methodology: brainstorming -> writing-plans -> TDD -> subagent execution ->
# code review -> verification. APEX-AGENT PRO was built with it and recommends
# it for all future contributions.
#
# Repo: https://github.com/obra/superpowers
# ============================================================================
set -euo pipefail

echo "Superpowers installs as a Claude Code *plugin* (not a python package)."
echo

cat <<'EOF'
── For Claude Code (interactive) ───────────────────────────────────────────
Run these slash commands inside Claude Code:

  # Official Anthropic marketplace:
  /plugin install superpowers@claude-plugins-official

  # …or the Superpowers community marketplace:
  /plugin marketplace add obra/superpowers-marketplace
  /plugin install superpowers@superpowers-marketplace

Then restart the session. The skills trigger automatically.

── For other harnesses ─────────────────────────────────────────────────────
Codex / Cursor / Gemini / Kimi / OpenCode / Pi: see the install matrix at
https://github.com/obra/superpowers#installation

── Vendored methodology (no plugin needed) ─────────────────────────────────
A distilled, in-repo version of the methodology lives at
  docs/methodology/SUPERPOWERS.md
so the workflow is documented even where the plugin isn't installed.
EOF

# Optionally clone the repo locally for reference (read-only).
if [[ "${1:-}" == "--clone" ]]; then
  DEST="${2:-./.superpowers-reference}"
  echo
  echo "Cloning reference copy into $DEST …"
  git clone --depth 1 https://github.com/obra/superpowers.git "$DEST"
  echo "Done. (This is reference only; it is git-ignored.)"
fi
