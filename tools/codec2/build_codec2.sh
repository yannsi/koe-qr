#!/usr/bin/env bash
# vendor/codec2.wasm を作り直すときの手順（ふだんは不要）。
# 必要なもの: git, cmake, gcc, python3（pip install ziglang）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"; WORK="$(mktemp -d)"
git clone --depth 1 https://github.com/drowe67/codec2.git "$WORK/codec2"   # 作成時: 310777b1c6f1af0bc7c72f5b32f80f6fd9136962
cmake -S "$WORK/codec2" -B "$WORK/codec2/build" -DUNITTEST=OFF -DCMAKE_BUILD_TYPE=Release >/dev/null
make -C "$WORK/codec2/build" -j"$(nproc)" codec2 >/dev/null     # 符号帳（codebook*.c）を生成するため
S="$WORK/codec2/src"; B="$WORK/codec2/build/src"
python3 -m ziglang cc -target wasm32-wasi -Oz -s -mexec-model=reactor \
  -I"$S" -I"$B" -I"$WORK/codec2/build" \
  -DCODEC2_MODE_EN_DEFAULT=0 -DCODEC2_MODE_1200_EN=1 -DCODEC2_MODE_700C_EN=1 -Wno-everything \
  "$HERE/c2wasm.c" "$S"/{lpc,nlp,postfilter,sine,codec2,codec2_fft,kiss_fft,kiss_fftr,interp,lsp,mbest,newamp1,phase,quantise,pack,codec2_fifo,dump}.c \
  "$B"/{codebook,codebookd,codebookjmv,codebookge,codebooknewamp1,codebooknewamp1_energy,codebooknewamp2,codebooknewamp2_energy}.c \
  -o "$ROOT/vendor/codec2.wasm"
cp "$WORK/codec2/COPYING" "$ROOT/vendor/licenses/codec2-COPYING.txt"
echo "vendor/codec2.wasm を作り直しました"
