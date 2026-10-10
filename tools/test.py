#!/usr/bin/env python3
"""公開用 index.html の動作確認（ブラウザを画面なしで動かして確かめる）。

使い方:  python3 tools/test.py
必要なもの: pip install playwright （Chromium が入っていること）
確かめること:
  1. ページがエラーなく開き、声の圧縮部品（Codec2）が動く
  2. 声だけ・メロディだけ・両方 のQRを作って読み戻すと、中身が1バイトも違わない
  3. 写真（画像）からQRを読み、再生ボタンで音声が流れ始める
  4. カメラで読める形（https://koe-qr.web.app/#…）でも 2 と同じように読み戻せ、
     いちばん長い声を入れても型番40に収まる。古い形（先頭が VQ）も今までどおり収まる
  5. そのアドレスで開くと「届いた声のQR」が出て、再生できる
  6. ひとこと（種類3）が往復し、届いた画面に出る。「リンクで送る」で送ったリンクを開くと聞ける
  7. 「カメラで読み取る」で、カメラの映像（試験用のにせのカメラに、少しぼかした細かいQRを映す）から読み取れる
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

    # カメラで読める形
    res = page.evaluate("""([pcm]) => {
      const k = __koe, out = {}, pre = k.CANON + '#', cap = k.capLink(k.CANON);
      const mel = k.parseMelody(document.getElementById('melText').value);
      const md = k.encodeMelody(mel.notes, 108, 2);
      for (const [name, pc, m] of [['both', Int16Array.from(pcm), md], ['voice', Int16Array.from(pcm), null], ['melody', null, md]]) {
        const pl = k.buildPayload(pc, 5, m, cap), qr = k.makeQR(pl.bytes, pre), raw = k.readQRFromCanvas(qr.canvas);
        let text = ''; if (raw) for (const b of raw) text += String.fromCharCode(b);
        let got = null; try { got = k.extractPayload(raw); } catch (e) {}
        const same = !!got && got.length === pl.bytes.length && got.every((v, i) => v === pl.bytes[i]);
        out[name] = { same, url: text.startsWith(pre), ver: qr.version, bytes: pl.bytes.length };
      }
      /* いちばん長い声（30秒を入れて、入るところまで）でも型番40に収まるか */
      const long = new Int16Array(8000 * 40); for (let i = 0; i < long.length; i++) long[i] = Math.round(8000 * Math.sin(i / 8000 * 2 * Math.PI * (140 + (i % 4000) / 40)));
      for (const [name, mode, c, pre2] of [['link-hq', 5, cap, pre], ['link-long', 8, cap, pre], ['raw-hq', 5, k.CAP, null], ['raw-long', 8, k.CAP, null]]) {
        try { const pl = k.buildPayload(long, mode, null, c), qr = k.makeQR(pl.bytes, pre2);
          let got = null; try { got = k.extractPayload(k.readQRFromCanvas(qr.canvas)); } catch (e) {}
          const same = !!got && got.length === pl.bytes.length && got.every((v, i) => v === pl.bytes[i]);
          out[name] = { ok: same, ver: qr.version, bytes: pl.bytes.length, sec: pl.voiceSec };
        } catch (e) { out[name] = { ok: false, err: String(e) }; }
      }
      /* 43文字の書き方の往復（奇数の長さ・0と255を含む） */
      let b43 = true;
      for (const n of [0, 1, 2, 3, 7, 300, 301]) { const a = new Uint8Array(n); for (let i = 0; i < n; i++) a[i] = i % 3 === 0 ? 255 : (i * 37) % 256;
        const r = k.fromB43(k.toB43(a)); b43 = b43 && r.length === n && r.every((v, i) => v === a[i]); }
      out.b43 = b43;
      return out; }""", [pcm])
    for name in ("both", "voice", "melody"):
        r = res[name]
        check(f"カメラで読める形の往復（{name}）", r["same"] and r["url"], f"型番{r['ver']}・{r['bytes']}バイト")
    for name in ("link-hq", "link-long", "raw-hq", "raw-long"):
        r = res[name]
        check(f"いちばん長い声が収まる（{name}）", r["ok"] and r.get("ver") == 40, str(r))
    check("43文字の書き方で元に戻る", res["b43"])
    hq_gap = res["raw-hq"].get("sec", 0) - res["link-hq"].get("sec", 0)
    long_gap = res["raw-long"].get("sec", 0) - res["link-long"].get("sec", 0)
    check("カメラで読める形で短くなるのは約1秒まで", 0 < hq_gap < 1.0 and 0 < long_gap < 1.3, f"音質優先 {hq_gap:.2f}秒・長さ優先 {long_gap:.2f}秒")
    d = page.evaluate("document.getElementById('qrImg').src")
    img = os.path.join(ROOT, ".test-qr.png"); open(img, "wb").write(base64.b64decode(d.split(",")[1]))
    page.click("#tabRead"); page.set_input_files("#photoFile", img)
    page.wait_for_selector("#resultCard:not([hidden])", timeout=10000)
    page.click("#playBtn"); page.wait_for_timeout(1200)
    st = page.evaluate("(() => { const a = __koe.audio(); return a ? { paused: a.paused, t: a.currentTime } : null })()")
    check("写真から読み取って再生できる", bool(st) and not st["paused"] and st["t"] > 0.3, str(st))
    os.remove(img)

    # カメラで読んだときに開くアドレス（# の後ろに中身）で開く
    code = page.evaluate("""([pcm]) => { const k = __koe;
      const mel = k.parseMelody(document.getElementById('melText').value);
      return k.toB43(k.buildPayload(Int16Array.from(pcm), 5, k.encodeMelody(mel.notes, 108, 2), k.capLink(k.CANON)).bytes); }""", [pcm])
    p2 = b.new_page(viewport={"width": 400, "height": 860})
    p2.on("pageerror", lambda e: errs.append(str(e)))
    p2.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p2.goto(URL + "#" + code)
    p2.wait_for_selector("#linkCard:not([hidden])", timeout=15000)
    txt = p2.inner_text("#linkText")
    p2.click("#linkPlay"); p2.wait_for_timeout(1200)
    st = p2.evaluate("(() => { const a = __koe.audio(); return a ? { paused: a.paused, t: a.currentTime } : null })()")
    check("アドレスで開くと届いた声が出て再生できる", "秒の声" in txt and bool(st) and not st["paused"] and st["t"] > 0.3, f"{txt} {st}")
    p2.goto(URL + "#ABC%"); p2.reload()
    p2.wait_for_selector("#linkMsg:not([hidden])", timeout=15000)
    check("壊れたアドレスでは読めないと知らせる", p2.is_hidden("#linkCard"))
    # ひとこと（種類3）と「リンクで送る」
    MSG = "はなより お誕生日おめでとう🎂"
    ctx = b.new_context(viewport={"width": 400, "height": 860})
    ctx.add_init_script("""window.__shared = []; navigator.share = async d => { window.__shared.push(d); };""")
    p5 = ctx.new_page(); p5.on("pageerror", lambda e: errs.append(str(e)))
    p5.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p5.goto(URL); p5.wait_for_selector("#outCard:not([hidden])", timeout=15000)
    rt = p5.evaluate("""([pcm, msg]) => { const k = __koe;
      const pl = k.buildPayload(Int16Array.from(pcm), 5, null, k.CAP, new TextEncoder().encode(msg));
      const c = k.parsePayload(pl.bytes); return { text: c.text, voice: c.voice ? c.voice.seconds : 0 }; }""", [pcm, MSG])
    check("ひとことが往復する", rt["text"] == MSG and rt["voice"] > 2.9, str(rt))
    cap0 = p5.inner_text("#capHq")
    p5.fill("#msgText", MSG); p5.wait_for_timeout(700)
    cap1 = p5.inner_text("#capHq"); qcap = p5.inner_text("#qrCap")
    check("ひとことがQRの説明に出る", MSG in qcap, qcap)
    p5.click("#shareBtn"); p5.wait_for_timeout(300)
    sh = p5.evaluate("window.__shared")
    url = sh[0]["url"] if sh else ""
    check("リンクで送るで共有メニューにリンクとひとことを渡す", bool(url) and "#" in url and MSG in sh[0]["text"], (url[:40] + "…") if url else str(sh))
    p6 = ctx.new_page(); p6.on("pageerror", lambda e: errs.append(str(e)))
    p6.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p6.goto(URL + url[url.index("#"):])
    p6.wait_for_selector("#linkCard:not([hidden])", timeout=15000)
    frm = p6.inner_text("#linkFrom")
    p6.click("#linkPlay"); p6.wait_for_timeout(1200)
    st = p6.evaluate("(() => { const a = __koe.audio(); return a ? { paused: a.paused, t: a.currentTime } : null })()")
    check("送ったリンクを開くと、ひとことが出て聞ける", MSG in frm and bool(st) and not st["paused"], f"{frm} {st}")
    ctx.close()
    # 共有メニューがない端末では、リンクをコピーする
    ctx = b.new_context(viewport={"width": 400, "height": 860})
    ctx.add_init_script("""delete Navigator.prototype.share; window.__copied = '';
      Object.defineProperty(navigator, 'clipboard', { get: () => ({ writeText: async t => { window.__copied = t; } }) });""")
    p7 = ctx.new_page(); p7.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p7.goto(URL); p7.wait_for_selector("#outCard:not([hidden])", timeout=15000)
    p7.click("#shareBtn"); p7.wait_for_timeout(300)
    check("共有メニューがなければリンクをコピーする", "#" in p7.evaluate("window.__copied") and p7.is_visible("#shareMsg"))
    p7.check("#rawFmt"); p7.wait_for_timeout(300)
    check("最大の長さの形では「リンクで送る」を出さない", p7.is_hidden("#shareBtn"))
    ctx.close()

    # iPhoneのホーム画面から開いたときの印刷（共有メニューにQRの画像を渡す）
    ctx = b.new_context(viewport={"width": 400, "height": 860},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
    ctx.add_init_script("""Object.defineProperty(navigator, 'standalone', { get: () => true });
      window.__shared = []; navigator.canShare = d => !!(d && d.files && d.files.length);
      navigator.share = async d => { window.__shared.push(d.files.map(f => ({ name: f.name, type: f.type, size: f.size }))); };
      window.print = () => { window.__printed = true; };""")
    p3 = ctx.new_page(); p3.on("pageerror", lambda e: errs.append(str(e)))
    p3.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p3.goto(URL); p3.wait_for_selector("#outCard:not([hidden])", timeout=15000); p3.wait_for_timeout(500)
    p3.click("#printBtn"); p3.wait_for_timeout(300)
    sh = p3.evaluate("({ shared: window.__shared, printed: !!window.__printed })")
    ok_share = bool(sh["shared"]) and sh["shared"][0][0]["type"] == "image/png" and sh["shared"][0][0]["size"] > 1000 and not sh["printed"]
    check("iPhoneのホーム画面では印刷ボタンで共有メニューにQRの画像を渡す", ok_share, str(sh))
    ctx.close()
    p4 = b.new_page(); p4.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p4.add_init_script("window.print = () => { window.__printed = true; };")
    p4.goto(URL); p4.wait_for_selector("#outCard:not([hidden])", timeout=15000)
    p4.click("#printBtn"); p4.wait_for_timeout(200)
    check("ほかの端末では印刷ボタンでそのまま印刷する", p4.evaluate("!!window.__printed"))
    # メロディの見本ボタン：押したものに印が付き、書きかえると外れる
    p8 = b.new_page(viewport={"width": 400, "height": 860}); p8.on("pageerror", lambda e: errs.append(str(e)))
    p8.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    p8.goto(URL); p8.wait_for_function("window.__koe && __koe.ready()", timeout=15000)
    pressed = lambda: p8.evaluate("[...document.querySelectorAll('[data-sample]')].map(b => b.getAttribute('aria-pressed'))")
    first = pressed()
    p8.click("[data-sample=ryukyu]"); after = pressed()
    p8.fill("#melText", "ド レ ミ"); p8.dispatch_event("#melText", "input"); edited = pressed()
    check("押したメロディの見本に印が付き、書きかえると外れる",
          first == ["true", "false", "false"] and after == ["false", "false", "true"] and edited == ["false", "false", "false"], f"{first} {after} {edited}")

    # にせのカメラの映像を作る（10秒の声が入った細かいQRを、1280×720 の灰色の背景の真ん中に、少しぼかして置く）
    gray = page.evaluate("""([pcm]) => { const k = __koe; const long = new Int16Array(8000*10);
      for (let i = 0; i < long.length; i++) long[i] = pcm[i % pcm.length];
      const pl = k.buildPayload(long, 5, null, k.capLink(k.CANON)), qr = k.makeQR(pl.bytes, k.CANON + '#');
      const c = qr.canvas, d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data, g = [];
      for (let i = 0; i < d.length; i += 4) g.push(d[i]); return { w: c.width, h: c.height, g, ver: qr.version }; }""", [pcm])
    W, H = 1280, 720
    frame = bytearray([150]) * (W * H)
    qw, qh, g = gray["w"], gray["h"], gray["g"]
    ox, oy = (W - qw) // 2, (H - qh) // 2
    for y in range(qh):
        for x in range(qw):
            if 0 < x < qw - 1 and 0 < y < qh - 1:
                v = (g[y*qw+x]*4 + g[y*qw+x-1] + g[y*qw+x+1] + g[(y-1)*qw+x] + g[(y+1)*qw+x]) // 8
            else:
                v = g[y*qw+x]
            frame[(oy+y)*W + ox+x] = 30 + v * 190 // 255
    y4m = os.path.join(ROOT, ".test-cam.y4m")
    with open(y4m, "wb") as f:
        f.write(f"YUV4MPEG2 W{W} H{H} F10:1 Ip A1:1 C420jpeg\n".encode())
        chroma = bytes([128]) * (W * H // 2)
        for _ in range(3):
            f.write(b"FRAME\n"); f.write(frame); f.write(chroma)
    bc = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", f"--use-file-for-fake-video-capture={y4m}"])
    pc = bc.new_page(viewport={"width": 400, "height": 860}); pc.on("pageerror", lambda e: errs.append(str(e)))
    pc.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pc.goto(URL); pc.wait_for_function("window.__koe && __koe.ready()", timeout=15000)
    pc.click("#tabRead"); pc.click("#camBtn")
    try:
        pc.wait_for_selector("#resultCard:not([hidden])", timeout=20000); txt = pc.inner_text("#rdText")
    except Exception:
        txt = pc.inner_text("#readMsg")
    check("カメラの映像から細かいQRを読み取れる", "秒の声" in txt and pc.is_hidden("#camBox"), f"型番{gray['ver']} {txt}")
    bc.close(); os.remove(y4m)
    check("ページのエラーなし", not errs, "; ".join(errs))
    b.close()
sys.exit(0 if ok else 1)
