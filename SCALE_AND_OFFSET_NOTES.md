There are two )OK, three) distinct types of scaling in gflabel.

- The `--xscale`, `--yscale`, and `--zscale` command line options can be used to scale the entire created physical labels along any of the axes.
That scaling is done at the very end of things and is best used for small nudges when the pysical label is not quite the right size.
- The `{scale()}` fragment provides for inline scaling along any one or more of the x/y/z axes.
The scaling is applied for individual fragments in a line after the fragment has been rendered into a Sketch
and the Sketch is extruded into a Part.
It's best used when you want to distort the shape of a rendered fragment.
--gflabel code has many options, calculations, and heuristics for presenting label content pleasantly in a generally desirable layout.
Those factors are extremely handy for someone who just wants to make a nice-looking label without a lot of bother.

Unfortunately, these things can interact in mysterious ways that are difficult to overcome.
It's easy to make fragments expand beyond the base's pysical boundaries,
have fragments overlap with each other,
or just generally show up in ways you don't expect.

There is a brute force option when all else fails: the `{offset()}` fragment.
Fragments are positioned on the label base according to calculations done by `gflabel` code.
In the simplest case, a single item is placed at the (0,0,0) origin point,
with the X and Y dimensions centered and the Z dimension extruded from 0 according top the label style.
When there are mutliple fragments, the `gflabel` logic places each at a calculated location in the XCY plane.
The `{offset()}` fragment, as its name implies,
lets you apply a specific offset to any of the X/Y/Z axes.
For example, a negative X offset value will move the affected fragments to the left by that amount.

Both `scale()}` and `{offset()}` take pairs of arguments.
The first item in each pair is an axis letter (x, y, or z).
The second item in each pair is a number for the amount of scaling or offset for that axis.
You can give 1, 2, or 3 pairs of arguments in a single fragment.
Order of pairs and extra spaces are not significant.
If you are using both `{scale()}` and `{offset()}` consecutively,
it doesn't matter which comes first.

Here are some examples:

```
gflabel --vscode pred "normal" "{scale(x,0.5)}thin" "{scale(x,2)}wide"
```
```
gflabel --vscode pred "normal{|}{scale(x,0.5)}thin{|}{scale(x,2)}wide"
```

```
gflabel --vscode pred "normal" "{scale(y,0.5)}short" "{scale(y,2)}tall"
```

```
gflabel --vscode pred "normal{|}{scale(y,0.5)}short{|}{scale(y,2)}tall"
```

```
gflabel --vscode pred "{scale(x,0.5)}word" "{scale(y,2)}word"
```
```
gflabel --vscode pred "normal" "{scale(z,0.5)}thin" "{scale(z,2)}thick"
```
```
gflabel --vscode pred "grab here:{7|}{scale(z,8, x,0.2, y,0.2)}{color(red)}{head(hex)}"
```
```
gflabel --vscode pred "twirl here:{7|}{scale(z,5, x,0.3, y,0.3)}{offset(z,2)}{color(red)}{head(hex)}" --style embedded
```
```
gflabel --vscode pred "{scale(z,3)}stencil" --style debossed
```
```
gflabel --vscode pred "stencil" --style debossed --depth 3
```
