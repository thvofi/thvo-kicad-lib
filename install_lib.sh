#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Packing library..."
rm -f "$SCRIPT_DIR/lib_symbol.kicad_sym"
python3 "$SCRIPT_DIR/kicad_lib_pack.py" \
    --input "$SCRIPT_DIR/lib_symbol.kicad_symdir" \
    --output "$SCRIPT_DIR" \
    -v

echo ""
read -p "Install library files to project? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing to project..."
    cp "$SCRIPT_DIR/lib-table/sym-lib-table" "$SCRIPT_DIR/../"
    cp "$SCRIPT_DIR/lib-table/fp-lib-table" "$SCRIPT_DIR/../"
    cp "$SCRIPT_DIR/lib-table/design-block-lib-table" "$SCRIPT_DIR/../"
    echo "Done!"
else
    echo "Skipped installation."
fi
