#!/usr/bin/python3

import argparse
import base64
import json
from kicad_project import KicadProject
import os
from protel_pcb import Board
from protel_sch import Schematic, SchematicLibrary
import signal
import subprocess
import sys



# Handler to allow a graceful exit in case of Ctrl-C
def sigint_handler (signal, frame):
    print(" Good bye!")
    sys.exit(0)



def protel_read_string (f):
    s = ""

    length = f.read(1)[0]
    if length > 0:
        bytestring = f.read(length)
        s = bytestring.decode("iso8859_15")

    return s


def convert_pcb (project_name, ppcb, kpcb, kpcblib_path, kpro):
    # See if file starts with known header of binary PCB file
    s = protel_read_string(ppcb)
    ppcb.seek(0)

    if s == "PCB 3.0 Binary File":
        print("convert_pcb bin 3.0")
        pcb = Board.from_protel_bin(project_name, ppcb, version=3)
        pcb.to_kicad7(kpcb, kpcblib_path)
    elif s == "PCB 4.0 Binary File":
        print("convert_pcb bin 4.0")
        pcb = Board.from_protel_bin(project_name, ppcb)
        pcb.to_kicad7(kpcb, kpcblib_path)
    else:
        # May be an ASCII file
        print("convert_pcb ascii")
        pcb = Board.from_protel_ascii(project_name, ppcb)
        pcb.to_kicad7(kpcb, kpcblib_path)

    pro = KicadProject()
    pro.apply_protel_rules(pcb.rules)
    pro.to_kicad7(kpro)


def convert_sch (project_name, psch, ksch, klib, klibpower):
    # See if file starts with known header of binary SCH file
    header = protel_read_string(psch)
    if header == "Protel for Windows - Schematic Capture Binary File Version 1.2 - 2.0":
        print("convert_sch bin 1.2-2.0")
        sch = Schematic.from_protel_bin(project_name, psch)
        sch.to_kicad7(ksch, klib, klibpower)
    else:
        print("convert_sch ascii")
        print("  SCH ASCII NOT YET IMPLEMENTED!")
        #convert_sch_ascii(psch, ksch, klib)
        pass
    return


def convert_lib (filename, plib, kschlib_path, kpcblib_path):
    header = protel_read_string(plib)
    if header == "Protel for Windows - Schematic Library Editor Binary File Version 1.2 - 2.0":
        print("convert_lib bin 1.2-2.0")
        kschlib = open(kschlib_path, "w+")
        lib = SchematicLibrary.from_protel_bin(filename, plib)
        lib.to_kicad7(kschlib)
    elif header == "PCB 4.0 Binary Library File":
        print("convert_pcblib bin 4.0")
        print("  PCBLIB NOT YET IMPLEMENTED!")
        #kpcblib = open(kpcblib_path, "w+")
        #convert_pcblib_bin(filename, plib, kpcblib)
    else:
        print("unsupported format")
        pass
    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = 'Protel99SE to KiCAD7 Converter')
    parser.add_argument('protelfiles', nargs='*', help='Name of Protel99SE file(s) (sch, pcb, lib, ddb)')
    args = parser.parse_args()

    # Install Ctrl-C handler
    signal.signal(signal.SIGINT, sigint_handler)

    # Create output directory
    try:
        os.makedirs('kicad')
    except FileExistsError:
        pass

    # Inflate .DDB archives
    for name_infile in args.protelfiles:
        # Check file extension for supported files
        basename = os.path.basename(name_infile)
        filename, fileext = os.path.splitext(basename)

        if fileext.upper() == '.DDB':
            print("processing", name_infile)

            # Check database file and extract schematic/PCB/library
            # All database documents are listed as entries in the 'Items' table.
            db_dir = os.path.join('db', filename)
            try:
                os.makedirs(db_dir)
            except FileExistsError:
                pass
            result = subprocess.run(["mdb-json", name_infile, "Items"],
                                    stdout=subprocess.PIPE)
            # Put all JSON formatted table lines in a list
            docs = result.stdout.decode("utf-8").splitlines()

            # TODO: Extract all files in the database
            # Extract all sch/pcb/lib and add to the list.
            # Those files have their content stored as base64 encoded binary
            # data in "Data/$binary"
            for d in docs:
                j = json.loads(d)
                name, ext = os.path.splitext(j["Name"])
                # Design files
                if (ext.upper() == '.SCH') or (ext.upper() == '.PCB') or (ext.upper() == '.LIB') or (ext.upper() == '.PRJ'):
                    with open(os.path.join(db_dir, j["Name"]), "wb+") as f:
                        data = j.get("Data")
                        if data is not None:
                            f.write(base64.b64decode(j["Data"]["$binary"]))
                            args.protelfiles.append(os.path.join(db_dir, j["Name"]))
                # Image files
                if (ext.upper() == '.JPG') or (ext.upper() == '.PNG'):
                    with open(os.path.join(db_dir, j["Name"]), "wb+") as f:
                        data = j.get("Data")
                        if data is not None:
                            f.write(base64.b64decode(j["Data"]["$binary"]))

    # LIB/SCH files
    for name_infile in args.protelfiles:
        # Check file extension for supported files
        basename = os.path.basename(name_infile)
        filename, fileext = os.path.splitext(basename)

        if fileext.upper() == '.LIB':
            print("processing", name_infile)
            with open(name_infile, "rb") as plib:
                kschlib_path = os.path.join("kicad", filename + "_export.kicad_sym")
                kpcblib_path = os.path.join("kicad", filename + "_export_pcb.pretty")
                convert_lib(filename, plib, kschlib_path, kpcblib_path)

        if (fileext.upper() == '.SCH') or (fileext.upper() == '.PRJ'):
            print("processing", name_infile)
            with open(name_infile, "rb") as psch:
                ksch = open("kicad/" + filename + ".kicad_sch", "w+")
                klib = open("kicad/" + filename + "_export.kicad_sym", "w+")
                klibpower = open("kicad/" + filename + "_export_power.kicad_sym", "w+")
                convert_sch(filename, psch, ksch, klib, klibpower)

    # PCB files
    for name_infile in args.protelfiles:
        # Check file extension for supported files
        basename = os.path.basename(name_infile)
        filename, fileext = os.path.splitext(basename)

        if fileext.upper() == '.PCB':
            print("processing", name_infile)
            with open(name_infile, "rb") as ppcb:
                kpcb = open("kicad/" + filename + ".kicad_pcb", "w+")
                kpcblib_path = os.path.join("kicad", filename + "_export_pcb.pretty")
                kpro = open("kicad/" + filename + ".kicad_pro", "w+")
                convert_pcb(filename, ppcb, kpcb, kpcblib_path, kpro)
