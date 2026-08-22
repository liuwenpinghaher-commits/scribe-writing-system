#!/usr/bin/env bash
# 第十轮 L01：用管理员 token 给 main 加上分支保护。
# 需要 GITHUB_TOKEN 或 GH_TOKEN，权限含 administration。
set -euo pipefail
TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
OWNER="${GITHUB_OWNER:-liuwenpinghaher-commits}"
REPO="${GITHUB_REPO:-scribe-writing-system}"
BRANCH="${GITHUB_BRANCH:-main}"
if [[ -z "$TOKEN" ]]; then
  echo "缺少 GITHUB_TOKEN / GH_TOKEN，无法改 GitHub 设置。" >&2
  exit 2
fi
API="https://api.github.com/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection"
BODY='{
  "required_status_checks": {
    "strict": true,
    "contexts": ["backend"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false
}'
echo "PUT ${API}"
curl -sS -X PUT "$API" \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d "$BODY" \
  | tee /tmp/branch-protection-put.json
echo
echo "GET ${API}"
curl -sS "$API" \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  | tee /tmp/branch-protection-get.json
echo
echo "已写入 /tmp/branch-protection-put.json 与 /tmp/branch-protection-get.json"
