#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "同步已停止：Wiki 工作副本存在未提交修改。" >&2
  exit 1
fi

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "同步已停止：当前分支不是 main。" >&2
  exit 1
fi

if [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
elif [[ -x "$repo_root/../.venv/bin/python" ]]; then
  python_bin="$repo_root/../.venv/bin/python"
else
  python_bin="${WIKI_PYTHON:-python3}"
fi

git fetch --prune origin main

local_head="$(git rev-parse HEAD)"
remote_head="$(git rev-parse origin/main)"
if [[ "$local_head" == "$remote_head" ]]; then
  "$python_bin" -m builder.validate
  echo "Wiki 已是最新版本：$local_head"
  exit 0
fi

if ! git merge-base --is-ancestor HEAD origin/main; then
  echo "同步已停止：本地 main 与 origin/main 已分叉，禁止自动合并。" >&2
  exit 1
fi

validation_tree="$(mktemp -d "${TMPDIR:-/tmp}/yuna102-wiki-validate.XXXXXX")"
cleanup() {
  git worktree remove --force "$validation_tree" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git worktree add --detach "$validation_tree" origin/main >/dev/null
(
  cd "$validation_tree"
  "$python_bin" -m builder.validate
)

git merge --ff-only origin/main
"$python_bin" -m builder.validate
echo "Wiki 已安全同步到：$remote_head"
