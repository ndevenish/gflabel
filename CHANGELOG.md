# GFLabel 0.2.dev

- Label base type must now always be specified. You can pass `--pred` to
  get the old default kind. You can also specify partial/incomplete
  names, as long as it is unambuguous (e.g. `gflabel cull` will select
  `cullenect` labels).
- Added ability to specify label base version, for labels with multiple
  standards version.
<<<<<<< HEAD
- Added alias "Robertson" for square-drive, as it is generally used in
  Canada. Thanks to [@MinchinWeb](https://github.com/MinchinWeb).
||||||| parent of ab009af (Fix logic requiring output filename after label)
=======
- Bugfix: Specifying output filename will no longer break generation
  when written before the label contents.
>>>>>>> ab009af (Fix logic requiring output filename after label)

# GFLabel 0.1.7 (2024-05-30)

- Bugfix: Symbol generation was broken by a reorganisation. Thanks to [@PaulBone](https://github.com/PaulBone).
- Bugfix: Standalone whitespace was not using fonts correctly. ([#6](https://github.com/ndevenish/gflabel/issues/6))

# GFLabel 0.1.6 (2024-05-20)

- Added `{magnet}` fragment. Thanks to [@PaulBone](https://github.com/PaulBone)
  for the contribution.
- Changed text/font handling. Instead of Futura, GFLabel now defaults to a
  bundled version of [Open Sans][opensans]. You can still specify your
  font of choice with `--font` (if it is a system font), or if you want to
  specify a specific font file you can set `--font-path`.
- You can set the default font at an environment level by setting `GFLABEL_FONT`
  to the name of the system font that you want to use.

[opensans]: https://github.com/googlefonts/opensans

# GFLabel 0.1.5 (2024-05-12)

- Fix error when using `ocp_vscode` to preview labels and exporting SVG (the
  label was only rendered in 2D, but the code to push the preview assumed that
  it was always in 3D)
- Breaking: Renamed `--gap` option to `--label-gap`. The name "gap" was too
  generic when we wanted to allow specifying different "gaps".
- Add new `predbox` base. These bases are labels for the [Parametric Gridfinity Storage Box by Pred][predbox]
  box labels. It is supported for width 4, 5, 6 and 7, which corresponds to the
  label size corresponding to a storage box of that many gridfinity units.
- Added alignment specifiers `{<}` and `{>}`. These can only be used at the
  start of a label column (or label division) and causes the contents of the
  column to all be left-aligned or right-aligned. For aligning only specific
  lines in a column, the padding fragment `{...}` can still be used.
- Add fragment `{|}`. This allows you to designate columns between which
  the text area will be split. You can specify the ratio of column widths
  by specifying the proportions in the fragment e.g. `{2|1}`.
- Added new option `--column-gap`, that specifies the gap between columns when
  using the column specification fragment.
- Added a `{measure}` fragment, that shows column widths. This can be useful
  for demonstration or debugging purposes.

[predbox]: https://www.printables.com/model/543553-gridfinity-storage-box-by-pred-now-parametric

# GFLabel 0.1.4 (2024-05-11)

- Added option `--font-size-maximum`. If this is set (instead of `--font-size`)
  then text will be allowed to shrink to fit the available space, but will not
  get any larger than specified (in mm). This is different from `--font-size`,
  which would force the text to be rendered at the same size, which risked
  causing overflow when rendering many varied text fields.
- Fixed occasional issue where labels would rerender themselves to correct
  minute scale differences (e.g. trying to scale down to correct a 99.9999999
  undersize).
- Fixed issue where undersized fragments would downscale based on the height of
  the full available area, instead of the actual undersized height it was
  rendered at.
- Rework SVG rendering. SVG will now _only_ render the label fields, and will
  not try to project the label base into the SVG. This is much faster, but also
  ensures cleaner SVG output and avoids topology issues when trying to add more
  and more data into the SVG projection (this is used to generate the example
  tables).
- ~~Added `--gap` option, which when multiple labels are being generated, allows
  you to customise the gap between labels.~~
- Made progress towards a more user-friendly console output.
- Add fragment `symbol(...)`. This rendered electronic symbols, taken from
  Chris Pikul' [electronic-symbols][christ-pikul] diagrams. Not all of the
  symbols currently render without issue.

[chris-pikul]: https://github.com/chris-pikul/electronic-symbols

# GFLabel 0.1.3 (2024-05-03)

- Add style `webbolt(partial)`. This causes a thread to be generated only on
  the bottom part of the screw, representing a partially threaded bolt.
- Added `lockwasher` for a locking washer. The size of this and the washer
  were slightly adjusted to be closer to the webb-style size.
- Adjusted the proportions of `webbolt` to match the published version of the
  system (this was previously measured off of preview screenshots).

# GFLabel 0.1.2 (2024-05-03)

- Update the `webb` base to match the new v1.1.0 style. The trapezoid cutouts
  have been replaced for easier printing and more satisfying snap.

# GFLabel 0.1.1 (2024-05-02)

- Fix `variable_resistor` arrow such that it now has even width along the
  arrow head.
- Add an "Overheight" system. Some fragments (`variable_resistor` and
  `webbolt`) will now cause other fragments on the same label to preemptively
  shrink down before the overheight fragment. This helps avoid
  dispropotionately large text which otherwise would have to be controlled by
  setting font size. This behaviour can be turned off with `--no-overheight`.


# GFLabel 0.1.0 (2024-05-01)
- Initial Release


