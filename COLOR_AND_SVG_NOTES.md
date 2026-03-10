# Color and SVG Notes

## Color Basics

There are global default colors for the base and label,
set via `--base-color` and `--label-color`, respectively.
They default to `orange` and `blue`.
Colors can be any of the names standardized in CSS3.
You can also specify a color in the 6-digit hex notation,
for example `#008080`.

In addition, there is a label fragment type for changing colors within a label.
Each line of a label starts with the default label color.
When a color fragment is seen,
all fragments after that will be rendered in the named color
until another color fragment is seen or the end of the line is reached.

There are some examples below.
They are all rendered in VScode OCP CAD Viewer.
For many examples, a label with just the default colors
is shown along with the same label using colors.
The Viewer assembly tree is expanded to show the node labels in the CAD model.

## Slicers

`gflabel` can produce STL, STEP, and 3MF output files.
STL format is not color-aware.
STEP and 3MF formats can handle colors,
and the colors described here are part of the STEP/3MF file export from `gflabel`.
However, treatment of color information when a STEP/3MF file is imported into a slicer varies a bit.
In general, most slicers don't bother with STEP/3MF file colors on import.
(Some CAD tools do, which is not surprising since STEP and 3MF are a CAD file formats.)

Most slicer color testing was done with Bambu Studio.
It does not notice colors in STEP files.
Bambu Studio does notice colors in OBJ and 3MF files,
though it deals with them slightly differently.
The file converter at
[convert3d.org](https://convert3d.org)
can convert a STEP file into an OBJ or 3MF file that has colors expressed in a way that Bambu Studio understands.
As of Bambu Studio 2.5, it understands standard color indications in 3MF files,
so 3MF output from `gflabel` can be used directly.

If you open one of those 3MF files in Bambu Studio,
you will immediately see it rendered in the expected colors.
Since those are just color names and not specific filaments,
Bambu Studio will prompt you to map the colors to filaments
when you try to send the sliced model to the 3D printer.

If you open one of those OBJ files
(and its accompanying MTL file)
in Bambu Studio, you are immediately prompted to confirm or modify
the color mapping choices it has made.
But, again, you must map the colors to specific filaments
when you try to send the sliced model to the 3D printer.

## Color Examples

Here is a very simple example showing a lot of colors:
```
gflabel --vscode pred '{washer} R O Y G B I V {nut}' '{color(chartreuse)}{washer} {color(red)}R {color(orange)}O {color(yellow)}Y {color(green)}G {color(blue)}B {color(indigo)}I {color(violet)}V {color(chartreuse)}{nut}'
```
<img width="1413" height="777" alt="image" src="https://github.com/user-attachments/assets/ff64cecd-2975-4556-8fab-15b221d9f0d4" />

Nobody is likely to have that many colors when 3D printing labels,
but there is no enforced limit.
Here's a slightly more complicated example:
```
gflabel --vscode pred '{<}I used to\nbe an\nadventurer\nlike you,{|}{variable_resistor}{|}{<}but\nthen....' '{<}I used to\nbe an\nadventurer\nlike you,{|}{color(red)}{variable_resistor}{|}{<}but\nthen....'
```
<img width="1409" height="772" alt="image" src="https://github.com/user-attachments/assets/ab77e4d9-9f52-4ca7-bdd4-1484502e6578" />

This is an example of a divided label:
```
gflabel --vscode pred 'R{|}G{|}B' '{color(red)}R{|}{color(green)}G{|}{color(blue)}B'
```
<img width="1416" height="778" alt="image" src="https://github.com/user-attachments/assets/00579354-5098-45fe-aaf1-c1029d08b231" />

Another example:
```
gflabel --vscode pred 'Danger! {head(triangle)}' '{color(red)}Danger! {color(black)}{head(triangle)}'
```
<img width="1409" height="770" alt="image" src="https://github.com/user-attachments/assets/858d326b-3931-4928-bdc2-afd158556d97" />

And another:
```
gflabel  --vscode pred "{head(hex)} {bolt(50)}\nM5x50" "{color(tan)}{head(hex)} {color(red)}{bolt(50)}\n{color(blue)}M5x50"
```
<img width="1406" height="770" alt="image" src="https://github.com/user-attachments/assets/67dbe780-1daf-491c-a0a0-c06ce0b5f16d" />

The color fragment should work properly with all of the other fragment types since there is no nesting.
Here is one of the `{measure}` examples from the README:
```
gflabel --vscode predbox -w=5 'A\n{measure}{4|}B\n{measure}{1|2}C\n{measure}' 'A\n{color(white)}{measure}{4|}B\n{color(chartreuse)}{measure}{1|2}C\n{color(pink)}{measure}'
```
<img width="1715" height="1128" alt="image" src="https://github.com/user-attachments/assets/6d48873a-9402-4920-85f8-a80ffe3fceb4" />

There is one side effect that you might not expect.
If you change the color inside a text fragment,
the spacing is likely to be affected.
It's because rendering an uninterrupted text fragment is done
with the assistance of low-level font handling code.
(It's the same reason you might see slight spacing differences on different platforms,
even though you're using the same font.)
When that same piece of text is broken into two or more
pieces, the spacing between them is handled directly by
the `gflabel` code.

Have a close look at the spacing between the tips of these letters:
```
gflabel --vscode pred 'WWW' 'W{color(blue)}W{color(blue)}W'
```
<img width="1409" height="772" alt="image" src="https://github.com/user-attachments/assets/ba0cbf84-4dd1-4b19-8fa9-fb75a21d4be1" />

## SVG Treatment

SVG files can be produced by `gflabel` (via the `-o` or `--output` options)
and can also be imported (via the `{svg()}` fragment).
Treatment of colors is controlled by the `--svg-mono` option, whose argument can be
`none` (default), `import`, `export`, or `both`.
With the default, colors are preserved both for imported SVG files
and for exported SVG files.

The `{svg()}` fragment takes the following key=value arguments:
- `file` (required) the path to an SVG file
- `flip_y` (optional, `true` (default) or `false`) whether to flip the model
- `color` (optional, defaults to `--label-color`) the name of a color to use SVG elements without specific colors, or all SVG elements when the SVG file is being imported as monocolor

## SVG Examples

Here is an multi-colored example (from [https://www.w3schools.com/graphics/tryit.asp?filename=trysvg_fill0](https://www.w3schools.com/graphics/tryit.asp?filename=trysvg_fill0)):
```
gflabel --vscode -o label.step -o fillcolors.svg plain --width 25 --height 15 "{svg(file=wjc/fillcolors.svg)}"
```
<img width="791" height="481" alt="fillcolors" src="https://github.com/user-attachments/assets/916d4577-530e-47aa-a25d-8a428cef812a" />

For exported SVG files written in monocolor, the color is the default labels color,
which can be changed via the `--label-color` option.

For imported SVG files read in monocolor,
any color values within the SVG file are replaced.
If a `color` value was given in the `{svg()}` fragment,
that color is used.
Else, the default labels color is used.
The same color choice is used for any element of the SVG file
that does not have its own color designation when read.

Here is an SVG file (from [https://svgsilh.com/image/1801287.html](https://svgsilh.com/image/1801287.html))
colored various ways.

The color in the SVG file is black.
```
gflabel --vscode -o label.step -o black.svg plain --width 25 --height 25 "{svg(file=wjc/kitten_bw.svg)}"
```
<img width="790" height="787" alt="black" src="https://github.com/user-attachments/assets/2aa07db0-ec4e-4f6a-82ce-94b83df32e40" />

Here it is colored with the default label color (`blue`).
```
gflabel --vscode -o label.step -o blue.svg plain --width 25 --height 25 "{svg(file=wjc/kitten_bw.svg)}" --svg-mono import
```
<img width="786" height="786" alt="blue" src="https://github.com/user-attachments/assets/eace5343-fdbe-44f1-b5ec-0c719b002f35" />

Here it is colored `red` due to an earlier `{color()}` fragment.

```
gflabel --vscode -o label.step -o red.svg plain --width 25 --height 25 "{color(red)}{svg(file=wjc/kitten_bw.svg)}" --svg-mono import
```
<img width="777" height="777" alt="red" src="https://github.com/user-attachments/assets/da39fc84-cd90-40dd-9bbb-d088ac551276" />

And here it is colored `green` due to an explicit `color` in the `{svg()}` fragment.
```
gflabel --vscode -o label.step -o green.svg plain --width 25 --height 25 "{color(red)}{svg(file=wjc/kitten_bw.svg,color=green)}" --svg-mono import
```
<img width="781" height="784" alt="green" src="https://github.com/user-attachments/assets/ea3b8efb-2524-4d29-bd50-668b2bc0025c" />

The `{svg()}` fragment uses the `build123d` function `import_svg()` which in turn
uses the `ocpsvg` function `import_svg_document()`.
That function includes the important caveat:
_This importer does not cover the whole SVG specification, its most notable known limitations are...._

From our point of view, the most important limitations are
1. it does not import text items at all, and
1. it only deals with faces and wires.
1. it chokes on numbers like `100%`
1. various SVG translations and transformations seem to be ignored

This basic example from
[https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorials/SVG_from_scratch/Getting_started](https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorials/SVG_from_scratch/Getting_started)
should have text "SVG" in the center of the green circle,
but the text does not get imported.
```
gflabel --vscode -o label.step -o mdn_basic.svg plain --width 25 --height 15 "{svg(file=wjc/mdn_basic.svg)}"
```
<img width="787" height="479" alt="mdn_basic" src="https://github.com/user-attachments/assets/4219b0dc-90da-4811-ab89-9bffa7645ef2" />

And sometimes things just go awry.
An imported element that becomes a `build123d` Wire can't be extruded into a Part because Wires are 1-dimensional.
The sensible thing to do in such cases is make the Wire 2-dimensional by calling `Wire.trace()`.
Unfortunately, that often throws an error.
The `{svg()}` fragment code watches for those errors and implements a tedious fallback strategy.
A message is given in the fallback cases so you can know what happened.

Even after all that, there still seem to be some glitches with complex SVGs.
Here's the famous Ghostscript Tiger, downloaded from
[https://commons.wikimedia.org/wiki/File:Ghostscript_Tiger.svg](https://commons.wikimedia.org/wiki/File:Ghostscript_Tiger.svg).
Something more than half of it works correctly, but it's not close to correct.
There are a lot of SVGs that just don't import properly this way.
I've even seen at least one that crashes the program.
Complex SVGs can also take a very long time to import and process.
Most simple graphics (without text) work well.
```
gflabel --vscode -o tiger.step -o tiger.svg --svg-base solid plain --width 50 --height 25 'Beware of\nTiger!{|}{svg(label=tiger, file=wjc/tiger.svg)}'
```
<img width="1560" height="786" alt="tiger" src="https://github.com/user-attachments/assets/151f5acb-d443-45f3-87d7-0ea709f01bf0" />

Sure, that's still scary, but just compare it to this with  this label using an image obtained from
[https://svgsilh.com/image/161467.html](https://svgsilh.com/image/161467.html)
```
gflabel --vscode -o rabbit.step -o rabbit.svg --svg-base solid plain --width 50 --height 25 'Beware of\nRabbit!{|}{scale(x=0.6,y=0.6)}{svg(label=rabbit, file=wjc/rabbit.svg, color=chocolate)}'
```
<img width="1273" height="648" alt="rabbit" src="https://github.com/user-attachments/assets/b1103abd-20b2-4733-b7ec-8ce7ecbc65dc" />
