#! /usr/bin/env python3
import argparse
import enum
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def is_unpacked_symdir(path: Path) -> bool:
    """Check if the path is an unpacked library folder
    (i.e. a folder that contains .kicad_sym files)
    """
    if not path.is_dir():
        return False

    for child in path.iterdir():
        if child.is_file() and child.suffix == ".kicad_sym":
            return True

    return False


class ParseState(enum.Enum):
    """State of the parser when packing libraries."""

    HEADER = 1
    SYMBOL = 2
    FOOTER = 3


@dataclass
class SymInfo:
    name: str
    extend: str | None = None
    content: list[str] = field(default_factory=list)


@dataclass
class ParseModel:
    """
    Parser state for one .kicad_sym file.
    """

    state: ParseState = ParseState.HEADER
    curr_sym_name: str | None = None
    curr_sym_extend: str | None = None
    curr_sym_lines: list[str] = field(default_factory=list)
    header: list[str] = field(default_factory=list)
    footer: list[str] = field(default_factory=list)
    all_syms: list[SymInfo] = field(default_factory=list)


@dataclass
class PackRecord:
    output_path: Path
    n_syms: int


class KicadSymParser:
    """Class to parse a .kicad_sym file and extract symbol information.

    Note that this is not a full parser for .kicad_sym files, but exploits certain
    formatting assumptions to be able to parse the files without a full s-expression parser.
    """

    def parse(self, sym_content: Iterable[str]) -> ParseModel:
        state = ParseModel()

        def handle_sym_name(line: str) -> None:
            match = re.search(r'"(.*?)"', line)
            if not match:
                raise ValueError(f"Could not parse symbol name from: {line!r}")
            symname = match.group(1)
            state.curr_sym_name = symname
            state.curr_sym_lines = [line]

        def finalise_sym() -> None:
            state.all_syms.append(
                SymInfo(
                    name=state.curr_sym_name,
                    extend=state.curr_sym_extend,
                    content=state.curr_sym_lines,
                )
            )

        for line in sym_content:

            if state.state == ParseState.HEADER:
                if line.startswith("\t(symbol "):
                    state.state = ParseState.SYMBOL
                    handle_sym_name(line)
                else:
                    state.header.append(line)
            elif state.state == ParseState.SYMBOL:
                if line.startswith("\t(symbol "):
                    # We are starting a new symbol, so we save the previous one (if it exists) and start a new one
                    finalise_sym()
                    handle_sym_name(line)
                elif line == ")\n":
                    # End of symbols, done
                    finalise_sym()
                    state.footer.append(line)
                    state.state = ParseState.FOOTER
                else:
                    # We are inside a symbol definition, so we just add the line to the current symbol's lines

                    # If we need to
                    if line.startswith("\t\t(extends "):

                        match = re.search(r'"(.*?)"', line)
                        if not match:
                            raise ValueError(
                                f"Could not parse extended symbol name from: {line!r}"
                            )
                        state.curr_sym_extend = match.group(1)

                    state.curr_sym_lines.append(line)
            elif state.state == ParseState.FOOTER:
                pass

        return state


class LibPacker:
    """Class to pack KiCad symbol libraries into one-file .kicad_sym files."""

    def __init__(self, output_folder: Path) -> None:
        self.output_folder = output_folder
        self.packed_libs: list[PackRecord] = []

    def pack(self, unpacked_path: Path) -> None:
        """Pack the library into a .kicad_sym file."""

        full_path = unpacked_path.resolve()

        base, _ = os.path.splitext(full_path.name)
        libname = base + ".kicad_sym"

        logging.info(
            f"Packing library {full_path} into {self.output_folder / libname}..."
        )

        syms: list[SymInfo] = []
        header: list[str] = []
        footer: list[str] = []
        parser = KicadSymParser()

        for child in sorted(full_path.iterdir()):
            if child.is_file() and child.suffix == ".kicad_sym":
                logging.debug(f"Parsing {child}...")

                with open(child, "r", encoding="utf-8") as f:
                    content = f.readlines()

                state = parser.parse(content)

                logging.debug(f"Found {len(state.all_syms)} symbols in {child}.")

                # Use header/footer from the first file
                # If files have different headers/footers...they shouldn't do that.
                if not header:
                    header = state.header
                if not footer:
                    footer = state.footer

                syms.extend(state.all_syms)

        logging.debug(f"Found {len(syms)} symbols in total.")

        # Reorder here if needed (e.g. to put base symbols before extended ones)
        syms.sort(key=lambda sym: sym.name)

        os.makedirs(self.output_folder, exist_ok=True)

        packed_lib_path = self.output_folder / libname

        with open(packed_lib_path, "w") as f:
            f.writelines(header)

            for sym in syms:
                f.writelines(sym.content)

            f.writelines(footer)

        self.packed_libs.append(
            PackRecord(
                output_path=packed_lib_path,
                n_syms=len(syms),
            )
        )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Pack KiCad symbol libraries into one-file .kicad_sym files."
    )

    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        nargs="+",
        help="Input library files or folders.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output folder for the packed .kicad_sym files.",
    )
    parser.add_argument(
        "--table",
        type=Path,
        help="Path to the symbol library table file to update with packed libraries.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (use -v, -vv for more verbosity).",
    )

    parser.epilog = """Examples:
  Pack the whole kicad-symbols repo:
    kicad_lib_pack.py -i path/to/kicad-symbols -o packed_path

  Pack a single library:
    kicad_lib_pack.py -i path/to/kicad-symbols/Library.kicad_symdir -o packed_path
    """
    parser.formatter_class = argparse.RawDescriptionHelpFormatter

    args = parser.parse_args()

    if args.verbose == 1:
        logging.basicConfig(level=logging.INFO)
    elif args.verbose >= 2:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    packer = LibPacker(args.output)

    if not args.input:
        parser.error("No input files or folders specified.")
        exit(1)

    for input_path in args.input:
        if is_unpacked_symdir(input_path):
            packer.pack(input_path)

        else:
            # Look for unpacked symdirs inside the input path
            for child in sorted(input_path.iterdir()):
                if is_unpacked_symdir(child):
                    packer.pack(child)

    total_syms = sum(record.n_syms for record in packer.packed_libs)

    logging.info(
        f"Packed {len(packer.packed_libs)} libraries with a total of {total_syms} symbols."
    )

    if args.table:
        logging.info(f"Updating symbol library table {args.table}...")

        table_content = []
        n_updates = 0

        with open(args.table, "r", encoding="utf-8") as f:

            for line in f:
                # Update paths to point to the new packed libraries

                for record in packer.packed_libs:
                    # if we find a line that references the old unpacked library, we replace it with the new packed library path
                    if record.output_path.stem in line:
                        line = line.replace(".kicad_symdir", ".kicad_sym")
                        n_updates += 1
                        break

                table_content.append(line)

        # Ensure this is a library table file by checking for the expected header
        if not table_content or not table_content[0].startswith("(sym_lib_table"):
            logging.error(
                f"The specified table file {args.table} does not appear to be a valid symbol library table."
            )
            exit(1)

        output_path = args.output / args.table.name

        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(table_content)

        logging.info(f"Updated symbol library table {output_path} with new packed library paths ({n_updates} updates).")
