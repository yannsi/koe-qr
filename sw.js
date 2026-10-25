/* 声のQR：一度開けば、以後はネットなしで動くようにファイルを端末に保存する（tools/build.py が生成） */
const CACHE = "koe-qr-v0.7.2";
const FILES = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./icon-512-maskable.png", "./icon-180.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); self.skipWaiting(); });
/* 古い版の保存を片付ける。予備の GitHub Pages（yannsi.github.io/koe-qr/）では他の作品と保存場所を共有しているので、
   「koe-qr-」で始まる自分の古い版だけを消す */
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith("koe-qr-") && k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
/* ページを開くとき（navigate）は、ネットにつながっていれば最新の版を先に取りに行く（4秒待っても来なければ保存した分）。
   つながっていないときは保存した分を出す。こうしないと、新しい版が出ても1回目は古い版が出てしまう */
function fromNet(req, ms) {
  return new Promise((ok, ng) => {
    const t = setTimeout(() => ng(new Error("timeout")), ms);
    fetch(req, { cache: "no-cache" }).then(res => { clearTimeout(t); if (res && res.ok) ok(res); else ng(new Error("status")); }, err => { clearTimeout(t); ng(err); });
  });
}
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  if (e.request.mode === "navigate") {
    e.respondWith(fromNet(e.request, 4000).then(res => { const cp = res.clone(); caches.open(CACHE).then(c => c.put("./index.html", cp)); return res; })
      .catch(() => caches.match("./index.html").then(hit => hit || caches.match("./")).then(hit => hit || fetch(e.request))));
    return;
  }
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(hit => {
    const net = fetch(e.request).then(res => { if (res && (res.ok || res.type === "opaque")) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); } return res; });
    return hit || net.catch(() => caches.match("./index.html"));
  }));
});
