# 小蓝web 防丢失发布页

纯静态「官方发布页」：用户收藏这一个网址，主站域名变了也能在这里找到最新地址。

## 最新地址：自动更新，不用管

`domains.json` 里的 `latest` 就是「最新地址」。VPS 上的域名监测机器人每小时抓一次
xiaolan1.com 公布的最新网址，变了就自动改这个文件并提交，1~2 分钟后页面生效。

机器人挂了想手改：打开 `domains.json`，点铅笔（Edit），改 `latest` 里的网址和 `updated` 日期，
点绿色 **Commit changes**。

```json
{
  "latest": ["https://新域名.com"],
  "updated": "2026-10-28 11:50",
  "by": "manual"
}
```

## 永久地址 / 联系方式 / 注意事项：改 index.html 顶部 CONFIG

1. 打开 `index.html`，点铅笔（Edit）
2. 找到文件开头 `CONFIG`：
   - `permanentDomains`：永久地址，一行一个，行尾保留逗号
   - `telegram`：频道 / 群链接
   - `contactEmail`：自动回复邮箱
   - `notices`：注意事项，一行一条
   - `latestDomains`：最新地址的兜底，只有 `domains.json` 读不到时才用
3. 顺手把 `updated` 改成当天日期，点 **Commit changes**

## 注意

- 最新地址显示的是 3 条随机二级域名：机器人给的地址只取主域名（56dtd6.b9o9j2b0s3.cc → b9o9j2b0s3.cc），二级域名每次打开随机生成，靠主站泛解析。条数在 `CONFIG.randomSubdomains` 改，0 = 不随机、原样显示
- 只改 `CONFIG` 那一段，页面其他部分不用动
- 网址建议带 `https://`（漏写了页面也会自动补上）
- `probePath` 是「可用性检测」用的小图路径，主站必须真实存在这张图（默认 `/favicon.ico`）
- `og.png` 是分享卡片图（1200×630），源文件在 `og-src/og.html`，改完用 Chrome 无头重新截一张即可
- SEO：`<title>`、canonical、`robots.txt`、`sitemap.xml`、页面底部「关于」那段写死的文字都在仓库里；Search Console / Yandex 站长的验证 meta 标签在 index.html 头部
- 机器人改 `domains.json` 的代码见 `vps-hook/`
