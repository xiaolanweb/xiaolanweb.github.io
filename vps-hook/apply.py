#!/usr/bin/env python3
"""把 github_pages_sync.py 接进 /opt/tg-domain-bot/bot.py（幂等：已接过就跳过）。
用法：python3 apply.py /opt/tg-domain-bot/bot.py
做三件事：
  1. 在 `async def cmd_gmail_sync` 之前插入整段同步代码
  2. outreach_watch_job / daily_job 里 sync_gmail_if_changed 后面加 sync_github_if_changed
  3. 注册私聊命令「同步发布页」
"""
import re
import sys
import pathlib

bot_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/tg-domain-bot/bot.py")
hook_path = pathlib.Path(__file__).with_name("github_pages_sync.py")
src = bot_path.read_text(encoding="utf-8")
hook = hook_path.read_text(encoding="utf-8")

if "sync_github_if_changed" in src:
    print("已经接过了，跳过")
    sys.exit(0)

anchor = "async def cmd_gmail_sync("
assert src.count(anchor) == 1, "找不到 cmd_gmail_sync 锚点"
src = src.replace(anchor, hook.rstrip("\n") + "\n\n\n" + anchor, 1)

# 两处 job：紧跟在 sync_gmail_if_changed(context, dom) 后面加一行，缩进照抄
pat = re.compile(r"^([ \t]+)await sync_gmail_if_changed\(context, dom\)\n", re.M)
n = 0
def _add(m):
    global n
    n += 1
    return m.group(0) + f"{m.group(1)}await sync_github_if_changed(context, dom)\n"
src = pat.sub(_add, src)
assert n == 2, f"期望改 2 处 job 调用，实际 {n}"

reg = 'app.add_handler(MessageHandler(filters.Regex(r"^\\s*/?(?:同步邮箱|gmailsync)\\s*$"), cmd_gmail_sync))'
assert src.count(reg) == 1, "找不到 同步邮箱 handler 注册行"
src = src.replace(reg, reg + '\n    app.add_handler(MessageHandler(filters.Regex(r"^\\s*/?(?:同步发布页|ghsync)\\s*$"), cmd_github_sync))', 1)

bot_path.write_text(src, encoding="utf-8")
print(f"OK: 已写入 {bot_path}（同步代码 + {n} 处 job 调用 + 命令注册）")
