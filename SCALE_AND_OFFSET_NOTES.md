There are two (OK, three) distinct types of scaling in `gflabel`.

- The `--xscale`, `--yscale`, and `--zscale` command line options can be used to scale the entire created physical labels along any of the axes.
That scaling is done at the very end of things and is best used for small nudges when the pysical label is not quite the right size.
- The `{scale()}` fragment provides for inline scaling along any one or more of the x/y/z axes.
The scaling is applied for individual fragments in a line after the fragment has been rendered into a Sketch
and the Sketch is extruded into a Part.
It's best used when you want to distort the shape of a rendered fragment.
- `gflabel` code has many options, calculations, and heuristics for presenting label content pleasantly in a generally desirable layout.
Those factors are extremely handy for someone who just wants to make a nice-looking label without a lot of bother.

Unfortunately, these things can interact in mysterious ways that are difficult to overcome.
It's easy to make fragments expand beyond the base's pysical boundaries,
have fragments overlap with each other,
or just generally show up in ways you don't expect.

There is a brute force option when all else fails: the `{offset()}` fragment.
Fragments are positioned on the label base according to calculations done by `gflabel` code.
In the simplest case, a single item is placed at the (0,0,0) origin point,
with the X and Y dimensions centered and the Z dimension extruded from 0 according to the label style.
When there are mutliple fragments, the `gflabel` logic places each at a calculated location in the X/Y plane.
The `{offset()}` fragment, as its name implies,
lets you apply a specific offset to any of the X/Y/Z axes.
For example, a negative X offset value will move the affected fragments to the left by that amount (in millimeters).

Both `{scale()}` and `{offset()}` take "KEY=VALUE" arguments,
and 1, 2, or 3 such arguments can be given.
The key is an axis letter (x, y, or z).
The value is a number for the amount of scaling or offset for that axis.
Order of keys is not significant.
If you are using both `{scale()}` and `{offset()}` consecutively,
it doesn't matter which comes first.
The `{offset()}` is always applied after the `{scale()}` has been applied.

Here are some examples:

This is an illustration of scaling on the X axis.
It's shown in separate labels to make the difference obvious.
A scale factor smaller than 1 makes the text thinner,
and a scale factor larger than 1 makes it wider.
```
gflabel --vscode pred "normal" "{scale(x=0.5)}thin" "{scale(x=2)}wide"
```
<img width="1082" height="1096" alt="image" src="https://github.com/user-attachments/assets/ed7b8bf8-9267-49e9-9b29-9e8eb634288d" />

Here's another look, this time with divisions within a single label.
In this case, the `gflabel` autoscaling competes with us a bit.
```
gflabel --vscode pred "normal{|}{scale(x=0.5)}thin{|}{scale(x=2)}wide"
```
<img width="1089" height="366" alt="image" src="https://github.com/user-attachments/assets/1c762329-eb99-4de1-a31f-4c3a428aeef1" />

Negative scale factors are also allowed, providing a flipping effect.
```
gflabel --vscode pred "{scale(x=-1)}flipped" "{scale(x=-0.5)}thin" "{scale(x=-2)}wide"
```
<img width="1081" height="1078" alt="image" src="https://github.com/user-attachments/assets/05318327-6298-43c0-a1a0-6e8834ae39e6" />

Here are similar examples for scaling on the Y axis.
Notice that the `tall` rendering goes past the base boundary.
An `{offset()}` could be used to move it completely back onto the base.
```
gflabel --vscode pred "normal" "{scale(y=0.5)}short" "{scale(y=2)}tall"
```
<img width="1087" height="1091" alt="image" src="https://github.com/user-attachments/assets/9a5c0856-bbe0-4548-b361-a732d32b04e6" />

```
gflabel --vscode pred "normal{|}{scale(y=0.5)}short{|}{scale(y=2)}tall"
```
<img width="1088" height="348" alt="image" src="https://github.com/user-attachments/assets/3739e678-b635-4bec-90ea-148f5cd34f4c" />

```
gflabel --vscode pred "{scale(y=-1)}flipped" "{scale(y=-0.5)}short" "{scale(y=-2)}tall"
```
<img width="1084" height="1082" alt="image" src="https://github.com/user-attachments/assets/1ed56a28-6997-4bbd-9dd6-3bb9732c1ed5" />

If you use negative scaling for both the X and Y axis, you generally end up with a normal label rendered upside down.
That's not that useful.

You might expect that scaling X and Y with inverse values would yield similar results.
You are right that they are similar, but they are not identical.
That's because of the various manipulations within the `gflabel` code intended for default (non-scaled) cases.
```
gflabel --vscode pred "{scale(x=0.5)}word" "{scale(y=2)}word"
```
<img width="1093" height="724" alt="image" src="https://github.com/user-attachments/assets/e2b50885-2da6-415f-b1d6-fa9350147ac8" />

Here are some Z axis examples.
The images are tilted so that the differences can actually be seen.
```
gflabel --vscode pred "normal" "{scale(z=0.5)}thin" "{scale(z=2)}thick"
```
<img width="976" height="1004" alt="image" src="https://github.com/user-attachments/assets/a66d0789-a9d2-4756-96b4-d4c95f563322" />

In this example, `--style embedded` is used, and a Z offset is used for part of the label to raise it above the base surface.
```
gflabel --vscode pred "twirl here:{7|}{scale(z=5, x=0.3, y=0.3)}{offset(z=2)}{color(red)}{head(hex)}" --style embedded
```
<img width="917" height="434" alt="image" src="https://github.com/user-attachments/assets/c4ba95eb-e357-42ef-936b-c6d86439f6cf" />

If you use `--style debossed` and scale on the Z axis to make it larger than the base's minimum Z axis value
(in this case, -0.4mm for `pred` base),
you create a stencil effect with the label content pierced all the way through.
```
gflabel --vscode pred "{scale(z=3)}stencil" --style debossed
```
<img width="1442" height="482" alt="image" src="https://github.com/user-attachments/assets/dbcc9a7f-87f1-4651-91a2-d9838fd600b7" />

For that simple example, the same thing could be achieved without scaling by using a larger `--depth` value:
```
gflabel --vscode pred "stencil" --style debossed --depth 3
```
<img width="1450" height="464" alt="image" src="https://github.com/user-attachments/assets/fe00ac3d-c69b-4971-b67d-a07fdf979171" />
