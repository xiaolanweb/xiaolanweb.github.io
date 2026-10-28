# ---------- GitHub 发布页 domains.json 同步 ----------
# 挂在 tg-domain-bot 的 bot.py 里。最新域名变了 → 用 GitHub Contents API 改仓库里的 domains.json，
# GitHub Pages 1~2 分钟后自动重新发布，发布页「最新地址」就跟着换。
# .env 需要：GH_PAGES_TOKEN（gh auth token 或 PAT，要有 repo 写权限）
#            GH_PAGES_REPO（如 xiaolanweb/xiaolanweb.github.io）
# 没配就全部跳过，不影响原有功能。
GH_PAGES_TOKEN = os.getenv("GH_PAGES_TOKEN", "").strip()
GH_PAGES_REPO = os.getenv("GH_PAGES_REPO", "").strip()
GH_PAGES_FILE = os.getenv("GH_PAGES_FILE", "domains.json").strip() or "domains.json"
GH_PAGES_URL = os.getenv("GH_PAGES_URL", "").strip()      # 发布页网址，只用于通知文案
GH_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_github_domain.txt")


def _last_github_domain() -> str:
    try:
        with open(GH_STATE_FILE, encoding="utf-8") as f:
            return _norm_domain(f.read())
    except FileNotFoundError:
        return ""
    except Exception as e:
        log.warning("读 github 域名状态失败: %s", e)
        return ""


def _save_github_domain(domain: str):
    try:
        with open(GH_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(_norm_domain(domain))
    except Exception as e:
        log.warning("存 github 域名失败: %s", e)


def _call_github_sync(domain: str) -> dict:
    """读 domains.json 拿 sha → 内容不同才写回。返回 {"changed":bool,"domain":url,"commit":sha?}"""
    import base64
    import requests
    api = f"https://api.github.com/repos/{GH_PAGES_REPO}/contents/{GH_PAGES_FILE}"
    h = {"Authorization": f"Bearer {GH_PAGES_TOKEN}",
         "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28",
         "User-Agent": "tg-domain-bot"}
    url = "https://" + _norm_domain(domain)
    r = requests.get(api, headers=h, timeout=30)
    sha, old = None, {}
    if r.status_code == 200:
        j = r.json()
        sha = j.get("sha")
        try:
            old = json.loads(base64.b64decode(j.get("content") or "").decode("utf-8"))
        except Exception:
            old = {}
    elif r.status_code != 404:
        raise RuntimeError(f"读 {GH_PAGES_FILE} 失败 HTTP {r.status_code}: {r.text[:200]}")
    cur = [("https://" + _norm_domain(u)) for u in (old.get("latest") or []) if isinstance(u, str) and u.strip()]
    if cur == [url]:
        return {"changed": False, "domain": url}
    body = {"latest": [url],
            "updated": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M"),
            "by": "domain-bot"}
    content = base64.b64encode((json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8")).decode("ascii")
    payload = {"message": f"最新地址 → {_norm_domain(domain)}", "content": content}
    if sha:
        payload["sha"] = sha
    r2 = requests.put(api, headers=h, json=payload, timeout=30)
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"写 {GH_PAGES_FILE} 失败 HTTP {r2.status_code}: {r2.text[:200]}")
    commit = ((r2.json().get("commit") or {}).get("sha") or "")[:7]
    return {"changed": True, "domain": url, "commit": commit}


async def sync_github_if_changed(context, domain: str, force: bool = False):
    """域名和上次写到发布页的不一样 → 改仓库 domains.json，改了就发话题 TOPIC_ID 通知；
    失败发话题 + 私信 OWNER。没变就不动。返回接口结果或 None。"""
    if not GH_PAGES_TOKEN or not GH_PAGES_REPO or not domain:
        return None
    if not force and _norm_domain(domain) == _last_github_domain():
        return None
    try:
        data = await asyncio.to_thread(_call_github_sync, domain)
    except Exception as e:
        log.warning("同步 GitHub 发布页失败: %s", e)
        msg = (f"⚠️ 发布页最新地址更新失败\n最新地址：{domain}\n原因：{e}\n"
               f"请先人工去 GitHub 仓库改 {GH_PAGES_FILE}，再检查 GH_PAGES_TOKEN。")
        for chat_id, kw in ((GROUP_ID, {"message_thread_id": TOPIC_ID}), (OWNER_ID, {})):
            try:
                await context.bot.send_message(chat_id, msg, disable_web_page_preview=True, **kw)
            except Exception:
                pass
        return None
    _save_github_domain(domain)            # 成功才记,失败下次重试
    if data.get("changed"):
        txt = f"🌐 发布页最新地址已更新\n最新地址：{data.get('domain') or domain}"
        if GH_PAGES_URL:
            txt += f"\n发布页：{GH_PAGES_URL}（1~2 分钟后生效）"
        try:
            await context.bot.send_message(GROUP_ID, txt, message_thread_id=TOPIC_ID,
                                           disable_web_page_preview=True)
        except Exception as e:
            log.warning("发发布页同步结果失败: %s", e)
        log.info("发布页 domains.json 已更新为 %s (commit %s)", domain, data.get("commit"))
    else:
        log.info("发布页已是最新地址 %s,不用改", domain)
    return data


async def cmd_github_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """OWNER 私聊「同步发布页」:不管有没有变,强制同步一次,并回结果。"""
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    if not GH_PAGES_TOKEN or not GH_PAGES_REPO:
        await update.message.reply_text("还没配置 GH_PAGES_TOKEN / GH_PAGES_REPO")
        return
    dom = await asyncio.to_thread(fetch_latest_domain)
    if not dom:
        await update.message.reply_text("没抓到 xiaolan1.com 的最新域名，稍后再试")
        return
    data = await sync_github_if_changed(context, dom, force=True)
    if data is None:
        await update.message.reply_text("同步失败，详情看话题里的告警")
    else:
        await update.message.reply_text(
            f"✅ 最新地址 {data.get('domain') or dom}\n"
            f"发布页 {'已更新，1~2 分钟后生效' if data.get('changed') else '本来就是这个地址，没动'}")
# ---------- GitHub 发布页同步 结束 ----------
