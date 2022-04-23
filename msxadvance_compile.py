#!/usr/bin/python3

import sys, os.path, struct, argparse, bz2, base64
from sys import argv

EMUID = int(0x1A4C4F43) # "COL",0x1A - probably unintentional since Formats.txt incorrectly states it should be "MSX",0x1A
SRAM_SAVE = 65536

default_outputfile = "msxadv-compilation.gba"
default_emubinary = "msxadva.gba"
default_bios = "bios.bin" # recommended to use 'MSX System v1.0 + MSX BASIC (1983)(Microsoft)[MSX.ROM]'
header_struct_format = "<8I31sc" # https://docs.python.org/3/library/struct.html

# ROM header
#
# from gba.h in the MSXAdvance source code and Formats.txt in the binary distribution, and testing with the Win32 builder
#
#typedef struct {
#	u32 identifier;
#	u32 filesize;
#	u32 flags;
#		Bit 0: 0=NTSC, 1=PAL (1 in decimal)
#		Bit 4: reserved for CPU speedhacks
#		Bit 5: 0=spritefollow, 1=addressfollow (32 in decimal)
#	u32 spritefollow;
#	u32 0=Game ROM, 1=MSX1 BIOS ROM;
#	u32 reserved[3];
#	char name[32] null terminated;
#} romheader;

#def readfile(name):
#	with open(name, "rb") as fh:
#		contents = fh.read()
#	return contents

def writefile(name, contents):
	with open(name, "wb") as fh:
		fh.write(contents)
		if name == default_outputfile:
			print("...wrote", name)	

#def get_bit(value, n):
#    return ((value >> n & 1) != 0)

def set_bit(value, n):
    return value | (1 << n)

#def clear_bit(value, n):
#    return value & ~(1 << n)


if __name__ == "__main__":

	if os.path.dirname(argv[0]) and os.path.dirname(argv[0]) != ".":
		localpath = os.path.dirname(argv[0]) + os.path.sep
	else:
		localpath = ""

	parser = argparse.ArgumentParser(
		description="This script will assemble the MSXAdvance emulator, a BIOS and MSX1 ROMs into a Gameboy Advance ROM image. It is recommended to type the script name, then drag and drop multiple ROM files onto the shell window, then add any additional arguments as needed.",
		epilog="coded by patters in 2022"
	)

	parser.add_argument(
		dest = 'romfile',
		help = ".rom image to add to compilation. Drag and drop multiple files onto your shell window.",
		type = argparse.FileType('rb'),
		nargs = '*' # it's possible to build a compilation with only a BIOS ROM
	)
	parser.add_argument(
		'-s',
		dest = 'splashscreen',
		help = "76800 byte raw 240x160 15bit splashscreen image",
		type = argparse.FileType('rb')
	)
	parser.add_argument(
		'-b',
		dest = 'bios',
		help = "mandatory BIOS rom image, defaults to " + default_bios,
		type = argparse.FileType('rb'),
		default = default_bios
	)
	parser.add_argument(
		'-bb',
		help = "allow boot to the BIOS only, via an '-- Empty --' romlist entry",
		action = 'store_true'
	)
	parser.add_argument(
		'-e', 
		dest = 'emubinary',
		help = "MSXAdvance binary, defaults to " + default_emubinary,
		type = argparse.FileType('rb'),
		default = default_emubinary
	)
	parser.add_argument(
		'-m',
		help = "mark small ROMs suitable for link transfer",
		action = 'store_true'
	)
	parser.add_argument(
		'-c',
		help = "clean brackets from ROM titles",
		action = 'store_true'
	)

	# don't use FileType('wb') here because it writes a zero-byte file even if it doesn't parse the arguments correctly
	parser.add_argument(
		'-o',
		dest = 'outputfile',
		help = "compilation output filename, defaults to " + default_outputfile,
		type = str,
		default = default_outputfile
	)
	parser.add_argument(
		'-sav',
		help = "for EZ-Flash IV firmware 1.x - create a blank 64KB .sav file for the compilation, store in the SAVER folder, not needed for firmware 2.x which creates its own blank saves",
		action = 'store_true'
	)
	parser.add_argument(
		'-pat',
		help = "for EZ-Flash IV firmware 2.x - create a .pat file for the compilation to force 64KB SRAM saves, store in the PATCH folder",
		action = 'store_true'
	)
	args = parser.parse_args()


	compilation = args.emubinary.read()

	if args.splashscreen:
		compilation = compilation + args.splashscreen.read()

	if args.bios:
		biosflag = 1
		flags = 0
		follow = 0 # sprite or address follow for 'Unscaled (Auto)' display mode
		bios = args.bios.read()
		bios = bios + b"\0" * (len(bios)%4)
		biosfilename = os.path.split(args.bios.name)[1]
		biosheader = struct.pack(header_struct_format, EMUID, len(bios), flags, follow, biosflag, 0, 0, 0, biosfilename[:31].encode('ascii'), b"\0")
		compilation = compilation + biosheader + bios

	for item in args.romfile:

		biosflag = 0
		flags = 0
		follow = 0 # sprite or address follow for Unscaled (Auto) display mode

		romfilename = os.path.split(item.name)[1]
		romtype = os.path.splitext(romfilename)[1]
		romtitle = os.path.splitext(romfilename)[0]

		if romtype.lower() == ".rom":

			if "(E)" in romtitle or "(Europe)" in romtitle or "(EUR)" in romtitle:
				flags = set_bit (flags, 0) # set PAL timing for EUR-only titles

		else:
			print("Error: unsupported filetype for compilation -", romfilename)
			sys.exit(1)

		if args.c:
			romtitle = romtitle.split(" [")[0] # strip the square bracket parts of the name
			romtitle = romtitle.split(" (")[0] # strip the bracket parts of the name

		if args.m:
			if os.path.getsize(item.name) <= 196608:
				romtitle = "* " + romtitle[:29]
			else:
				romtitle = "  " + romtitle[:29]
		else:
			romtitle = romtitle[:31]


		rom = item.read()
		rom = rom + b"\0" * (len(rom)%4)
		romheader = struct.pack(header_struct_format, EMUID, len(rom), flags, follow, biosflag, 0, 0, 0, romtitle.encode('ascii'), b"\0")
		compilation = compilation + romheader + rom

		print (romtitle)

	writefile(args.outputfile, compilation)

	if args.pat:
		# EZ-Flash IV fw2.x GSS patcher metadata to force 64KB SRAM saves - for PATCH folder on SD card
		patchname = os.path.splitext(args.outputfile)[0] + ".pat"
		patchdata = b'QlpoOTFBWSZTWRbvmZEAAAT44fyAgIAAEUAAAACIAAQAAAQESaAAVEIaaGRoxBKeqQD1GTJoks40324rSIskHSFhIywXzTCaqwSzf4exCBTgBk/i7kinChIC3fMyIA=='
		writefile(patchname, bz2.decompress(base64.b64decode(patchdata)))

	if args.sav:
		# EZ-Flash IV fw1.x blank save - for SAVER folder on SD card
		savename = os.path.splitext(args.outputfile)[0] + ".sav"
		saveempty = b"\xff" * SRAM_SAVE
		if not os.path.exists(savename): # careful not to overwrite an existing save
			writefile(savename, saveempty)
