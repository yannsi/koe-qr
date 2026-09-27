#!/usr/bin/env python3
"""公開用 index.html の動作確認（ブラウザを画面なしで動かして確かめる）。

使い方:  python3 tools/test.py
必要なもの: pip install playwright （Chromium が入っていること）
確かめること:
  1. ページがエラーなく開き、声の圧縮部品（Codec2）が動く
  2. 声だけ・メロディだけ・両方 のQRを作って読み戻すと、中身が1バイトも違わない
  3. 写真（画像）からQRを読み、再生ボタンで音声が流れ始める
"""
import os, sys, math, base64
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(ROOT, "index.html")
ok = True
def check(name, cond, detail=""):
    global ok
    print(("OK  " if cond else "NG  ") + name + (f"  {detail}" if detail else ""))
    ok = ok and cond

# 声の代わりに、声に似た倍音の多い音（8kHz・3秒）を作る
pcm = []
for i in range(8000 * 3):
    f0 = 120 + 30 * math.sin(i / 8000 * 2)
    v = sum(math.sin(2 * math.pi * f0 * h * i / 8000) / h for h in range(1, 20))
    pcm.append(int(v * 3000 * (0.5 + 0.5 * math.sin(i / 8000 * 6))))

with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={"width": 400, "height": 860})
    errs = []; page.on("pageerror", lambda e: errs.append(str(e)))
    page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    page.goto(URL)
    page.wait_for_function("window.__koe && __koe.ready()", timeout=15000)
    check("ページが開き、Codec2 が動く", True)
    res = page.evaluate("""([pcm]) => {
      const k = __koe, out = {};
      const mel = k.parseMelody(document.getElementById('melText').value);
      const md = k.encodeMelody(mel.notes, 108, 2);
      for (const [name, pc, m] of [['both', Int16Array.from(pcm), md], ['voice', Int16Array.from(pcm), null], ['melody', null, md]]) {
        const pl = k.buildPayload(pc, 5, m), qr = k.makeQR(pl.bytes), got = k.readQRFromCanvas(qr.canvas);
        const same = !!got && got.length === pl.bytes.length && got.every((v, i) => v === pl.bytes[i]);
        const c = same ? k.parsePayload(got) : null;
        out[name] = { same, ver: qr.version, bytes: pl.bytes.length, voice: c && c.voice ? c.voice.seconds : 0, notes: c && c.melody ? c.melody.notes.length : 0 };
      }
      return out; }""", [pcm])
    for name, r in res.items():
        check(f"QR往復（{name}）", r["same"], f"型番{r['ver']}・{r['bytes']}バイト・声{r['voice']:.1f}秒・{r['notes']}音")
    d = page.evaluate("document.getElementById('qrImg').src")
    img = os.path.join(ROOT, ".test-qr.png"); open(img, "wb").write(base64.b64decode(d.split(",")[1]))
    page.click("#tabRead"); page.set_input_files("#photoFile", img)
    page.wait_for_selector("#resultCard:not([hidden])", timeout=10000)
    page.click("#playBtn"); page.wait_for_timeout(1200)
    st = page.evaluate("(() => { const a = __koe.audio(); return a ? { paused: a.paused, t: a.currentTime } : null })()")
    check("写真から読み取って再生できる", bool(st) and not st["paused"] and st["t"] > 0.3, str(st))
    os.remove(img)
    check("ページのエラーなし", not errs, "; ".join(errs))
    b.close()
sys.exit(0 if ok else 1)
