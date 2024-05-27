#!/usr/bin/python3

import math
from protel_primitive import ProtelString
import re
import struct
import uuid



class ProtelString16:
    def __init__ (self, bin_file):
        self.s = ""
        length = struct.unpack('<H', bin_file.read(2))[0]
        if length > 0:
            bytestring = bin_file.read(length)
            self.s = bytestring.decode("iso8859_15").replace("\"","'")
            if self.s.endswith('\x00'):
                self.s = self.s[:-1]

    def get (self):
        return self.s


def pointrotate(xcenter, ycenter, x, y, angle):
    dx = x - xcenter
    dy = y - ycenter
    r = math.sqrt(dx * dx + dy * dy)
    startangle_rad = math.atan2(dy, dx)
    endangle_rad = startangle_rad + angle / 180.0 * math.pi
    xnew = xcenter + r * math.cos(endangle_rad)
    ynew = ycenter + r * math.sin(endangle_rad)

    return xnew, ynew


def protel_read_string (f):
    s = ""

    length = f.read(1)[0]
    if length > 0:
        bytestring = f.read(length)
        s = bytestring.decode("iso8859_15")

    return s


class Layers:
    def __init__ (self):
        self.num_layers = 0
        self.d = [{"id":0, "name":""}]
        self.stack = []
        self.num_copper_layers = 0

    def init_default_v3 (self, board):
        self.d.append({"id":1, "name":"TopLayer"})
        self.d.append({"id":2, "name":"MidLayer1"})
        self.d.append({"id":3, "name":"MidLayer2"})
        self.d.append({"id":4, "name":"MidLayer3"})
        self.d.append({"id":5, "name":"MidLayer4"})
        self.d.append({"id":6, "name":"MidLayer5"})
        self.d.append({"id":7, "name":"MidLayer6"})
        self.d.append({"id":8, "name":"MidLayer7"})
        self.d.append({"id":9, "name":"MidLayer8"})
        self.d.append({"id":10, "name":"MidLayer9"})
        self.d.append({"id":11, "name":"MidLayer10"})
        self.d.append({"id":12, "name":"MidLayer11"})
        self.d.append({"id":13, "name":"MidLayer12"})
        self.d.append({"id":14, "name":"MidLayer13"})
        self.d.append({"id":15, "name":"MidLayer14"})
        self.d.append({"id":16, "name":"BottomLayer"})
        self.d.append({"id":17, "name":"Top Silkscreen"})
        self.d.append({"id":18, "name":"Bottom Silkscreen"})
        self.d.append({"id":19, "name":"Top Paste Mask"})
        self.d.append({"id":20, "name":"Bottom Paste Mask"})
        self.d.append({"id":21, "name":"Top Solder Mask"})
        self.d.append({"id":22, "name":"Bottom Solder Mask"})
        self.d.append({"id":23, "name":"InternalPlane1"})
        self.d.append({"id":24, "name":"InternalPlane2"})
        self.d.append({"id":25, "name":"InternalPlane3"})
        self.d.append({"id":26, "name":"InternalPlane4"})
        self.d.append({"id":27, "name":"L27"})
        self.d.append({"id":28, "name":"L28"})
        self.d.append({"id":29, "name":"Mechanical1"})
        self.d.append({"id":30, "name":"Mechanical2"})
        self.d.append({"id":31, "name":"Mechanical3"})
        self.d.append({"id":32, "name":"Mechanical4"})
        self.d.append({"id":33, "name":"L33"})
        self.d.append({"id":34, "name":"MultiLayer"})
        self.num_layers = len(self.d)

        self.stack = [{"protel":"TopLayer", "type":"signal", "kicad":"F.Cu", "kicad_num":0},
                      {"protel":"BottomLayer", "type":"signal", "kicad":"B.Cu", "kicad_num":31}]
        self.num_copper_layers = len(self.stack)

    def to_mm (self, mils):
        if type(mils) == str:
            mils = mils.rstrip('\r\n')
            if mils.endswith("mil"):
                mils = mils[:-3]
            mils = float(mils)
        return mils * 0.0254

    def get_layer_by_name (self, name):
        for layer in self.d:
            if layer["name"] == name:
                return layer
        return None

    # Height of layer stackup (copper + dielectric)
    def get_total_height (self):
        h = 0
        for layer in self.stack:
            detail = self.get_layer_by_name(layer["protel"])
            if detail is not None:
                h += detail.get("cop_thick", 0.035)
                diel_type = detail.get("diel_type", 0)
                if diel_type > 0:
                    h += detail.get("diel_thick", 0.3)
        return h

    def init_from_board_dict (self, board):
        # Collect layer information. Layer numbers start with 1.
        # Look for all consecutive layer numbers.
        n = 1
        while True:
            name = board.get(f"LAYER{n}NAME", None)
            if name is not None:
                layer = {"id": n, "name": name}
                prev = board.get(f"LAYER{n}PREV", None)
                layer["prev"] = 0 if prev is None else int(prev)
                nxt = board.get(f"LAYER{n}NEXT", None)
                layer["next"] = 0 if nxt is None else int(nxt)
                ena = board.get(f"LAYER{n}MECHENABLED", None)
                layer["mech"] = 0 if ena is None else bool(ena)
                cop_thick = board.get(f"LAYER{n}COPTHICL", None)
                layer["cop_thick"] = 0.035 if cop_thick is None else self.to_mm(cop_thick)
                er = board.get(f"LAYER{n}DIELCONST", None)
                layer["er"] = 4.8 if er is None else float(er)
                diel_thick = board.get(f"LAYER{n}DIELHEIGHT", None)
                layer["diel_thick"] = 1.0 if diel_thick is None else self.to_mm(diel_thick)
                diel_type = board.get(f"LAYER{n}DIELTYPE", None)
                layer["diel_type"] = 1 if diel_type is None else int(diel_type)
                diel_mat = board.get(f"LAYER{n}DIELMATERIAL", None)
                layer["diel_mat"] = "FR4" if diel_mat is None else diel_mat

                self.d.append(layer)
                n = n + 1
            else:
                break

        # Determine copper layers in use.
        # The layer stack always starts with Protel TopLayer, all following
        # layers are linked by the "LAYER...NEXT" element, until the last
        # layer (BottomLayer) is reached where LAYER...NEXT=0.

        layer_num = 1
        n = 0
        while layer_num != 0:
            # Look ahead to the next layer in the stack
            nxt = self.d[layer_num]["next"]

            # In case this is an inner layer: Determine the type for KiCad,
            # "signal" (MidLayerX) or "mixed" (InternalPlaneX, Protel layer
            # ID's 39...54).
            kicad_type = "mixed" if (layer_num >= 39) and (layer_num <= 54) else "signal"

            # Add current layer to the stack
            layer = {"protel": self.d[layer_num]["name"], "type": kicad_type}
            if layer_num == 1:      # First layer
                layer["kicad"] = "F.Cu"
                layer["kicad_num"] = 0
            elif nxt == 0:          # Last layer
                layer["kicad"] = "B.Cu"
                layer["kicad_num"] = 31
            else:                   # Inner layer
                layer["kicad"] = f"In{n}"
                layer["kicad_num"] = n

            netname = ""
            if 39 <= layer_num <= 54:
                netname = board.get(f'PLANE{layer_num - 39 + 1}NETNAME', None)
            layer["netname"] = netname

            self.stack.append(layer)

            n += 1
            layer_num = nxt
        self.num_copper_layers = n

        # TODO
        # In case of an odd number of layers, add one more internal plane
        # at the bottom.
        n = self.num_copper_layers
        if (n % 2) == 1:
            layer = {"protel":f"auto_inner{n-1}", "type":"mixed", "kicad":f"In{n-1}", "kicad_num":n-1}
            self.stack = self.stack[0:n-1] + [layer] + [self.stack[n-1]]
            self.num_copper_layers += 1

        #print(f"Layer stack: {self.stack}")
        #for layer in self.d:
        #    if layer["id"] > 0:
        #        print(f"{layer['id']} = {layer['name']}")

    def get_name (self, layer_number):
        if layer_number <= len(self.d):
            name = self.d[layer_number]["name"]
        else:
            raise RuntimeError(f"Illegal layer number {layer_number}")
        return name

    def translate (self, layer):
        # TODO Make these translations configurable
        if layer == "Board-Outline":
            layer = "Mechanical1"
        if (layer == "Dimension") or (layer == "Dimensions"):
            layer = "Mechanical2"
        if layer == "tNames":
            layer = "Mechanical4"
        if layer == "tValues":
            layer = "Mechanical5"
        if layer == "bNames":
            layer = "Mechanical6"
        if layer == "bValues":
            layer = "Mechanical7"
        if layer == "Occupied Area":
            layer = "Mechanical16"

        if layer == "TopSolder":
            layer = "Top Solder Mask"
        if layer == "BottomSolder":
            layer = "Bottom Solder Mask"
        if layer == "TopPaste":
            layer = "Top Paste Mask"
        if layer == "BottomPaste":
            layer = "Bottom Paste Mask"
        if layer == "TopOverlay":
            layer = "Top Silkscreen"
        if layer == "BottomOverlay":
            layer = "Bottom Silkscreen"
        if layer == "Kontur":
            layer = "Mechanical1"

        # Layer names used in Protel ASCII format
        translate = {"TOP": "TopLayer",
                     "BOTTOM": "BottomLayer",
                     "TOPSOLDER": "Top Solder Mask",
                     "BOTTOMSOLDER": "Bottom Solder Mask",
                     "TOPPASTE": "Top Paste Mask",
                     "BOTTOMPASTE": "Bottom Paste Mask",
                     "TOPOVERLAY": "Top Silkscreen",
                     "BOTTOMOVERLAY": "Bottom Silkscreen",
                     "MID1": "MidLayer1",
                     "PLANE1": "MidLayer1",
                     "MECHANICAL1": "Mechanical1",
                     "MECHANICAL2": "Mechanical2",
                     "MECHANICAL16": "Mechanical16",
                     "KEEPOUT": "KeepOutLayer"
                     }
        name = translate.get(layer, None)
        if name is not None:
            layer = name

        # Is the layer part of the (inner) copper layer stack?
        # (Check this first, because without knowing the actual stack,
        # Protel's MidLayerX and InternalPlaneX are ambiguous.)
        for i in range(1,self.num_copper_layers-1):
            if layer == self.stack[i]["protel"]:
                return [{"layer":self.stack[i]["kicad"], "mirror":""}]

        # Translate known layer names to KiCad layers.
        # TODO keep track of enabled mechanical layers, and use this to
        # populate KiCad user layers in sequence
        # TODO configurable assignments of mechanical layers
        translate = {"TopLayer": [{"layer":"F.Cu", "mirror":""}],
                     "BottomLayer": [{"layer":"B.Cu", "mirror":"mirror"}],
                     "Top Solder Mask": [{"layer":"F.Mask", "mirror":""}],
                     "Bottom Solder Mask": [{"layer":"B.Mask", "mirror":"mirror"}],
                     "Top Paste Mask": [{"layer":"F.Paste", "mirror":""}],
                     "Bottom Paste Mask": [{"layer":"B.Paste", "mirror":"mirror"}],
                     "Top Silkscreen": [{"layer":"F.SilkS", "mirror":""}],
                     "Bottom Silkscreen": [{"layer":"B.SilkS", "mirror":"mirror"}],
                     "KeepOutLayer": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical1": [{"layer":"Edge.Cuts", "mirror":""}],
                     "Mechanical2": [{"layer":"Dwgs.User", "mirror":""}],
                     "Mechanical3": [{"layer":"F.Fab", "mirror":""}],
                     "Mechanical4": [{"layer":"F.Fab", "mirror":""}],
                     "Mechanical5": [{"layer":"F.Fab", "mirror":""}],
                     "Mechanical6": [{"layer":"B.Fab", "mirror":""}],
                     "Mechanical7": [{"layer":"B.Fab", "mirror":""}],
                     "Mechanical8": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical9": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical10": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical11": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical12": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical13": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical14": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical15": [{"layer":"Cmts.User", "mirror":""}],
                     "Mechanical16": [{"layer":"F.CrtYd", "mirror":""}, {"layer":"B.CrtYd", "mirror":"mirror"}],
                     "DrillDrawing": [{"layer":"Cmts.User", "mirror":""}]
                     }
    
        klayer = translate.get(layer, None)
        if klayer is None:
            print("Cannot translate layer", layer, self.stack)
            klayer = [{"layer":"Eco1.User", "mirror":""}]
    
        return klayer


class Board:
    def __init__ (self, filename, file):
        self.board = {}
        self.fps = []
        self.vias = []
        self.freepads = []
        self.nets = {0 : {"ID" : 0, "NAME" : ""}}
        self.tracks = []
        self.polygons = {}
        self.freegraphics = []
        self.rules = []
        self.classes = []
        self.filename = filename
        self.layers = Layers()
        self.file = file
        self.offset = [0,0]
        self.ps = ProtelString(file)
        self.bounding_box = None

    def to_mm (self, mils):
        if type(mils) == str:
            mils = mils.rstrip('\r\n')
            if mils.endswith("mil"):
                mils = mils[:-3]
            mils = float(mils)
        return mils * 0.0254

    def to_point (self, xmils, ymils):
        # TODO
        x = 40 + self.to_mm(xmils) + self.offset[0]
        y = 40 + self.offset[1] - self.to_mm(ymils)
        return x, y

    def to_kicad_angle (self, protel_angle):
        # Protel angles:
        # Start at 3 o'clock and count counterclockwise
        # KiCad angles:
        # Start at 12 o'clock and count clockwise
        return 90.0 - protel_angle

    def ascii_to_dict (self, line):
        fields = line.split('|')
        rec = {}
        for field in fields:
            key_value = field.split('=')
            if (len(key_value) == 2):
                rec[key_value[0]] = key_value[1]
        return rec

    def find_fp (self, id):
        for i in range(len(self.fps)):
            fp = self.fps[i]
            if fp["id"] == id:
                return i, fp
    
        fp = {"id":id, "prims":[]}
        self.fps.append(fp)

        return len(self.fps)-1, fp

    def read_string (self, data, index):
        s = ""
        length = int(data[index])
        if length > 0:
            s = data[index+1:index+1+length].decode("iso8859_15")
        s = s.replace("\"", "")
        return s

    def read_float (self, raw):
        f = struct.unpack('<I', raw[1:5])[0] / 4294967296.0
        f = (f + int(raw[5] & 0x7F)) / 128.0 + 1
        if raw[0] == 0:
            f = 0
        else:
            f *= 2 ** (raw[0] - 129)
            if (raw[5] & 0x80) != 0:
                f = -f
        return f

    def get_canvas_origin (self):
        x = self.board["ORIGINX"]
        y = self.board["ORIGINY"]
        return x, y

    def set_offset (self):
        # TODO  Just look at tracks for now

        if len(self.tracks) == 0:
            self.offset = [0,0]
        else:
            xmax = -1e12
            ymax = -1e12
            xmin = 1e12
            ymin = 1e12
    
            for t in self.tracks:
                if t["RECORD"] == "Track":
                    x1 = None

                    x1 = self.to_mm(t['X1'])
                    y1 = self.to_mm(t['Y1'])
                    x2 = self.to_mm(t['X2'])
                    y2 = self.to_mm(t['Y2'])

                    xmax = max(xmax, x1)
                    xmax = max(xmax, x2)
                    ymax = max(ymax, y1)
                    ymax = max(ymax, y2)
                    xmin = min(xmin, x1)
                    xmin = min(xmin, x2)
                    ymin = min(ymin, y1)
                    ymin = min(ymin, y2)
    
            self.offset = [-xmin, ymax]

    def get_netid_by_name (self, name):
        netid = 0
        for id, prim in self.nets.items():
            if name == prim['NAME']:
                netid = id
                break
        return netid

    @classmethod
    def from_protel_ascii (cls, filename, ppcb):
        pcb = cls(filename, ppcb)

        for line in ppcb:
            fields = line.decode("iso8859-15").split('|')
            rec = {}
            for field in fields:
                key_value = field.split('=')
                if len(key_value) == 2:
                    rec[key_value[0]] = key_value[1]
    
            if "RECORD" in rec:
                record = rec["RECORD"]
    
                if record == "Arc":
                    if "COMPONENT" in rec:
                        pass   # ignore
                    elif "POLYGON" in rec:
                        pass   # ignore
                    else:
                        pcb.freegraphics.append(rec)
    
                if record == "Board":
                    for key, value in rec.items():
                        if (key != "RECORD"):
                            pcb.board[key] = value
    
                if record == "Component":
                    index, comp = pcb.find_fp(rec["ID"])
                    comp["X"] = rec["X"]
                    comp["Y"] = rec["Y"]
                    comp["rotation"] = rec["ROTATION"]
                    comp["numprims"] = rec["COUNT"]
                    comp["layer"] = rec["LAYER"]
                    comp["libref"] = rec["PATTERN"]
                    pcb.fps[index] = comp

                if (record == "Arc") or (record == "Fill") or (record == "Pad"):
                    if "COMPONENT" in rec:
                        index, comp = pcb.find_fp(rec["COMPONENT"])
                        comp["prims"].append(rec)
                        pcb.fps[index] = comp

                if record == "Text":
                    if "COMPONENT" in rec:
                        index, comp = pcb.find_fp(rec["COMPONENT"])
                        comp["prims"].append(rec)
                        pcb.fps[index] = comp
                    else:
                        pcb.freegraphics.append(rec)

                if record == "Fill":
                    rec["KEEPOUT"] = "KEEPOUT" == rec.get("LAYER", "")
                    rec["ROTATION"] = float(rec.get("ROTATION", "0"))
                    if "COMPONENT" in rec:
                        index, comp = pcb.find_fp(rec["COMPONENT"])
                        comp["prims"].append(rec)
                        pcb.fps[index] = comp
                    else:
                        pcb.freegraphics.append(rec)

                if record == "Net":
                    pcb.nets[int(rec["ID"]) + 1] = rec

                if record == "Polygon":
                    pcb.polygons[int(rec["ID"])] = rec

                if record == "Track":
                    if "NET" in rec:
                        pcb.tracks.append(rec)
                    elif "COMPONENT" in rec:
                        index, comp = pcb.find_fp(rec["COMPONENT"])
                        comp["prims"].append(rec)
                        pcb.fps[index] = comp
                    elif ("POLYGON" in rec):
                        pass    # ignore
                    else:
                        pcb.freegraphics.append(rec)
    
                if record == "Via":
                    pcb.vias.append(rec)

        pcb.layers.init_from_board_dict(pcb.board)
        pcb.set_offset()
 
        return pcb

    @classmethod
    def from_protel_bin (cls, filename, ppcb, version=4):
        pcb = cls(filename, ppcb)

        section_offset = 0
        while True:
            ppcb.seek(section_offset)
    
            section_name = pcb.ps()
            ppcb.seek(section_offset + 256)
    
            section_element_size = struct.unpack('<H', ppcb.read(2))[0]
            num_elements = struct.unpack('<I', ppcb.read(4))[0]
            section_offset = struct.unpack('<I', ppcb.read(4))[0]
            #print(f"Section: {section_name}, size {section_element_size}, {num_elements} elements, @0x{ppcb.tell():X}")


            if section_name == "PCB 3.0 Binary File":
                '''
                0:          ?
                1:          ?
                2...3:      String length N
                4...4+N-1:  String
                '''
                for i in range(num_elements):
                    ppcb.read(2)
                    length = struct.unpack('<H', ppcb.read(2))[0]
                    fields = ppcb.read(length).decode("iso8859_15").split('|')
                    for field in fields:
                        key_value = field.split('=')
                        if len(key_value) == 2:
                            pcb.board[key_value[0]] = key_value[1]
                    pcb.board["ORIGINX"] = float(re.sub("[^0-9.]", "", pcb.board.get("ORIGINX", 0)))
                    pcb.board["ORIGINY"] = float(re.sub("[^0-9.]", "", pcb.board.get("ORIGINY", 0)))
                #print(pcb.board)

                pcb.layers.init_default_v3(pcb.board)

            if section_name == "PCB 4.0 Binary File":
                '''
                0:          ?
                1:          ?
                2...3:      String length N
                4...4+N-1:  String
                '''
                for i in range(num_elements):
                    ppcb.read(2)
                    length = struct.unpack('<H', ppcb.read(2))[0]
                    fields = ppcb.read(length).decode("iso8859_15").split('|')
                    for field in fields:
                        key_value = field.split('=')
                        if len(key_value) == 2:
                            pcb.board[key_value[0]] = key_value[1].strip()
                    pcb.board["ORIGINX"] = float(re.sub("[^0-9.]", "", pcb.board.get("ORIGINX", 0)))
                    pcb.board["ORIGINY"] = float(re.sub("[^0-9.]", "", pcb.board.get("ORIGINY", 0)))

                # The "board" dict contains all entries from the 'BOARD'
                # section of the whole file. Extract layer information.
                pcb.layers.init_from_board_dict(pcb.board)

            if section_name == "Classes":
                '''
                0:          ?
                '''
                for i in range(num_elements):
                    ppcb.read(2)
                    rec = pcb.ascii_to_dict(ProtelString16(ppcb).get())
                    rec["RECORD"] = "Class"
                    pcb.classes.append(rec)

            if section_name == "Nets":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...9:      ?
                    10...13:    ?
                    14...17:    X
                    18...21:    Y
                    22...26:    ?
                    27...47:    Name (string8)
                    48:         ?
                    '''
                    for i in range(num_elements):
                        netdef = ppcb.read(section_element_size)
                        net = {"RECORD":"Net"}
                        #print(" ".join(f"{x:02X}" for x in netdef))
                        net["layer"] = pcb.layers.get_name(netdef[2])
                        id = struct.unpack('<H', netdef[4:6])[0]
                        index, comp = pcb.find_fp(id)
                        net["ID"] = struct.unpack('<h', netdef[4:6])[0]
                        net["X"] = struct.unpack('<i', netdef[14:18])[0] / 1e4
                        net["Y"] = struct.unpack('<i', netdef[18:22])[0] / 1e4
                        net["NAME"] = pcb.read_string(netdef, 27)
                        pcb.nets[1 + i] = net

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2...3:      String length N
                    4...4+N-1:  String
                    '''
                    for i in range(num_elements):
                        ppcb.read(2)
                        rec = pcb.ascii_to_dict(ProtelString16(ppcb).get())
                        rec["RECORD"] = "Net"
                        rec["ID"] = f"{i}"
                        pcb.nets[1 + i] = rec

            if section_name == "Components":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Component ID
                    6...9:      unknown X
                    10...13:    unknown Y
                    14...38:    ?
                    39...42:    X
                    43...46:    Y
                    47...?:     libref (string8)
                    ?...:308    ?
                    309...314:  Rotation (float6)
                    '''
                    for i in range(num_elements):
                        compdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in compdef[0:80]))
                        id = struct.unpack('<H', compdef[4:6])[0]
                        index, comp = pcb.find_fp(id)
                        comp["X"] = struct.unpack('<i', compdef[39:43])[0] / 1e4
                        comp["Y"] = struct.unpack('<i', compdef[43:47])[0] / 1e4
                        comp["rotation"] = pcb.read_float(compdef[309:315])
                        comp["numprims"] = 0
                        comp["layer"] = pcb.layers.get_name(int(compdef[2]))
                        comp["libref"] = pcb.read_string(compdef, 47)
                        pcb.fps[index] = comp

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Component ID
                    6...9:      unknown X
                    10...13:    unknown Y
                    14...38:    ?
                    39...42:    X
                    43...46:    Y
                    47...?:     libref (string8)
                    ?...:308    ?
                    309...314:  Rotation (float6)
                    315...580:  ?
                    '''
                    for i in range(num_elements):
                        compdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in compdef[0:80]))
                        id = struct.unpack('<H', compdef[4:6])[0]
                        index, comp = pcb.find_fp(id)
                        comp["X"] = struct.unpack('<i', compdef[39:43])[0] / 1e4
                        comp["Y"] = struct.unpack('<i', compdef[43:47])[0] / 1e4
                        comp["rotation"] = pcb.read_float(compdef[309:315])
                        comp["numprims"] = 0
                        comp["layer"] = pcb.layers.get_name(int(compdef[2]))
                        comp["libref"] = pcb.read_string(compdef, 47)
                        pcb.fps[index] = comp
    
            if section_name == "Polygons":
                '''
                0:          ?
                1:          ?
                2:          Layer
                3:          ?
                4...5:      Polygon ID
                6...9:      X?
                10...13:    Y?
                14...17:    X?
                18...21:    Y?
                22:         ?
                23...24:    Net ID
                25...28:    ?
                29...32:    Grid Size
                33...36:    Track Width
                37...40:    Min. Primitive Length
                41...42:    ?
                43...44:    Number N of vertices (+1) that follow

                N+1 times:
                0:          Kind
                1...4:      VX
                5...8:      VY
                9...12:     Center X
                13...16:    Center Y
                17...22:    Start Angle (float6)
                23...28:    End Angle (float6)
                29...32:    Radius
                '''
                for i in range(num_elements):
                    polydef = ppcb.read(section_element_size)
                    #print(" ".join(f"{x:02X}" for x in polydef))
                    poly = {"RECORD":"Polygon"}
                    poly["LAYER"] = pcb.layers.get_name(int(polydef[2]))
                    id = struct.unpack('<h', polydef[4:6])[0]
                    poly["ID"] = f"{id}"
                    netno = struct.unpack('<h', polydef[23:25])[0]
                    if netno != -1:
                        poly["NET"] = netno

                    N = struct.unpack('<H', polydef[43:45])[0]
                    for n in range(N+1):
                        vdef = ppcb.read(33)
                        poly[f"KIND{n}"] = f"{vdef[0]}"
                        poly[f"VX{n}"] = f"{struct.unpack('<i', vdef[1:5])[0] / 1e4}"
                        poly[f"VY{n}"] = f"{struct.unpack('<i', vdef[5:9])[0] / 1e4}"
                        poly[f"CX{n}"] = f"{struct.unpack('<i', vdef[9:13])[0] / 1e4}"
                        poly[f"CY{n}"] = f"{struct.unpack('<i', vdef[13:17])[0] / 1e4}"
                        poly[f"SA{n}"] = f"{pcb.read_float(vdef[17:23])}"
                        poly[f"EA{n}"] = f"{pcb.read_float(vdef[23:29])}"
                        poly[f"R{n}"] = f"{struct.unpack('<i', vdef[29:33])[0] / 1e4}"

                    pcb.polygons[f"{id}"] = poly

            if section_name == "Dimensions":
                '''
                0:          Selection (0/1)
                1:          ?
                2:          Layer
                3:          ?
                4...5:      ID
                6...9:      Bounding Box X1
                10...13:    Bounding Box Y1
                14...17:    Bounding Box X2
                18...21:    Bounding Box Y2
                22:         ?
                23...26:    X1
                27...30:    Y1
                31...34:    X2
                35...38:    Y2
                39...42:    Height
                43...46:    Line Width
                47...50:    Text Height
                51...54:    Text Width
                55:         Font (0=Default, 1=Sans Serif, 2=Serif)
                56...58:    ?
                59:         Unit Style (0=None, 1=Normal, 2=Brackets)
                '''
                for i in range(num_elements):
                    dimdef = ppcb.read(section_element_size)
                    #print(" ".join(f"{x:02X}" for x in dimdef))
                    dim = {"RECORD":"Dimension"}
                    dim["LAYER"] = pcb.layers.get_name(dimdef[2])
                    dim["BBOX_X1"] = struct.unpack('<i', dimdef[6:10])[0] / 1e4
                    dim["BBOX_Y1"] = struct.unpack('<i', dimdef[10:14])[0] / 1e4
                    dim["BBOX_X2"] = struct.unpack('<i', dimdef[14:18])[0] / 1e4
                    dim["BBOX_Y2"] = struct.unpack('<i', dimdef[18:22])[0] / 1e4
                    dim["X1"] = struct.unpack('<i', dimdef[23:27])[0] / 1e4
                    dim["Y1"] = struct.unpack('<i', dimdef[27:31])[0] / 1e4
                    dim["X2"] = struct.unpack('<i', dimdef[31:35])[0] / 1e4
                    dim["Y2"] = struct.unpack('<i', dimdef[35:39])[0] / 1e4
                    dim["HEIGHT"] = struct.unpack('<i', dimdef[39:43])[0] / 1e4
                    dim["LINEWIDTH"] = struct.unpack('<i', dimdef[43:47])[0] / 1e4
                    dim["TEXTHEIGHT"] = struct.unpack('<i', dimdef[47:51])[0] / 1e4
                    dim["TEXTWIDTH"] = struct.unpack('<i', dimdef[51:55])[0] / 1e4
                    dim["FONT"] = dimdef[55]
                    dim["UNITSTYLE"] = dimdef[59]
                    pcb.freegraphics.append(dim)

            if section_name == "Rules":
                '''
                0:          ?
                '''
                for i in range(num_elements):
                    ppcb.read(2)
                    rec = pcb.ascii_to_dict(ProtelString16(ppcb).get())
                    rec["RECORD"] = "Rule"
                    pcb.rules.append(rec)

            if section_name == "Embeddeds":
                if version == 4:
                    edef = bytearray()
                    for i in range(num_elements):
                        edef.extend(ppcb.read(section_element_size))
                    '''
                    for i in range(0,len(edef),16):
                        s = ""
                        for j in range(16):
                            if i+j < len(edef):
                                c = edef[i+j]
                                if (c >= 0x20) and (c <= 0x7E):
                                    s += chr(c)
                                else:
                                    s += '.'
                        print(f"{i:04X} ", " ".join(f"{x:02X}" for x in edef[i:i+16]), s)
                    '''
 
            if section_name == "Arcs":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...7:      ?
                    8...9:      Component ID
                    10...11:    ?
                    12...13:    ?
                    14...17:    Location.X
                    18...21:    Location.Y
                    22...25:    Radius
                    26...31:    Start Angle (float6)
                    32...37:    End Angle (float6)
                    38...41:    Width
                    42...43:    ?
                    '''
                    for i in range(num_elements):
                        arcdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in arcdef))
                        arc = {"RECORD":"Arc"}
                        arc["LAYER"] = pcb.layers.get_name(int(arcdef[2]))
                        netno = struct.unpack('<h', arcdef[4:6])[0]
                        #polyno = struct.unpack('<h', arcdef[11:13])[0]
                        #if polyno != -1:
                        #    arc["POLYGON"] = polyno
                        compno = struct.unpack('<h', arcdef[8:10])[0]
                        if compno != -1:
                            arc["COMPONENT"] = compno
                        if netno != -1:
                            arc["NET"] = netno
                        arc["LOCATION.X"] = struct.unpack('<i', arcdef[14:18])[0] / 1e4
                        arc["LOCATION.Y"] = struct.unpack('<i', arcdef[18:22])[0] / 1e4
                        arc["RADIUS"] = struct.unpack('<i', arcdef[22:26])[0] / 1e4
                        arc["STARTANGLE"] = pcb.read_float(arcdef[26:32])
                        arc["ENDANGLE"] = pcb.read_float(arcdef[32:38])
                        arc["WIDTH"] = struct.unpack('<i', arcdef[38:42])[0] / 1e4
    
                        if compno != -1:
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(arc)
                            pcb.fps[index] = fp
                        else:
                            pass
                            pcb.freegraphics.append(arc)

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...9:      ?
                    10:         ?
                    11...12:    Polygon ID
                    13...14:    Component ID
                    15...18:    ?
                    19...22:    Location.X
                    23...26:    Location.Y
                    27...30:    Radius
                    31...36:    Start Angle (float6)
                    37...42:    End Angle (float6)
                    43...46:    Width
                    47...48:    ?
                    '''
                    for i in range(num_elements):
                        arcdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in arcdef))
                        arc = {"RECORD":"Arc"}
                        netno = struct.unpack('<h', arcdef[4:6])[0]
                        polyno = struct.unpack('<h', arcdef[11:13])[0]
                        if polyno != -1:
                            arc["POLYGON"] = polyno
                        compno = struct.unpack('<h', arcdef[13:15])[0]
                        if compno != -1:
                            arc["COMPONENT"] = compno
                        if netno != -1:
                            arc["NET"] = netno
                        arc["STARTANGLE"] = pcb.read_float(arcdef[31:37])
                        arc["ENDANGLE"] = pcb.read_float(arcdef[37:43])
                        arc["LOCATION.X"] = struct.unpack('<i', arcdef[19:23])[0] / 1e4
                        arc["LOCATION.Y"] = struct.unpack('<i', arcdef[23:27])[0] / 1e4
                        arc["RADIUS"] = struct.unpack('<i', arcdef[27:31])[0] / 1e4
                        arc["WIDTH"] = struct.unpack('<i', arcdef[43:47])[0] / 1e4
                        arc["LAYER"] = pcb.layers.get_name(int(arcdef[2]))
    
                        if netno != -1:
                            pcb.tracks.append(arc)
                        else:
                            if compno != -1:
                                index, fp = pcb.find_fp(compno)
                                fp["prims"].append(arc)
                                pcb.fps[index] = fp
                            else:
                                pcb.freegraphics.append(arc)

            if section_name == "Pads":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...7:      ?
                    8...9:      Component ID
                    10...11:    ?
                    12...13:    ?
                    14...17:    X
                    18...21:    Y
                    22...25:    XSIZE (no padstack: all layers,
                                       padstack: Top layer)
                    26...29:    YSIZE (no padstack: all layers,
                                       padstack: Top layer)
                    30...33:    XSIZE (only padstack: Mid layer)
                    34...37:    YSIZE (only padstack: Mid layer)
                    38...41:    XSIZE (only padstack: Bottom layer)
                    42...45:    YSIZE (only padstack: Bottom layer)
                    46...49:    Holesize
                    50:         Padshape (Top layer) (1=round, 2=rect, 3=octa)
                    51:         Padshape (Inner layers)
                    52:         Padshape (Bottom layer)
                    53...57:    Name (string8, max. 4 (sic!) characters)
                    58...63:    Rotation (float6)
                    64:         Plated?
                    65...66:    ?
                    67...88:    ?
                    89...92:    ?
                    93...100:   ?
                    '''
                    for i in range(num_elements):
                        paddef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in paddef[0:80]))
                        pad = {"RECORD":"Pad"}
                        pad["LAYER"] = pcb.layers.get_name(paddef[2])
                        netno = struct.unpack('<h', paddef[4:6])[0]
                        if netno != -1:
                            pad["NET"] = netno
                        pad["X"] = struct.unpack('<i', paddef[14:18])[0] / 1e4
                        pad["Y"] = struct.unpack('<i', paddef[18:22])[0] / 1e4
                        xtop = struct.unpack('<i', paddef[22:26])[0] / 1e4
                        ytop = struct.unpack('<i', paddef[26:30])[0] / 1e4
                        xmid = struct.unpack('<i', paddef[30:34])[0] / 1e4
                        ymid = struct.unpack('<i', paddef[34:38])[0] / 1e4
                        xbot = struct.unpack('<i', paddef[38:42])[0] / 1e4
                        ybot = struct.unpack('<i', paddef[42:46])[0] / 1e4
                        stack = (xtop != xmid) or (xtop != xbot) or \
                                (ytop != ymid) or (ytop != ybot)
                        if stack:
                            pad["TOPXSIZE"] = xtop
                            pad["TOPYSIZE"] = ytop
                            pad["MIDXSIZE"] = xmid
                            pad["MIDYSIZE"] = ymid
                            pad["BOTXSIZE"] = xbot
                            pad["BOTYSIZE"] = ybot
                        else:
                            pad["XSIZE"] = xtop
                            pad["YSIZE"] = ytop
                        pad["ROTATION"] = pcb.read_float(paddef[58:64])
                        shape = "RECTANGLE" if paddef[50] == 2 else "ROUND"
                        pad["SHAPE"] = "OCTAGONAL" if paddef[50] == 2 else shape
                        pad["PLATED"] = "FALSE" if paddef[64] == 0 else "TRUE"
                        pad["HOLESIZE"] = struct.unpack('<i', paddef[46:50])[0] / 1e4
                        pad["NAME"] = pcb.read_string(paddef, 53)
                        compno = struct.unpack('<h', paddef[8:10])[0]
                        pad["COMPONENT"] = compno
                        if compno != -1:
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(pad)
                            pcb.fps[index] = fp
                        else:
                            # Convert free pads to vias
                            via = {}
                            if netno != -1:
                                via["NET"] = netno
                            via["X"] = pad["X"]
                            via["Y"] = pad["Y"]
                            via["HOLESIZE"] = pad["HOLESIZE"]
                            via["DIAMETER"] = pad["XSIZE"]
                            pcb.vias.append(via)

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...7:      ?
                    8:          Tenting (0/1)
                    9:          ?
                    10:         Keepout (0/1)
                    11...12:    ?
                    13...14:    Component ID
                    15...18:    ?
                    19...22:    X
                    23...26:    Y
                    27...30:    XSIZE (no padstack: all layers,
                                       padstack: Top layer)
                    31...34:    YSIZE (no padstack: all layers,
                                       padstack: Top layer)
                    35...38:    XSIZE (only padstack: Mid layer)
                    39...42:    YSIZE (only padstack: Mid layer)
                    43...46:    XSIZE (only padstack: Bottom layer)
                    47...50:    YSIZE (only padstack: Bottom layer)
                    51...54:    Holesize
                    55:         Padshape (Top layer) (1=round, 2=rect, 3=octa)
                    56:         Padshape (Inner layers)
                    57:         Padshape (Bottom layer)
                    58...78:    Name (string8, max. 20 characters)
                    79...84:    Rotation (float6)
                    85:         Plated (0/1)
                    86:         Electrical type (0=Load, 1=Terminator, 2=Source)
                    87...105:   ?
                    106...109:  Paste Maske Override value
                    110...113:  Solder Mask Override value
                    114...120:  ?
                    121:        Paste Mask Override (1=no, 2=yes)
                    122:        Solder Mask Override (1=no, 2=yes)
                    123...124:  ?
                    '''
                    for i in range(num_elements):
                        paddef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in paddef))
                        pad = {"RECORD":"Pad"}
                        pad["LAYER"] = pcb.layers.get_name(int(paddef[2]))
                        netno = struct.unpack('<h', paddef[4:6])[0]
                        if netno != -1:
                            pad["NET"] = netno
                        pad["X"] = struct.unpack('<i', paddef[19:23])[0] / 1e4
                        pad["Y"] = struct.unpack('<i', paddef[23:27])[0] / 1e4
                        xtop = struct.unpack('<i', paddef[27:31])[0] / 1e4
                        ytop = struct.unpack('<i', paddef[31:35])[0] / 1e4
                        xmid = struct.unpack('<i', paddef[35:39])[0] / 1e4
                        ymid = struct.unpack('<i', paddef[39:43])[0] / 1e4
                        xbot = struct.unpack('<i', paddef[43:47])[0] / 1e4
                        ybot = struct.unpack('<i', paddef[47:51])[0] / 1e4
                        stack = (xtop != xmid) or (xtop != xbot) or \
                                (ytop != ymid) or (ytop != ybot)
                        if stack:
                            pad["TOPXSIZE"] = xtop
                            pad["TOPYSIZE"] = ytop
                            pad["MIDXSIZE"] = xmid
                            pad["MIDYSIZE"] = ymid
                            pad["BOTXSIZE"] = xbot
                            pad["BOTYSIZE"] = ybot
                        else:
                            pad["XSIZE"] = xtop
                            pad["YSIZE"] = ytop
                        pad["ROTATION"] = pcb.read_float(paddef[79:85])
                        shape = "RECTANGLE" if paddef[55] == 2 else "ROUND"
                        pad["SHAPE"] = "OCTAGONAL" if paddef[55] == 2 else shape
                        pad["PLATED"] = "FALSE" if paddef[85] == 0 else "TRUE"
                        pad["HOLESIZE"] = struct.unpack('<i', paddef[51:55])[0] / 1e4
                        pad["NAME"] = pcb.read_string(paddef, 58)
                        compno = struct.unpack('<h', paddef[13:15])[0]
                        pad["COMPONENT"] = compno
                        if compno != -1:
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(pad)
                            pcb.fps[index] = fp
                        else:
                            # Convert free pads to vias
                            via = {}
                            if netno != -1:
                                via["NET"] = netno
                            via["X"] = pad["X"]
                            via["Y"] = pad["Y"]
                            via["HOLESIZE"] = pad["HOLESIZE"]
                            via["DIAMETER"] = pad["XSIZE"]
                            pcb.vias.append(via)

            if section_name == "Vias":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer (34=MULTILAYER)
                    3:          ?
                    4...5:      Net ID
                    6...13:     ?
                    14...17:    X
                    18...21:    Y
                    22...25:    Diameter
                    26...29:    Hole Size
                    30:         ?
                    31:         Start Layer
                    32:         End Layer
                    '''
                    for i in range(num_elements):
                        viadef = ppcb.read(section_element_size)
                        via = {}
                        #print(" ".join(f"{x:02X}" for x in viadef))
                        via["NET"] = struct.unpack('<h', viadef[4:6])[0]
                        via["X"] = struct.unpack('<i', viadef[14:18])[0] / 1e4
                        via["Y"] = struct.unpack('<i', viadef[18:22])[0] / 1e4
                        via["DIAMETER"] = struct.unpack('<I', viadef[22:26])[0] / 1e4
                        via["HOLESIZE"] = struct.unpack('<I', viadef[26:30])[0] / 1e4
                        via["STARTLAYER"] = viadef[31]
                        via["ENDLAYER"] = viadef[32]
                        pcb.vias.append(via)

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer (74=MULTILAYER)
                    3:          ?
                    4...5:      Net ID
                    6...18:     ?
                    19...22:    X
                    23...26:    Y
                    27...30:    Diameter
                    31...34:    Hole Size
                    35:         Start Layer
                    36:         End Layer
                    37:         ?
                    38...41:    CCW
                    42...43:    CEN
                    44...47:    CAG
                    48...51:    CPC
                    52...55:    CPR
                    56...74:    ?
                    '''
                    for i in range(num_elements):
                        viadef = ppcb.read(section_element_size)
                        via = {}
                        via["NET"] = struct.unpack('<h', viadef[4:6])[0]
                        via["X"] = struct.unpack('<i', viadef[19:23])[0] / 1e4
                        via["Y"] = struct.unpack('<i', viadef[23:27])[0] / 1e4
                        via["DIAMETER"] = struct.unpack('<I', viadef[27:31])[0] / 1e4
                        via["HOLESIZE"] = struct.unpack('<I', viadef[31:35])[0] / 1e4
                        via["STARTLAYER"] = viadef[35]
                        via["ENDLAYER"] = viadef[36]
                        pcb.vias.append(via)

            if section_name == "Tracks":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...7:      ?
                    8...9:      Component ID
                    10...13:    ?
                    14...17:    X1
                    18...21:    Y1
                    22...25:    X2
                    26...29:    Y2
                    30...33:    Width
                    34...37:    ?
                    '''
                    for i in range(num_elements):
                        trackdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in trackdef))
                        track = {"RECORD":"Track"}
                        netno = struct.unpack('<h', trackdef[4:6])[0]
                        track["NET"] = netno
                        track["LAYER"] = pcb.layers.get_name(trackdef[2])
#                        polyno = struct.unpack('<h', trackdef[11:13])[0]
#                        if polyno != -1:
#                            track["POLYGON"] = polyno
                        compno = struct.unpack('<h', trackdef[8:10])[0]
                        track["COMPONENT"] = compno
                        track["X1"] = struct.unpack('<i', trackdef[14:18])[0] / 1e4
                        track["Y1"] = struct.unpack('<i', trackdef[18:22])[0] / 1e4
                        track["X2"] = struct.unpack('<i', trackdef[22:26])[0] / 1e4
                        track["Y2"] = struct.unpack('<i', trackdef[26:30])[0] / 1e4
                        track["WIDTH"] = struct.unpack('<i', trackdef[30:34])[0] / 1e4
                        track["SUBPOLYINDEX"] = 0
    
                        if netno != -1:
                            pcb.tracks.append(track)
                        elif compno != -1:
                            if True:#track["LAYER"] == "MECHANICAL1":
                                index, fp = pcb.find_fp(compno)
                                fp["prims"].append(track)
                                pcb.fps[index] = fp
                        elif "POLYGON" in track:
                            i = 1   # ignore
                        else:
                            pcb.freegraphics.append(track)

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      Net ID
                    6...9:      ?
                    10:         ?
                    11...12:    Polygon ID
                    13...14:    Component ID
                    15...18:    ?
                    19...22:    X1
                    23...26:    Y1
                    27...30:    X2
                    31...34:    Y2
                    35...38:    Width
                    39...40:    Sub PolygonID
                    '''
                    for i in range(num_elements):
                        trackdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in trackdef))
                        track = {"RECORD":"Track"}
                        netno = struct.unpack('<h', trackdef[4:6])[0]
                        track["NET"] = netno
                        track["LAYER"] = pcb.layers.get_name(int(trackdef[2]))
                        polyno = struct.unpack('<h', trackdef[11:13])[0]
                        if polyno != -1:
                            track["POLYGON"] = polyno
                        compno = struct.unpack('<h', trackdef[13:15])[0]
                        track["COMPONENT"] = compno
                        track["X1"] = struct.unpack('<i', trackdef[19:23])[0] / 1e4
                        track["Y1"] = struct.unpack('<i', trackdef[23:27])[0] / 1e4
                        track["X2"] = struct.unpack('<i', trackdef[27:31])[0] / 1e4
                        track["Y2"] = struct.unpack('<i', trackdef[31:35])[0] / 1e4
                        track["WIDTH"] = struct.unpack('<i', trackdef[35:39])[0] / 1e4
                        track["SUBPOLYINDEX"] = struct.unpack('<h', trackdef[39:41])[0]
    
                        if netno != -1:
                            pcb.tracks.append(track)
                        elif compno != -1:
                            if True:#track["LAYER"] == "MECHANICAL1":
                                index, fp = pcb.find_fp(compno)
                                fp["prims"].append(track)
                                pcb.fps[index] = fp
                        elif "POLYGON" in track:
                            i = 1   # ignore
                        else:
                            pcb.freegraphics.append(track)

            if section_name == "Texts":
                if version == 3:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      ?
                    6...7:      ?
                    8...9:      Component ID
                    10...11:    ?
                    12...13:    ?
                    14...17:    X
                    18...21:    Y
                    22...25:    Height
                    26...27:    ?
                    28...33:    Rotation (float6)
                    34:         ?
                    35...290:   Text (string8, max. 255 characters)
                    291...294:  Width
                    295:        Flag Comment (0/1)
                    296:        Flag Designator (0/1)
                    '''
                    for i in range(num_elements):
                        txtdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in txtdef[0:80]))
                        #print("   ", " ".join(f"{x:02X}" for x in txtdef[220:297]))
                        txt = {"RECORD":"Text"}
                        txt["LAYER"] = pcb.layers.get_name(txtdef[2])
                        compno = struct.unpack('<h', txtdef[8:10])[0]
                        txt["HEIGHT"] = struct.unpack('<i', txtdef[22:26])[0] / 1e4
                        txt["ROTATION"] = pcb.read_float(txtdef[28:34])
                        txt["X"] = struct.unpack('<i', txtdef[14:18])[0] / 1e4
                        txt["Y"] = struct.unpack('<i', txtdef[18:22])[0] / 1e4
                        txt["TEXT"] = pcb.read_string(txtdef, 35)
                        txt["WIDTH"] = struct.unpack('<i', txtdef[291:295])[0] / 1e4
                        if txtdef[295] != 0:
                            txt["COMMENT"] = "True"
                        if txtdef[296] != 0:
                            txt["DESIGNATOR"] = "True"
                        if compno != -1:
                            txt["COMPONENT"] = compno
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(txt)
                            pcb.fps[index] = fp
                        else:
                            pcb.freegraphics.append(txt)

                if version == 4:
                    '''
                    0:          ?
                    1:          ?
                    2:          Layer
                    3:          ?
                    4...5:      ?
                    6...9:      ?
                    10:         ?
                    11...12:    ?
                    13...14:    Component ID
                    15...18:    ?
                    19...22:    X
                    23...26:    Y
                    27...30:    Height
                    31...32:    ?
                    33...38:    Rotation (float6)
                    39:         ?
                    40...295:   Text (string8, max. 255 characters)
                    296...299:  Width
                    300:        Flag Comment (0/1)
                    301:        Flag Designator (0/1)
                    '''
                    for i in range(num_elements):
                        txtdef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in txtdef))
                        txt = {"RECORD":"Text"}
                        compno = struct.unpack('<h', txtdef[13:15])[0]
                        txt["X"] = struct.unpack('<i', txtdef[19:23])[0] / 1e4
                        txt["Y"] = struct.unpack('<i', txtdef[23:27])[0] / 1e4
                        txt["HEIGHT"] = struct.unpack('<i', txtdef[27:31])[0] / 1e4
                        txt["ROTATION"] = pcb.read_float(txtdef[33:39])
                        txt["TEXT"] = pcb.read_string(txtdef, 40)
                        txt["WIDTH"] = struct.unpack('<i', txtdef[296:300])[0] / 1e4
    
                        txt["LAYER"] = pcb.layers.get_name(int(txtdef[2]))
                        if txtdef[300] != 0:
                            txt["COMMENT"] = "True"
                        if txtdef[301] != 0:
                            txt["DESIGNATOR"] = "True"
                        if compno != -1:
                            txt["COMPONENT"] = compno
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(txt)
                            pcb.fps[index] = fp
                        else:
                            pcb.freegraphics.append(txt)

            if section_name == "Fills":
                if version == 3:
                    '''
                    0:          Selection (0/1)
                    1:          ?
                    2:          Layer
                    '''
                    for i in range(num_elements):
                        filldef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in filldef))
                        fill = {"RECORD":"Fill"}
                        '''
                        fill["X1"] = struct.unpack('<i', filldef[19:23])[0] / 1e4
                        fill["Y1"] = struct.unpack('<i', filldef[23:27])[0] / 1e4
                        fill["X2"] = struct.unpack('<i', filldef[27:31])[0] / 1e4
                        fill["Y2"] = struct.unpack('<i', filldef[31:35])[0] / 1e4
                        fill["ROTATION"] = pcb.read_float(filldef[35:41])
                        fill["LAYER"] = pcb.layers.get_name(int(filldef[2]))
                        compno = struct.unpack('<h', filldef[13:15])[0]
                        if compno != -1:
                            fill["COMPONENT"] = compno
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(fill)
                            pcb.fps[index] = fp
                        else:
                            pcb.freegraphics.append(fill)
                        '''
    
                if version == 4:
                    '''
                    0:          Selection (0/1)
                    1:          ?
                    2:          Layer
                    3:          Locked (0=locked, 1=unlocked)
                    4...5:      Net ID
                    6...9:      ?
                    10:         Keepout (0/1)
                    11...12:    ?
                    13...14:    Component ID
                    15...18:    ?
                    19...22:    X1
                    23...26:    Y1
                    27...30:    X2
                    31...34:    Y2
                    35...40:    Rotation (float6)
                    '''
                    for i in range(num_elements):
                        filldef = ppcb.read(section_element_size)
                        #print(" ".join(f"{x:02X}" for x in filldef))
                        fill = {"RECORD":"Fill"}
                        fill["KEEPOUT"] = int(filldef[2]) == 56     # TODO
                        fill["X1"] = struct.unpack('<i', filldef[19:23])[0] / 1e4
                        fill["Y1"] = struct.unpack('<i', filldef[23:27])[0] / 1e4
                        fill["X2"] = struct.unpack('<i', filldef[27:31])[0] / 1e4
                        fill["Y2"] = struct.unpack('<i', filldef[31:35])[0] / 1e4
                        fill["ROTATION"] = pcb.read_float(filldef[35:41])
                        fill["LAYER"] = pcb.layers.get_name(int(filldef[2]))
                        compno = struct.unpack('<h', filldef[13:15])[0]
                        if compno != -1:
                            fill["COMPONENT"] = compno
                            index, fp = pcb.find_fp(compno)
                            fp["prims"].append(fill)
                            pcb.fps[index] = fp
                        else:
                            pcb.freegraphics.append(fill)
    
            # Go to next section
            if section_offset == 0:
                break

        pcb.set_offset()
 
        return pcb

    def to_kicad7 (self, kpcb, kpcblib_path):
        # Write KiCAD board

        # ---------- Header ----------
        kpcb.write("(kicad_pcb (version 20221018) (generator protel2kicad)\n")
        kpcb.write("\n")
    
        # ---------- General ----------
        kpcb.write(
             "  (general\n"
            f"    (thickness {self.layers.get_total_height():.2f})\n"
             "  )\n"
             )
        kpcb.write( "\n")
    
        # ---------- Page ----------
        kpcb.write('  (paper "A3")\n')

        # ---------- Layers ----------
        kpcb.write('  (layers\n')
        for layer in self.layers.stack:
            kpcb.write(f'    ({layer["kicad_num"]} \"{layer["kicad"]}\" {layer["type"]})\n')
        kpcb.write('    (32 "B.Adhes" user "B.Adhesive")\n')
        kpcb.write('    (33 "F.Adhes" user "F.Adhesive")\n')
        kpcb.write('    (34 "B.Paste" user)\n')
        kpcb.write('    (35 "F.Paste" user)\n')
        kpcb.write('    (36 "B.SilkS" user "B.Silkscreen")\n')
        kpcb.write('    (37 "F.SilkS" user "F.Silkscreen")\n')
        kpcb.write('    (38 "B.Mask" user)\n')
        kpcb.write('    (39 "F.Mask" user)\n')
        kpcb.write('    (40 "Dwgs.User" user "User.Drawings")\n')
        kpcb.write('    (41 "Cmts.User" user "User.Comments")\n')
        kpcb.write('    (42 "Eco1.User" user "User.Eco1")\n')
        kpcb.write('    (43 "Eco2.User" user "User.Eco2")\n')
        kpcb.write('    (44 "Edge.Cuts" user)\n')
        kpcb.write('    (45 "Margin" user)\n')
        kpcb.write('    (46 "B.CrtYd" user "B.Courtyard")\n')
        kpcb.write('    (47 "F.CrtYd" user "F.Courtyard")\n')
        kpcb.write('    (48 "B.Fab" user)\n')
        kpcb.write('    (49 "F.Fab" user)\n')
        kpcb.write('  )\n')
        kpcb.write('\n')

        # ---------- Setup ----------
        kpcb.write("  (setup\n")
        kpcb.write("    (stackup\n")
        kpcb.write("      (layer \"F.SilkS\" (type \"Top Silk Screen\"))\n")
        kpcb.write("      (layer \"F.Paste\" (type \"Top Solder Paste\"))\n")

        top_er = float(self.board.get("TOPCONST", "3.5"))
        top_height = self.to_mm(self.board.get("TOPHEIGHT", "0.4mil"))
        kpcb.write(f"      (layer \"F.Mask\" (type \"Top Solder Mask\") (thickness {top_height:.3f}) (epsilon_r {top_er:.2f}))\n")

        diel_count = 1
        for copper_layer in self.layers.stack:
            details = self.layers.get_layer_by_name(copper_layer["protel"])
            thick = 0.035
            if details is not None:
                thick = details.get("cop_thick", 0.035)
                diel_type = details.get("diel_type", 0)
                diel_name = "core" if diel_type == 1 else "prepreg"
                diel_thick = details.get("diel_thick", 0.3)
                diel_mat = details.get("diel_mat", "FR4")
                diel_er = details.get("er", 4.5)
            kpcb.write(f"      (layer \"{copper_layer['kicad']}\" (type \"copper\") (thickness {thick:.3f}))\n")
            if (diel_type == 1) or (diel_type == 2):
                kpcb.write(f"      (layer \"dielectric {diel_count}\" (type \"{diel_name}\") (thickness {diel_thick:.3f}) (material \"{diel_mat}\") (epsilon_r {diel_er}))\n")
            diel_count += 1

        bot_er = float(self.board.get("BOTTOMCONST", "3.5"))
        bot_height = self.to_mm(self.board.get("BOTTOMHEIGHT", "0.4mil"))
        kpcb.write(f"      (layer \"B.Mask\" (type \"Bottom Solder Mask\") (thickness {bot_height:.3f}) (epsilon_r {bot_er:.2f}))\n")

        kpcb.write("      (layer \"B.Paste\" (type \"Bottom Solder Paste\"))\n")
        kpcb.write("      (layer \"B.SilkS\" (type \"Bottom Silk Screen\"))\n")
        kpcb.write("      (copper_finishe \"None\")\n")
        kpcb.write("      (dielectric_constraints no)\n")
        kpcb.write("    )\n")
        kpcb.write("  )\n")
        kpcb.write("\n")

        # ---------- Properties ----------

        # ---------- Nets ----------
        for id, prim in self.nets.items():
            kpcb.write(f"  (net {id} \"{prim['NAME']}\")\n")
        kpcb.write("\n")

        # ---------- Footprints ----------

        # While processing footprints and free graphics elements, update the bounding box based on elements
        # in the Edge.Cuts layer.
        bx1 = math.inf
        by1 = math.inf
        bx2 = -math.inf
        by2 = -math.inf

        for fp in self.fps:
            if not "layer" in fp.keys():
                continue

            uu = uuid.uuid4()
            l = self.layers.translate(fp["layer"])[0]["layer"]
            kpcb.write(f'  (footprint "{self.filename}_export_pcb:{fp["libref"]}" (layer "{l}")\n')
            compx, compy = self.to_point(fp["X"], fp["Y"])
            comprotation = float(fp["rotation"])
            kpcb.write(f'    (at {compx:.3f} {compy:.3f} {comprotation:.3f})\n')
            kpcb.write( '    (attr smd board_only)\n')

            for prim in fp["prims"]:
                if prim["RECORD"] == "Arc":
                    cx, cy = self.to_point(prim["LOCATION.X"], prim["LOCATION.Y"])
                    cx, cy = pointrotate(compx, compy, cx, cy, comprotation)
                    cx -= compx
                    cy -= compy
                    r = self.to_mm(prim["RADIUS"])
                    endx = cx + r
                    endy = cy
                    width = self.to_mm(prim["WIDTH"])
                    start_angle = (float(prim["ENDANGLE"]) - comprotation) % 360
                    end_angle = (float(prim["STARTANGLE"]) - comprotation) % 360
                    klayer = self.layers.translate(prim["LAYER"])[0]['layer']

                    if start_angle == end_angle:
                        kpcb.write(f'    (fp_circle (center {cx:.3f} {cy:.3f}) (end {endx:.4f} {endy:.4f})\n')
                        kpcb.write(f'      (stroke (width {width}) (type solid)) (fill none) (layer {klayer}))\n')
                    else:
                        alpha1 = self.to_kicad_angle(start_angle)
                        alpha3 = self.to_kicad_angle(end_angle)
                        alpha2 = alpha1 + ((360 + alpha3 - alpha1) % 360) / 2
                        x1 = cx + r * math.sin(alpha1 / 57.29578)
                        y1 = cy - r * math.cos(alpha1 / 57.29578)
                        x2 = cx + r * math.sin(alpha2 / 57.29578)
                        y2 = cy - r * math.cos(alpha2 / 57.29578)
                        x3 = cx + r * math.sin(alpha3 / 57.29578)
                        y3 = cy - r * math.cos(alpha3 / 57.29578)

                        kpcb.write(f'    (fp_arc (start {x1:.3f} {y1:.3f}) (mid {x2:.3f} {y2:.3f}) (end {x3:.3f} {y3:.3f})\n')
                        kpcb.write(f'      (stroke (width {width}) (type solid)) (layer {klayer}))\n')

                        if klayer == 'Edge.Cuts':
                            bx1 = min(x1 + compx, x2 + compx, x3 + compx, bx1)
                            by1 = min(y1 + compy, y2 + compy, y3 + compy, by1)
                            bx2 = max(x1 + compx, x2 + compx, x3 + compx, bx2)
                            by2 = max(y1 + compy, y2 + compy, y3 + compy, by2)

                if prim["RECORD"] == "Text":
                    if "DESIGNATOR" in prim:
                        designator = prim["TEXT"]
                        x, y = self.to_point(prim["X"], prim["Y"])
                        x, y = pointrotate(compx, compy, x, y, comprotation)
                        x -= compx
                        y -= compy
                        height = self.to_mm(prim["HEIGHT"])
                        thick = self.to_mm(prim["WIDTH"])
    
                        trot = float(prim["ROTATION"])
                        tlayer = "F.Fab"
                        mirror = ""
                        if l == "B.Cu":
                            tlayer = "B.Fab"
                            mirror = " mirror"
    
                        s_pos = f"(at {x:.3f} {y:.3f} {trot}) (layer \"{tlayer}\")"
                        s_font = f"(font (size {height:.3f} {height:.3f}) (thickness {thick:.3f}))"
                        kpcb.write(
                            f"    (fp_text reference \"{designator}\" {s_pos}\n"
                            f"      (effects {s_font} (justify left{mirror}))\n"
                             "    )\n"
                             )
    
                    if "COMMENT" in prim:
                        comment = prim["TEXT"]
                        x, y = self.to_point(prim["X"], prim["Y"])
                        x, y = pointrotate(compx, compy, x, y, comprotation)
                        x -= compx
                        y -= compy
                        height = self.to_mm(prim["HEIGHT"])
                        thick = self.to_mm(prim["WIDTH"])
    
                        trot = float(prim["ROTATION"])
                        tlayer = "F.Fab"
                        mirror = ""
                        if l == "B.Cu":
                            tlayer = "B.Fab"
                            mirror = " mirror"
    
                        s_pos = f'(at {x:.3f} {y:.3f} {trot}) (layer "{tlayer}")'
                        s_font = f'(font (size {height:.3f} {height:.3f}) (thickness {thick:.3f}))'
                        kpcb.write(
                            f'    (fp_text value "{comment}" {s_pos}\n'
                            f'      (effects {s_font} (justify left{mirror}))\n'
                             '    )\n'
                             )
    
                if prim["RECORD"] == "Track":
                    x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                    x1, y1 = pointrotate(compx, compy, x1, y1, comprotation)
                    x2, y2 = self.to_point(prim["X2"], prim["Y2"])
                    x2, y2 = pointrotate(compx, compy, x2, y2, comprotation)
                    x1 -= compx
                    y1 -= compy
                    x2 -= compx
                    y2 -= compy
                    width = self.to_mm(prim["WIDTH"])

                    ldef = self.layers.translate(prim["LAYER"])
                    layer = ldef[0]["layer"]
                    if (l == "B.Cu") and (len(ldef) >= 2):
                        layer = ldef[1]["layer"]
                    kpcb.write(f'    (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n')
                    kpcb.write(f'      (stroke (width {width:.3f}) (type solid)) (layer {layer}))\n')

                    if layer == 'Edge.Cuts':
                        bx1 = min(x1 + compx, x2 + compx, bx1)
                        by1 = min(y1 + compy, y2 + compy, by1)
                        bx2 = max(x1 + compx, x2 + compx, bx2)
                        by2 = max(y1 + compy, y2 + compy, by2)

                if prim["RECORD"] == "Fill":
                    fillrotation = float(prim["ROTATION"])
                    klayers = self.layers.translate(prim["LAYER"])
                    x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                    x2, y2 = self.to_point(prim["X2"], prim["Y2"])
                    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                    x1, y1 = pointrotate(center_x, center_y, x1, y1, fillrotation)
                    x2, y2 = pointrotate(center_x, center_y, x2, y2, fillrotation)
                    x1, y1 = pointrotate(compx, compy, x1, y1, comprotation)
                    x2, y2 = pointrotate(compx, compy, x2, y2, comprotation)
                    x1 -= compx
                    y1 -= compy
                    x2 -= compx
                    y2 -= compy
                    for klayer in klayers:
                        layer = klayer["layer"]
                        kpcb.write(
                            f'    (fp_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n'
                             '      (stroke (width 0.01) (type solid)) (fill solid)'
                            f' (layer "{layer}"))\n'
                             )

            for prim in fp["prims"]:
                if prim["RECORD"] == "Pad":
                    compname = "?"
                    if prim.get("COMPONENT", None) is not None:
                        n, fp = self.find_fp(prim["COMPONENT"])
                        compname = fp["libref"]

                    # Detect Protel style fiducial.
                    # There seems to be this convention: A pad in the KeepOutLayer defines
                    # the solder mask opening, and the drill diameter value defines the
                    # SMD pad size in the middle.
                    if prim["LAYER"] == "KeepOutLayer":
                        prim["LAYER"] = "TopLayer" if l == "F.Cu" else "BottomLayer"
                        prim["SOLDERMASK_OVERRIDE"] = prim["XSIZE"] / 2
                        prim["XSIZE"] = prim["HOLESIZE"]
                        prim["YSIZE"] = prim["HOLESIZE"]
                        prim["HOLESIZE"] = 0
                        prim["SHAPE"] = "ROUND"

                    x, y = self.to_point(prim["X"], prim["Y"])
                    x, y = pointrotate(compx, compy, x, y, comprotation)
                    x -= compx
                    y -= compy
                    if prim.get("XSIZE", None) is not None:
                        xsize = self.to_mm(prim["XSIZE"])
                        ysize = self.to_mm(prim["YSIZE"])
                    else:
                        #print(f"Unsupported pad stack in {compname} @({x:.3f},{y:.3f})")
                        xsize = self.to_mm(prim["TOPXSIZE"])
                        ysize = self.to_mm(prim["TOPYSIZE"])
                    padrotation = float(prim["ROTATION"])
    
                    padshape = "rect"
                    padtype = "smd"
                    padlayers = "\"F.Cu\" \"F.Paste\" \"F.Mask\""
    
                    if prim["LAYER"] == "MultiLayer":   # TODO
                        padtype = "thru_hole"
                        padlayers = "\"*.Cu\" \"*.Mask\""
                        if prim["PLATED"] == "FALSE":
                            padtype = "np_thru_hole"
                            padlayers = "\"*.Cu\" \"*.Mask\""
                            if not "NET" in prim:
                                prim["NAME"] = ""
                    elif prim["LAYER"] == "BottomLayer":    # TODO
                        padlayers = "\"B.Cu\" \"B.Paste\" \"B.Mask\""

                    if prim.get("SHAPE", None) is not None:
                        shape = prim["SHAPE"]
                    else:
                        print(f"Unsupported pad stack in {compname} @({x:.3f},{y:.3f})")
                        shape = prim["TOPSHAPE"]
                    if shape == "ROUND":
                        padshape = "circle"
                        if xsize != ysize:
                            padshape = "oval"

                    size = self.to_mm(prim["HOLESIZE"])
                    paddrill = f"(drill {size:.2f})"

                    kpcb.write(
                        f"    (pad \"{prim['NAME']}\" {padtype} {padshape} (at {x:.3f} {y:.3f}"
                        f" {padrotation:.3f}) (size {xsize:.3f} {ysize:.3f}) {paddrill} (layers {padlayers})"
                        )
    
                    if "NET" in prim:
                        netid = int(prim["NET"]) + 1
                        kpcb.write(f'\n      (net {netid} \"{self.nets[netid]["NAME"]}\")')
                    soldermask_override = self.to_mm(prim.get("SOLDERMASK_OVERRIDE", 0))
                    if soldermask_override > 0:
                        kpcb.write(f'\n      (solder_mask_margin {soldermask_override})')
                    kpcb.write(')\n')

            kpcb.write("  )\n")
            kpcb.write("\n")

        # ---------- Graphics ----------

        for prim in self.freegraphics:
            klayers = self.layers.translate(prim["LAYER"])
    
            if prim["RECORD"] == "Track":
                for klayer in klayers:
                    if not "POLYGON" in prim:
                        layer = klayer["layer"]
                        x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                        x2, y2 = self.to_point(prim["X2"], prim["Y2"])
                        width = self.to_mm(prim["WIDTH"])
                        kpcb.write(
                            f'  (gr_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n'
                            f'    (stroke (width {width:.3f}) (type solid)) (layer {layer}))\n'
                            )

                    if layer == 'Edge.Cuts':
                        bx1 = min(x1, x2, bx1)
                        by1 = min(y1, y2, by1)
                        bx2 = max(x1, x2, bx2)
                        by2 = max(y1, y2, by2)

            if prim["RECORD"] == "Arc":
                if not "POLYGON" in prim:
                    layer = self.layers.translate(prim["LAYER"])[0]["layer"]

                    cx, cy = self.to_point(prim["LOCATION.X"], prim["LOCATION.Y"])
                    r = self.to_mm(prim["RADIUS"])
                    width = self.to_mm(prim["WIDTH"])

                    start_angle = float(prim["ENDANGLE"]) % 360
                    end_angle = float(prim["STARTANGLE"]) % 360
                    alpha1 = self.to_kicad_angle(start_angle)
                    alpha3 = self.to_kicad_angle(end_angle)
                    alpha2 = alpha1 + ((360 + alpha3 - alpha1) % 360) / 2
                    x1 = cx + r * math.sin(alpha1 / 57.29578)
                    y1 = cy - r * math.cos(alpha1 / 57.29578)
                    x2 = cx + r * math.sin(alpha2 / 57.29578)
                    y2 = cy - r * math.cos(alpha2 / 57.29578)
                    x3 = cx + r * math.sin(alpha3 / 57.29578)
                    y3 = cy - r * math.cos(alpha3 / 57.29578)

                    kpcb.write(
                        f'  (gr_arc (start {x1:.3f} {y1:.3f}) (mid {x2:.3f} {y2:.3f}) (end {x3:.3f} {y3:.3f})\n'
                        f'    (stroke (width {width:3f}) (type solid)) (layer {layer}))\n'
                        )

                    if layer == 'Edge.Cuts':
                        bx1 = min(x1, x2, x3, bx1)
                        by1 = min(y1, y2, y3, by1)
                        bx2 = max(x1, x2, x3, bx2)
                        by2 = max(y1, y2, y3, by2)

            if prim["RECORD"] == "Text":
                for klayer in klayers:
                    layer = klayer["layer"]
                    mirror = klayer["mirror"]
                    x, y = self.to_point(prim["X"], prim["Y"])
                    text = prim["TEXT"]
                    height = self.to_mm(prim["HEIGHT"])
                    thick = self.to_mm(prim["WIDTH"])
                    rotation = 0
                    if "ROTATION" in prim:
                        rotation = prim["ROTATION"]
                    kpcb.write(
                        f'  (gr_text "{text}" (at {x:.3f} {y:.3f} {rotation}) (layer "{layer}")\n'
                        f'    (effects (font (size {height:.2f} {height:.2f}) (thickness {thick:.3f}))'
                            f' (justify left bottom {mirror}))\n'
                         '  )\n'
                         )
    
            if prim["RECORD"] == "Fill":
                for klayer in klayers:
                    layer = klayer["layer"]
                    mirror = klayer["mirror"]
                    x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                    x2, y2 = self.to_point(prim["X2"], prim["Y2"])

                    # Keepouts will be defined later as zones
                    if not prim["KEEPOUT"]:
                        if prim["ROTATION"] == 0:
                            kpcb.write(
                                f'  (gr_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n'
                                f'    (stroke (width 0.1) (type solid)) (fill solid) (layer "{layer}"))\n'
                                )
                        else:
                            # Rotate rectangle vertices
                            cx = (x1 + x2) / 2
                            cy = (y1 + y2) / 2
                            angle = -prim["ROTATION"]
                            xa, ya = pointrotate(cx, cy, x1, y1, angle)
                            xb, yb = pointrotate(cx, cy, x2, y1, angle)
                            xc, yc = pointrotate(cx, cy, x2, y2, angle)
                            xd, yd = pointrotate(cx, cy, x1, y2, angle)
                            kpcb.write(
                                 '  (gr_poly\n'
                                 '    (pts\n'
                                f'      (xy {xa:.3f} {ya:.3f})\n'
                                f'      (xy {xb:.3f} {yb:.3f})\n'
                                f'      (xy {xc:.3f} {yc:.3f})\n'
                                f'      (xy {xd:.3f} {yd:.3f})\n'
                                 '    )\n'
                                f'    (stroke (width 0.1) (type solid)) (fill solid) (layer "{layer}"))\n'
                                )

            if prim["RECORD"] == "Dimension":
                for klayer in klayers:
                    layer = klayer["layer"]
                    x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                    x2, y2 = self.to_point(prim["X2"], prim["Y2"])
                    line_width = self.to_mm(prim["LINEWIDTH"])
                    unit_style = prim["UNITSTYLE"]

                    kpcb.write(
                        f'  (dimension (type aligned) (layer "{layer}")\n'
                        f'    (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f}))\n'
                        f'    (format (units 2) (units_format {unit_style}) (precision 7))\n'
                        f'    (style (thickness {line_width:.3f}) (text_position_mode 1))\n'
                         '  )\n'
                         )
    
        kpcb.write("\n")

        # Save bounding box coordinates
        if (bx1 < bx2) and (by1 < by2):
            self.bounding_box = {"x1":bx1, "y1":by1, "x2":bx2, "y2":by2}

        # ---------- Images ----------
        # There are no images encoded in Protel PCB files

        # ---------- Tracks ----------

        # Segments
        for prim in self.tracks:
            if prim["RECORD"] == "Track":
                track = prim
                x1, y1 = self.to_point(track["X1"], track["Y1"])
                x2, y2 = self.to_point(track["X2"], track["Y2"])
                layer = self.layers.translate(track["LAYER"])[0]["layer"]
                width = self.to_mm(track["WIDTH"])
                netno = 1 + int(track["NET"])
                if netno >= 1:
                    kpcb.write(
                        f"  (segment"
                        f" (start {x1:.3f} {y1:.3f})"
                        f" (end {x2:.3f} {y2:.3f})"
                        f" (width {width:.3f})"
                        f" (layer {layer})"
                        f" (net {netno}))\n"
                        )

            if prim["RECORD"] == "Arc":
                if not "POLYGON" in prim:
                    layer = self.layers.translate(prim["LAYER"])[0]["layer"]

                    cx, cy = self.to_point(prim["LOCATION.X"], prim["LOCATION.Y"])
                    r = self.to_mm(prim["RADIUS"])
                    width = self.to_mm(prim["WIDTH"])

                    start_angle = prim["ENDANGLE"] % 360
                    end_angle = prim["STARTANGLE"] % 360
                    alpha1 = self.to_kicad_angle(start_angle)
                    alpha3 = self.to_kicad_angle(end_angle)
                    alpha2 = alpha1 + ((360 + alpha3 - alpha1) % 360) / 2
                    x1 = cx + r * math.sin(alpha1 / 57.29578)
                    y1 = cy - r * math.cos(alpha1 / 57.29578)
                    x2 = cx + r * math.sin(alpha2 / 57.29578)
                    y2 = cy - r * math.cos(alpha2 / 57.29578)
                    x3 = cx + r * math.sin(alpha3 / 57.29578)
                    y3 = cy - r * math.cos(alpha3 / 57.29578)

                    netno = 1 + int(prim["NET"])
                    if netno >= 1:
                        kpcb.write(
                            f'  (arc (start {x1:.3f} {y1:.3f})'
                            f' (mid {x2:.3f} {y2:.3f}) (end {x3:.3f} {y3:.3f})\n'
                            f' (net {netno})'
                            f' (layer {layer}) (width {width:3f}))\n'
                            )
        kpcb.write("\n")
    
        # Vias
        for via in self.vias:
            fromto = "F.Cu B.Cu"
            netid = via.get("NET", None)
            if netid is not None:
                netid = int(netid) + 1
                x, y = self.to_point(via["X"], via["Y"])
                kpcb.write(
                    f"  (via (at {x:.3f} {y:.3f})"
                    f" (size {self.to_mm(via['DIAMETER']):.3f})"
                    f" (drill {self.to_mm(via['HOLESIZE']):.3f})"
                    f" (layers {fromto})"
                    f" (net {netid}))\n"
                    )
        kpcb.write("\n")

        # ---------- Zones ----------
        for id, prim in self.polygons.items():
            netid = prim.get("NET", None)
            if netid is not None:
                netid = int(netid)
                netprim = self.nets[netid+1]
                polylayer = self.layers.translate(prim["LAYER"])[0]["layer"]

                kpcb.write(f'  (zone (net {netid+1}) (net_name {netprim["NAME"]}) (layer {polylayer}) (hatch edge 0.508)\n')
                kpcb.write( '    (priority 1)\n')       # Take priority over background fill in power planes
                kpcb.write( '    (connect_pads (clearance 0.2))\n')
                kpcb.write( '    (min_thickness 0.1778)\n')
                kpcb.write( '    (fill yes (arc_segments 16) (thermal_gap 0.254) (thermal_bridge_width 0.4064))\n')
                kpcb.write( '    (polygon\n')
                kpcb.write( '      (pts\n')
                i = 0
                while True:
                    # Key for vertex i
                    keyx = f'VX{i}'
                    keyy = f'VY{i}'
                    if (keyx in prim) and (keyy in prim):
                        x, y = self.to_point(prim[keyx], prim[keyy])
                        kpcb.write(f'        (xy {x:.3f} {y:.3f})\n')
                    else:
                        break
                    i += 1
                kpcb.write( '      )\n')
                kpcb.write( '    )\n')
                kpcb.write( '  )\n')

        # Free fills on keepout layer translate to zones
        # TODO: Must use design rules to adjust size!
        for prim in self.freegraphics:
            klayers = self.layers.translate(prim["LAYER"])

            if prim["RECORD"] == "Fill":
                if prim["KEEPOUT"]:
                    x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                    x2, y2 = self.to_point(prim["X2"], prim["Y2"])

                    # Rotate rectangle vertices
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    angle = -prim["ROTATION"]
                    xa, ya = pointrotate(cx, cy, x1, y1, angle)
                    xb, yb = pointrotate(cx, cy, x2, y1, angle)
                    xc, yc = pointrotate(cx, cy, x2, y2, angle)
                    xd, yd = pointrotate(cx, cy, x1, y2, angle)

                    kpcb.write( '  (zone (net 0) (net_name "") (layers "F&B.Cu") '
                               f'(name "keepout_{x1}_{y1}") (hatch edge 0.5)\n')
                    kpcb.write( '    (keepout (tracks not_allowed) (vias not_allowed) '
                                '(pads not_allowed) (copperpour not_allowed))\n')
                    kpcb.write( '    (polygon\n')
                    kpcb.write( '      (pts\n')
                    x1, y1 = self.to_point(prim["X1"], prim["Y1"])
                    x2, y2 = self.to_point(prim["X2"], prim["Y2"])
                    kpcb.write(f'        (xy {xa:.3f} {ya:.3f})\n')
                    kpcb.write(f'        (xy {xb:.3f} {yb:.3f})\n')
                    kpcb.write(f'        (xy {xc:.3f} {yc:.3f})\n')
                    kpcb.write(f'        (xy {xd:.3f} {yd:.3f})\n')
                    kpcb.write( '      )\n')
                    kpcb.write( '    )\n')
                    kpcb.write( '  )\n')

        # Add filled zones on power planes.
        # Board boundary must be known
        if self.bounding_box is not None:
            # Check for power planes (they have Kicad type 'mixed')
            for layer in self.layers.stack:
                if layer["type"] == "mixed":
                    #print("power plane:", layer, self.bounding_box, layer["netname"])

                    netname = layer['netname']
                    netid = self.get_netid_by_name(netname)
                    s_netname = f'(net_name {netname})'

                    if netname == '(No Net)':
                        s_netname = ''
                        netid = -1

                    kpcb.write(f'  (zone (net {netid+1}) {s_netname} (layer {layer["kicad"]}) (hatch edge 0.508)\n')
                    kpcb.write( '    (priority 0)\n')       # Lowest priority
                    kpcb.write( '    (connect_pads (clearance 0.2))\n')
                    kpcb.write( '    (min_thickness 0.1778)\n')
                    kpcb.write( '    (fill yes (arc_segments 16) (thermal_gap 0.254) (thermal_bridge_width 0.4064))\n')
                    kpcb.write( '    (polygon\n')
                    kpcb.write( '      (pts\n')
                    kpcb.write(f'        (xy {self.bounding_box["x1"]:.3f} {self.bounding_box["y1"]:.3f})\n')
                    kpcb.write(f'        (xy {self.bounding_box["x2"]:.3f} {self.bounding_box["y1"]:.3f})\n')
                    kpcb.write(f'        (xy {self.bounding_box["x2"]:.3f} {self.bounding_box["y2"]:.3f})\n')
                    kpcb.write(f'        (xy {self.bounding_box["x1"]:.3f} {self.bounding_box["y2"]:.3f})\n')
                    kpcb.write( '      )\n')
                    kpcb.write( '    )\n')
                    kpcb.write( '  )\n')

        # ---------- Groups ----------

        kpcb.write(")\n")
