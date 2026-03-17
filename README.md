# thvo-kicad-lib

Personal KiCad symbol and footprint library.

## Symbols packing

The Python script `kicad_lib_pack.py` is taken from https://gitlab.com/kicad/libraries/kicad-symbols to pack symbol library inside `.kicad_symdir` directory into a single `.kicad_sym` file.

Run the Python script:

```bash
python3 kicad_lib_pack.py --input lib_symbol.kicad_symdir --output . -v
```
