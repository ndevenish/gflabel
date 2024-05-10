# GFLabel 0.1.4 (Unreleased)

- Added option `--font-size-maximum`. If this is set (instead of `--font-size`)
  then text will be allowed to shrink to fit the available space, but will not
  get any larger than specified (in mm). This is different from `--font-size`,
  which would force the text to be rendered at the same size, which risked
  causing overflow when rendering many varied text fields.

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


