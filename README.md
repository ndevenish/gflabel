# GFLabel

Generates labels for labelled gridfinity bins, and similar uses.

## Usage

### Basic Examples

A simple, single label generation on a pred-style base. By default, labels are
written to an output file "`label.step`". You can change this with `-o
FILENAME`. `.step`, `.stl` and `.svg` are recognised:

```
gflabel "Basic Label" -o basic.step
```
![](images/example_basic.png)


Symbols are specified with `{` curly braces `}`. If you specify more labels
than divisions (which defaults to one), then multiple labels will be generated
with a single call:

```
gflabel "{nut}M2" "{nut}M3" "{nut}M4"
```

![](images/example_multi.png)

Or, if you specify divisions, then you can generate a multi-bin label (in this
example, a margin is also added to ensure that the labels are not too dense):
```
gflabel --width 2 --divisions=3 "{nut}M2" "{nut}M3" "{nut}M4" --vscode --margin=2
```
![](images/example_multibin.png)

You can span multiple lines, mix text and symbols, and some symbols can be
passed configuration (e.g. in this case the bolt length is dynamically
specified as  20mm):
```
gflabel "{head(hex)} {bolt(20)}\nM2×20"
```
![](images/example_boltbin.png)

Some symbols can also take many modifiers for e.g. drive or head type:
```
gflabel "{head(+)} {bolt(50,slotted,round)}\nM3×50"
```
![](images/example_bolt_broken.png)

## Command Parameters

Core command parameters (call `gflabel --help` for the full list):

```
usage: gflabel [options] LABEL [LABEL ...]

options:
  --base {pred,plain,none,webb}
                        Label base to generate onto. [Default: pred]
  --vscode              Run in vscode_ocp mode, and show the label afterwards.
  -w WIDTH, --width WIDTH
                        Label width. If using a gridfinity standard base, then
                        this is width in U. Otherwise, width in mm.
  --height HEIGHT       Label height, in mm. Ignored for fixed-height bases.
  --depth DEPTH_MM      How high (or deep) the label extrusion is.
  --divisions DIVISIONS
                        How many areas to divide a single label into. If more
                        labels that this are requested, multiple labels will be
                        generated. Default: 1.
  --font FONT           The font to use for rendering. [Default: Futura]
  --font-size SIZE_MM   The font size (in mm) to use for rendering. By default,
                        this will be adjusted to fit the label horizontal area.
  --margin MARGIN       Margin area (in mm) to leave around the label contents.
  -o FILENAME           Output filename. [Default: label.step]
  --style {embossed,debossed}
                        How the label contents are formed.
  --list-fragments      List all available fragments.
```

## Defining Labels

Labels can consist of:
- Regular text, including unicode symbols (although complex symbols like emoji
  are unlikely to render properly, or at all - this is down to the underlying
  library)
- Newlines, either explicitly typed in (e.g. at the terminal), or 
### Symbols/Fragments

Along with text, you can add symbols and features to a label by specifying
"fragments". These are directives enclosed in `{`curly braces`}`

| Names             | Description                                                       |
|-------------------|-------------------------------------------------------------------|
| ...               | Blank area that always expands to fill available space.<br><br>If specified multiple times, the areas will be balanced between<br>entries. This can be used to justify/align text. |
| &lt;number&gt;    | A gap of specific width, in mm.                                   |
| bolt              | Variable length bolt, in the style of Printables pred-box labels.<br><br>If the requested bolt is longer than the available space, then the<br>bolt will be as large as possible with a broken thread. |
| box               | Arbitrary width, height centered box. If height is not specified, will expand to row height. |
| head              | Screw head with specifiable head-shape.                           |
| hexhead           | Circular screw head with a hexagonal drive. Same as 'head(hex)'.  |
| hexnut, nut       | Hexagonal outer profile nut with circular cutout.                 |
| threaded_insert   | Representation of a threaded insert.                              |
| variable_resistor | Electrical symbol of a variable resistor.                         |
| washer            | Circular washer with a circular hole.                             |
| webbolt           | Alternate bolt representation incorporating screw drive, with fixed length. |


### Label Bases

The base (specified by `--base=TYPE`) defines the shape of what the label is generated on top of. Currently, the following bases are understood:

| Base | Description | Image |
| ---- | ----------- | ----- |
| `pred` | For [Pred's parametric labelled bins](https://www.printables.com/model/592545-gridfinity-bin-with-printable-label-by-pred-parame) labels. If specifying this style, then height is ignored and width is in gridfinity units (e.g. `--width=1` for a label for a single 42mm bin). | ![](images/base_pred.png) |
| `plain` | For a blank, square label with a chamfered top edge. The specified width and height will be the whole area of the label base. You must specify at least a width. | ![](images/base_plain.png)
| `webb` | For [Cullen J Webb's ](https://makerworld.com/en/models/446624) swappable label system. Label is a 36.4 mm x 11 mm rounded rectangle with snap-fit inserts on the back. Use without margins to match the author's style labels. | ![](images/base_webb.png)
| `none` | For no base at all - the label will still be extruded. This is useful if you want to generate a label model to place onto another volume in the slicer. | ![](images/base_none.png) |

Generate Pred-style Gridfinity Labels


