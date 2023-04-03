#!/usr/bin/python3

import os
import struct



class ProtelString:
    def __init__ (self, bin_file):
        self.s = ""
        self.file = bin_file

    def __call__(self):
        self.s = ""
        length = self.file.read(1)[0]
        if length > 0:
            bytestring = self.file.read(length)
            self.s = bytestring.decode("iso8859_15").replace("\"","'")
        return self.s


class ProtelString16:
    def __init__ (self, bin_file):
        self.s = ""
        self.file = bin_file

    def __call__(self):
        length = struct.unpack('<H', self.file.read(2))[0]
        if length > 0:
            bytestring = self.file.read(length)
            self.s = bytestring.decode("iso8859_15")
            self.s = self.s.replace("\r", "").replace("\n", "\\n").replace("\"","'")
        return self.s


class KicadString:
    def __init__ (self):
        pass

    def __call__(self, s):
        if s.find('\\') >= 0:
            s = s.replace('\\', "")
            s = "~{" + s + "}"
        return s


class Primitive:
    def __init__ (self):
        self.name = ""
        self.variants = []
        self.fileoffset = None
        self.d = {}

    # Translate orientation code to rotation angle
    def get_rotation (self, orientation):
        rotate = 0
        if orientation == 1:
            rotate = 90
        if orientation == 2:
            rotate = 180
        if orientation == 3:
            rotate = 270
        return rotate

    # Translate from width code (0=smallest, 1=small, 2=medium, 3=large) to mm.
    def get_width (self, width_code):
        if width_code == 1:
            width = 0.1524
        elif width_code == 2:
            width = 0.4572
        elif width_code == 3:
            width = 0.762
        else:
            width = 0.01
        return width

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

    def read_bin (self, infile):
        gelem = None
        ps = ProtelString(infile)
        ps16 = ProtelString16(infile)

        prim_type = infile.read(1)[0]
        #print(f"Prim type {prim_type}")

        if prim_type == 1:      # Component
            '''
            0...1:      X
            2...3:      Y
            4:          Mode (0=Normal, 1=DeMorgan, 2=IEEE)
            5:          Mirrored, Y axis (0/1)
            6:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            7:          Selection (0/1)
            8:          Unit number
            9...11:     ?
            12:         Show hidden fields (0/1)
            13:         Show hidden pins (0/1)
            14...x      Library reference
            x+1...      Footprint name
            ...         List of child primitives, ends with type=255
            '''
            gelem = {"type":"component"}
            compdef = infile.read(14)
            gelem["x"] = struct.unpack('<h', compdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', compdef[2:4])[0] * 0.254
            gelem["mirrored_y"] = compdef[5]
            gelem["rotation"] = self.get_rotation(compdef[6])
            gelem["unit"] = compdef[8]
            gelem["libref"] = ps()
            gelem["footprint"] = ps()
            #print("Component", " ".join(f"{x:02X}" for x in compdef), gelem["libref"])
            children = []
            while True:
                child = self.read_bin(infile)
                if child is None:
                    break
                children.append(child)
            gelem["prims"] = children

        elif prim_type == 2:    # Pin
            '''
            0:          Dot Symbol (0/1)
            1:          Clk Symbol (0/1)
            2:          Electrical Type (0=Input, 1=IO, 2=Output,
                                         3=OpenCollector, 4=Passive, 5=HiZ,
                                         6=OpenEmitter, 7=Power)
            3:          Hidden
            4:          Show Name (0/1)
            5:          Show Number (0/1)
            6:          Length
            7:          Selection (0/1)
            8...9:      X
            10...11:    Y
            12:         Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            13...16:    Color (RGBA)
            17...       Name (string8)
            ?...        Number (string8)
            '''
            gelem = {"type":"pin"}
            pindef = infile.read(17)
            gelem["dotsymbol"] = pindef[0]
            gelem["clksymbol"] = pindef[1]
            gelem["electrical"] = pindef[2]
            gelem["hidden"] = pindef[3]
            gelem["showname"] = pindef[4]
            gelem["shownumber"] = pindef[5]
            gelem["length"] = pindef[6] * 0.254
            gelem["selection"] = pindef[7]
            gelem["x"] = struct.unpack('<h', pindef[8:10])[0] * 0.254
            gelem["y"] = struct.unpack('<h', pindef[10:12])[0] * 0.254
            gelem["rotation"] = self.get_rotation(pindef[12])
            gelem["color"] = pindef[13:17]
            gelem["name"] = ps()
            gelem["number"] = ps()
            #print("Pin ", " ".join(f"{x:02X}" for x in pindef), gelem["name"])

        elif prim_type == 3:    # IEEE Symbol
            '''
            0:          Symbol (0=none, 1=Dot, 2=Right Left Signal Flow, ...)
            1...2:      X
            3...4:      Y
            5...6:      Size
            7:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            8:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Color (RGBA)
            13:         Selection (0/1)
            '''
            gelem = {"type":"ieee_symbol"}
            ieeedef = infile.read(14)
            gelem["symbol"] = ieeedef[0]
            gelem["x"] = struct.unpack('<h', ieeedef[1:3])[0] * 0.254
            gelem["y"] = struct.unpack('<h', ieeedef[3:5])[0] * 0.254
            gelem["size"] = struct.unpack('<h', ieeedef[5:7])[0] * 0.254
            gelem["rotation"] = self.get_rotation(ieeedef[7])
            gelem["width"] = self.get_width(ieeedef[8])
            gelem["color"] = ieeedef[9:13]
            gelem["selection"] = ieeedef[13]
            #print("IEEE Symbol ", " ".join(f"{x:02X}" for x in ieeedef))

        elif prim_type == 4:    # Text
            '''
            0...1:      X
            2...3:      Y
            4:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            5...8:      Color (RGBA)
            9...10:     Index in font table (starts with 1)
            11:         Selection (0/1)
            12...x:     Text (string8)
            '''
            gelem = {"type":"text"}
            txtdef = infile.read(12)
            gelem["x"] = struct.unpack('<h', txtdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', txtdef[2:4])[0] * 0.254
            gelem["rotation"] = self.get_rotation(txtdef[4])
            gelem["color"] = txtdef[5:9]
            gelem["font"] = struct.unpack('<H', txtdef[9:11])[0]
            gelem["text"] = ps()
            #print(f"  Text before 0x{infile.tell():X}", " ".join(f"{x:02X}" for x in txtdef), gelem["text"])

        elif prim_type == 5:    # Bezier
            '''
            0:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            1...4:      Color (RGBA)
            5:          Selection (0/1)
            6...7:      N (number of points that follow)
            N times:
            0...1:      Xi
            2...3:      Yi
            '''
            gelem = {"type":"bezier"}
            bezdef = infile.read(8)
            gelem["width"] = self.get_width(bezdef[0])
            gelem["color"] = bezdef[1:5]
            npoints = struct.unpack('<h', bezdef[6:8])[0]
            points = []
            for i in range(npoints):
                x = struct.unpack('<h', infile.read(2))[0] * 0.254
                y = struct.unpack('<h', infile.read(2))[0] * 0.254
                points.append([x,y])
            if npoints >= 1:
                # There should always be 3n+1 points for n quadratic
                # Bezier segments. The last point is duplicated and
                # can be dropped.
                gelem["npoints"] = npoints - 1
                gelem["points"] = points[:-1]
            #print("Bezier", " ".join(f"{x:02X}" for x in bezdef))

        elif prim_type == 6:    # Polyline
            '''
            0:          Line Width (0=smallest, 1=small, 2=medium, 3=large)
            1:          Line Style (0=solid, 1=dashed, 2=dotted)
            2...5:      Color (RGBA)
            6:          Selection (0/1)
            7...8:      N (number of points that follow)
            N times:
            0...1:      Xi
            2...3:      Yi
            '''
            gelem = {"type":"polyline"}
            polydef = infile.read(9)
            gelem["borderwidth"] = self.get_width(polydef[0])
            gelem["style"] = polydef[1]
            gelem["border_color"] = polydef[2:6]
            npoints = struct.unpack('<h', polydef[7:9])[0]
            points = []
            for n in range(npoints):
                x = struct.unpack('<h', infile.read(2))[0] * 0.254
                y = struct.unpack('<h', infile.read(2))[0] * 0.254
                points.append([x,y])
            gelem["npoints"] = npoints
            gelem["points"] = points
            #print("Polyline", " ".join(f"{x:02X}" for x in polydef))

        elif prim_type == 7:    # Polygon (filled)
            '''
            0:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            1...4:      Border Color (RGBA)
            5...8:      Fill Color (RGBA)
            9:          Draw solid (0/1)
            10:         Selection (0/1)
            11...12:    N (number of points that follow)
            N times:
            0...1:      Xi
            2...3:      Yi
            '''
            gelem = {"type":"polygon"}
            polydef = infile.read(13)
            gelem["borderwidth"] = self.get_width(polydef[0])
            gelem["border_color"] = polydef[1:5]
            gelem["fill_color"] = polydef[5:9]
            gelem["drawsolid"] = polydef[9]
            npoints = struct.unpack('<h', polydef[11:13])[0]
            points = []
            for n in range(npoints):
                x = struct.unpack('<h', infile.read(2))[0] * 0.254
                y = struct.unpack('<h', infile.read(2))[0] * 0.254
                points.append([x,y])
            gelem["npoints"] = npoints
            gelem["points"] = points
            #print("Polygon", " ".join(f"{x:02X}" for x in polydef))

        elif prim_type == 8:    # Ellipse
            '''
            0...1:      X
            2...3:      Y
            4...5:      Radius X
            6...7:      Radius Y
            8:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Border Color (RGBA)
            13...16:    Fill Color (RGBA)
            17:         Draw solid (0/1)
            18:         Selection (0/1)
            '''
            edef = infile.read(19)
            gelem = {"type":"ellipse"}
            gelem["x"] = struct.unpack('<h', edef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', edef[2:4])[0] * 0.254
            gelem["rx"] = struct.unpack('<h', edef[4:6])[0] * 0.254
            gelem["ry"] = struct.unpack('<h', edef[6:8])[0] * 0.254
            gelem["borderwidth"] = self.get_width(edef[8])
            gelem["border_color"] = edef[9:13]
            gelem["fill_color"] = edef[13:17]
            gelem["drawsolid"] = edef[17]

        elif prim_type == 9:    # Pie Chart
            '''
            0...1:      X
            2...3:      Y
            4...5:      Radius
            6:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            7...12:     Start Angle (float6)
            13...18:    End Angle (float6)
            19...22:    Border Color (RGBA)
            23...26:    Fill Color (RGBA)
            27:         Draw solid (0/1)
            28:         Selection (0/1)
            '''
            piedef = infile.read(29)
            gelem = {"type":"pie"}
            gelem["x"] = struct.unpack('<h', piedef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', piedef[2:4])[0] * 0.254
            gelem["radius"] = struct.unpack('<h', piedef[4:6])[0] * 0.254
            gelem["borderwidth"] = self.get_width(piedef[6])
            gelem["sa"] = self.read_float(piedef[9:15])
            gelem["ea"] = self.read_float(piedef[15:21])
            gelem["border_color"] = piedef[19:23]
            gelem["fill_color"] = piedef[23:27]
            gelem["drawsolid"] = piedef[27]

        elif prim_type == 10:   # Rounded Rectangle
            '''
            0...1:      X1
            2...3:      Y1
            4...5:      X2
            6...7:      Y2
            8...9:      X-Radius
            10...11:    Y-Radius
            12:         Border width (0=smallest, 1=small, 2=medium, 3=large)
            13...16:    Border Color (RGBA)
            17...20:    Fill Color (RGBA)
            21:         Selection (0/1)
            22:         Draw solid (0/1)
            '''
            rrectdef = infile.read(23)
            gelem = {"type":"rounded_rectangle"}
            gelem["x1"] = struct.unpack('<h', rrectdef[0:2])[0] * 0.254
            gelem["y1"] = struct.unpack('<h', rrectdef[2:4])[0] * 0.254
            gelem["x2"] = struct.unpack('<h', rrectdef[4:6])[0] * 0.254
            gelem["y2"] = struct.unpack('<h', rrectdef[6:8])[0] * 0.254
            gelem["rx"] = struct.unpack('<h', rrectdef[8:10])[0] * 0.254
            gelem["ry"] = struct.unpack('<h', rrectdef[10:12])[0] * 0.254
            gelem["borderwidth"] = self.get_width(rrectdef[12])
            gelem["border_color"] = rrectdef[13:17]
            gelem["fill_color"] = rrectdef[17:21]
            gelem["selection"] = rrectdef[21]
            gelem["drawsolid"] = rrectdef[22]
            #print("RRect", " ".join(f"{x:02X}" for x in rrectdef))

        elif prim_type == 11:   # EllipticalArc
            '''
            0...1:      X
            2...3:      Y
            4...5:      Radius X
            6...7:      Radius Y
            8:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            9...14:     Start angle (float6)
            15...20:    End angle (float6)
            21...24:    Color (RGBA)
            25:         Selection (0/1)
            '''
            earcdef = infile.read(26)
            gelem = {"type":"arc"}
            gelem["x"] = struct.unpack('<h', earcdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', earcdef[2:4])[0] * 0.254
            gelem["rx"] = struct.unpack('<h', earcdef[4:6])[0] * 0.254
            gelem["ry"] = struct.unpack('<h', earcdef[6:8])[0] * 0.254
            gelem["borderwidth"] = self.get_width(earcdef[8])
            gelem["sa"] = self.read_float(earcdef[9:15])
            gelem["ea"] = self.read_float(earcdef[15:21])
            gelem["color"] = earcdef[21:25]
            #print("EArc", " ".join(f"{x:02X}" for x in earcdef))

        elif prim_type == 12:   # Arc
            '''
            0...1:      X
            2...3:      Y
            4...5:      Radius
            6:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            7...12:     Start angle (float6)
            13...18:    End angle (float6)
            19...22:    Color (RGBA)
            23:         Selection (0/1)
            '''
            arcdef = infile.read(24)
            gelem = {"type":"arc"}
            gelem["x"] = struct.unpack('<h', arcdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', arcdef[2:4])[0] * 0.254
            gelem["rx"] = struct.unpack('<h', arcdef[4:6])[0] * 0.254
            gelem["ry"] = gelem["rx"]
            gelem["borderwidth"] = self.get_width(arcdef[6])
            gelem["sa"] = self.read_float(arcdef[7:13])
            gelem["ea"] = self.read_float(arcdef[13:19])
            gelem["color"] = arcdef[19:23]
            #print("Arc", " ".join(f"{x:02X}" for x in earcdef))

        elif prim_type == 13:   # Line
            '''
            0...1:      X1
            2...3:      Y1
            4...5:      X2
            6...7:      Y2
            8:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            9:          Style (0=solid, 1=dashed, 2=dotted)
            10...13:    Color (RGBA)
            14:         Selection (0/1)
            '''
            linedef = infile.read(15)
            gelem = {"type":"line"}
            gelem["x1"] = struct.unpack('<h', linedef[0:2])[0] * 0.254
            gelem["y1"] = struct.unpack('<h', linedef[2:4])[0] * 0.254
            gelem["x2"] = struct.unpack('<h', linedef[4:6])[0] * 0.254
            gelem["y2"] = struct.unpack('<h', linedef[6:8])[0] * 0.254
            gelem["linewidth"] = self.get_width(linedef[8])
            gelem["style"] = linedef[9]
            gelem["color"] = linedef[10:14]
            #print("Line", " ".join(f"{x:02X}" for x in linedef))

        elif prim_type == 14:   # Rectangle
            '''
            0...1:      X1
            2...3:      Y1
            4...5:      X2
            6...7:      Y2
            8:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Border Color (RGBA)
            13...16:    Fill Color (RGBA)
            17:         Selection (0/1)
            18:         Draw Solid (0/1)
            '''
            gelem = {"type":"rectangle"}
            rdef = infile.read(19)
            gelem["x1"] = struct.unpack('<h', rdef[0:2])[0] * 0.254
            gelem["y1"] = struct.unpack('<h', rdef[2:4])[0] * 0.254
            gelem["x2"] = struct.unpack('<h', rdef[4:6])[0] * 0.254
            gelem["y2"] = struct.unpack('<h', rdef[6:8])[0] * 0.254
            gelem["borderwidth"] = self.get_width(rdef[8])
            gelem["border_color"] =  rdef[9:13]
            gelem["fill_color"] =  rdef[13:17]
            gelem["selection"] = rdef[17]
            gelem["drawsolid"] = rdef[18]

        elif prim_type == 15:   # Sheet Symbol
            '''
            0...1:      X
            2...3:      Y
            4...5:      X Size
            6...7:      Y Size
            8:          Border width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Border Color (RGBA)
            13...16:    Fill Color (RGBA)
            17:         Selection (0/1)
            18:         Draw Solid (0/1)
            '''
            gelem = {"type":"sheet_symbol"}
            shdef = infile.read(19)
            gelem["x"] = struct.unpack('<h', shdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', shdef[2:4])[0] * 0.254
            gelem["xsize"] = struct.unpack('<h', shdef[4:6])[0] * 0.254
            gelem["ysize"] = struct.unpack('<h', shdef[6:8])[0] * 0.254
            gelem["border_color"] = shdef[9:13]
            gelem["fill_color"] = shdef[13:17]
            #print("Sheet Symbol", " ".join(f"{x:02X}" for x in shdef))
            children = []
            while True:
                child = self.read_bin(infile)
                if child is None:
                    break
                children.append(child)
            gelem["prims"] = children

        elif prim_type == 16:   # Sheet Net (Sheet Entry)
            '''
            0:          I/O Type (0=Unspecified, 1=Output, 2=Input, 3=Bidirectional)
            1:          Style (0=None, 1=Left, 2=Right, 3=Left&Right)
            2:          Side (0=Left, 1=Right, 2=Top, 3=Bottom)
            3...4:      Position
            5...8:      Border Color (RGBA)
            9...12:     Fill Color (RGBA)
            13...16:    Text Color (RGBA)
            17:         Selection (0/1)
            18...x:     Name (string8)
            '''
            shnetdef = infile.read(18)
            gelem = {"type":"sheet_net"}
            gelem["iotype"] = shnetdef[0]
            gelem["style"] = shnetdef[1]
            gelem["side"] = shnetdef[2]
            gelem["position"] = struct.unpack('<h', shnetdef[3:5])[0]
            gelem["border_color"] = shnetdef[5:9]
            gelem["fill_color"] = shnetdef[9:13]
            gelem["text_color"] = shnetdef[13:17]
            gelem["name"] = ps()
            #print("Sheet Net", " ".join(f"{x:02X}" for x in shnetdef), gelem["name"])

        elif prim_type == 17:   # PowerPort
            '''
            0:          Style (0=Circle, 1=Arrow, 2=Bar, 3=Wave,
                               4=PowerGround, 5=SignalGround, 6=Earth)
            1...2:      X
            3...4:      Y
            5:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            6...9:      Color (RGBA)
            10:         Selection (0/1)
            9...x:      Name (string8)
            '''
            pwrdef = infile.read(11)
            gelem = {"type":"powerobject"}
            gelem["symbol"] = pwrdef[0]
            gelem["x"] = struct.unpack('<h', pwrdef[1:3])[0] * 0.254
            gelem["y"] = struct.unpack('<h', pwrdef[3:5])[0] * 0.254
            gelem["rotation"] = self.get_rotation(pwrdef[5])
            gelem["color"] = pwrdef[6:10]
            gelem["name"] = ps()
            #print("Power Port", " ".join(f"{x:02X}" for x in pwrdef), gelem["name"])

        elif prim_type == 18:   # Port
            '''
            0:          Style (0=none (H), 1=left, 2=right, 3=left&right,
                               4=none (V), 5=top, 6=bottom, 7=top&bottom
            1:          I/O Type (0=unspecified, 1=output, 2=input, 3=bidirectional)
            2:          Alignment (0=center, 1=left, 2=right)
            3...4:      Length
            5...6:      X
            7...8:      Y
            9...12:     Border Color (RGBA)
            13...16:    Fill Color (RGBA)
            17...20:    Text Color (RGBA)
            21:         Selection (0/1)
            22...x:     Name (string8)
            '''
            portdef = infile.read(22)
            gelem = {"type":"port"}
            gelem["style"] = portdef[0]
            gelem["iotype"] = portdef[1]
            gelem["alignment"] = portdef[2]
            gelem["length"] = struct.unpack('<h', portdef[3:5])[0] * 0.254
            gelem["x"] = struct.unpack('<h', portdef[5:7])[0] * 0.254
            gelem["y"] = struct.unpack('<h', portdef[7:9])[0] * 0.254
            gelem["border_color"] = portdef[9:13]
            gelem["fill_color"] = portdef[13:17]
            gelem["text_color"] = portdef[17:21]
            gelem["name"] = ps()
            #print("Port", " ".join(f"{x:02X}" for x in portdef), gelem["name"])

        elif prim_type == 19:   # Probe Directive
            '''
            0...1:      X
            2...3:      Y
            4...7:      Color (RGBA)
            8:          Selection (0/1)
            9...x:      Name (string8)
            '''
            gelem = {"type":"probe"}
            probedef = infile.read(9)
            gelem["x"] = struct.unpack('<h', probedef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', probedef[2:4])[0] * 0.254
            gelem["color"] = probedef[4:8]
            gelem["name"] = ps()

        elif prim_type == 20:   # Test Vector Directive
            '''
            0...1:      X
            2...3:      Y
            4...7:      Color (RGBA)
            8:          Selection (0/1)
            9...x:      Name (string8)
            '''
            gelem = {"type":"test_vector_index"}
            tvdef = infile.read(9)
            gelem["x"] = struct.unpack('<h', tvdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', tvdef[2:4])[0] * 0.254
            gelem["color"] = tvdef[4:8]
            gelem["name"] = ps()

        elif prim_type == 21:   # Stimulus Directive
            '''
            0...1:      X
            2...3:      Y
            4...7:      Color (RGBA)
            8:          Selection (0/1)
            9...x:      Name (string8)
            '''
            gelem = {"type":"stimulus"}
            tvdef = infile.read(9)
            gelem["x"] = struct.unpack('<h', tvdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', tvdef[2:4])[0] * 0.254
            gelem["color"] = tvdef[4:8]
            gelem["name"] = ps()

        elif prim_type == 22:   # NoERC
            '''
            0...1:      X
            2...3:      Y
            4...7:      Color (RGBA)
            8:          Selection (0/1)
            '''
            noercdef = infile.read(9)
            gelem = {"type":"noerc"}
            gelem["x"] = struct.unpack('<h', noercdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', noercdef[2:4])[0] * 0.254
            gelem["color"] = noercdef[4:8]
            #print("NoERC", " ".join(f"{x:02X}" for x in noercdef))

        elif prim_type == 23:   # ErrorMarker
            gelem = {"type":"errormarker"}
            gelem["x"] = struct.unpack('<h', infile.read(2))[0] * 0.254
            gelem["y"] = struct.unpack('<h', infile.read(2))[0] * 0.254
            infile.read(1)
            infile.read(4)

        elif prim_type == 24:   # PCB Layout Directive
            '''
            0...1:      Track Width
            2...3:      Via Width
            4:          ?
            5:          ?
            6:          ?
            7...8:      X
            9...10:     Y
            11...14:    Color (RGBA)
            15:         Selection (0/1)
            '''
            gelem = {"type":"pcb_layout"}
            pcbdef = infile.read(16)
            gelem["track_width"] = struct.unpack('<h', pcbdef[0:2])[0] * 0.254
            gelem["via_width"] = struct.unpack('<h', pcbdef[2:4])[0] * 0.254
            gelem["x"] = struct.unpack('<h', pcbdef[7:9])[0] * 0.254
            gelem["y"] = struct.unpack('<h', pcbdef[9:11])[0] * 0.254
            gelem["color"] = pcbdef[11:15]

        elif prim_type == 25:   # Net Label
            '''
            0...1:      X
            2...3:      Y
            4:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            5...8:      Color (RGBA)
            9...10:     Font
            11:         Selection (0/1)
            '''
            netldef = infile.read(12)
            gelem = {"type":"net_label"}
            gelem["x"] = struct.unpack('<h', netldef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', netldef[2:4])[0] * 0.254
            gelem["rotation"] = self.get_rotation(netldef[4])
            gelem["color"] = netldef[5:9]
            gelem["font"] = struct.unpack('<h', netldef[9:11])[0]
            gelem["name"] = ps()
            #print("Net Label", " ".join(f"{x:02X}" for x in netldef), gelem["name"])

        elif prim_type == 26:   # Bus
            '''
            0:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            1...4:      Color (RGBA)
            5:          Selection (0/1)
            6...7:      N (number of points that follow)
            N times:
            0...1:      Xi
            2...3:      Yi
            '''
            busdef = infile.read(8)
            gelem = {"type":"bus"}
            gelem["width"] = busdef[0]
            gelem["color"] = busdef[1:5]
            npoints = struct.unpack('<h', busdef[6:8])[0]
            points = []
            for n in range(npoints):
                x = struct.unpack('<h', infile.read(2))[0] * 0.254
                y = struct.unpack('<h', infile.read(2))[0] * 0.254
                points.append([x,y])
            gelem["npoints"] = npoints
            gelem["points"] = points
            #print("Bus", " ".join(f"{x:02X}" for x in busdef))

        elif prim_type == 27:   # Wire
            '''
            0:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            1...4:      Color (RGBA)
            5:          Selection (0/1)
            6...7:      N (number of points that follow)
            N times:
            0...1:      Xi
            2...3:      Yi
            '''
            wdef = infile.read(8)
            gelem = {"type":"wire"}
            gelem["width"] = wdef[0]
            gelem["color"] = wdef[1:5]
            npoints = struct.unpack('<h', wdef[6:8])[0]
            points = []
            for n in range(npoints):
                x = struct.unpack('<h', infile.read(2))[0] * 0.254
                y = struct.unpack('<h', infile.read(2))[0] * 0.254
                points.append([x,y])
            gelem["npoints"] = npoints
            gelem["points"] = points

        elif prim_type == 28:   # Text Frame
            '''
            0...1:      X1 (bottom left)
            2...3:      Y1 (bottom left)
            4...5:      X2 (top right)
            6...7:      Y2 (top right)
            8:          Border Width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Border Color (RGBA)
            13...16:    Fill Color (RGBA)
            17...20:    Text Color (RGBA)
            21...22:    Index in font table (starts with 1)
            23:         DrawSolid (0/1)
            24:         ShowBorder (0/1)
            25:         Alignment (0=center, 1=left, 2=right)
            26:         WordWrap (0/1)
            27:         ClipToArea (0/1)
            28:         Selection (0/1)
            29...x:     Text (string16)
            ?           0x00 (string termination?)
            '''
            gelem = {"type":"text_frame"}
            framedef = infile.read(29)
            gelem["x1"] = struct.unpack('<h', framedef[0:2])[0] * 0.254
            gelem["y1"] = struct.unpack('<h', framedef[2:4])[0] * 0.254
            gelem["x2"] = struct.unpack('<h', framedef[4:6])[0] * 0.254
            gelem["y2"] = struct.unpack('<h', framedef[6:8])[0] * 0.254
            gelem["border_width"] = framedef[8]
            gelem["border_color"] = framedef[9:13]
            gelem["fill_color"] = framedef[13:17]
            gelem["text_color"] = framedef[17:21]
            gelem["font"] = struct.unpack('<H', framedef[21:23])[0]
            gelem["text"] = ps16()
            infile.read(1)

        elif prim_type == 29:   # Junction
            '''
            0...1:      X
            2...3:      Y
            4:          Size (0=smallest, 1=small, 2=medium, 3=large)
            5...8:      Color (RGBA)
            9:          Selection (0/1)
            '''
            gelem = {"type":"junction"}
            juncdef = infile.read(10)
            gelem["x"] = struct.unpack('<h', juncdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', juncdef[2:4])[0] * 0.254
            gelem["size"] = juncdef[4]
            gelem["color"] = juncdef[5:9]
            #print("Junction", " ".join(f"{x:02X}" for x in juncdef))

        elif prim_type == 30:   # Image
            '''
            0...1:      X1
            2...3:      Y1
            4...5:      X2
            6...7:      Y2
            8:          Border Width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Border Color (RGBA)
            13:         Selection (0/1)
            14:         Border On (0/1)
            15:         XY Ratio 1:1 (0/1)
            16...?:     Name (string8)
            '''
            gelem = {"type":"image"}
            imdef = infile.read(16)
            gelem["x1"] = struct.unpack('<h', imdef[0:2])[0] * 0.254
            gelem["y1"] = struct.unpack('<h', imdef[2:4])[0] * 0.254
            gelem["x2"] = struct.unpack('<h', imdef[4:6])[0] * 0.254
            gelem["y2"] = struct.unpack('<h', imdef[6:8])[0] * 0.254
            gelem["border_width"] = imdef[8]
            gelem["border_color"] = imdef[9:13]
            gelem["show_border"] = imdef[14]
            gelem["keep_ratio"] = imdef[15]
            gelem["name"] = ps()
            # Store the path to the bin file from which we are reading
            gelem["path"] = os.path.dirname(infile.name)
            #print("Image", " ".join(f"{x:02X}" for x in imdef))

        elif prim_type == 32:   # Sheet Name
            gelem = {"type":"sheet_name"}
            gelem["x"] = struct.unpack('<h', infile.read(2))[0] * 0.254
            gelem["y"] = struct.unpack('<h', infile.read(2))[0] * 0.254
            infile.read(9)
            gelem["name"] = ps()

        elif prim_type == 33:   # Sheet File Name
            gelem = {"type":"sheet_file_name"}
            gelem["x"] = struct.unpack('<h', infile.read(2))[0] * 0.254
            gelem["y"] = struct.unpack('<h', infile.read(2))[0] * 0.254
            infile.read(9)
            gelem["name"] = ps()

        elif prim_type == 34:   # Part Designator
            '''
            0...1:      X
            2...3:      Y
            4:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            5...8:      Color (RGBA)
            9...10:     Font
            11:         Selection (0/1)
            12:         Hide (0/1)
            '''
            pddef = infile.read(13)
            gelem = {"type":"part_designator"}
            gelem["x"] = struct.unpack('<h', pddef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', pddef[2:4])[0] * 0.254
            gelem["rotation"] = self.get_rotation(pddef[4])
            gelem["color"] = pddef[5:9]
            gelem["font"] = struct.unpack('<h', pddef[9:11])[0]
            gelem["name"] = ps()
            #print("Part Designator", " ".join(f"{x:02X}" for x in pddef), gelem["name"])

        elif prim_type == 35:   # Part Type
            '''
            0...1:      X
            2...3:      Y
            4:          Rotation (0=0°, 1=90°, 2=180°, 3=270°)
            5...8:      Color (RGBA)
            9...10:     Font
            11:         Selection (0/1)
            12:         Hide (0/1)
            '''
            ptdef = infile.read(13)
            gelem = {"type":"part_type"}
            gelem["x"] = struct.unpack('<h', ptdef[0:2])[0] * 0.254
            gelem["y"] = struct.unpack('<h', ptdef[2:4])[0] * 0.254
            gelem["rotation"] = self.get_rotation(ptdef[4])
            gelem["color"] = ptdef[5:9]
            gelem["font"] = struct.unpack('<h', ptdef[9:11])[0]
            gelem["name"] = ps()
            #print("Part Type", " ".join(f"{x:02X}" for x in ptdef), gelem["name"])

        elif prim_type == 36:   # Text field(s)
            '''
            0...12:     ?
            13...x:     Text (string8)
            '''
            tfdef = infile.read(13)
            gelem = {"type":"text_field"}
            gelem["text"] = ps()
            #print("Text field", " ".join(f"{x:02X}" for x in tfdef), gelem["text"])

        elif prim_type == 37:   # Bus Entry
            '''
            0...1:      X1
            2...3:      Y1
            4...5:      X1
            6...7:      Y1
            8:          Line width (0=smallest, 1=small, 2=medium, 3=large)
            9...12:     Color (RGBA)
            13:         Selection (0/1)
            '''
            bedef = infile.read(14)
            gelem = {"type":"bus_entry"}
            gelem["x1"] = struct.unpack('<h', bedef[0:2])[0] * 0.254
            gelem["y1"] = struct.unpack('<h', bedef[2:4])[0] * 0.254
            gelem["x2"] = struct.unpack('<h', bedef[4:6])[0] * 0.254
            gelem["y2"] = struct.unpack('<h', bedef[6:8])[0] * 0.254
            gelem["width"] = bedef[8]
            gelem["color"] = bedef[9:13]
            #print("Bus Entry", " ".join(f"{x:02X}" for x in bedef))

        elif prim_type == 38:   # Sheet Part Filename
            infile.read(13)
            ps()

        elif prim_type == 39:   # Template
            gelem = {"type":"template"}
            ps()    # File name
            children = []
            while True:
                child = self.read_bin(infile)
                if child is None:
                    break
                children.append(child)
            gelem["prims"] = children

        elif prim_type == 255:  # End of list
            #print("end of list")
            pass

        else:
            raise RuntimeError(f"Unknown graphical primitive #{prim_type} @0x{infile.tell()-1:X}")
    
        #print(gelem)
        return gelem

