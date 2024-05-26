#!/usr/bin/python3

import json
import os



class KicadProject:
    def __init__ (self):
        self.sheets = []
        self.default = {"name": "Default"}
        self.rules = {}
        self.rule_log = ""

    def add_sheet (self, sheet):
        self.sheets.append(sheet)

    def to_mm (self, mils):
        if type(mils) == str:
            mils = mils.rstrip('\r\n')
            if mils.endswith("mil"):
                mils = mils[:-3]
            mils = float(mils)
        return mils * 0.0254

    def apply_protel_rules (self, prules):
        for prule in prules:
            if prule["RULEKIND"] == "Clearance":
                s1cnt = int(prule["SCOPE1COUNT"])
                s1kind = prule["SCOPE1_0_KIND"]
                s2cnt = int(prule["SCOPE2COUNT"])
                s2kind = prule["SCOPE2_0_KIND"]
                if (s1cnt == 1) and (s2cnt == 1):
                    if (s1kind == 'Board') and (s2kind == 'Board'):
                        self.rules["min_clearance"] = self.to_mm(prule["GAP"])
                        self.rule_log += f'  Minimum clearance = {self.rules["min_clearance"]}\n'
                        self.default["clearance"] = self.to_mm(prule["GAP"])
            if prule["RULEKIND"] == "RoutingVias":
                self.rules["min_through_hole_diameter"] = self.to_mm(prule["MINHOLEWIDTH"])
                self.rule_log += f'  Minimum through hole = {self.rules["min_through_hole_diameter"]}\n'
                self.default["via_diameter"] = self.to_mm(prule["MINWIDTH"])
                self.default["via_drill"] = self.to_mm(prule["MINHOLEWIDTH"])
            if prule["RULEKIND"] == "MinimumAnnularRing":
                w = prule.get("MINIMUMRING", None)
                if w is None:
                    w = prule.get("MINIMUM", None)
                if w is not None:
                    self.rules["min_via_annular_width"] = w
                    self.rule_log += f'  Minimum annular width = {self.rules["min_via_annular_width"]}\n'
            if prule["RULEKIND"] == "SolderMaskExpansion":
                self.rules["solder_mask_clearance"] = self.to_mm(prule["EXPANSION"])
                self.rule_log += f'  Solder mask expansion = {self.rules["solder_mask_clearance"]}\n'

    def get_board (self):
        brd = {}
        brd["3dviewports"] = []
        dset = {}
        dset["drc_exclusions"] = []
        dset["meta"] = {"version": 2}
        dset["rules"] = self.rules
        dset["track_widths"] = [0.0]
        dset["via_dimension"] = {"diameter": 0.0, "drill": 0.0}
        dset["zone_allow_externaL-fillets"] = False
        brd["design_settings"] = dset
        brd["layer_presets"] = []
        brd["viewports"] = []
        return brd

    def get_boards (self):
        return []

    def get_cvpcb (self):
        return {"equivalence_files": []}

    def get_libraries (self):
        libs = {}
        libs["pinned_footprint_libs"] = []
        libs["pinned_symbol_libs"] = []
        return libs

    def get_meta (self, kpro):
        meta = {"filename": os.path.basename(kpro.name)}
        meta["version"] = 1
        return meta

    def get_net_settings (self):
        net = {}
        net["classes"] = [self.default]
        net["meta"] = {"version": 3}
        return net

    def get_pcbnew (self):
        pcb = {}
        lpaths = {}
        lpaths["gencad"] = ""
        lpaths["idf"] = ""
        lpaths["netlist"] = ""
        lpaths["specctra_dsn"] = ""
        lpaths["step"] = ""
        lpaths["vrml"] = ""
        pcb["last_paths"] = lpaths
        pcb["page_layout_descr_file"] = ""
        return pcb

    def get_schematic (self):
        sch = {}
        dwg = {}
        dwg["label_size_ratio"] = 0.25
        dwg["pin_symbol_size"] = 0
        dwg["text_offset_ratio"] = 0.08
        sch["drawing"] = dwg
        sch["legacy_lib_dir"] = ""
        sch["legacy_lib_list"] = []
        return sch

    def get_sheets (self):
        return []

    def get_text_variables (self):
        return {}

    def to_kicad7 (self, kpro):
        # Write KiCAD project
        pro = {
            "board": self.get_board(),
            "boards": self.get_boards(),
            "cvpcb": self.get_cvpcb(),
            "libraries": self.get_libraries(),
            "meta": self.get_meta(kpro),
            "net_settings": self.get_net_settings(),
            "pcbnew": self.get_pcbnew(),
            "schematic": self.get_schematic(),
            "sheets": self.get_sheets(),
            "text_variables": self.get_text_variables()
            }
        kpro.write(json.dumps(pro, indent=2))
        print(f'Board rules:\n{self.rule_log}')

