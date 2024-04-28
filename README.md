# GFLabel

Generates labels for labelled gridfinity bins, and similar uses.

## Usage

### Basic Example

```
gflabel "Basic Label"
```

### Fragments



### Label Bases

The base (specified by `--base=TYPE`) defines the shape of what the label is generated on top of. Currently, the following bases are understood:

| Base | Description | Image |
| ---- | ----------- | ----- |
| `pred` | For [Pred's parametric labelled bins](https://www.printables.com/model/592545-gridfinity-bin-with-printable-label-by-pred-parame) labels. If specifying this style, then height is ignored and width is in gridfinity units (e.g. `--width=1` for a label for a single 42mm bin). | ![](images/base_pred.png) |
| `plain` | For a blank, square label with a chamfered top edge. The specified width and height will be the whole area of the label base. You must specify at least a width. | ![](images/base_plain.png)
| `webb` | For [Cullen J Webb's ](https://makerworld.com/en/models/446624) swappable label system. Label is a 36.4 mm x 11 mm rounded rectangle with snap-fit inserts on the back. Use without margins to match the author's style labels. | ![](images/base_webb.png)
| `none` | For no base at all - the label will still be extruded. This is useful if you want to generate a label model to place onto another volume in the slicer. | ![](images/base_none.png) |

Generate Pred-style Gridfinity Labels


