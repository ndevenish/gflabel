"""
Generate the example layouts for the README
"""

from __future__ import annotations

import argparse
import glob
import shlex
import shutil
import subprocess
import sys

import gflabel.fragments as fragments

if not shutil.which("svgo"):
    sys.exit("Error: Requires svgo utility (https://svgo.dev/) to be on PATH")

parser = argparse.ArgumentParser(description="Generate example images for GFlabel")

EXAMPLES = ["fragment", "bolt", "drives", "symbols", "columns"]
parser.add_argument("--vscode", help="Run in OCP_vscode mode", action="store_true")

for kind in EXAMPLES:
    parser.add_argument(
        f"--{kind}", help=f"Run the {kind} examples", action="store_true"
    )

args = parser.parse_args()
vscode = ["--vscode"] if args.vscode else []

if all(not x for x in [getattr(args, name) for name in EXAMPLES]):
    for name in EXAMPLES:
        setattr(args, name, True)


def gflabel(*args):
    command = ["gflabel", "-v", *vscode, *args]
    print("+ " + " ".join(shlex.quote(x) for x in command))
    subprocess.run(command, check=True)


def svgo(*args):
    cmd = ["svgo"]
    for arg in args:
        if "*" in arg:
            cmd.extend(glob.glob(arg))
        else:
            cmd.append(arg)
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


if args.fragment:
    EXAMPLES = [
        "L{...}R",
        "{box(35)}",
    ]

    HEAD = "gflabel none -w=100 --height=12 --divisions=3 --vscode"

    command = [
        "none",
        "-w=100",
        "--height=12",
        "--divisions=3",
        "--output=examples.svg",
        "--font-size=7",
    ]

    for frag in fragments.fragment_description_table():
        for example in frag.examples:
            print(frag.names[0], example)
            command.extend([example.replace("{", "{{").replace("}", "}}"), "", example])

    gflabel(*command)

    svgo("examples.svg", "--precision=2")

if args.drives:
    # Generate a table of head drive types
    command = [
        "gflabel",
        "none",
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
        "none",
        "-w=100",
        "--height=12",
        "--divisions=3",
        "--font-size=5",
        "-o",
        "bolts.svg",
        *vscode,
        "bolt(10,",
        "Style",
        "cullbolt",
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
        command.extend([f"{{bolt(10,{text})}}", text, f"{{cullbolt({text})}}"])

    # Bolt-only
    for style in [["slot"], ["pan,flanged"]]:
        text = ",".join(style)
        command.extend([f"{{bolt(10,{text})}}", text, ""])

    # Webb-only
    for style in [["partial"], ["hex", "security"]]:
        text = ",".join(style)
        command.extend(["", text, f"{{cullbolt({text})}}"])

    print("+ " + " ".join(shlex.quote(x) for x in command))
    subprocess.run(command)

if args.symbols:
    manifest = fragments.electronic_symbols_manifest()
    command = [
        "gflabel",
        "none",
        "-w=200",
        "--height=12",
        "--divisions=6",
        "--font-size-maximum=5.3",
        "--output=symbols.svg",
        "--label-gap=3",
        *vscode,
    ]
    names: dict[str, list[str]] = {}
    for sym in manifest:
        names.setdefault(sym["name"], []).append(sym["name"])
    i = -20
    for sym in manifest:
        # Skip symbols known to not work well here
        if sym["id"] in {"transformer-com-center-double"}:
            continue
        i += 1
        if i < 0:
            continue
        name = sym["name"]
        # If we have the same symbol with different standard, say
        if len(names[name]) > 1:
            name += f" ({sym['standard']})"
        # Some very basic attempts at making some of these more readable
        name = (
            name.replace(" Flip-Flop", "\\nFlip-Flop")
            .replace(" Capacitor", "\\nCapacitor")
            .replace("Relay N", "Relay\\nN")
            .replace("MOSFET ", "MOSFET\\n")
            .replace("Pushbutton ", "Pushbutton\\n")
            .replace("Variable Resistor", "Variable\\nResistor")
            .replace("Relay (Common", "Relay\\n(Common")
            .replace(") Converter", ")\\nConverter")
            .replace("Potentiometer ", "Potentiometer\\n")
            .replace("Wave Generator", "Wave\\nGenerator")
            .replace("Controlled ", "Controlled\\n")
            .replace("Photovoltaic Solar", "Photovoltaic\\nSolar")
            .replace("Photoresistor ", "Photoresistor\\n")
            .replace("-Pot ", "-Pot\\n")
            .replace("Inductor ", "Inductor\\n")
            .replace("Amplifier ", "Amplifier\\n")
        )

        command.extend([f"{name}", f"{{symbol({sym['id']})}}"])
        # if i > 20:
        #     break
    print("+ " + " ".join(shlex.quote(x) for x in command))
    subprocess.run(command)

if args.columns:
    # ("division", "A\n{measure}" "B\n{measure}" "C\n{measure}"),

    gflabel(
        "predbox",
        "--width=5",
        "--divisions=3",
        "--box",
        "--output=column_division.svg",
        "A\\n{measure}",
        "B\\n{measure}",
        "C\\n{measure}",
    )

    column_examples = [
        ("basic", "A\n{measure}{|}B\n{measure}{|}C\n{measure}"),
        (
            "basic_proportion",
            "A\n{measure}{4|}B\n{measure}{1|2}C\n{measure}",
        ),  # "A{4|}B\nC{|}D\nE"),
        (
            "basic_proportion_align",
            "{<}A\n{measure}{4|}{>}B\n{measure}{1|2}{<}C\n{measure}",
        ),
    ]

    for name, example in column_examples:
        gflabel(
            "predbox",
            "--width=5",
            "--box",
            f"--output=column_{name}.svg",
            example,
        )

    svgo("column_*.svg", "--precision=2")
