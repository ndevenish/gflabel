# Color Notes

## Basics

There are global default colors for the base and label,
set via `--base-color` and `--label-color`, respectively.
They default to `orange` and `blue`.
Colors can be any of the names standardized in CSS3.

In addition, there is a label fragment type for changing colors within a label.
Each line of a label starts with the default label color.
When a color fragment is seen, 
all fragments after that will be rendered in the named color
until another color fragment is seen or the end of the line is reached.

Here are some examples.
They are all rendered in VScode OCP CAD Viewer.
For each example, a label with just the default colors
is shown along with the same label using colors.

## Slicers

`gflabel` can produce STL and STEP output files.
STL format is not color-aware.
STEP format can handle colors,
and the colors described here are part of the STEP file export from `gflabel`.
However, treatment of color information when a STEP file is imported into a slicer varies a bit.
In general, most slicers don't bother with STEP file colors on import.
(Most CAD tools do, which is not surprising since STEP is a CAD file format.)

Most color testing was done with Bambu Studio.
It does not notice colors in STEP files.
However, Bambu Studio does notice colors in OBJ and 3MF files,
though it deals with them differently.
The file converter at
[convert3d.org](https://convert3d.org)
can convert a STEP file into an OBJ or 3MF file that has colors expressed in a way that Bambu Studio understands.

If you open one of those 3MF files in Bambu Studio,
you will immediately see it rendered in the expected colors.
Since those are just color names and not specific filaments,
Bambu Studio will prompt you to map the colors to filaments
when you try to send the sliced model to the 3D printer.

- bs 3MF

If you open one of those OBJ files
(and its accompanying MTL file)
in Bambu Studio, you are immediately prompted to confirm or modify
the color mapping choices it has made.
But, again, you must map the colors to specific filaments
when you try to send the sliced model to the 3D printer.

- bs OBJ

## Examples

Here is a very simple example:

> gflabel --style embossed pred 'R{|}G{|}B' '{color(red)}R{|}{color(green)}G{|}{color(blue)}B' --vscode

- RGB

Nobody is likely to have more than a few colors when 3D printing labels,
but there is no enforced limit.
Here's a slightly more complicated example:

> gflabel --style embossed pred '{washer} R O Y G B I V {nut} {color(chartreuse)}{washer}' '{color(red)}R {color(orange)}O {color(yellow)}Y {color(green)}G {color(blue)}B {color(indigo)}I {color(violet)}V {color(chartreuse)}{nut}' --vscode

- ROYGBIV

This is an example of a divided label:

> gflabel --style embossed pred '{<}I used to\nbe an\nadventurer\nlike you,{|}{variable_resistor}{|}{<}but\nthen....' '{<}I used to\nbe an\nadventurer\nlike you,{|}{color(red)}{variable_resistor}{|}{<}but\nthen....' --vscode

- adventurer

Another example:

> gflabel --style embossed pred 'Danger! {head(triangle)}' '{color(red)}Danger! {color(black)}{head(triangle)}' --vscode

- danger

The color fragment should work properly with all of the other fragment types since there is no nesting.
Here is one of the `{measure}` examples from the README:

> gflabel predbox -w=5 'A\n{measure}{4|}B\n{measure}{1|2}C\n{measure}' 'A\n{color(white)}{measure}{4|}B\n{color(chartreuse)}{measure}{1|2}C\n{color(pink)}{measure}' --vscode

- measure

There is one side effect that you might not expect.
If you change the color inside a text fragment, 
the spacing is likely to be affected.
It's because rendering an uninterrupted text fragment is down
with the assistance of low-level font handling code.
When that same piece of text is broken into two or more
pieces, the spacing between them is handled directly by
the `gflabel` code.

> gflabel --style embossed pred 'WWW' 'W{color(blue)}W{color(blue)}W' --vscode

- www
