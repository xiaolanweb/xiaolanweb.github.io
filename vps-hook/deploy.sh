#!/bin/bash
# 在 Mac 上跑：把钩子部署到 Contabo 的 tg-domain-bot。
# 用法：GH_PAGES_TOKEN=xxx GH_PAGES_REPO=xiaolanweb/xiaolanweb.github.io GH_PAGES_URL=https://xiaolanweb.github.io/ bash deploy.sh
set -euo pipefail
: "${GH_PAGES_TOKEN:?需要 GH_PAGES_TOKEN}"; : "${GH_PAGES_REPO:?需要 GH_PAGES_REPO}"; GH_PAGES_URL="${GH_PAGES_URL:-}"
VPS="root@173.212.253.62"; KEY="$HOME/.ssh/contabo_vps"; DIR=/opt/tg-domain-bot
HERE="$(cd "$(dirname "$0")" && pwd)"
TS=$(date +%Y%m%d_%H%M%S)
scp -i "$KEY" -q "$HERE/github_pages_sync.py" "$HERE/apply.py" "$VPS:$DIR/"
ssh -i "$KEY" "$VPS" bash -s <<REMOTE
set -euo pipefail
cd $DIR
cp bot.py bot.py.bak.ghpages_$TS
python3 apply.py bot.py
# .env：有就替换，没有就追加
for kv in "GH_PAGES_TOKEN=$GH_PAGES_TOKEN" "GH_PAGES_REPO=$GH_PAGES_REPO" "GH_PAGES_URL=$GH_PAGES_URL"; do
  k=\${kv%%=*}
  if grep -q "^\$k=" .env; then sed -i "s|^\$k=.*|\$kv|" .env; else printf '\n%s\n' "\$kv" >> .env; fi
done
.venv/bin/python -c "import ast,sys; ast.parse(open('bot.py').read())" && echo "bot.py 语法 OK"
systemctl restart tg-domain-bot && sleep 3 && systemctl is-active tg-domain-bot
echo "备份：$DIR/bot.py.bak.ghpages_$TS   回滚：cp $DIR/bot.py.bak.ghpages_$TS $DIR/bot.py && systemctl restart tg-domain-bot"
REMOTE
