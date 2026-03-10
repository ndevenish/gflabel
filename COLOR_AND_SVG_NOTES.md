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

## Color Examples

Here is a very simple example showing a lot of colors:
```
gflabel --vscode pred '{washer} R O Y G B I V {nut}' '{color(chartreuse)}{washer} {color(red)}R {color(orange)}O {color(yellow)}Y {color(green)}G {color(blue)}B {color(indigo)}I {color(violet)}V {color(chartreuse)}{nut}'
```

Nobody is likely to have that many colors when 3D printing labels,
but there is no enforced limit.

This is an example of a divided label:
```
gflabel --vscode pred 'R{|}G{|}B' '{color(red)}R{|}{color(green)}G{|}{color(blue)}B'
```

The color fragment should work properly with all of the other fragment types since there is no nesting.

There is one side effect that you might not expect.
If you change the color inside a text fragment,
the spacing is likely to be affected.
It's because rendering an uninterrupted text fragment is done
with the assistance of low-level font handling code.
When that same piece of text is broken into two or more
pieces, the spacing between them is handled directly by
the `gflabel` code.
