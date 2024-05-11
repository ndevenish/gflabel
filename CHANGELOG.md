# GFLabel 0.1.5 (Unreleased)

- Fix error when using `ocp_vscode` to preview labels and exporting SVG (the
  label was only rendered in 2D, but the code to push the preview assumed that
  it was always in 3D)
- Breaking: Renamed `--gap` option to `--label-gap`. The name "gap" was too
  generic when we wanted to allow specifying different "gaps".

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


