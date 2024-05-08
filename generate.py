"""
Generate the example layouts for the README
"""

from __future__ import annotations

import argparse
import subprocess

import gflabel.fragments as fragments

parser = argparse.ArgumentParser(description="Generate example images for GFlabel")
parser.add_argument("--vscode", help="Run in OCP_vscode mode", action="store_true")
parser.add_argument("--fragment", help="Run the fragment examples", action="store_true")
parser.add_argument("--bolt", help="Run the bolt examples", action="store_true")
parser.add_argument("--drives", help="Run the drive examples", action="store_true")
parser.add_argument("--symbols", help="Run the symbol examples", action="store_true")

args = parser.parse_args()
vscode = ["--vscode"] if args.vscode else []
if all(not x for x in [args.fragment, args.bolt, args.drives, args.symbols]):
    args.fragment = True
    args.bolt = True
    args.drives = True
    args.symbols = True

if args.fragment:
    EXAMPLES = [
        "L{...}R",
        "{box(35)}",
    ]

    HEAD = "gflabel --base=none -w=100 --height=12 --divisions=3 --vscode"

    command = [
        "gflabel",
        "--base=none",
        "-w=100",
        "--height=12",
        "--divisions=3",
        "-o",
        "examples.svg",
        *vscode,
        "--font-size=7",
    ]

    for frag in fragments.fragment_description_table():
        for example in frag.examples:
            print(frag.names[0], example)
            command.extend([example.replace("{", "{{").replace("}", "}}"), "", example])

    subprocess.run(command)

if args.drives:
    # Generate a table of head drive types
    command = [
        "gflabel",
        "--base=none",
        "-w=100",
        "--height=12",
        "--divisions=4",
        "--font-size=5",
        "-o",
        "drives.svg",
        *vscode,
        # "{{head(DRIVE)}}",
        # "",
        # "",
        # "",
    ]
    drives = [x for x in sorted(fragments.DRIVES) if x != "security"]
    drives.extend(["slot,triangle", "slot,square", "torx,security"])
    for drive in drives:
        command.extend([f"{{...}}{drive}", f"{{head({drive})}}"])
    subprocess.run(command)

if args.bolt:
    # And bolt styles
    command = [
        "gflabel",
        "--base=none",
        "-w=100",
        "--height=12",
        "--divisions=3",
        "--font-size=5",
        "-o",
        "bolts.svg",
        *vscode,
        "bolt(10,",
        "Style",
        "webbolt",
    ]

    for style in [
        ["pan"],
        ["socket"],
        ["round"],
        ["countersunk"],
        ["tapping"],
        ["flipped"],
    ]:
        text = ",".join(style)
        command.extend([f"{{bolt(10,{text})}}", text, f"{{webbolt({text})}}"])

    # Bolt-only
    for style in [["slot"], ["pan,flanged"]]:
        text = ",".join(style)
        command.extend([f"{{bolt(10,{text})}}", text, ""])

    # Webb-only
    for style in [["partial"], ["hex", "security"]]:
        text = ",".join(style)
        command.extend(["", text, f"{{webbolt({text})}}"])

    subprocess.run(command)

if args.symbols:
    manifest = fragments.electronic_symbols_manifest()
    command = [
        "gflabel",
        "--base=none",
        "-w=200",
        "--height=12",
        "--divisions=6",
        "-o",
        "symbols.svg",
        *vscode,
    ]
    names: dict[str, list[str]] = {}
    for sym in manifest:
        names.setdefault(sym["name"], []).append(sym["name"])
    i = 0
    for sym in manifest:
        name = sym["name"]
        # If we have the same symbol with different standard, say
        if len(names[name]) > 1:
            name += f" ({sym['standard']})"
        command.extend([name, f"{{symbol({sym['id']})}}"])
        i += 1
        # if i > 20:
        #     break
    print("+ " + " ".join(command))
    subprocess.run(command)
