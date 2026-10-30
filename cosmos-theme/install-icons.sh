#!/bin/zsh
# Put the Cosmos icon in place of every Wine-branded .ico (classic red wine glass).
# Run from the cosmos-engine root after patches, with the Wine source tree as $1
# (GitHub: src/sources/wine; local cosmos-build: src/).
set -euo pipefail
ROOT=${0:A:h}
WINE=${1:?usage: install-icons.sh <wine-src>}
ICO=$ROOT/oic_winlogo.ico
[[ -f $ICO ]] || { echo "missing $ICO"; exit 1 }
for rel in \
  dlls/user32/resources/oic_winlogo.ico \
  programs/winecfg/logo.ico \
  programs/winecfg/winecfg.ico \
  programs/winefile/winefile.ico \
  programs/winetest/winetest.ico
do
  dest=$WINE/$rel
  mkdir -p ${dest:h}
  cp -f $ICO $dest
  echo "cosmos icon: $rel"
done
