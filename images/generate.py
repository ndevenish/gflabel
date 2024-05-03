"""
Generate the example layouts for the README
"""

from __future__ import annotations

import subprocess
import sys

import gflabel.fragments as fragments

vscode = ["--vscode"] if "--vscode" in sys.argv else []
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
# sys.exit(1)

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

# sys.exit(1)

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
