#!/usr/bin/python3

import base64
from io import BytesIO
import math
import ntpath
import os
from PIL import Image
from protel_primitive import Primitive, ProtelString, KicadString
import struct
import textwrap
import uuid


class SchSymbol:
    def __init__ (self, filename, bin_file):
        self.name = ""
        self.variants = []
        self.fileoffset = None
        self.globals = {}
        self.parts = []
        self.filename = filename
        self.ps = ProtelString(bin_file)
        self.file = bin_file

    def symbol_body_from_bin_file (self):
        self.ps()
        self.globals["description"] = self.ps()
        self.globals["footprint1"] = self.ps()
        self.globals["footprint2"] = self.ps()
        self.globals["footprint3"] = self.ps()
        self.globals["footprint4"] = self.ps()
        self.globals["textfield1"] = self.ps()
        self.globals["textfield2"] = self.ps()
        self.globals["textfield3"] = self.ps()
        self.globals["textfield4"] = self.ps()
        self.globals["textfield5"] = self.ps()
        self.globals["textfield6"] = self.ps()
        self.globals["textfield7"] = self.ps()
        self.globals["textfield8"] = self.ps()
        self.globals["designator"] = self.ps()
        self.globals["sheet_part_filename"] = self.ps()
        nparts = struct.unpack('<h', self.file.read(2))[0]

        for partno in range(nparts):
            part = {"index": partno}

            self.file.read(4)

            # Process graphical elements of the component
            gelems = []
            prim = Primitive()
            while True:
                gelem = prim.read_bin(self.file)
                if gelem is None:
                    break;
                gelems.append(gelem)
            part["prims"] = gelems
            self.parts.append(part)
    
            # Read (and ignore) DeMorgan symbol
            while prim.read_bin(self.file) is not None:
                pass
    
            # Read (and ignore) IEEE symbol
            while prim.read_bin(self.file) is not None:
                pass

    @classmethod
    def from_sch_bin_file (cls, filename, bin_file):
        sym = cls(filename, bin_file)

        # Read component directory
        nvariants = struct.unpack('<h', bin_file.read(2))[0]
        for v in range(nvariants):
            sym.variants.append(sym.ps())
        sym.name = sym.variants[0] if nvariants > 0 else ""

        sym.symbol_body_from_bin_file()

        return sym

    @classmethod
    def from_lib_bin_file (cls, filename, bin_file):
        sym = cls(filename, bin_file)

        fileoffset = struct.unpack('<i', bin_file.read(4))[0]

        nvariants = struct.unpack('<h', bin_file.read(2))[0]
        for v in range(nvariants):
            sym.variants.append(sym.ps())
        sym.name = sym.variants[0] if nvariants > 0 else ""

        go_back_to = bin_file.tell()
        bin_file.seek(fileoffset)
        #print(f"seek file offset 0x{fileoffset:X}")

        sym.symbol_body_from_bin_file()

        # More global data
        sym.ps()
        sym.ps()
        sym.globals["partfieldname1"] = sym.ps()
        sym.globals["partfieldname2"] = sym.ps()
        sym.globals["partfieldname3"] = sym.ps()
        sym.globals["partfieldname4"] = sym.ps()
        sym.globals["partfieldname5"] = sym.ps()
        sym.globals["partfieldname6"] = sym.ps()
        sym.globals["partfieldname7"] = sym.ps()
        sym.globals["partfieldname8"] = sym.ps()
        sym.globals["partfieldname9"] = sym.ps()
        sym.globals["partfieldname10"] = sym.ps()
        sym.globals["partfieldname11"] = sym.ps()
        sym.globals["partfieldname12"] = sym.ps()
        sym.globals["partfieldname13"] = sym.ps()
        sym.globals["partfieldname14"] = sym.ps()
        sym.globals["partfieldname15"] = sym.ps()
        sym.globals["partfieldname16"] = sym.ps()

        bin_file.seek(go_back_to)

        return sym

    def to_kicad7 (self, kfile, add_nickname=False):
        # Write to KiCad file

        # Determine whether to show pin names and/or pin numbers
        # Protel can control this on an individual pin basis, while KiCAD can only do
        # this globally per component.
        # If name/number is enabled for at least one pin, enable it in KiCAD.
        hidenames = True
        hidenumbers = True
        for part in self.parts:
            gelems = part["prims"]
            for gelem in gelems:
                if gelem["type"] == "pin":
                    hidenames = hidenames and (gelem["showname"] == 0)
                    hidenumbers = hidenumbers and (gelem["shownumber"] == 0)
        hidenames_text = "(pin_names hide) " if hidenames else ""
        hidenumbers_text = "(pin_numbers hide) " if hidenumbers else ""

        nickname = f"{self.filename}_export:" if add_nickname else ""
        kfile.write(f"    (symbol \"{nickname}{self.name}\" {hidenumbers_text}{hidenames_text}(in_bom yes) (on_board yes)\n")

        for part in self.parts:
            kfile.write(f"      (symbol \"{self.name}_{1+part['index']}_1\"\n")

            for gelem in part["prims"]:
                if (gelem["type"] == "polyline") or (gelem["type"] == "polygon"):
                    width = gelem["borderwidth"]
                    c = gelem["border_color"]
                    color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    npoints = gelem["npoints"]
                    points = gelem["points"]
                    if gelem["type"] == "polygon":
                        points.append(points[0])
                        npoints = npoints + 1

                    kfile.write("        (polyline\n")
                    kfile.write("          (pts\n")
                    for n in range(npoints):
                        x, y = (points[n][0], points[n][1])
                        kfile.write(f"            (xy {x:.3f} {y:.3f})\n")
                    kfile.write( "          )\n")
                    kfile.write(f"          (stroke (width {width}) (type default) (color {color}))\n")
                    kfile.write( "          (fill (type none))\n")
                    kfile.write( "        )\n")
    
                if gelem["type"] == "line":
                    x1, y1 = (gelem["x1"], gelem["y1"])
                    x2, y2 = (gelem["x2"], gelem["y2"])
                    width = gelem["linewidth"]
                    c = gelem["color"]
                    color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"

                    kfile.write("        (polyline\n")
                    kfile.write("          (pts\n")
                    kfile.write(f"            (xy {x1:.3f} {y1:.3f})\n")
                    kfile.write(f"            (xy {x2:.3f} {y2:.3f})\n")
                    kfile.write( "          )\n")
                    kfile.write(f"          (stroke (width {width}) (type default) (color {color}))\n")
                    kfile.write( "          (fill (type none))\n")
                    kfile.write( "        )\n")
    
                if gelem["type"] == "arc":
                    r = min(gelem["rx"], gelem["ry"])
                    cx = gelem["x"]
                    cy = gelem["y"]
                    linewidth = gelem["borderwidth"]
                    start_angle = gelem["sa"]
                    end_angle = gelem["ea"]
                    c = gelem["color"]
                    color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    if start_angle == end_angle:
                        kfile.write(f"        (circle (center {cx} {cy}) (radius {r:.3f})\n")
                        kfile.write(f"          (stroke (width {linewidth:.3f}) (type solid) (color {color}))")
                        kfile.write( "          (fill (type none))\n")
                        kfile.write( "        )\n")
                    else:
                        alpha1 = end_angle
                        a = ((360 + end_angle - start_angle) / 2) % 180
                        alpha2 = start_angle + a
                        alpha3 = start_angle
                        x1 = cx + r * math.cos(alpha1 / 57.29578)
                        y1 = cy + r * math.sin(alpha1 / 57.29578)
                        x2 = cx + r * math.cos(alpha2 / 57.29578)
                        y2 = cy + r * math.sin(alpha2 / 57.29578)
                        x3 = cx + r * math.cos(alpha3 / 57.29578)
                        y3 = cy + r * math.sin(alpha3 / 57.29578)

                        kfile.write(f"        (arc (start {x1:.3f} {y1:.3f}) (mid {x2:.3f} {y2:.3f}) (end {x3:.3f} {y3:.3f})\n")
                        kfile.write(f"          (stroke (width {linewidth:.3f}) (type default) (color {color}))\n")
                        kfile.write( "          (fill (type none))\n")
                        kfile.write( "        )\n")
    
                if gelem["type"] == "text":
                    kfile.write(f"        (text \"{gelem['text']}\" (at {gelem['x']:.3f} {gelem['y']:.3f} {10*gelem['rotation']})\n")
                    kfile.write( "          (effects (font (size 1.27 1.27)) (justify left bottom))\n")
                    kfile.write( "        )\n")

                if gelem["type"] == "ellipse":
                    r = min(gelem["rx"], gelem["ry"])
                    linewidth = gelem["borderwidth"]
                    c = gelem["border_color"]
                    border_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    c = gelem["fill_color"]
                    fill_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    solid = gelem["drawsolid"]
                    fill_type = "color" if border_color == fill_color else "background"

                    kfile.write(f"        (circle (center {gelem['x']} {gelem['y']}) (radius {r:.3f})\n")
                    kfile.write(f"          (stroke (width {linewidth:.3f}) (type solid) (color {border_color}))")
                    if solid == 0:
                        kfile.write( "          (fill (type none))\n")
                    else:
                        kfile.write(f"          (fill (type {fill_type}) (color {fill_color}))\n")
                    kfile.write( "        )\n")

                if gelem["type"] == "bezier":
                    linewidth = gelem["width"]
                    c = gelem["color"]
                    color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    npoints = gelem["npoints"]
                    points = gelem["points"]

                    # Protel stores quadratic Bezier with 3 points per segment.
                    for i in range(0,npoints,3):
                        p0, p1, p2 = points[i+0], points[i+1], points[i+2]
                        # Transform into a cubic Bezier curve (KiCad format)
                        q0 = p0
                        x = p0[0] + (p1[0] - p0[0]) * 2/3
                        y = p0[1] + (p1[1] - p0[1]) * 2/3
                        q1 = [x, y]
                        x = p2[0] + (p1[0] - p2[0]) * 2/3
                        y = p2[1] + (p1[1] - p2[1]) * 2/3
                        q2 = [x, y]
                        q3 = p2

                        kfile.write(
                             "        (bezier\n"
                             "          (pts\n"
                            f"            (xy {q0[0]:.3f} {q0[1]:.3f})\n"
                            f"            (xy {q1[0]:.3f} {q1[1]:.3f})\n"
                            f"            (xy {q2[0]:.3f} {q2[1]:.3f})\n"
                            f"            (xy {q3[0]:.3f} {q3[1]:.3f})\n"
                             "          )\n"
                            f"          (stroke (width {linewidth:.3f}) (type solid) (color {color}))"
                             "          (fill (type none))\n"
                             "        )\n"
                             )
    
            for gelem in part["prims"]:
                if gelem["type"] == "pin":
                    x = gelem["x"]
                    y = gelem["y"]
                    length = gelem["length"]
    
                    orientation = 180
                    xx = x + length
                    yy = y
                    if (gelem["rotation"] == 90):
                        orientation = 270
                        xx = x
                        yy = y + length
                    if (gelem["rotation"] == 180):
                        orientation = 0
                        xx = x - length
                        yy = y
                    if (gelem["rotation"] == 270):
                        orientation = 90
                        xx = x
                        yy = y - length
    
                    etype = 'input'
                    electrical_code = gelem["electrical"]
                    if (electrical_code == 1):
                        etype = 'bidirectional'
                    elif (electrical_code == 2):
                        etype = 'output'
                    elif (electrical_code == 3):
                        etype = 'open_collector'
                    elif (electrical_code == 4):
                        etype = 'passive'
                    elif (electrical_code == 5):
                        etype = 'tri_state'
                    elif (electrical_code == 6):
                        etype = 'open_emitter'
                    elif (electrical_code == 7):
                        etype = 'power_in'
    
                    is_clk = gelem["clksymbol"] > 0
                    is_inv = gelem["dotsymbol"] > 0
                    if is_clk and not is_inv:
                        graphical_style = 'clock';
                    elif not is_clk and is_inv:
                        graphical_style = 'inverted';
                    elif is_clk and is_inv:
                        graphical_style = 'inverted_clock';
                    else:
                        graphical_style = 'line'

                    hide = " hide" if (gelem["showname"] == 0) and (gelem["shownumber"] == 0) and (length == 0) else ""

                    ks = KicadString()
                    name = ks(gelem["name"])
                    number = ks(gelem["number"])
                    kfile.write(f"        (pin {etype} {graphical_style} (at {xx:.3f} {yy:.3f} {orientation}) (length {length}){hide}\n")
                    kfile.write(f"          (name \"{name}\" (effects (font (size 1.27 1.27))))\n")
                    kfile.write(f"          (number \"{number}\" (effects (font (size 1.27 1.27))))\n")
                    kfile.write( "        )\n")

            # TODO How to make sure filled rectangles are in the background?
            for gelem in part["prims"]:
                if (gelem["type"] == "rounded_rectangle") or (gelem["type"] == "rectangle"):
                    x1, y1 = (gelem["x1"], gelem["y1"])
                    x2, y2 = (gelem["x2"], gelem["y2"])
                    width = gelem["borderwidth"]
                    c = gelem["border_color"]
                    border_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    c = gelem["fill_color"]
                    fill_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                    solid = gelem["drawsolid"]
                    fill_type = "color" if border_color == fill_color else "background"
    
                    kfile.write(f"        (rectangle (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n")
                    kfile.write(f"          (stroke (width {width}) (type default) (color {border_color}))\n")
                    if solid == 0:
                        kfile.write( "          (fill (type none))\n")
                    else:
                        kfile.write(f"          (fill (type {fill_type}) (color {fill_color}))\n")
                    kfile.write( "        )\n")

            kfile.write("      )\n")

        kfile.write( "    )\n")



class SchematicLibrary:
    def __init__ (self):
        self.syms = []
        self.full_name = ""
        self.fonts = []

    @classmethod
    def from_syms (cls, symbol_list):
        lib = cls()

        if type(symbol_list) != list:
            raise RuntimeError("from_syms() requires SchSymbol list")
        if len(symbol_list) > 0:
            if type(symbol_list[0]) != SchSymbol:
                raise RuntimeError("from_syms() requires SchSymbol list")
        lib.syms = symbol_list

        return lib

    @classmethod
    def from_protel_bin (cls, filename, plib):
        lib = cls()
        ps = ProtelString(plib)

        plib.read(4)
        lib.full_name = ps()   # Library Name
        plib.read(11)

        # Font names: int16 count, then count*fonts
        nfonts = struct.unpack('<h', plib.read(2))[0]
        for n in range(nfonts):
            plib.read(8)
            name = ps()     # Font name
            lib.fonts.append({"name":name})

        # Read component directory
        ncomps = struct.unpack('<h', plib.read(2))[0]
        #print(f"{ncomps} symbols in library")
        for n in range(ncomps):
            lib.syms.append(SchSymbol.from_lib_bin_file(filename, plib))

        # Workspace definition
        t = plib.read(1)[0]
        if t != 200:
            print("Expected workspace (200), but found type #", t)
            return
        plib.read(25)

        return lib

    def to_kicad7 (self, klib):
        # Write KiCAD schematic library

        # Header
        klib.write( "(kicad_symbol_lib (version 20211014) (generator protel2kicad)\n")

        for sym in self.syms:
            sym.to_kicad7(klib)

        klib.write(")\n")



def symbol_gnd (libname, netname):
    return (f"""
    (symbol \"{libname}:{netname}\" (power) (pin_names (offset 0)) (in_bom yes) (on_board yes)
      (property \"Reference\" \"#PWR\" (id 0) (at 0 -6.35 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property \"Value\" \"{netname}\" (id 1) (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)))
      )
      (property \"ki_keywords\" \"global power\" (id 4) (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol \"{netname}_0_1\"
        (polyline
          (pts
            (xy 0 0)
            (xy 1.27 0)
            (xy 1.27 1.27)
            (xy 2.54 0)
            (xy 1.27 -1.27)
            (xy 1.27 0)
          )
          (stroke (width 0) (type default) (color 0 0 0 0))
          (fill (type none))
        )
      )
      (symbol \"{netname}_1_1\"
        (pin power_in line (at 0 0 270) (length 0) hide
          (name \"{netname}\" (effects (font (size 1.27 1.27))))
          (number \"1\" (effects (font (size 1.27 1.27))))
        )
      )
    )
""")


def symbol_arrow (libname, netname):
    return (f"""
    (symbol \"{libname}:{netname}\" (power) (pin_names (offset 0)) (in_bom yes) (on_board yes)
      (property \"Reference\" \"#PWR\" (id 0) (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property \"Value\" \"{netname}\" (id 1) (at 0 3.81 0)
        (effects (font (size 1.27 1.27)))
      )
      (property \"ki_keywords\" \"global power\" (id 4) (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol \"{netname}_0_1\"
        (polyline
          (pts (xy 1.27 0.762) (xy 2.54 0) (xy 1.27 -0.762))
          (stroke (width 0) (type default) (color 0 0 0 0))
          (fill (type none))
        )
        (polyline
          (pts (xy 0 0) (xy 2.54 0))
          (stroke (width 0) (type default) (color 0 0 0 0))
          (fill (type none))
        )
      )
      (symbol \"{netname}_1_1\"
        (pin power_in line (at 0 0 90) (length 0) hide
          (name \"{netname}\" (effects (font (size 1.27 1.27))))
          (number \"1\" (effects (font (size 1.27 1.27))))
        )
      )
    )
""")



class CoordinateTransform:
    def __init__ (self, canvas_w, canvas_h, bounds_x1, bounds_y1, bounds_x2, bounds_y2):
        self.center = [round((canvas_w / 2 + 0.635) / 1.27) * 1.27,
                       round((canvas_h / 2 + 0.635) / 1.27) * 1.27]
        self.cog = [(bounds_x2 + bounds_x1) / 2, (bounds_y2 + bounds_y1) / 2]

    def __call__(self, x, y):
        x = self.center[0] + (x - self.cog[0])
        y = self.center[1] - (y - self.cog[1])
        return x, y


class Schematic:
    def __init__ (self, filename):
        self.fonts = []
        self.syms = []
        self.component_instances = []
        self.canvas = {"w":21.0, "h":16.0, "grid_visible":False, "snap_to_grid":False}
        self.filename = filename
        self.power_sym_defs = {}
        self.power_symbol_text = ""

    def get_font (self, index): # index: 1...N
        font = None
        if (index >= 1) and (index <= len(self.fonts)):
            font = self.fonts[index - 1]
        return font

    def get_bounds (self):
        xmax = -1e12
        ymax = -1e12
        xmin = 1e12
        ymin = 1e12

        for ci in self.component_instances:
            x1 = None

            if (ci["type"] == "junction") or (ci["type"] == "noerc") or \
               (ci["type"] == "component") or (ci["type"] == "powerobject"):
                x1, y1 = (ci['x'], ci['y'])
                x2 = x1
                y2 = y1

            if (ci["type"] == "wire") or (ci["type"] == "bus"):
                npoints = ci["npoints"]
                if (npoints >= 2):
                    points = ci["points"]
                    for n in range(npoints - 1):
                        x1, y1 = (points[n][0], points[n][1])
                        x2, y2 = (points[n+1][0], points[n+1][1])

            # TODO: Must add placed symbols (watch rotation!)

            if x1 is not None:
                xmax = max(xmax, x1)
                xmax = max(xmax, x2)
                ymax = max(ymax, y1)
                ymax = max(ymax, y2)
                xmin = min(xmin, x1)
                xmin = min(xmin, x2)
                ymin = min(ymin, y1)
                ymin = min(ymin, y2)

        return xmin, ymin, xmax, ymax

    def get_canvas_size (self):
        w = self.canvas["w"]
        h = self.canvas["h"]
        if self.canvas["custom_style"] == 0:
            style = self.canvas["standard_style"]
            if style == 0:          # A4
                w, h = (297, 210)
            elif style == 1:        # A3
                w, h = (420, 297)
            elif style == 2:        # A2
                w, h = (594, 420)
            elif style == 3:        # A1
                w, h = (841, 594)
            elif style == 4:        # A0
                w, h = (1189, 841)
            elif style == 5:        # A
                w, h = (304.8, 228.6)
            elif style == 6:        # B
                w, h = (457.2, 304.8)
            elif style == 7:        # C
                w, h = (609.6, 457.2)
            elif style == 8:        # D
                w, h = (914.4, 609.6)
            elif style == 9:        # E
                w, h = (1219.2, 914.4)
            elif style == 10:       # Letter
                w, h = (279.4, 215.9)
            elif style == 11:       # Legal
                w, h = (355.6, 215.9)
            elif style == 12:       # Tabloid
                w, h = (431.8, 279.4)
            elif style == 13:       # Orcad A
                w, h = (304.8, 228.6)
            elif style == 14:       # Orcad B
                w, h = (457.2, 304.8)
            elif style == 15:       # Orcad C
                w, h = (609.6, 457.2)
            elif style == 16:       # Orcad D
                w, h = (914.4, 609.6)
            elif style == 17:       # Orcad E
                w, h = (1219.2, 914.4)

            if self.canvas["portrait"] != 0:
                w, h = h, w
                
        return w, h

    def get_symbol_text_rotate (self, symbol_rotation, text_rotation, mirrored):
        rot = [[(0, "left bottom"), (90, "right top"), (0, "right top"), (90, "left bottom")],
               [(0, "right bottom"), (90, "left top"), (0, "left top"), (90, "right bottom")]]
        index = ((360 + symbol_rotation - text_rotation) % 360) // 90
        return rot[mirrored][index]

    def define_power_symbol (self, protel_symbol, libname, netname, ksch):
        if not netname in self.power_sym_defs.keys():
            if protel_symbol == 2:
                self.power_sym_defs[netname] = {"libname":libname}
                ksch.write(symbol_gnd(libname, netname))
                self.power_symbol_text += symbol_gnd(libname, netname)
            else:
                self.power_sym_defs[netname] = {"libname":libname}
                ksch.write(symbol_arrow(libname, netname))
                self.power_symbol_text += symbol_arrow(libname, netname)

    @classmethod
    def from_protel_bin (cls, filename, bin_file):
        sch = cls(filename)
        ps = ProtelString(bin_file)

        # One 32-bit integer
        bin_file.read(4)
    
        # Font table: int16 count, then count*fonts
        nfonts = struct.unpack('<h', bin_file.read(2))[0]
        #print(f"{nfonts} fonts")
        for n in range(nfonts):
            fontdef = bin_file.read(8)
            font = {}
            scale = 0.3/2   # officially 0.353/2, but it's too large :-(
            font["size"] = struct.unpack('<H', fontdef[0:2])[0] * scale
            font["underline"] = fontdef[4]      # (0/1)
            font["italic"] = fontdef[5]         # (0/1)
            font["bold"] = fontdef[6]           # (0/1)
            font["strikeout"] = fontdef[7]      # (0/1)
            font["name"] = ps()
            sch.fonts.append(font)
            #print(sch.fonts[n]["name"], " ".join(f"{x:02X}" for x in fontdef))

        # Read component library
        ncomps = struct.unpack('<h', bin_file.read(2))[0]
        #print(f"{ncomps} components")
        for n in range(ncomps):
            #print("sym", n)
            sym = SchSymbol.from_sch_bin_file(filename, bin_file)
            sch.syms.append(sym)

        # Workspace
        #print("Reading workspace definition @0x{:X}".format(bin_file.tell()))
        sch.canvas["organization"] = ps()       # Organization
        sch.canvas["address1"] = ps()           # Address 1
        sch.canvas["address2"] = ps()           # Address 2
        sch.canvas["address3"] = ps()           # Address 3
        sch.canvas["address4"] = ps()           # Address 4
        sch.canvas["document_title"] = ps()     # Document Title
        sch.canvas["document_number"] = ps()    # Document No
        sch.canvas["revision"] = ps()           # Revision
        sch.canvas["page_number"] = struct.unpack('<h', bin_file.read(2))[0]
        sch.canvas["page_total"] = struct.unpack('<h', bin_file.read(2))[0]
        bin_file.read(2)
        sch.canvas["electrical_grid_size"] = struct.unpack('<h', bin_file.read(2))[0]
        sch.canvas["standard_style"] = bin_file.read(1)[0]
        bin_file.read(11)
        sch.canvas["title_block"] = bin_file.read(1)[0] # 0=standard, 1=ANSI
        bin_file.read(1)
        sch.canvas["portrait"] = bin_file.read(1)[0] # 0=landscape, 1=portrait
        sch.canvas["show_border"] = bin_file.read(1)[0]
        sch.canvas["title_block_enable"] = bin_file.read(1)[0]
        bin_file.read(4)    # color RGBA
        bin_file.read(4)    # color RGBA
        sch.canvas["grid_snap_enable"] = struct.unpack('B', bin_file.read(1))[0]
        sch.canvas["grid_snap_size"] = bin_file.read(2)     # Grid snap size
        sch.canvas["grid_visible"] = struct.unpack('B', bin_file.read(1))[0]
        sch.canvas["grid_size"] = bin_file.read(2)          # Grid size
        sch.canvas["w"] = struct.unpack('<h', bin_file.read(2))[0] * 0.254
        sch.canvas["h"] = struct.unpack('<h', bin_file.read(2))[0] * 0.254
        sch.canvas["custom_style"] = bin_file.read(1)[0]
        w, h = sch.get_canvas_size()

        #print(f"Reading component instantiations @0x{bin_file.tell():X}")
        prim = Primitive()
        while True:
            comp = prim.read_bin(bin_file)
            if comp is None:
                break
            sch.component_instances.append(comp)

        #print(f"Reading SCH ends @0x{bin_file.tell():X} with {bin_file.read(1)}")

        return sch

    def to_kicad7 (self, ksch, klib, klibpower):
        # Export library
        lib = SchematicLibrary.from_syms(self.syms)
        lib.to_kicad7(klib)

        # Write KiCAD schematic

        x1, y1, x2, y2 = self.get_bounds()
        w, h = self.get_canvas_size()
        #print(f"canvas size: {w}x{h}, bounds: ({x1},{y1}) / ({x2},{y2})")
        ct = CoordinateTransform(w, h, x1, y1, x2, y2)

        # Header
        ksch.write( "(kicad_sch (version 20230121) (generator protel2kicad)\n")

        # Unique Identifier
        uu = uuid.uuid4()
        ksch.write(f"  (uuid {uu})\n")

        # Page Settings
        # Use w/h in the file for custom style. Otherwise use size
        if (self.canvas["custom_style"] != 0) or (self.canvas["standard_style"] > 16):
            size = f"\"User\" {self.canvas['w']:.3f} {self.canvas['h']:.3f}"
        else:
            formats = [
                "A4", "A3", "A2", "A1", "A0", "A", "B", "C", "D", "E",
                "\"User\" 279.4 215.9",     # Letter
                "\"User\" 431.8 279.4",     # Tabloid
                "A",        # Orcad A
                "B",        # Orcad B
                "C",        # Orcad C
                "D",        # Orcad D
                "E"]        # Orcad E
            size = formats[self.canvas["standard_style"]]
        portrait = " portrait" if self.canvas["portrait"] != 0 else ""
        ksch.write(f"  (paper {size}{portrait})\n")

        # Title Block Section
        ksch.write(
             "  (title_block\n"
            f"    (title \"{self.canvas['document_title']}\")\n"
            f"    (rev \"{self.canvas['revision']}\")\n"
            f"    (company \"{self.canvas['organization']}\")\n"
            f"    (comment 1 \"{self.canvas['address1']}\")\n"
            f"    (comment 2 \"{self.canvas['address2']}\")\n"
            f"    (comment 3 \"{self.canvas['address3']}\")\n"
            f"    (comment 4 \"{self.canvas['address4']}\")\n"
             "  )\n"
            )

        # Symbol Library Symbol Definition
        ksch.write( "  (lib_symbols\n")
        for sym in self.syms:
            sym.to_kicad7(ksch, add_nickname=True)

        # Power symbols
        # We define a new KiCad power symbol for each combination of
        # net name and Protel power symbol.
        for ci in self.component_instances:
            if ci["type"] == "powerobject":
                protel_symbol = ci["symbol"]
                netname = ci["name"]
                self.define_power_symbol(protel_symbol, f"{self.filename}_export_power", netname, ksch)
        if len(self.power_symbol_text) > 0:
            klibpower.write("(kicad_symbol_lib (version 20211014) (generator protel2kicad)\n")
            klibpower.write(self.power_symbol_text)
            klibpower.write(")\n")

        ksch.write( "  )\n")
        ksch.write( "\n")

        # Junction Section
        for ci in self.component_instances:
            if ci["type"] == "junction":
                uu = uuid.uuid4()
                x, y = ct(ci['x'], ci['y'])
                ksch.write(f"  (junction (at {x:.3f} {y:.3f}) (diameter 0) (color 0 0 0 0)\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write( "  )\n")
        ksch.write( "\n")
    
        # No Connect Section
        for ci in self.component_instances:
            if ci["type"] == "noerc":
                uu = uuid.uuid4()
                x, y = ct(ci['x'], ci['y'])
                ksch.write(f"  (no_connect (at {x:.3f} {y:.3f}) (uuid {uu}))\n")
        ksch.write( "\n")

        # Wire and Bus Section
        # a) Wrires and Busses
        for ci in self.component_instances:
            if ci["type"] == "wire":
                npoints = ci["npoints"]
                if (npoints >= 2):
                    points = ci["points"]
                    for n in range(npoints - 1):
                        x1, y1 = ct(points[n][0], points[n][1])
                        x2, y2 = ct(points[n+1][0], points[n+1][1])
                        uu = uuid.uuid4()
                        ksch.write(f"  (wire (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f}))\n")
                        ksch.write( "    (stroke (width 0) (type default) (color 0 0 0 0))\n")
                        ksch.write(f"    (uuid {uu})\n")
                        ksch.write( "  )\n")
            if ci["type"] == "bus":
                npoints = ci["npoints"]
                if (npoints >= 2):
                    points = ci["points"]
                    for n in range(npoints - 1):
                        x1, y1 = ct(points[n][0], points[n][1])
                        x2, y2 = ct(points[n+1][0], points[n+1][1])
                        uu = uuid.uuid4()
                        ksch.write(f"  (bus (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f}))\n")
                        ksch.write( "    (stroke (width 0) (type default) (color 0 0 0 0))\n")
                        ksch.write(f"    (uuid {uu})\n")
                        ksch.write( "  )\n")
        # b) Bus Entries
        for ci in self.component_instances:
            if ci["type"] == "bus_entry":
                x1, y1 = (ci["x1"], ci["y1"])
                x2, y2 = (ci["x2"], ci["y2"])
                x, y = (x1, y1)

                # See if any wire touches the bus entry on one side
                # Then use that as the bus entry's location
                for ciw in self.component_instances:
                    if ciw["type"] == "wire":
                        npointsw = ciw["npoints"]
                        pointsw = ciw["points"]
                        for n in range(npointsw):
                            xw, yw = (pointsw[n][0], pointsw[n][1])
                            if (xw == x1) and (yw == y1):
                                x, y = (xw, yw)
                            if (xw == x2) and (yw == y2):
                                x, y = (xw, yw)

                # Bus entry end point is given as a delta to the start point
                deltax, deltay = (x2 - x1, y2 - y1)
                if (x == x2) and (y == y2):
                    deltax, deltay = (x1 - x2, y1 - y2)
                deltay = -deltay  # y direction different for KiCad!

                #print(x,y,x1,y1,x2,y2,deltax,deltay)
 
                uu = uuid.uuid4()
                x, y = ct(x, y)
                ksch.write(f"  (bus_entry (at {x:.3f} {y:.3f}) (size {deltax:.3f} {deltay:.3f})\n")
                ksch.write( "    (stroke (width 0) (type default) (color 0 0 0 0))\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write( "  )\n")
        ksch.write( "\n")
    
        # Image Section
        for ci in self.component_instances:
            if ci["type"] == "image":
                x1, y1 = ct(ci["x1"], ci["y1"])
                x2, y2 = ct(ci["x2"], ci["y2"])

                img_path = ci.get("path", "")

                # Protel does not store the image, but rather just the path
                # to the image on the system where the Protel file was created.
                # See if we can find the image in the directory of the
                # Protel file.
                img_filename = os.path.join(img_path, ntpath.basename(ci["name"]))

#TODO: Determine path relative to schematic
                if os.path.isfile(img_filename):
                    # Force to PNG format with PIL library
                    im = Image.open(img_filename)
                    png = BytesIO()
                    im.save(png, "PNG")
                    png.seek(0)

                    # Compute scale factor from image size and bounding box
                    # TODO just a guess...
                    w, h = im.size
                    scale = 12 * (x2 - x1) / w

                    # KiCad image position is the center of the scaled image
                    x, y = (x1 + x2) / 2, (y1 + y2) / 2

                    # Encode as BASE64 string
                    bmp_b64 = base64.b64encode(png.read()).decode("ascii")
                    data_list = textwrap.wrap(bmp_b64, 76)

                    uu = uuid.uuid4()
                    ksch.write(
                        f"  (image (at {x:.3f} {y:.3f}) (scale {scale:.3f})\n"
                        f"    (uuid {uu})\n"
                         "    (data\n"
                         )
                    for s in data_list:
                        ksch.write(f"      {s}\n")
                    ksch.write(
                         "    )\n"
                         "  )\n"
                         )
                else:
                    print(f"  Cannot find image file {img_filename}")

        # Graphical Line Section
        for ci in self.component_instances:
            if ci["type"] == "polyline":
                width = ci["borderwidth"]
                if ci["style"] == 1:
                    style = "dash"
                elif ci["style"] == 2:
                    style = "dot"
                else:
                    style = "default"
                c = ci["border_color"]
                color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                npoints = ci["npoints"]
                points = ci["points"]
                #print(f"{npoints} points: {points}")

                for n in range(1,npoints):
                    x1, y1 = ct(points[n-1][0], points[n-1][1])
                    x2, y2 = ct(points[n][0], points[n][1])
                    ksch.write( "  (polyline\n")
                    ksch.write(f"    (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f}))\n")
                    ksch.write(f"    (stroke (width {width}) (type {style}) (color {color}))\n")
                    ksch.write( "  )\n")

            if (ci["type"] == "rounded_rectangle") or (ci["type"] == "rectangle"):
                x1, y1 = ct(ci["x1"], ci["y1"])
                x2, y2 = ct(ci["x2"], ci["y2"])
                width = ci["borderwidth"]
                c = ci["border_color"]
                border_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                c = ci["fill_color"]
                fill_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                solid = ci["drawsolid"]
                fill_type = "color" if border_color == fill_color else "background"

                ksch.write(f"  (rectangle (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n")
                ksch.write(f"    (stroke (width {width}) (type default) (color {border_color}))\n")
                if solid == 0:
                    ksch.write( "    (fill (type none))\n")
                else:
                    ksch.write(f"    (fill (type {fill_type}) (color {fill_color}))\n")
                ksch.write( "  )\n")
    
            # Replace ellipse by a circle corresponding to the smaller
            # semiaxis of the ellipse.
            if ci["type"] == "ellipse":
                x, y = ct(ci["x"], ci["y"])
                r = min(ci["rx"], ci["ry"])
                width = ci["borderwidth"]
                c = ci["border_color"]
                border_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                c = ci["fill_color"]
                fill_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                solid = ci["drawsolid"]

                ksch.write(f"  (circle (center {x:.3f} {y:.3f}) (radius {r})\n")
                ksch.write(f"    (stroke (width {width}) (type default) (color {border_color}))\n")
                if solid == 0:
                    ksch.write( "    (fill (type none))\n")
                else:
                    ksch.write(f"    (fill (type background) (color {fill_color}))\n")
                ksch.write( "  )\n")
    
            if ci["type"] == "polygon":
                width = ci["borderwidth"]
                c = ci["border_color"]
                border_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                c = ci["fill_color"]
                fill_color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                solid = ci["drawsolid"]

                npoints = ci["npoints"]
                points = ci["points"]
                points.append(points[0])
                npoints = npoints + 1

                ksch.write( "  (polyline\n")
                ksch.write( "    (pts\n")
                for p in points:
                    x, y = ct(p[0], p[1])
                    ksch.write(f"      (xy {x:.3f} {y:.3f})\n")
                ksch.write( "    )\n")
                ksch.write(f"    (stroke (width {width}) (type default) (color {border_color}))\n")
                if solid == 0:
                    ksch.write( "    (fill (type none))\n")
                else:
                    ksch.write(f"    (fill (type background) (color {fill_color}))\n")
                ksch.write( "  )\n")

            # KiCad crashes when it encounters a free Bezier curve... :-(
            '''
            if ci["type"] == "bezier":
                linewidth = ci["width"]
                c = ci["color"]
                color = f"{c[0]:d} {c[1]:d} {c[2]:d} {(255-c[3])/255:.2f}"
                npoints = ci["npoints"]
                points = ci["points"]

                # Protel stores quadratic Bezier with 3 points per segment.
                for i in range(0,npoints,3):
                    p0, p1, p2 = points[i+0], points[i+1], points[i+2]
                    # Transform into a cubic Bezier curve (KiCad format)
                    q0 = p0
                    x = p0[0] + (p1[0] - p0[0]) * 2/3
                    y = p0[1] + (p1[1] - p0[1]) * 2/3
                    q1 = [x, y]
                    x = p2[0] + (p1[0] - p2[0]) * 2/3
                    y = p2[1] + (p1[1] - p2[1]) * 2/3
                    q2 = [x, y]
                    q3 = p2

                    ksch.write(
                         "  (bezier\n"
                         "    (pts\n"
                        f"      (xy {q0[0]:.3f} {q0[1]:.3f})\n"
                        f"      (xy {q1[0]:.3f} {q1[1]:.3f})\n"
                        f"      (xy {q2[0]:.3f} {q2[1]:.3f})\n"
                        f"       xy {q3[0]:.3f} {q3[1]:.3f})\n"
                         "    )\n"
                        f"    (stroke (width {linewidth:.3f}) (type solid) (color {color}))"
                         " (fill (type none))\n"
                         "  )\n"
                         )
            '''

        # Graphical Text Section
        for ci in self.component_instances:
            if ci["type"] == "text_frame":
                x, y = ct(ci["x1"], ci["y2"])   # sic!
                sizex = ci["x2"] - ci["x1"]
                sizey = ci["y2"] - ci["y1"]
                font = self.get_font(ci["font"])
                bold = ""
                italic = ""
                if font is not None:
                    bold = " bold" if font["bold"] != 0 else ""
                    italic = " italic" if font["italic"] != 0 else ""
                bw = ci["border_width"]
                if bw == 0:
                    border_width = 0.1
                elif bw == 1:
                    border_width = 0.2
                elif bw == 2:
                    border_width = 0.4
                else:
                    border_width = 1.0

                fc = ci["fill_color"]
                fill_color = f"{fc[0]:d} {fc[1]:d} {fc[2]:d} {(255-fc[3])/255:.2f}"
                bc = ci["border_color"]
                border_color = f"{bc[0]:d} {bc[1]:d} {bc[2]:d} {(255-bc[3])/255:.2f}"
                tc = ci["text_color"]
                text_color = f"{tc[0]:d} {tc[1]:d} {tc[2]:d} {(255-tc[3])/255:.2f}"

                uu = uuid.uuid4()
                ksch.write(f"  (text_box \"{ci['text']}\"\n")
                ksch.write(f"    (at {x:.3f} {y:.3f} 0) (size {sizex:.2f} {sizey:.2f})\n")
                ksch.write(f"    (stroke (width {border_width}) (type default) (color {border_color}))\n")
                ksch.write(f"    (fill (type color) (color {fill_color}))\n")
                ksch.write(f"    (effects (font (face \"{font['name']}\") (size {font['size']:.2f} {font['size']:.2f}) (color {text_color}){bold}{italic}) (justify left))\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write( "  )\n")
        ksch.write( "\n")

        for ci in self.component_instances:
            if ci["type"] == "text":
                x, y = ct(ci["x"], ci["y"])
                rotation = ci["rotation"]
                font = self.get_font(ci["font"])
                bold = ""
                italic = ""
                if font is not None:
                    bold = " bold" if font["bold"] != 0 else ""
                    italic = " italic" if font["italic"] != 0 else ""

                uu = uuid.uuid4()
                ksch.write(f"  (text \"{ci['text']}\" (at {x:.3f} {y:.3f} {rotation})\n")
                ksch.write(f"    (effects (font (face \"{font['name']}\") (size {font['size']:.2f} {font['size']:.2f}){bold}{italic}) (justify left bottom))\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write( "  )\n")
        ksch.write( "\n")

        # Local Label Section
        for ci in self.component_instances:
            if ci["type"] == "net_label":
                x, y = ct(ci["x"], ci["y"])
                rotation = ci["rotation"]

                uu = uuid.uuid4()
                ksch.write(f"  (label \"{ci['name']}\" (at {x:.3f} {y:.3f} {rotation})\n")
                ksch.write( "    (effects (font (size 1.0 1.0)) (justify left bottom))\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write( "  )\n")

        # Global Label Section
        for ci in self.component_instances:
            if ci["type"] == "port":
                style = ci["style"]
                iotype = ci["iotype"]
                length = ci["length"]

                # Translate position, alignment
                # NOTE: Protel port position is always the left (bottom)
                #       end of the label, NOT the electrical connection end.
                xraw = ci["x"]
                yraw = ci["y"]
                rotation = 0
                just = "left"
                if (style == 2) and (iotype == 2):  # right & input
                    xraw += length
                    just = "right"
                    rotation = 180
                if (style == 2) and (iotype == 1):  # right & output
                    pass
                if (style == 1) and (iotype == 2):  # left & input
                    pass
                if (style == 1) and (iotype == 1):  # left & output
                    xraw += length
                    just = "right"
                    rotation = 180
                if (style == 5) and (iotype == 2):  # top & input
                    yraw += length
                    rotation = 90
                if (style == 5) and (iotype == 1):  # top & output
                    rotation = 90
                if (style == 6) and (iotype == 2):  # bottom & input
                    rotation = 270
                if (style == 6) and (iotype == 1):  # bottom & output
                    yraw += length
                    rotation = 270
                x, y = ct(xraw, yraw)

                shape = "passive"
                if iotype == 1:
                    shape = "output"
                if iotype == 2:
                    shape = "input"
                if iotype == 3:
                    shape = "bidirectional"

                uu = uuid.uuid4()
                ksch.write(f"  (hierarchical_label \"{ci['name']}\" (shape {shape}) (at {x:.3f} {y:.3f} {rotation})\n")
                ksch.write(f"    (effects (font (size 1.0 1.0)) (justify  {just}))\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write( "  )\n")

        # Symbol Section
        for ci in self.component_instances:
            if ci["type"] == "component":
                prims = ci["prims"]
    
                rotation = ci["rotation"]
                x, y = ct(ci["x"], ci["y"])
                mirror = "(mirror y) " if ci["mirrored_y"] == 1 else ""
    
                designator = "?"
                designator_x = 0
                designator_y = 0
                designator_rotation = 0
                value = "?"
                value_x = 0
                value_y = 0
                value_rotation = 0
                for gelem in prims:
                    if gelem["type"] == "part_designator":
                        designator = gelem["name"]
                        designator_x, designator_y = ct(gelem["x"], gelem["y"])
                        designator_rotation, designator_just = self.get_symbol_text_rotate(rotation, gelem["rotation"], ci["mirrored_y"])
    
                    if gelem["type"] == "part_type":
                        value = gelem["name"]
                        value_x, value_y = ct(gelem["x"], gelem["y"])
                        value_rotation, value_just = self.get_symbol_text_rotate(rotation, gelem["rotation"], ci["mirrored_y"])

                unit = ci["unit"]

                ksch.write(f"  (symbol (lib_id \"{self.filename}_export:{ci['libref']}\") (at {x:.3f} {y:.3f} {rotation}) {mirror}(unit {unit})\n")
                ksch.write(f"    (property \"Reference\" \"{designator}\" (id 0) (at {designator_x:.3f} {designator_y:.3f} {designator_rotation})\n")
                ksch.write(f"      (effects (font (size 1.0 1.0)) (justify {designator_just}))\n")
                ksch.write( "    )\n")
                ksch.write(f"    (property \"Value\" \"{value}\" (id 1) (at {value_x:.3f} {value_y:.3f} {value_rotation})\n")
                ksch.write(f"      (effects (font (size 1.0 1.0)) (justify {value_just}))\n")
                ksch.write( "    )\n")
                ksch.write(f"    (property \"Footprint\" \"{self.filename}_export_pcb:{ci['footprint']}\" (id 2) (at {x:.3f} {y:.3f} 0)\n")
                ksch.write( "      (effects (font (size 1.0 1.0)) hide)\n")
                ksch.write( "    )\n")
                ksch.write( "  )\n")

            if ci["type"] == "powerobject":
                orientation = ci["rotation"]
                x, y = (ci["x"], ci["y"])
                name = ci["name"]

                value_x = x
                value_y = y
                if orientation == 0:
                    value_x += 4.5
                elif orientation == 90:
                    value_y += 3.8
                elif orientation == 180:
                    value_x -= 4.5
                else:
                    value_y -= 3.8

                if not name in self.power_sym_defs.keys():
                    print(f"Need: {name}, have: {self.power_sym_defs}")
                    raise RuntimeError("Can\'t find power symbol")

                libid = self.power_sym_defs[name]["libname"]

                x, y = ct(x, y)
                value_x, value_y = ct(value_x, value_y)

                uu = uuid.uuid4()
                if libid is not None:
                    ksch.write(f"  (symbol (lib_id \"{libid}:{name}\") (at {x:.3f} {y:.3f} {orientation}) (unit 1)\n")
                    ksch.write( "    (in_bom yes) (on_board yes)\n")
                    ksch.write(f"    (uuid {uu})\n")
                    ksch.write(f"    (property \"Reference\" \"#PWR?\" (id 0) (at {x:.3f} {y:.3f} {orientation % 180})\n")
                    ksch.write( "      (effects (font (size 1.0 1.0)) hide)\n")
                    ksch.write( "    )\n")
                    ksch.write(f"    (property \"Value\" \"{name}\" (id 1) (at {value_x:.3f} {value_y:.3f} {orientation % 180})\n")
                    ksch.write( "      (effects (font (size 1.0 1.0)))\n")
                    ksch.write( "    )\n")
                    ksch.write( "  )\n")

        # Sheets
        for ci in self.component_instances:
            if ci["type"] == "sheet_symbol":
                xsheet, ysheet = ct(ci["x"], ci["y"])
                xsize = ci["xsize"]
                ysize = ci["ysize"]
                children = ci["prims"]
                for child in children:
                    if child["type"] == "sheet_name":
                        sheet_name = child["name"]
                    if child["type"] == "sheet_file_name":
                        sheet_file_name_base, sheet_file_name_ext = os.path.splitext(str(child["name"]))
                        sheet_file_name = sheet_file_name_base + ".kicad_sch"

                uu = uuid.uuid4()
                ksch.write(f"  (sheet (at {xsheet:.3f} {ysheet:.3f})\n")
                ksch.write(f"    (size {xsize:.3f} {ysize:.3f})\n")
                ksch.write( "    (stroke (width 0) (type default) (color 0 0 0 0))\n")
                ksch.write( "    (fill (type background))\n")
                ksch.write(f"    (uuid {uu})\n")
                ksch.write(f"    (property \"Sheet name\" \"{sheet_name}\" (id 0) (at {xsheet:.3f} {ysheet:.3f} 0)\n")
                ksch.write( "      (effects (font (size 1.0 1.0)) (justify bottom left))\n")
                ksch.write( "    )\n")
                ksch.write(f"    (property \"Sheet file\" \"{sheet_file_name}\" (id 1) (at {xsheet+xsize:.3f} {ysheet+ysize:.3f} 0)\n")
                ksch.write( "      (effects (font (size 1.0 1.0)) (justify top right))\n")
                ksch.write( "    )\n")
                for child in children:
                    if child["type"] == "sheet_net":

                        iotype = child["iotype"]
                        iotype_txt = "passive"
                        if iotype == 1:
                            iotype_txt = "output"
                        if iotype == 2:
                            iotype_txt = "input"
                        if iotype == 3:
                            iotype_txt = "bidirectional"

                        side = child["side"]
                        position = child["position"]
                        x = xsheet
                        if side == 1:
                            x += xsize
                        y = ysheet + position * 2.54

                        just = "right" if side == 1 else "left"
                        rotation = 0 if side == 1 else 180

                        uu = uuid.uuid4()
                        ksch.write(f"    (pin \"{child['name']}\" {iotype_txt} (at {x:.3f} {y:.3f} {rotation})\n")
                        ksch.write(f"      (effects (font (size 1.0 1.0)) (justify {just}))\n")
                        ksch.write(f"      (uuid {uu})\n")
                        ksch.write( "    )\n")
                ksch.write( "  )\n")

        ksch.write(")\n")
