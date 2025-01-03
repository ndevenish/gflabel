# GFLabel

Generates 3d printable labels for labelled [gridfinity][gridfinity] bins (such as
[pred][pred], [Cullen J Webb][webb] and [Modern Gridfinity Case][modern] labels), and similar
generate-smallish-printable-label uses. Leverages [build123d][build123d].

[gridfinity]: https://gridfinity.xyz/
[pred]: https://www.printables.com/model/592545-gridfinity-bin-with-printable-label-by-pred-parame
[webb]: https://makerworld.com/en/models/446624
[build123d]: https://github.com/gumyr/build123d

## State

This is a hobby project. Thus:

- Updates and attention to this project can come intermittently (although I
  will try to respond to outright bugs).
- It has a lot of rough edges, not the least that the output is messy and
  snot very useful. And functionality not used much might not work well.
- It sometimes needs manual encouragement to make labels looking good or
  consistent.
- A habit of sometimes crashing OCP when geometry is a little bit odd.


## Usage

### Installation

You should be able to install into your favorite python-virtual-environment
manager by just using pip:

```
pip install gflabel
```

This should work on most modern platforms, but with the following caveats:

- Linux wheels for the dependency cadquery-ocp are only available on
  resonably modern (e.g. Ubuntu 22.4+) linux distributions, so you may have to
  go to conda to install on an older machine.

[install_build123d]: https://build123d.readthedocs.io/en/latest/installation.html#special-notes-on-apple-silicon-installs

Otherwise, you can check out this repository and `pip install` it directly, or
install directly from the github repo:

```
pip install git+https://github.com/ndevenish/gflabel.git
```
### VSCode Preview

If you are using VSCode with the [vscode-ocp-cad-viewer][ocp-vscode] extension,
you can add the `--vscode` flag when running `gflabel`, and the label should
show up as a preview. This saves opening the output CAD files in a slicer or
other viewer, and is useful when prototyping labels.

[ocp-vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer

### Basic Examples

By default, labels are written to an output file "`label.step`". You can change
this with `-o FILENAME`. `.step`, `.stl` and `.svg` are recognised

A simple, single label generation on a pred-style base:

```
gflabel pred "Basic Label" -o basic.step
```
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_basic.png)

Symbols are specified with `{` curly braces `}`. If you specify more labels
than divisions (which defaults to one), then multiple labels will be generated
with a single call:

```
gflabel pred "{nut}M2" "{nut}M3" "{nut}M4"
```

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_multi.png)

Or, if you specify divisions, then you can generate a multi-bin label (in this
example, a margin is also added to ensure that the labels are not too dense):
```
gflabel pred --width 2 --divisions=3 "{nut}M2" "{nut}M3" "{nut}M4" --vscode --margin=2
```
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_multibin.png)

You can span multiple lines, mix text and symbols, and some symbols can be
passed configuration (e.g. in this case the bolt length is dynamically
specified as  20mm):
```
gflabel pred "{head(hex)} {bolt(20)}\nM2×20"
```
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_boltbin.png)

Some symbols can also take many modifiers for e.g. drive or head type:

```
gflabel pred "{head(+)} {bolt(50,slotted,round)}\nM3×50"
```
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_bolt_broken.png)

And multiple label styles/symbol styles/fonts can be selected:
```
gflabel cullenect --font=Arial "M3×20{...}{cullbolt(+)}"
```
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_webb.png)

Here's a more complex example, generating a [Pred Gridfinity Storage Box][predbox]
label. This uses multiple proportioned columns, symbols, and alignment:

```
gflabel predbox -w 5 "HEX\n{head(hex)} {bolt(5)}{3|}{<}M2\nM3\nM4\nM5{2|2}{<}M6\nM8\nM10\n"
```

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/example_hex.png)

## Command Parameters

The full command parameter usage (as generate by `gflabel --help`):

```
usage: gflabel [-h] [--vscode] [-w WIDTH] [--height HEIGHT] [--depth DEPTH_MM] [--no-overheight] [-d DIVISIONS] [--font FONT]
               [--font-size-maximum FONT_SIZE_MAXIMUM | --font-size FONT_SIZE] [--font-style {regular,bold,italic}] [--font-path FONT_PATH]
               [--margin MARGIN] [-o OUTPUT] [--style {embossed,debossed,embedded}] [--list-fragments] [--list-symbols] [--label-gap LABEL_GAP]
               [--column-gap COLUMN_GAP] [-v] [--version VERSION]
               BASE LABEL [LABEL ...]

Generate gridfinity bin labels

positional arguments:
  BASE                  Label base to generate onto (pred, plain, none, cullenect, predbox).
  LABEL

options:
  -h, --help            show this help message and exit
  --vscode              Run in vscode_ocp mode, and show the label afterwards.
  -w WIDTH, --width WIDTH
                        Label width. If using a gridfinity standard base, then this is width in U. Otherwise, width in mm.
  --height HEIGHT       Label height, in mm. Ignored for standardised label bases.
  --depth DEPTH_MM      How high (or deep) the label extrusion is.
  --no-overheight       Disable the 'Overheight' system. This allows some symbols to oversize, meaning that the rest of the line will first shrink
                        before they are shrunk.
  -d DIVISIONS, --divisions DIVISIONS
                        How many areas to divide a single label into. If more labels that this are requested, multiple labels will be generated.
                        Default: 1.
  --font FONT           The name of the system font to use for rendering. If unspecified, a bundled version of Open Sans will be used. Set GFLABEL_FONT
                        in your environment to change the default.
  --font-size-maximum FONT_SIZE_MAXIMUM
                        Specify a maximum font size (in mm) to use for rendering. The text may end up smaller than this if it needs to fit in the area.
  --font-size FONT_SIZE
                        The font size (in mm) to use for rendering. If unset, then the font will use as much vertical space as needed (that also fits
                        within the horizontal area).
  --font-style {regular,bold,italic}
                        The font style use for rendering. [Default: regular]
  --font-path FONT_PATH
                        Path to font file, if not using a system-level font.
  --margin MARGIN       The margin area (in mm) to leave around the label contents. Default is per-base.
  -o OUTPUT, --output OUTPUT
                        Output filename(s). [Default: []]
  --style {embossed,debossed,embedded}
                        How the label contents are formed.
  --list-fragments      List all available fragments.
  --list-symbols        List all available electronic symbols
  --label-gap LABEL_GAP
                        Vertical gap (in mm) between physical labels. Default: 2 mm
  --column-gap COLUMN_GAP
                        Gap (in mm) between columns
  -v, --verbose         Verbose output
  --version VERSION     The version of geometry to use for a given label system (if a system has versions). [Default: latest]
```

## Defining Labels

Labels can consist of:

- A physical base, which is the object that the labels are extruded out of
  (or cut into).
- A label style, which specifies whether the label is raised out of, cut into,
  or flush with the surface of the base.
- Regular text, including unicode symbols (although complex symbols like emoji
  are unlikely to render properly, or at all - this is down to the underlying
  library).
- Newlines, either explicitly typed in (e.g. at the terminal), or escaped by
  writing `\n` in the label definition. Each line will be rendered separately,
  but still constrained to the same label area.
- Fragments. These are directives enclosed in `{`curly`}` braces that add
  symbols or define an area on the label.

Let's go through each of these:

### Label Bases

The base (specified by `--base=TYPE`) defines the shape of what the label is generated on top of. Currently, the following bases are understood:

| Base | Description | Image |
| ---- | ----------- | ----- |
| `pred` | For [Pred's parametric labelled bins][predlabel] labels. If specifying this style, then height is ignored and width is in gridfinity units (e.g. `--width=1` for a label for a single 42mm bin). | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/base_pred.png) |
| `predbox` | For labels matching the style of [Pred's Parametric Storage Box][predbox]. These are larger (~25 mm) labels for slotting in the front of the parametric storage boxes. `--width` is for the storage bin width, and is 4, 5, 6, or 7 u. | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/base_predbox.png)
| `plain` | For a blank, square label with a chamfered top edge. The specified width and height will be the whole area of the label base. You must specify at least a width. | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/base_plain.png)
| `cullenect` | For [Cullen J Webb's ](https://makerworld.com/en/models/446624) swappable label system. Label is a 36.4 mm x 11 mm rounded rectangle with snap-fit inserts on the back. Use without margins to match the author's style labels. | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/base_cullenect.png)
| `modern` | For [Modern Gridfinity Case][modern] labels, ~22 mm high labels that slot into the front. `--width` is for the storage bin width, and can be 3, 4, 5, 6, 7 or 8 u. | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/base_modern.png) |
| `none` | For no base at all - the label will still be extruded. This is useful if you want to generate a label model to place onto another volume in the slicer. | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/base_none.png) |

[predlabel]: https://www.printables.com/model/592545-gridfinity-bin-with-printable-label-by-pred-parame
[predbox]: https://www.printables.com/model/543553-gridfinity-storage-box-by-pred-now-parametric
[modern]: https://www.printables.com/model/894202-modern-gridfinity-case

### Label Styles

Label style controls whether the generated label is raised out of, cut into, or
flush with the base surface. This is controlled with the `--style=` parameter,
which can be set to `embossed`, `debossed`, or `embedded`:

| Style    | Description | Image      |
| -------- | ----------- | --------- |
| Embossed | This is the default. The labels contents are extruded upwards out of the base, as raised features. You can print this multicoloured by changing material at a specific layer height. | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/style_embossed.png)
| Debossed | Instead of being raised, the label contents are cut into the base. You can also print this multicoloured by changing material at specific layer height.  | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/style_debossed.png)
| Embedded | The label contents are flush with the surface of the label. This can be printed with a multimaterial system, as it will require material changes within a single layer. You can print this label face-down. To print this, you will need to "Split to Parts" (Bambu/OrcaSlicer) in your slicer and manually change the selected material for the bases.  | ![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/style_embedded.png)

### Text Style, and Fonts

Text is rendered as text on the label, including variable width whitespaces so e.g. a halfspace
will render a halfspace width, which is good for minor separation if you don't want a gap of
specific width.

GFLabel comes with [Open Sans][opensans], and will use this (in regular, bold or italic) if you
don't otherwise specify any font preference.

Options for controlling font rendering are:

| Setting       | Description |
| ------------- | ------------|
| `--font NAME` | Specified font directly, by name. This will have to be a font that is generally installed and available on your system. If you don't specify this (or -path), then a packaged version of Open Sans will be used. |
| `--font-path /path/to/font` | Specify font by directly specifying the location of the font file on disk. Takes precedence over `--font`, so if you specify both, this will be used.
| `--font-style STYLE` | Where `STYLE` can be `bolt`, `italic`, or `regular` (the default). If you haven't specified a font file then the underlying font system will make a best-effort attempt to find your selected font in one of these weights.
| `--font-size NUMBER` | Specifies a fixed height (in mm) for the font on the label. Text will always be rendered at this size, even if it causes the text to not fit. Using this can help text-size consistency over many labels, as otherwise the shorter text labels may end up at a larger scale (because they can fill the vertical without over-running it's available space).
| `--font-size-maximum NUMBER` | Specifies a _maximum_ font size. Text won't be allowed to go larger than this, but text can be shrunk to fit if it would otherwise overrun it's label area. This can help text-size disparity over many labels in cases where some of them are much longer, and you can tolerate them being shrunken. This is used to generate the electrical symbol examples.

### Symbols/Fragments

Along with text, you can add symbols and features to a label by specifying
"fragments". These are directives enclosed in `{`curly braces`}`.

A list of all the fragments currently recognised:

| Names             | Description                                                       |
|-------------------|-------------------------------------------------------------------|
| ...               | Blank area that always expands to fill available space.<br><br>If specified multiple times, the areas will be balanced between<br>entries. This can be used to justify/align text. |
| 1, 4.2, ...       | A gap of specific width, in mm.                                   |
| &lt;, &gt;        | Only used at the start of a single label or column. Specifies that all lines in the area should be left or right aligned. Invalid when specified elsewhere. |
| bolt              | Variable length bolt, in the style of Printables pred-box labels.<br><br>If the requested bolt is longer than the available space, then the<br>bolt will be as large as possible with a broken thread. |
| box               | Arbitrary width, height centered box. If height is not specified, will expand to row height. |
| circle            | A filled circle.                                                  |
| head              | Screw head with specifiable head-shape.                           |
| hexhead           | Hexagonal screw head. Will accept drives, but not compulsory.     |
| hexnut, nut       | Hexagonal outer profile nut with circular cutout.                 |
| nut_profile       | Rectangle with two horizontal lines, as the side view of a hex nut. |
| locknut_profile   | Rectangle with two horizontal lines, as the side view of a hex nut, with an added "top bump". |
| lockwasher        | Circular washer with a locking cutout.                            |
| magnet            | Horseshoe shaped magnet symbol.                                   |
| measure           | Fills as much area as possible with a dimension line, and shows the length. Useful for debugging. |
| sym, symbol       | Render an electronic symbol.                                      |
| threaded_insert   | Representation of a threaded insert.                              |
| variable_resistor | Electrical symbol of a variable resistor.                         |
| washer            | Circular washer with a circular hole.                             |
| cullbolt          | Alternate bolt representation incorporating screw drive, with fixed length, as used by the [Cullenect][cullenect] system. |
| `\|` (pipe)       | Denotes a column edge, where the label should be split. You can specify relative proportions for the columns, as well as specifying the column alignment. |

A basic set of examples showing the usage of some of these:

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/examples.svg)

### Bolt/Screw Drives

The `{head(...)}` fragment, and any other fragments that will accept drive
head types, takes a feature specification for the kind of drive that you want
to represent. These are stackable, so you can specify multiple drives and they
will be overlapped. Examples of using the drive types are:

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/drives.svg)

### Bolts and Screw Heads

There are two classes of bolt/screw representation:

- `bolt` corresponding to the [Pred's printable label bin](https://www.printables.com/model/592545-gridfinity-bin-with-printable-label-by-pred-parame) bolt style. This is
  used simple as `{bolt(LENGTH)}`, where `LENGTH` is the length of the bolt/
  screw stem that you want (excluding the height of the head). If the label
  area is too small to fit the entire bolt on, then the bolt will be rendered
  with a "break" in the middle, indicating that it does not show the whole
  bolt length. It will also accept a `slot` feature that marks a small indent
  on the top of the head, and `flanged` in order to render a washer-style
  flange at the bottom of the active head.
- `cullbolt` corresponding to the bolt style included with [Cullen J Webb's swappable
  gridfinity label][cullenect] system. It doesn't
  change length, but it will accept any combination of screw drive specifier
  and display them in the bolt head.

[cullenect]: https://makerworld.com/en/models/446624

Both types of bolts will accept a head style, one of `pan`, `socket`, `round`,
or `countersunk`. Both can be marked as `tapping` to have a pointed tip, and
both can be pointed backwards by adding the `flipped` feature.

Examples showing some differences between the two bolts:

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/bolts.svg)

### Multiple Columns

Although the division system (`--divisions`) can be used to create a single
label with multiple areas (e.g. the intended usage is for labels for a divided
gridfinity bin that has e.g. more bins than gridfinity units), it isn't as
flexible as the column separator fragment, `{|}` (using the pipe symbol).

In the simple case, this just separates the areas mostly the same as if you had
divided the bin, except that column mode has an explicit (and default) column
gap (controled by `--column-gap`). Here's a label split into three with
divisions (left), and columns(right):

```
$ gflabel predbox -w=3 --divisions=3 "A\n{measure}" "B\n{measure}" "C\n{measure}"
$ gflabel predbox -w=3               "A\n{measure}{|}B\n{measure}{|}C\n{measure}"
```
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/column_division.svg)
![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/column_basic.svg)

> [!NOTE]
> `{measure}` fragments have been added to make it easy to see how the layout
> is being affected.

However, with columns you can specify the proportions each column should be in
relation to each other, by specifying the proportion each side of the pipe e.g.
`{2|1}`. If unspecified, then the column is assumed to be proportion 1 compared
to whatever the other side is.

In this example, we've asked for 4:1:2 scaling:

```
$ gflabel predbox -w=5 "A\n{measure}{4|}B\n{measure}{1|2}C\n{measure}"
```

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/column_basic_proportion.svg)

And here, we're combining the column fragments with the alignment fragment.
Alignment markers can go at the start of any column:

```
gflabel predbox -w=5 "{<}A\n{measure}{4|}{>}B\n{measure}{1|2}{<}C\n{measure}"
```

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/column_basic_proportion_align.svg)


### Electronic Symbols

Electronic symbols can be generated using the `{symbol(...)}` fragment.
GFLabel is using the [Chris Pikul Electronic Symbols ][pikul] library kindly
released under MIT License.

[pikul]: https://github.com/chris-pikul/electronic-symbols

There are currently three main approaches to selecting the symbol that you
want:

- Exact [ID][ID], or exact [Filename][files], as defined the original source.
- Component name, as listed on the symbol source [README][pikul] (and in the
  table below). In cases where multiple symbols have the same name, they can
  be differentiated by standard e.g. `{symbol(capacitor,iec)}`. If standard is
  not specified, and there are multiple matches, then the first of [`common`,
  `iec`, `ieee`] will be chosen (if doing so makes it unambiguous).
- Fuzzy matching. You can pass in words or parts of words. Symbols with
  category, name or ID that match these (in any order) will be selected. If
  more than one candidate symbols matches, then the table of possible matches
  will be returned so that you can refine it further.

You can list all of the symbols available with `gflabel --list-symbols`.

For an example of this fuzzy matching, the fragment `{symbol(ground)}` isn't
enough to disambiguate between the possible options, so the table of matches
is printed to help you refine the definition:

```
$ gflabel [...] '{symbol(ground)}'
...
Could not decide on symbol from fuzzy specification "ground". Possible options:
    ID                 Category Name                  Standard Filename
    ground-com-signal  GROUND   Digital/Signal Ground COMMON   Ground-COM-Signal
    ground-com-general GROUND   Common/Earth Ground   COMMON   Ground-COM-General
    ground-com-chassis GROUND   Chassis Ground        COMMON   Ground-COM-Chassis

Could not proceed: Please specify symbol more precisely.
```

Given this, you could disambiguate by refining the fuzzy specification e.g.
`{symbol(signal ground)}`, matching the exact name `{symbol(Common/Earth Ground)}`,
or specifying the ID/Filename exactly: `{symbol(Ground-COM-Signal)}`.

[ID]: https://github.com/chris-pikul/electronic-symbols/blob/main/manifest.json
[files]: https://github.com/chris-pikul/electronic-symbols/tree/main/SVG

Here is a table of all symbols, rendered by GFLabel, with their name as per the
source symbol library. Note that for some of the symbols, they are rendered
incorrectly. This is an unresolved bug in GFLabel.

![](https://github.com/ndevenish/gflabel/raw/refs/heads/readme_images/symbols.svg)

# Bundled Dependencies

GFLabel uses (and bundles) a couple of dependencies in subdirectories:
- The [Chris Pikul Electronic Symbols ][pikul] library, MIT License © 2022 Chris Pikul.
- The [Open Sans][opensans] font family, OFL-1.1 License © 2020 The Open Sans Project Authors.


[opensans]: https://github.com/googlefonts/opensans
[pikul]: https://github.com/chris-pikul/electronic-symbols
