# 声のQR

録音した声と、ドレミや工工四（くんくんしー）で書いたメロディを、QRコードの中にそのまま入れる試作アプリです。
読み取りも再生も端末の中だけで行うので、一度開いてホーム画面に追加すれば、ネットがなくても使えます。

- 声：Codec2 で圧縮し、QRコード1枚に約15秒（音質優先）〜約26秒（長さ優先）
- メロディ：楽譜データとして入れ、読み取った端末で三線・オルゴール・ピアノの音に合成（1枚に最大約1,100音）
- QRの中身は独自形式（先頭が `VQ`）のため、スマホの標準カメラではなく、このアプリで読み取ります

## 使っているもの
- [Codec2](https://github.com/drowe67/codec2)（LGPL-2.1）… WebAssemblyにビルドして同梱
- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator)（MIT）
- [jsQR](https://github.com/cozmo/jsQR)（Apache-2.0）

工工四の音高は本調子（合＝ド、工＝上のド、尺＝シ♭、尺#＝シ）で鳴らしています。

QRコードは株式会社デンソーウェーブの登録商標です。

## 開発のしかた
- 編集するのは `src/app.html`。`python3 tools/build.py` で公開用の `index.html` と `sw.js` を作り、`python3 tools/test.py` で動作を確かめる。
- `main` 以外のブランチに送ると、7日間有効の確認用アドレス（Firebaseのプレビュー）に自動で公開される。
- `main` に入ると https://koe-qr.web.app/ に自動で公開される。
- 詳しい決まりごとは `CLAUDE.md` を参照。
