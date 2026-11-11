# Enclosure

A Blender model of the dock in a 1590DD-size box, with its removable device holder, built by script from `../hardware/layout.json`.

- `build_enclosure.py`: builds the scene, saves `open-pedal.blend` and renders six views
- `open-pedal.blend`: the generated scene (not in the repository; run the build to create it)
- `assets/tablet-screen.png`: the screenshot shown on the example tablet
- `renders/`: the bare unit (`front.png`, `rear.png`, `inside.png` with the body hidden) and the holder (`holder-tablet.png`, `holder-rear.png`, `holder-phone.png`)

Rebuild (tested with Blender 5.2; the six renders take about ten minutes on a laptop CPU):

```
blender --background --python enclosure/build_enclosure.py
```

The board in the model is the KiCad export `hardware/kicad/exports/open-pedal-board.glb`, so run the KiCad build first (see `../hardware/README.md`). Change positions in `layout.json` and rebuild both, and the holes, board and parts move together.

## Device holder

A printed stand for a phone or tablet that sits along the rear of the top face. Its dimensions are the `holder` block in `layout.json`.

- **Angle:** the device leans back at 60 degrees with its bottom edge on a padded ledge behind a 9 mm lip. The holder starts 18 mm behind the bank switches.
- **Fixing:** a lip hooks over the rear edge above the jacks, and two M4 thumbscrews go into threaded holes in the top face, one outside each bank switch. Undo the two screws and it lifts off.
- **Legs:** a side cheek at each end runs down to a rubber foot on the floor behind the unit, outside the outermost rear connectors. A tablet's weight sits behind the enclosure's own feet, so the legs carry it.
- **Side arms:** two arms slide in T-slots across the backrest, one above the other so each can cross the full width. Each ends in a jaw with a foam pad against the device's edge and a padded lip over its front face. A knob on the rear of the backrest locks each arm.
- **Range:** devices 58 to 286 mm wide and up to about 12 mm thick, set by the arm length. The build prints the width range.
- **Plastic:** about 150 cm³ for the printed parts; the build prints the figure. To get there the backrest is 66 mm high and 10 mm thick with a honeycomb cut into it from the rear, the base under the ledge is a 3 mm shell with cross ribs, and each leg is an open frame. The honeycomb stops behind a 2.5 mm front skin so the face the device rests on and the lips that hold the arms stay whole; only the row below the arm slots goes right through. The amounts are the `lightening` values in `layout.json`.
- **Cable:** an 18 mm slot in the ledge and lip clears a right-angle plug in the bottom of a portrait phone. A straight plug does not fit under the device.

In the `.blend`, slide `Holder side arm left` and `Holder side arm right` along X to fit another width. The example tablet is an iPad mini (195.4 x 134.8 x 6.3 mm) in landscape and the phone is a generic one in portrait; both are simple stand-ins, set by `example_devices` in `layout.json`. The iPad shows `assets/tablet-screen.png`, a screenshot of Soundshed Guitar with its window title bar cropped off; change `screen_image` to show something else. The phone shows a made-up app screen. The phone is hidden in the saved scene.

The holder covers the rear-panel labels on the top face while it is fitted.

## Renders

The renders are path-traced with Cycles on the CPU: three softbox lights plus the interior HDRI that ships with Blender, a concrete-style floor, fine surface grain on the powder coat and printed plastic, edges rounded at render time, and a slight lens blur. Two environment variables speed up a check: `OPEN_PEDAL_SAMPLES` (default 192) and `OPEN_PEDAL_VIEWS` (a comma-separated list such as `front,holder-tablet`).

## Limits of the model

The model is for checking fit and appearance, not for manufacture:

- The body is a plain rounded box with 2.5 mm walls, not Hammond's casting, and has no draft, lid screws or bosses.
- The LED-ring footswitches, jacks, pots, knobs and the OLED are simplified stand-ins. The switch hole size and ring diameter are assumed, not taken from a part.
- The rounded edges and surface grain are shading effects only; the meshes have sharp edges and flat faces.
- The body and holder are both shown black; the rings are shown with preset A lit and the others dim.
- Rear-panel hole heights come from `rear_cutouts` in `layout.json`. Those connector heights are from memory, not from datasheets; check them before drilling.
- The holder is not print-ready: its parts are separate overlapping solids with no fillets, travel stops, screw threads or print clearances tuned, and no STL is exported. Nothing about it has been printed or load-tested.
- The two M4 holes in the top face need tapping or rivet nuts; the model only draws the holes.
- There is no drill template or expression treadle yet.

Collections in the scene: Enclosure, Controls, Rear panel parts, Board, Labels, Device holder, Example devices, Stage.
