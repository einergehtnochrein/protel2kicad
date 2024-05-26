# protel2kicad
Python script to convert Protel99SE EDA files to KiCad7

This is an attempt to convert schematics, boards and (symbol) libraries from the outdated Protel99SE design tool (Protel99SE is the predecessor of the Altium Designer tool).

---

# Installation (Debian Linux)
Clone this repository into a folder of your choice. The converter must be called from this directory.

The following Python3 modules must be installed:<br>
`argparse, base64, os, PIL, signal, subprocess, sys`

The following external tool must be installed (Debian package) if you want to convert `.DDB` database files directly:<br>
`mdbtools`

# Installation (Windows 10)
Clone this repository into a folder of your choice. The converter must be called from this directory.

The following Python3 modules must be installed:<br>
`argparse, base64, os, PIL, signal, subprocess, sys`

A Windows build of `mdbtools` is required. Clone this repository `https://github.com/lsgunth/mdbtools-win`, it comes with the Windows executables prebuilt in the root directory. Add that directory to your PATH.

# Usage
Call the `p2k.py` scipt and specify the full path to one or more Protel design files. The following file extensions (case insensitive) are recognized: `.SCH .PCB .LIB .DDB`

For instance, convert the database `old_stuff.ddb` in your home directory:<br>

    ./p2k.py ~/old_stuff.ddb

The script will extract all design files from the database into a subfolder `db` in the current directory, then batch convert them all. The output may look similar to this example:

    processing /home/john/old_stuff.ddb
    processing db/old_stuff/thing.lib
    convert_lib bin 1.2-2.0
    processing db/old_stuff/thing.sch
    convert_sch bin 1.2-2.0
    processing db/old_stuff/thing.pcb
    convert_pcb bin 4.0

Converter output is placed into the `kicad` folder in the current directory. In this example the created files would be:

  * `kicad/thing.kicad_sym`

  * `kicad/thing.kicad_sch`<br>
    `kicad/thing_export.kicad_sym`<br>
    `kicad/thing_export_power.kicad_sym`<br>
All symbols of the schematic are exported to a library (`_export.kicad_sym`). Power symbols are hard or impossible to map to standard KiCad power symbols. Therefore, an additional library for power symbols (`_export_power.kicad_sym`) is created automatically. Note that all footprints assigned in the schematic are linked to a (not yet existing) footprint library `_export_pcb`. You can export a footprint library from a KiCad PCB file.

  * `kicad/thing.kicad_pcb`<br>
KiCad7 allows to export a footproint library from the produced PCB file. Choose the name `thing_export_pcb.pretty` for it, because the converter script has hardcoded the reference to this library name into the PCB file.

Multilayer PCB's and hierarchical sheet schematics have been successfully converted with this tool, but the more complex a design is the more likely the conversion will fail :-(

# Limitations

There are quite a few...   The list below is definitely incomplete!

  * When extracting a `.DDB` database file, only files in the root directory of the 'Documents' folder are extracted. Subdirectories are ignored.
  * Schematics are only supported in binary format, not ASCII.
  * Symbol libraries are only supported in binary format, not ASCII.
  * Footprint libraries are not supported.
  * There is only very rudimentary support for ancient PCB files in the old 3.0 binary format (used by Protel98).
  * The script attempts to convert the layer stack, but don't rely on it.
  * PCB design rules are not supported. Requires manual transfer.
  * Many other bugs... :-(
  * If your design uses oval pads/holes, workarounds were required due to the lack of native support for this feature in Protel. After conversion, you must manually convert these pads/footprints to use oval holes in KiCad.
  * 'Orientation' (object rotation by 0/90/180/270°) is notoriously buggy.
  * Customized mechanical layer names are not yet supported (patch the `protel_pcb.py` module if needed).
  * Schematics very likely require extra `PWR_FLAG` objects. Protel does not distinguish between power_in and power_out pins, and all such pins are converted to 'Power Input' in KiCad.
  * Filled rectangles in the schematic are filled in 'background' mode if border and fill color are different. They are filled in (opaque) 'fill' mode if border and fill color are identical. This is a simple heuristic that worked for almost all symbols in the old schematics/libraries I have.
  * In Protel you could define a pad stack for thru-hole pads with different pad geometries for outer and inner layers. KiCad does not support this, and the converter will give you a warning. It still creates an output though, just uses the TopLayer geometry of the Protel pad.
  * Images on schematic sheets (JPG/PNG) are supported. Protel stores a link to the image file, but not the image data itself (this is different from KiCad). Therefore, you must also provide the image file in addition to the schematic file. The converter searches for the image file in the same directory where the schematic is located. Ideally, store image files in the root directory of the `.ddb` design database.
  * If the Protel PCB is a multilayer board that uses a power plane layer (`InternalPlaneX`), the converter will create that layer, but you must manually add a filled zone to that layer in order to create the power plane equivalent of Protel.

NOTE: If the tool crashes during conversion, or in case the conversion result is not what you expect, please let me know. In such a case send me the files you are trying to convert along with a description of the error.

# New in V2 (2024-05-26)

  * Fix broken 'arc' handling. It worked by pure chance with some (but not all) versions of Kicad7. Also failed on Kicad8. Should now be fixed.
  * Support for power planes. Works if the Kicad output has a board boundary on the Edge.Cuts layer. Also supports split power planes, although design rule parameters (gap between planes, etc) must be fixed manually. "Negative" drawing elements (lines or fills to spare out copper in power planes) not yet supported, although these elements exist in the ouput and can be manually adjusted.
  * Try converting the 6-layer "PCB Benchmark 94 Board" from the Protel99SE examples folder. (ok, still some minor issues, but getting closer...)

# Example
The board shown here has been converted almost automatically. Only the oval holes required manual rework of the footprints in KiCad.

2-layer PCB example:![image](https://user-images.githubusercontent.com/32458301/228797211-e99c50bf-944c-412b-a244-165cab7c292b.png)

