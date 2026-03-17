# thvo-kicad-lib

Personal KiCad symbol and footprint library.

## Symbols packing

The Python script `kicad_lib_pack.py` is taken from https://gitlab.com/kicad/libraries/kicad-symbols to pack symbols library inside `.kicad_symdir` directory into a single `.kicad_sym` file.

Run the Python script:

```bash
python3 kicad_lib_pack.py --input lib_symbol.kicad_symdir --output . -v
```

## Installation

### Add library to KiCad:
- symbols: `lib_symbol.kicad_sym`
- footprints: `lib_footprint.pretty`
- models: `lib_model.3dshapes`

### Clone to fresh KiCad project and add library tables as Project Specific Libraries

```bash
cd kicad_project_dir

# git clone
git clone https://github.com/thvofi/thvo-kicad-lib.git
# or add as git submodule
git submodule add https://github.com/thvofi/thvo-kicad-lib.git thvo-kicad-lib

cd thvo-kicad-lib
./install_lib.sh
```

Installation script does:
- run Python packing script for symbols library
- copy library tables in `/lib-table` to `kicad_project_dir`
