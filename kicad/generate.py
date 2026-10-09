import uuid, re

LIBS = {'Amplifier_Operational':'/usr/share/kicad/symbols/Amplifier_Operational.kicad_sym',
        'Device':'/usr/share/kicad/symbols/Device.kicad_sym',
        'Connector_Generic':'/usr/share/kicad/symbols/Connector_Generic.kicad_sym',
        'power':'/usr/share/kicad/symbols/power.kicad_sym'}

def extract(lib, name):
    src = open(LIBS[lib]).read(); key = '(symbol "%s"' % name
    i = src.index(key); d = 0
    for j in range(i, len(src)):
        if src[j]=='(': d+=1
        elif src[j]==')':
            d-=1
            if d==0: return src[i:j+1]

def relib(b, lib, name): return b.replace('(symbol "%s"'%name, '(symbol "%s:%s"'%(lib,name), 1)
def U(): return str(uuid.uuid4())

lib_syms = "\n".join(relib(extract(l,n), l, n) for l,n in
                     [('Amplifier_Operational','LM741'), ('Device','R'), ('Device','C'),
                      ('power','+15V'), ('power','-15V'), ('power','GND'), ('power','PWR_FLAG'), ('Connector_Generic','Conn_01x04')])

out = []
def sym(lib_id, ref, val, x, y, rot=0, pins=()):
    pinblock = "\n".join(f'\t\t(pin "{n}" (uuid "{U()}"))' for n in pins)
    out.append(f'''	(symbol
		(lib_id "{lib_id}")
		(at {x} {y} {rot})
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{U()}")
{pinblock}
		(property "Reference" "{ref}"
			(at {x+3.2} {y-1.5} 0)
			(effects (font (size 1.27 1.27)) (justify left))
		)
		(property "Value" "{val}"
			(at {x+3.2} {y+1.5} 0)
			(effects (font (size 1.27 1.27)) (justify left))
		)
		(instances
			(project "kitticopter_controller"
				(path "/{SHEET}"
					(reference "{ref}") (unit 1)
				)
			)
		)
	)''')

def nc(x,y):
    out.append(f'''	(no_connect
		(at {x} {y})
		(uuid "{U()}")
	)''')

def wire(x1,y1,x2,y2):
    out.append(f'''	(wire
		(pts (xy {x1} {y1}) (xy {x2} {y2}))
		(stroke (width 0) (type solid))
		(uuid "{U()}")
	)''')

def label(name,x,y,rot=0,just="left"):
    out.append(f'''	(label "{name}"
		(at {x} {y} {rot})
		(effects (font (size 1.27 1.27)) (justify {just} bottom))
		(uuid "{U()}")
	)''')

SHEET = U()

# ---- resistors, vertical, pin1 top at y-3.81, pin2 bottom at y+3.81 ----
# (ref, value, top net, bottom net)
RES = [
 ('R1','10k','VREF','n2'),      ('R2','10k','n2','GND'),
 ('R3','10k','VFB','n1'),       ('R4','10k','n1','VE'),
 ('R5','100k','VE','n3'),       ('RV1','1k trim','n3','VG'),
 ('R7','4k7','+15V','n6'),      ('RV2','2k trim','n6','VBIAS'),
 ('R8','1k2','VBIAS','GND'),    ('R9','10k','VBIAS','n5'),
 ('R10','10k','n5','GND'),      ('R11','10k','VG','n4'),
 ('R12','10k','n4','VCMD'),
]
x0, y0, dx = 30.48, 38.10, 19.05
for i,(ref,val,top,bot) in enumerate(RES):
    col, row = i % 7, i // 7
    x = x0 + col*dx
    y = y0 + row*38.10
    sym('Device:R', ref, val, x, y, 0, ('1','2'))
    wire(x, y-3.81, x, y-8.89); label(top, x, y-8.89, 0, "left")
    wire(x, y+3.81, x, y+8.89); label(bot, x, y+8.89, 0, "left")

# ---- op-amps ----
OPA = [('U1','n1','n2','VE'), ('U2','n3','GND','VG'), ('U3','n4','n5','VCMD')]
oy = 127.0
for i,(ref,inv,noninv,outn) in enumerate(OPA):
    x = 45.72 + i*55.88
    sym('Amplifier_Operational:LM741', ref, 'UA741', x, oy, 0, ('1','2','3','4','5','6','7','8'))
    # pin 2 inverting at (x-7.62, y+2.54)
    wire(x-7.62, oy+2.54, x-17.78, oy+2.54); label(inv, x-17.78, oy+2.54, 0, "left")
    # pin 3 non-inverting at (x-7.62, y-2.54)
    wire(x-7.62, oy-2.54, x-17.78, oy-2.54); label(noninv, x-17.78, oy-2.54, 0, "left")
    # pin 6 output at (x+7.62, y)
    wire(x+7.62, oy, x+15.24, oy); label(outn, x+15.24, oy, 0, "left")
    nc(x, oy+7.62)        # pin 1, offset null, unused
    nc(x+2.54, oy+7.62)   # pin 5, offset null, unused
    # pin 7 V+ at (x-2.54, y-7.62)
    wire(x-2.54, oy-7.62, x-2.54, oy-15.24); label('+15V', x-2.54, oy-15.24, 90, "left")
    # pin 4 V- at (x-2.54, y+7.62)
    wire(x-2.54, oy+7.62, x-2.54, oy+15.24); label('-15V', x-2.54, oy+15.24, 270, "left")

# ---- decoupling caps ----
for i in range(3):
    x = 71.12 + i*55.88
    y = 165.10
    sym('Device:C', f'C{i+1}', '100n', x, y, 0, ('1','2'))
    wire(x, y-3.81, x, y-8.89)
    sym('power:+15V', f'#PWRC{i}', '+15V', x, y-8.89, 0, ('1',))
    wire(x, y+3.81, x, y+8.89)
    sym('power:GND', f'#PWRG{i}', 'GND', x, y+8.89, 0, ('1',))

# board interface to the DAQ and the setpoint divider
jx, jy = 220.98, 100.33
sym('Connector_Generic:Conn_01x04', 'J1', 'to DAQ', jx, jy, 0, ('1','2','3','4'))
for n,(pin,net) in enumerate([(1,'VREF'),(2,'VFB'),(3,'VCMD'),(4,'GND')]):
    py = jy - 2.54 + n*2.54
    wire(jx-5.08, py, jx-15.24, py)
    label(net, jx-15.24, py, 0, "left")

for i,(net,px) in enumerate([('+15V',198.12),('-15V',226.06),('GND',254.00)]):
    sym('power:PWR_FLAG', f'#FLG{i}', 'PWR_FLAG', px, 50.80, 0, ('1',))
    wire(px, 50.80, px, 57.15)
    lid = {'+15V':'power:+15V','-15V':'power:-15V','GND':'power:GND'}[net]
    sym(lid, f'#PWRF{i}', net, px, 57.15, 0 if net!='-15V' else 180, ('1',))

body = "\n".join(out)
sch = f'''(kicad_sch
	(version 20250114)
	(generator "eeschema")
	(generator_version "9.0")
	(uuid "{SHEET}")
	(paper "A3")
	(title_block
		(title "Kitticopter proportional controller, Kp = 0.005")
		(company "EEE3094S Lab 2")
	)
	(lib_symbols
{lib_syms}
	)
{body}
	(sheet_instances
		(path "/"
			(page "1")
		)
	)
)
'''
open('/home/tri/vault/school/eee3094s-control-systems-engineering/assignments/lab-2/kicad/controller.kicad_sch','w').write(sch)
print("written", len(sch), "chars")
