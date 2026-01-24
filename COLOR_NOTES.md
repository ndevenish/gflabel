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

There are some examples below.
They are all rendered in VScode OCP CAD Viewer.
For each example, a label with just the default colors
is shown along with the same label using colors.
The Viewer assemlby tree is expanded to show the node labels in the CAD model.

## Slicers

`gflabel` can produce STL and STEP output files.
STL format is not color-aware.
STEP format can handle colors,
and the colors described here are part of the STEP file export from `gflabel`.
However, treatment of color information when a STEP file is imported into a slicer varies a bit.
In general, most slicers don't bother with STEP file colors on import.
(Most CAD tools do, which is not surprising since STEP is a CAD file format.)

Most slicer color testing was done with Bambu Studio.
It does not notice colors in STEP files.
Bambu Studio does notice colors in OBJ and 3MF files,
though it deals with them slightly differently.
The file converter at
[convert3d.org](https://convert3d.org)
can convert a STEP file into an OBJ or 3MF file that has colors expressed in a way that Bambu Studio understands.

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

## Examples

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
