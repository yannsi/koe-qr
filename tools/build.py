#!/usr/bin/env python3
"""src/app.html と vendor/ の部品から、公開用の index.html と sw.js を組み立てる。

使い方:  python3 tools/build.py
- 版の番号は src/app.html の見出し「試作版 X.Y.Z」から読み取り、sw.js の保存名に使う
  （版を上げるとスマホに保存された古いファイルが入れ替わる）
"""
import base64, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def rd(p): return open(os.path.join(ROOT, p), encoding="utf-8").read()

app = rd("src/app.html")
m = re.search(r"試作版 ([0-9][0-9.]*)", app)
if not m: raise SystemExit("src/app.html に「試作版 X.Y.Z」が見つかりません")
version = m.group(1)

wasm = base64.b64encode(open(os.path.join(ROOT, "vendor/codec2.wasm"), "rb").read()).decode()
s = (app.replace("/*__QRGEN__*/", "/*! qrcode-generator 1.4.4 | (c) Kazuhiko Arase | MIT License */\n" + rd("vendor/qrcode.js"))
        .replace("/*__JSQR__*/", "/*! jsQR 1.4.0 | (c) Cosmo Wolfe | Apache License 2.0 */\n" + rd("vendor/jsQR.js"))
        .replace("__WASM_B64__", wasm)
        .replace("/*__STANDALONE__*/false", "true"))
for key in ("/*__QRGEN__*/", "/*__JSQR__*/", "__WASM_B64__", "/*__STANDALONE__*/"):
    assert key not in s, key

head = ('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="theme-color" content="#274A78">\n'
        '<meta name="description" content="録音した声とメロディをQRコードに入れ、ネットなしで読み取って再生するアプリ">\n'
        '<link rel="manifest" href="manifest.webmanifest">\n<link rel="icon" href="icon-192.png">\n'
        '<link rel="apple-touch-icon" href="icon-180.png">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-title" content="声のQR">\n')
i = s.index("</style>") + len("</style>")
html = head + s[:i] + "\n</head>\n<body>\n" + s[i:] + "\n</body>\n</html>\n"
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)

open(os.path.join(ROOT, "sw.js"), "w", encoding="utf-8").write(f'''/* 声のQR：一度開けば、以後はネットなしで動くようにファイルを端末に保存する（tools/build.py が生成） */
const CACHE = "koe-qr-v{version}";
const FILES = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./icon-512-maskable.png", "./icon-180.png"];
self.addEventListener("install", e => {{ e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); self.skipWaiting(); }});
self.addEventListener("activate", e => {{ e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); }});
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, {{ ignoreSearch: true }}).then(hit => {{
    const net = fetch(e.request).then(res => {{ if (res && (res.ok || res.type === "opaque")) {{ const cp = res.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); }} return res; }});
    return hit || net.catch(() => caches.match("./index.html"));
  }}));
}});
''')
print(f"index.html と sw.js を作りました（版 {version}、{len(html)//1024} KB）")
