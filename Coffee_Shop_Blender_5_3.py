"""Finished tutorial coffee shop. Run in Blender's Scripting workspace.

Axes: X across the storefront, Y into the shop, Z up. One unit per source stud.
Each rerun rebuilds this script's tagged shop in the active scene.
"""
from dataclasses import dataclass, field
from math import cos, pi, sin, sqrt
from pathlib import Path
from random import Random

TAG = "tutorial_coffee_shop_36"
SHOP = "Coffee Shop"
VIEWS = "Coffee Shop | Comparison"
# Optional. Set either to an absolute path, or use the console commands in chat.
SAVE_BLEND_TO = ""
EXPORT_GLB_TO = ""

# Material RGB values are sRGB. Fields: color, roughness, metallic, alpha, image.
MATERIALS = {
    "Earth green": ((39, 70, 45), .47, 0, 1, ""),
    "Awning green": ((32, 87, 54), .29, 0, 1, ""),
    "Awning white": ((239, 241, 239), .33, 0, 1, ""),
    "Pale brick": ((191, 177, 164), .9, 0, 1, "brick"),
    "Walnut planks": ((84, 62, 45), .68, 0, 1, "wood"),
    "Planter boards": ((83, 57, 42), .83, 0, 1, "planter"),
    "Roof aggregate": ((65, 79, 92), .91, 0, 1, "roof"),
    "Ceiling gray": ((166, 162, 163), .84, 0, 1, ""),
    "Window and door trim": ((208, 211, 216), .41, .19, 1, ""),
    "Painted white metal": ((228, 229, 225), .49, 0, 1, ""),
    "Pale blue glass": ((162, 205, 228), .22, 0, .24, ""),
    "Cabinet olive gray": ((136, 133, 111), .75, 0, 1, ""),
    "Charcoal": ((36, 43, 49), .43, .08, 1, ""),
    "Vent housing": ((138, 149, 164), .58, .15, 1, ""),
    "Fan grille": ((159, 169, 179), .46, .26, 1, ""),
    "Brushed metal": ((170, 180, 188), .34, .40, 1, ""),
    "Appliance white": ((235, 237, 235), .43, 0, 1, ""),
    "Display blue": ((46, 68, 83), .33, 0, 1, ""),
    "Register blue gray": ((143, 169, 192), .51, 0, 1, ""),
    "Strip diffuser": ((244, 248, 255), .5, 0, 1, ""),
    "Soil": ((54, 45, 38), .96, 0, 1, ""),
    "Mint leaf": ((183, 218, 185), .76, 0, 1, ""),
    "Mint leaf shade": ((149, 189, 154), .8, 0, 1, ""),
    "Table leaf": ((63, 110, 50), .76, 0, 1, ""),
    "Terracotta": ((195, 117, 43), .71, 0, 1, ""),
    "Petal red": ((170, 30, 42), .64, 0, 1, ""),
    "Petal yellow": ((238, 189, 54), .64, 0, 1, ""),
    "Syrup cream": ((203, 183, 162), .49, 0, 1, ""),
    "Syrup blue": ((163, 208, 221), .49, 0, 1, ""),
    "Syrup brown": ((157, 110, 72), .49, 0, 1, ""),
    "Print teal": ((37, 83, 79), .8, 0, 1, ""),
    "Print sky": ((141, 191, 181), .8, 0, 1, ""),
    "Print ochre": ((228, 174, 55), .8, 0, 1, ""),
    "Print orange": ((206, 115, 49), .8, 0, 1, ""),
    "Print peach": ((236, 172, 137), .8, 0, 1, ""),
    "Print moon": ((241, 226, 168), .8, 0, 1, ""),
}

GREEN = "Earth green"
WHITE = "Painted white metal"
TRIM = "Window and door trim"
GLASS = "Pale blue glass"
WOOD = "Walnut planks"
DARK = "Charcoal"
METAL = "Brushed metal"
APPLIANCE = "Appliance white"


def srgb(value):
    value /= 255
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def surface_pixels(kind, size=384):
    """Generate repeatable color maps in sRGB. No external texture files needed."""
    random = Random({"brick": 41, "wood": 82, "planter": 91, "roof": 99}[kind])
    bricks = [(209, 196, 182), (192, 174, 158), (218, 211, 198),
              (203, 180, 167), (184, 178, 168), (220, 200, 181)]
    boards = [(87, 66, 49), (79, 59, 44), (100, 75, 55),
              (76, 56, 41), (94, 70, 51), (108, 81, 59)]
    colors = bytearray()
    for y in range(size):
        v = y / size
        for x in range(size):
            u = x / size
            noise = random.uniform(-1, 1)
            if kind == "brick":
                row = int(v * 12)
                column = int(u * 6 + .5 * (row % 2))
                dx, dy = (u * 6 + .5 * (row % 2)) % 1, (v * 12) % 1
                edge = min(dx * 2, (1 - dx) * 2, dy, 1 - dy)
                cloud = 4 * sin(2*pi*(9*u + 7*v)) + 3 * sin(2*pi*(17*u - 8*v))
                base = bricks[(column % 6 * 17 + row * 13 + row // 3) % len(bricks)]
                if edge < .046:
                    base, detail = (157, 149, 134), cloud * .5 + noise * 7
                else:
                    detail = cloud + noise * 7 + (7 if edge < .08 else 0)
            elif kind in {"wood", "planter"}:
                count = 6 if kind == "wood" else 4
                row = int(v * count)
                offset = (row * .381966) % 1
                position = (u * 2 + offset) % 1
                across = (v * count) % 1
                plank = int(u * 2 + offset) % 2
                base = boards[(row * 7 + plank * 11) % len(boards)]
                if kind == "planter":
                    base = tuple(round(channel * .83) for channel in base)
                grain = sin(2*pi*(53*v + .5*sin(2*pi*(3*u + v))))
                detail = 4*grain + 4*sin(2*pi*(13*v + 2*u)) + noise*3
                if across < .019 or position < .008:
                    detail = -18 + noise*3
                elif across < .044:
                    detail += 10
            else:
                base, detail = (65, 79, 92), noise * 14 + 3*sin(2*pi*(11*u - 13*v))
            colors.extend(max(0, min(255, round(channel + detail))) for channel in base)
    return size, colors


def uv_project(point, mode, period):
    x, y, z = point
    if mode == "floor":
        return y / period[0], x / period[1]
    if mode == "xz":
        return x / period[0], z / period[1]
    if mode == "yz":
        return y / period[0], z / period[1]
    return x / period[0], y / period[1]


@dataclass
class Mesh:
    vertices: list = field(default_factory=list)
    faces: list = field(default_factory=list)
    materials: list = field(default_factory=list)
    uv: list = field(default_factory=list)
    smooth: list = field(default_factory=list)

    def add(self, vertices, faces, material, uvs=None, smooth=False):
        start = len(self.vertices)
        self.vertices.extend(vertices)
        for index, face in enumerate(faces):
            self.faces.append(tuple(start + k for k in face))
            self.materials.append(material if isinstance(material, str) else material[index])
            self.uv.append(uvs[index] if uvs is not None else [(0, 0)] * len(face))
            self.smooth.append(smooth if isinstance(smooth, bool) else smooth[index])
        return self

    def box(self, center, size, material, period=(8, 4), floor=False):
        x, y, z = center
        a, b, c = [d / 2 for d in size]
        vertices = [(x-a,y-b,z-c), (x+a,y-b,z-c), (x+a,y+b,z-c), (x-a,y+b,z-c),
                    (x-a,y-b,z+c), (x+a,y-b,z+c), (x+a,y+b,z+c), (x-a,y+b,z+c)]
        faces = [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
        modes = ("xy", "floor" if floor else "xy", "xz", "yz", "xz", "yz")
        uvs = [[uv_project(vertices[i], mode, period) for i in face]
               for face, mode in zip(faces, modes)]
        return self.add(vertices, faces, material, uvs)

    def rod(self, a, b, radius, material, sides=10, tip=None):
        direction = tuple(q-p for p,q in zip(a,b))
        axis = unit(direction)
        u = unit(cross(axis, (0,1,0) if abs(axis[1]) < .9 else (1,0,0)))
        v = cross(axis, u)
        vertices = []
        for center, r in ((a,radius), (b,radius if tip is None else tip)):
            for j in range(sides):
                angle = 2*pi*j/sides
                vertices.append(tuple(center[k]+r*(u[k]*cos(angle)+v[k]*sin(angle)) for k in range(3)))
        faces = [(j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides)]
        faces += [tuple(reversed(range(sides))),tuple(range(sides,2*sides))]
        return self.add(vertices, faces, material, smooth=[True]*sides+[False,False])

    def ring(self, center, outer, inner, height, material, sides=20):
        x,y,z = center
        vertices = [(x+r*cos(2*pi*j/sides), y+r*sin(2*pi*j/sides), z+dz)
                    for r,dz in ((outer,-height/2),(outer,height/2),
                                 (inner,height/2),(inner,-height/2))
                    for j in range(sides)]
        faces = []
        for k in range(4):
            a,b = k*sides, ((k+1)%4)*sides
            for j in range(sides):
                q=(j+1)%sides
                faces.append((a+j,a+q,b+q,b+j))
        return self.add(vertices,faces,material)


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(v):
    length = sqrt(sum(x*x for x in v))
    return tuple(x/length for x in v)


@dataclass
class Part:
    group: str
    name: str
    mesh: Mesh
    position: tuple = (0,0,0)
    angle: float = 0


def opening_frame(mesh, width, bottom, top, rail, bars=(), y=0, depth=.50):
    """Make rails and stiles meet edge to edge in the opening."""
    mesh.box((0,y,bottom+rail/2),(width,depth,rail),TRIM)
    mesh.box((0,y,top-rail/2),(width,depth,rail),TRIM)
    span = top-bottom-2*rail
    for side in (-1,1):
        mesh.box((side*(width-rail)/2,y,(top+bottom)/2),(rail,depth,span),TRIM)
    for x in bars:
        mesh.box((x,y,(top+bottom)/2),(rail*.83,depth,span),TRIM)
    return mesh


def awning_mesh():
    # Loft a quarter-round canopy. Width tapers at each white end.
    profile = [(-13.9,.015),(-13.83,.37),(-13.59,.71),(-13.28,.90),(-12.91,1),
               (-8.0,1),(-3.25,1),(2.0,1),(6.9,1),(12.91,1),
               (13.28,.90),(13.59,.71),(13.83,.37),(13.9,.015)]
    subdivisions = 14
    vertices, faces, mats, smoothing = [],[],[],[]
    span = subdivisions + 2
    for x,scale in profile:
        vertices.extend((x,-20.025-1.37*scale*sin(pi*j/(2*subdivisions)),
                         8.22+1.41*scale*cos(pi*j/(2*subdivisions)))
                        for j in range(subdivisions+1))
        vertices.append((x,-20.025,8.22))
    for i in range(len(profile)-1):
        material = "Awning white" if i in {0,1,2,3,5,7,9,10,11,12} else "Awning green"
        for j in range(span):
            a,b=i*span,(i+1)*span
            k=(j+1)%span
            faces.append((a+k,b+k,b+j,a+j))
            mats.append(material)
            smoothing.append(j<subdivisions)
    faces.extend([tuple(reversed(range(span))), tuple(range((len(profile)-1)*span,len(profile)*span))])
    mats.extend(["Awning white"]*2)
    smoothing.extend([False]*2)
    return Mesh().add(vertices,faces,mats,smooth=smoothing)


def fan_assembly():
    mesh = Mesh().box((0,0,.57),(8.0,4.22,1.14),"Vent housing")
    for x in (-1.98,1.98):
        mesh.rod((x,0,1.14),(x,0,1.21),1.66,DARK,20)
        mesh.ring((x,0,1.26),1.73,1.56,.12,"Fan grille",24)
        mesh.rod((x,0,1.21),(x,0,1.34),.32,"Fan grille",12)
        for blade in range(9):
            a=blade*2*pi/9
            def point(r, offset):
                return (x+r*cos(a+offset),r*sin(a+offset),1.243)
            vertices=[point(.27,-.18),point(1.49,.04),point(1.48,.24),point(.56,.22)]
            mesh.add(vertices,[(0,1,2,3)],"Fan grille")
    # Dark inset louver strips on the front face of each unit.
    for j in range(4):
        mesh.box((0,-2.116,.24+j*.19),(7.30,.018,.045),DARK)
    return mesh


def rosette(seed, leaf_count, material, variation):
    mesh = Mesh()
    random = Random(seed)
    for i in range(leaf_count):
        angle = 2*pi*(i/leaf_count + random.uniform(-.026,.026))
        length = random.uniform(.90,1.61)
        rise = random.uniform(.35,.85)
        width = random.uniform(.12,.22)
        vertices = []
        for j in range(1,6):
            t=j/6
            r=length*t
            z=rise*sin(pi*t*.90) + .07
            w=width*sin(pi*t)**.7
            vertices.extend([(r*cos(angle)+side*w*sin(angle),r*sin(angle)-side*w*cos(angle),
                              z+(.05*sin(pi*t) if side == 0 else 0)) for side in (-1,0,1)])
        vertices.extend([(0,0,.025),(length*cos(angle),length*sin(angle),rise*sin(pi*.90)+.035)])
        faces=[(15,1,0),(15,2,1)]
        for j in range(4):
            for k in range(2):
                q=j*3+k
                faces.append((q,q+1,q+4,q+3))
        faces += [(12,13,16),(13,14,16)]
        mesh.add(vertices,faces,variation if i%3==0 else material,smooth=True)
    return mesh


def chair_mesh():
    mesh = Mesh()
    # Bent plywood silhouette swept across the seat width.
    profile=[(-.92,1.62),(.58,1.62),(.86,1.76),(.99,2.04),(1.04,3.33)]
    vertices=[(side*1.0,y,z+shift) for shift in (-.065,.065)
              for side in (-1,1) for y,z in profile]
    faces=[]
    for i in range(4):
        faces.extend([(i,i+1,i+6,i+5),(i+10,i+15,i+16,i+11),
                      (i,i+10,i+11,i+1),(i+5,i+6,i+16,i+15)])
    faces.extend([(0,5,15,10),(4,14,19,9)])
    uvs=[[((vertices[i][0]+1)/6,(vertices[i][1]+vertices[i][2])/4) for i in f] for f in faces]
    mesh.add(vertices,faces,WOOD,uvs)
    for x in (-1,1):
        for y in (-1,1):
            mesh.rod((x*.95,y*.94,.035),(x*.74,y*.61,1.60),.067,WHITE,8,tip=.085)
        mesh.rod((x*.80,-.71,1.16),(x*.83,.71,1.16),.057,WHITE,8)
    return mesh


def table_mesh(width, depth):
    mesh=Mesh().box((0,0,2.91),(width,depth,.21),WOOD,period=(6,3.8),floor=True)
    mesh.box((0,0,1.40),(.31,.31,2.72),WOOD)
    mesh.ring((0,0,.10),1.12,.99,.115,WHITE,22)
    mesh.box((0,0,.10),(2.08,.13,.115),WHITE)
    mesh.box((0,0,.10),(.13,2.08,.115),WHITE)
    return mesh


def tabletop_plant(flowering):
    mesh=Mesh().rod((0,0,0),(0,0,.33),.18,"Terracotta",12,tip=.24)
    mesh.ring((0,0,.31),.263,.211,.10,"Terracotta",14)
    mesh.rod((0,0,.325),(0,0,.34),.21,"Soil",14)
    for i in range(7):
        a=2*pi*i/7
        r=.23 if i%2 else .31
        mesh.add([(0,0,.34),(r*.65*cos(a+.30),r*.65*sin(a+.30),.54),
                  (r*cos(a),r*sin(a),.51),(r*.65*cos(a-.30),r*.65*sin(a-.30),.53)],
                 [(0,1,2,3)],"Table leaf")
    if flowering:
        for i in range(3):
            a=i*2.4
            x,y,z=.14*cos(a),.14*sin(a),.68+i*.055
            mesh.rod((0,0,.34),(x,y,z),.023,"Table leaf",6)
            color="Petal yellow" if i==1 else "Petal red"
            for petal in range(5):
                angle=petal*2*pi/5
                mesh.rod((x+.073*cos(angle),y+.073*sin(angle),z),
                         (x+.073*cos(angle),y+.073*sin(angle),z+.034),.061,color,6)
            mesh.rod((x,y,z),(x,y,z+.051),.047,"Petal yellow",7)
    return mesh


def register_mesh():
    mesh=Mesh()
    vertices=[(-.80,-.60,0),(.80,-.60,0),(.80,.60,0),(-.80,.60,0),
              (-.80,-.60,.54),(.80,-.60,.54),(.80,.60,.25),(-.80,.60,.25)]
    mesh.add(vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),
                       (2,3,7,6),(3,0,4,7)],
             [APPLIANCE,"Register blue gray",APPLIANCE,APPLIANCE,APPLIANCE,APPLIANCE])
    for i in range(5):
        for j in range(4):
            y=.12+j*.106
            mesh.box((-.46+i*.23,y,.395-y*.242+.019),(.16,.073,.029),APPLIANCE)
    return mesh


def coffee_machine(compact):
    width = 2.62 if compact else 3.40
    shell = APPLIANCE if compact else DARK
    mesh=Mesh().box((0,0,.12),(width,1.60,.24),shell)
    mesh.box((0,.31,.79),(width,.91,1.16),shell)
    mesh.box((0,-.10,1.31),(width,1.16,.37),METAL if compact else DARK)
    mesh.box((0,-.688,1.34),(width*.86,.026,.24),DARK if compact else "Display blue")
    mesh.box((0,-.25,.265),(width*.91,1.02,.050),METAL)
    for j in range(9):
        mesh.box((0,-.66+j*.099,.293),(width*.80,.024,.012),DARK)
    for x in (-.69,.69):
        mesh.rod((x,-.46,1.01),(x,-.46,1.14),.18,METAL,10)
        mesh.rod((x,-.46,1.04),(x+.10,-.76,1.04),.044,DARK,8)
    for x in (-.75,-.57,-.39,.39,.57,.75):
        mesh.rod((x,-.716,1.34),(x,-.738,1.34),.047,APPLIANCE,8)
    if compact:
        mesh.rod((0,-.714,1.36),(0,-.775,1.36),.127,APPLIANCE,12)
        mesh.rod((0,.19,1.50),(0,.19,1.78),.27,METAL,12,tip=.35)
        mesh.box((0,.19,1.81),(.74,.52,.066),APPLIANCE)
        mesh.rod((.97,-.42,1.15),(1.05,-.61,.59),.040,DARK,8)
    else:
        mesh.box((0,-.151,.771),(width-.44,.031,.987),METAL)
        mesh.box((0,-.722,1.34),(.43,.018,.13),METAL)
        for x in (-1.60,1.60):
            mesh.box((x,-.25,.77),(.20,.91,.97),METAL)
    return mesh


def pump_bottles():
    mesh=Mesh()
    for i,color in enumerate(("Syrup cream","Syrup brown","Syrup cream","Syrup blue","Syrup brown")):
        x=(i-2)*.46
        mesh.rod((x,0,0),(x,0,.66),.177,color,12)
        mesh.rod((x,0,.66),(x,0,.78),.168,color,12,tip=.108)
        mesh.rod((x,0,.78),(x,0,.98),.056,METAL,8)
        mesh.rod((x,.115,.987),(x,-.17,.987),.048,DARK,8)
    return mesh


def fridge_mesh():
    mesh=Mesh().box((0,.16,2.72),(3.21,2.50,5.44),APPLIANCE)
    for x in (-.805,.805):
        mesh.box((x,-1.185,3.40),(1.58,.18,3.92),APPLIANCE)
        side = -1 if x < 0 else 1
        mesh.rod((side*.15,-1.38,2.15),(side*.15,-1.38,4.72),.068,METAL,8)
    mesh.box((0,-1.18,.73),(3.16,.16,1.38),APPLIANCE)
    mesh.rod((-1.10,-1.37,1.12),(1.10,-1.37,1.12),.067,METAL,8)
    mesh.box((-.89,-1.289,3.63),(.56,.025,.91),METAL)
    mesh.box((-.89,-1.312,3.59),(.43,.019,.69),DARK)
    return mesh


def sink_counter():
    mesh=Mesh().box((-.50,0,1.38),(23.0,2.60,2.76),"Cabinet olive gray")
    # The slate counter has a real cutout for the recessed rectangular basin.
    for x,y,w,d in [(-1.55,0,21.10,2.76),(10.75,0,.35,2.76),
                    (9.76,-1.10,1.52,.56),(9.76,1.10,1.52,.56)]:
        mesh.box((x,y,2.83),(w,d,.14),DARK)
    mesh.box((9.76,0,2.80),(1.94,1.63,.10),METAL)
    mesh.box((9.76,0,2.857),(1.49,1.23,.012),"Vent housing")
    for x,y,w,d in [(8.89,0,.16,1.65),(10.63,0,.16,1.65),
                    (9.76,-.74,1.58,.15),(9.76,.74,1.58,.15)]:
        mesh.box((x,y,2.921),(w,d,.10),METAL)
    for a,b in [((9.76,.78,2.96),(9.76,.78,3.44)),
                ((9.76,.78,3.44),(9.76,.38,3.52)),
                ((9.76,.38,3.52),(9.76,.30,3.35))]:
        mesh.rod(a,b,.065,METAL,10)
    return mesh


def strip_light():
    mesh=Mesh().box((0,0,0),(6.45,.73,.19),"Vent housing")
    for y in (-.143,.143):
        mesh.box((0,y,-.126),(6.10,.236,.076),"Strip diffuser")
    return mesh


def wall_print(landscape):
    mesh=Mesh().box((0,0,0),(3.16,.12,2.42),DARK)
    mesh.box((0,-.082,0),(2.94,.062,2.20),WHITE)
    def patch(points, color, depth):
        vertices=[(x,depth,z) for x,z in points]
        mesh.add(vertices,[tuple(range(len(vertices)))],color)
    patch([(-1.34,-.97),(1.34,-.97),(1.34,.97),(-1.34,.97)],
          "Print teal" if landscape else "Print sky",-.117)
    if landscape:
        patch([(-1.34,-.97),(1.34,-.97),(1.34,-.05),(.90,.04),(.54,-.12),
               (.17,-.39),(-.22,-.37),(-.60,-.15),(-1.34,.11)],"Print peach",-.118)
        patch([(-1.34,-.97),(1.34,-.97),(1.34,-.39),(-1.34,-.48)],"Print orange",-.119)
        patch([(-1.34,-.97),(1.34,-.97),(1.34,-.58),(-1.34,-.64)],"Print ochre",-.120)
        mesh.rod((.04,-.119,.11),(.04,-.124,.11),.21,"Print moon",18)
    else:
        patch([(-1.34,-.97),(1.34,-.97),(1.34,-.49),(-1.34,-.34)],"Print ochre",-.118)
        patch([(-1.21,-.72),(-.13,-.72),(-.13,.42),(-1.21,.42)],"Print orange",-.119)
        patch([(-.12,-.72),(1.15,-.72),(1.15,.12),(-.12,.12)],"Print peach",-.119)
        for x,z,w in ((-.86,-.02,.39),(.58,-.18,.32),(-.21,-.49,.13)):
            patch([(x-w/2,z-.13),(x+w/2,z-.13),(x+w/2,z+.13),(x-w/2,z+.13)],DARK,-.120)
    return mesh


def clock_mesh():
    mesh=Mesh().rod((0,0,0),(0,-.10,0),1.40,DARK,40)
    for radius in (1.34,.83):
        for j in range(36):
            a,b=2*pi*j/36,2*pi*(j+1)/36
            mesh.rod((radius*sin(a),-.112,radius*cos(a)),
                     (radius*sin(b),-.112,radius*cos(b)),.021,WHITE,5)
    marks=("XII","I","II","III","IV","V","VI","VII","VIII","IX","X","XI")
    strokes={"I":[((0,-1),(0,1))],
             "V":[((-1,1),(0,-1)),((0,-1),(1,1))],
             "X":[((-1,-1),(1,1)),((1,-1),(-1,1))]}
    for index,mark in enumerate(marks):
        angle=2*pi*index/12
        for j,letter in enumerate(mark):
            def point(local):
                x,z=local
                across=(j-(len(mark)-1)/2)*.101+x*.043
                radial=1.08+z*.142
                return (radial*sin(angle)+across*cos(angle),-.120,
                        radial*cos(angle)-across*sin(angle))
            for a,b in strokes[letter]:
                mesh.rod(point(a),point(b),.0145,WHITE,5)
    mesh.rod((0,-.135,0),(-.18,-.135,.69),.040,WHITE,8,tip=.020)
    mesh.rod((0,-.135,0),(.22,-.135,.36),.053,WHITE,8,tip=.023)
    mesh.rod((0,-.105,0),(0,-.152,0),.081,WHITE,12)
    return mesh


def glass_quad(mesh, x1, x2, y, z1, z2):
    return mesh.add([(x1,y,z1),(x2,y,z1),(x2,y,z2),(x1,y,z2)],[(0,1,2,3)],GLASS)


def design():
    """Describe the shop in source studs, independently of Blender context."""
    parts = []

    def add(group,name,mesh,position=(0,0,0),angle=0):
        parts.append(Part(group,name,mesh,position,angle))

    shell="01 Shell"
    front="02 Storefront"
    roof="03 Roof and vents"
    outdoor="04 Planters"
    seating="05 Seating"
    service="06 Service counters"
    decor="07 Interior fixtures and art"
    add(shell,"Dark plank floor",Mesh().box((0,0,-.16),(30,40,.32),WOOD,(15,7.8),floor=True))
    for x,label in ((-14.75,"Left"),(14.75,"Right")):
        add(shell,label+" pale brick wall",
            Mesh().box((x,0,5),(.50,39,10),"Pale brick",(9.6,9.6)))
    add(shell,"Rear pale brick wall",
        Mesh().box((0,19.75,5),(30,.50,10),"Pale brick",(9.6,9.6)))

    facade=Mesh().box((0,0,9),(30,.50,2),GREEN)
    for x in (-14.5,-3,3,14.5):
        facade.box((x,0,4),(1,.50,8),GREEN)
    for x in (-8.75,8.75):
        facade.box((x,0,1.5),(10.5,.50,3),GREEN)
    add(shell,"Earth green facade with three openings",facade,(0,-19.75,0))

    window = opening_frame(Mesh(),10.5,3,8,.20,bars=(0,),depth=.55)
    window.box((0,-.29,2.984),(10.72,.48,.122),TRIM)
    glazing=glass_quad(Mesh(),-5.06,5.06,.043,3.19,7.81)
    for x,side in [(-8.75,"Left"),(8.75,"Right")]:
        add(front,side+" display window | frame and sill",window,(x,-19.75,0))
        add(front,side+" display window | glass",glazing,(x,-19.75,0))

    jamb=opening_frame(Mesh(),5,.0,8,.17,depth=.54)
    add(front,"Entrance fixed jamb",jamb,(0,-19.75,0))
    # The leaf origin is at its hinge edge for later editing.
    leaf=opening_frame(Mesh(),4.62,.19,7.81,.39,y=-.012,depth=.20)
    leaf.box((0,-.012,3.15),(3.84,.20,.46),TRIM)
    glass_quad(leaf,-1.921,1.921,.008,.58,2.92)
    glass_quad(leaf,-1.921,1.921,.008,3.38,7.421)
    for y in (-.162,.139):
        leaf.rod((1.995,y,2.89),(1.995,y,3.50),.049,DARK,8)
        for z in (2.95,3.45):
            leaf.rod((1.995,-.016,z),(1.995,y,z),.038,DARK,8)
    leaf.vertices=[(x+2.31,y,z) for x,y,z in leaf.vertices]
    add(front,"Glazed entry door | hinge origin",leaf,(-2.31,-19.75,0))
    add(front,"Curved striped awning",awning_mesh())

    slab=Mesh().box((0,0,10.25),(30.07,40.07,.50),"Roof aggregate",(4,4))
    slab.materials[0]="Ceiling gray"
    add(roof,"Flat roof slab and ceiling",slab)
    vent=fan_assembly()
    for i,y in enumerate((6.60,11.12,15.64),1):
        add(roof,f"Rooftop vent {i} | twin fans",vent,(-8.0,y,10.5))

    trough=Mesh().box((0,0,.125),(11.85,2.17,.25),"Planter boards",(8,1.25))
    for y in (-.99,.99):
        trough.box((0,y,.48),(11.85,.19,.46),"Planter boards",(8,1.25))
    for x in (-5.83,5.83):
        trough.box((x,0,.48),(.19,1.79,.46),"Planter boards",(8,1.25))
    trough.box((0,0,.43),(11.45,1.78,.31),"Soil")
    plant_a=rosette(18,12,"Mint leaf","Mint leaf shade")
    plant_b=rosette(31,9,"Mint leaf","Mint leaf shade")
    for side,x in (("Left",-8.75),("Right",8.75)):
        add(outdoor,side+" wood planter",trough,(x,-21.31,0))
        for i in range(6):
            mesh=plant_a if (i%2) else plant_b
            add(outdoor,f"{side} planter | plant {i+1}",mesh,
                (x+(i-2.5)*1.88,-21.30+(i%2-.5)*.23,.584),i*.37)

    chair=chair_mesh()
    small, large=table_mesh(3.28,3.10),table_mesh(4.03,3.67)
    green_pot, flower_pot=tabletop_plant(False),tabletop_plant(True)
    layout=[(-8.8,-15.9,False,True),(-11.9,-8.1,False,False),
            (-7.8,-3.9,True,True),(-11.6,1.0,False,False),
            (9.25,-15.9,False,True),(10.65,-6.7,True,False)]
    for i,(x,y,big,flowers) in enumerate(layout,1):
        label=f"Table {i:02}"
        add(seating,label,large if big else small,(x,y,0))
        add(seating,label+" | terracotta centerpiece",flower_pot if flowers else green_pot,(x,y,3.015))
        seats=[(0,-2.71,pi),(0,2.71,0)] if not big else [
            (0,-2.80,pi),(0,2.80,0),(-2.80,0,pi/2),(2.80,0,-pi/2)]
        for j,(dx,dy,angle) in enumerate(seats,1):
            add(seating,f"{label} | chair {j}",chair,(x+dx,y+dy,0),angle)

    front_counter=Mesh().box((0,0,1.38),(24.35,2.7,2.76),"Cabinet olive gray")
    front_counter.box((0,0,2.89),(24.80,3.02,.26),WOOD,(10,5),floor=True)
    add(service,"Customer counter",front_counter,(-.10,9.55,0))
    add(service,"Rear prep counter | sink and faucet",sink_counter(),(-1.05,17.62,0))
    register=register_mesh()
    for i,x in enumerate((-7.60,8.05),1):
        add(service,f"Register {i}",register,(x,9.54,3.02))
    add(service,"Five syrup pumps",pump_bottles(),(-11.15,17.57,2.90))
    for compact,positions in ((False,(-7.91,-4.34)),(True,(.98,3.80))):
        machine=coffee_machine(compact)
        for i,x in enumerate(positions,1):
            label="Pale espresso machine" if compact else "Dark-trimmed coffee machine"
            add(service,f"{label} {i}",machine,(x,17.53,2.90))
    cups=Mesh()
    for x,count in ((-.21,14),(.20,12)):
        for j in range(count):
            z=j*.084
            cups.rod((x,0,z),(x,0,z+.15),.102,APPLIANCE,10,tip=.156)
    add(service,"Two stacks of cups",cups,(-1.70,17.45,2.90))
    add(service,"White refrigerator",fridge_mesh(),(12.62,17.76,0))

    light=strip_light()
    for i,y in enumerate((-12.5,-2.50,10.90),1):
        for side,x in (("Left",-7.55),("Right",7.55)):
            add(decor,f"{side} twin strip ceiling fixture {i}",light,(x,y,9.90))
    add(decor,"Roman numeral clock",clock_mesh(),(-14.49,-7.70,6.69),pi/2)
    screen=Mesh().box((0,0,0),(3.80,.13,2.28),DARK)
    screen.box((0,-.073,0),(3.60,.026,2.09),"Display blue")
    add(decor,"Dark wall screen",screen,(-14.40,12.20,6.60),pi/2)
    add(decor,"Framed desert buildings",wall_print(False),(14.38,10.0,6.35),-pi/2)
    add(decor,"Framed desert sunset",wall_print(True),(14.38,-6.80,6.35),-pi/2)
    return parts


def blender_material(bpy, name, textures):
    rgb,roughness,metallic,alpha,kind=MATERIALS[name]
    mat=bpy.data.materials.new(name)
    mat[TAG]=True
    mat.diffuse_color=(*map(srgb,rgb),alpha)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    shader=next(node for node in nodes if node.type=="BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value=(*map(srgb,rgb),1)
    shader.inputs["Roughness"].default_value=roughness
    shader.inputs["Metallic"].default_value=metallic
    shader.inputs["Alpha"].default_value=alpha
    if alpha<1:
        mat.surface_render_method="BLENDED"
    if name=="Strip diffuser":
        shader.inputs["Emission Color"].default_value=(.84,.92,1,1)
        shader.inputs["Emission Strength"].default_value=1.35
    if kind:
        if kind not in textures:
            size,pixels=surface_pixels(kind)
            from array import array
            lookup=[value/255 for value in range(256)]
            rgba=array("f",[1.0])*(size*size*4)
            for channel in range(3):
                rgba[channel::4]=array("f",(lookup[value] for value in pixels[channel::3]))
            img=bpy.data.images.new("Coffee Shop | "+kind,width=size,height=size,alpha=False)
            img[TAG]=True
            img.colorspace_settings.name="sRGB"
            img.pixels.foreach_set(rgba)
            img.update()
            img.pack()
            textures[kind]=img
        image=nodes.new("ShaderNodeTexImage")
        image.image=textures[kind]
        image.extension="REPEAT"
        mat.node_tree.links.new(image.outputs["Color"],shader.inputs["Base Color"])
    return mat


def install_mesh(bpy, part, collection, mesh_cache, materials, textures):
    key=id(part.mesh)
    if key not in mesh_cache:
        source=part.mesh
        mesh=bpy.data.meshes.new(part.name+" | mesh")
        mesh[TAG]=True
        mesh.from_pydata(source.vertices,[],source.faces)
        mesh.update()
        slots={}
        for name in dict.fromkeys(source.materials):
            if name not in materials:
                materials[name]=blender_material(bpy,name,textures)
            slots[name]=len(mesh.materials)
            mesh.materials.append(materials[name])
        uv=mesh.uv_layers.new(name="UVMap")
        for polygon,name,coords,smooth in zip(mesh.polygons,source.materials,source.uv,source.smooth):
            polygon.material_index=slots[name]
            polygon.use_smooth=smooth
            for loop,coord in zip(polygon.loop_indices,coords):
                uv.uv[loop].vector=coord
        mesh_cache[key]=mesh
    obj=bpy.data.objects.new(part.name,mesh_cache[key])
    obj[TAG]=True
    obj["coffee_display_name"]=part.name
    collection.objects.link(obj)
    obj.location=part.position
    obj.rotation_euler.z=part.angle
    return obj


def new_collection(bpy,parent,name):
    collection=bpy.data.collections.new(name)
    collection[TAG]=True
    collection["coffee_display_name"]=name
    parent.children.link(collection)
    return collection


def remove_generation(bpy, root, keep_parent):
    for child in list(root.children):
        if child.get(TAG):
            if child.users==1:
                remove_generation(bpy,child,keep_parent)
            else:
                root.children.unlink(child)
        else:
            if keep_parent.children.get(child.name) is None:
                keep_parent.children.link(child)
            root.children.unlink(child)
    for obj in list(root.objects):
        if obj.get(TAG):
            if len(obj.users_collection)==1:
                bpy.data.objects.remove(obj,do_unlink=True)
            else:
                root.objects.unlink(obj)
        else:
            if keep_parent.objects.get(obj.name) is None:
                keep_parent.objects.link(obj)
            root.objects.unlink(obj)
    bpy.data.collections.remove(root)


def add_comparison_views(bpy, collection):
    from mathutils import Vector

    def camera(name,position,target,lens,ortho=None):
        data=bpy.data.cameras.new(name)
        data[TAG]=True
        data.lens=lens
        if ortho is not None:
            data.type="ORTHO"
            data.ortho_scale=ortho
        obj=bpy.data.objects.new(name,data)
        obj[TAG]=True
        obj["coffee_display_name"]=name
        collection.objects.link(obj)
        obj.location=position
        obj.rotation_euler=(Vector(target)-Vector(position)).to_track_quat("-Z","Y").to_euler()

    camera("Compare | Straight storefront",(0,-72,5.4),(0,-20,5.4),48,37)
    camera("Compare | Raised front corner",(37,-82,32),(0,-4,4.3),53)
    camera("Compare | Roof overhead",(0,0,75),(0,.001,0),44,49)
    camera("Compare | Interior to counter",(0,-17.55,5.50),(0,14,4.15),25)
    for i,y in enumerate((-12.5,-2.50,10.90),1):
        for side,x in (("Left",-7.55),("Right",7.55)):
            name=f"Preview light | {side} {i}"
            data=bpy.data.lights.new(name,"AREA")
            data[TAG]=True
            data.energy=260
            data.shape="RECTANGLE"
            data.size=6
            data.size_y=.62
            obj=bpy.data.objects.new(name,data)
            obj[TAG]=True
            obj["coffee_display_name"]=name
            collection.objects.link(obj)
            obj.location=(x,y,9.66)


def export_shop_glb(filepath):
    """Export the shop meshes alone, preserving the current object selection."""
    import bpy
    scene=bpy.context.scene
    shop=next((col for col in scene.collection.children
               if col.get(TAG) and col.get("coffee_display_name")==SHOP),None)
    if shop is None:
        raise RuntimeError("Run the coffee shop script before exporting.")
    path=Path(bpy.path.abspath(filepath)).with_suffix(".glb")
    layer=bpy.context.view_layer
    objects=list(layer.objects)
    original_selection=[obj for obj in objects if obj.select_get()]
    shop_meshes={obj for obj in shop.all_objects if obj.get(TAG) and obj.type=="MESH"}
    if not shop_meshes.issubset(set(objects)):
        raise RuntimeError("Include the entire Coffee Shop collection in this view layer before exporting.")
    try:
        for obj in objects:
            obj.select_set(obj in shop_meshes)
        return bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",
                                         use_selection=True,export_animations=False,
                                         export_cameras=False,export_lights=False)
    finally:
        for obj in objects:
            obj.select_set(False)
        for obj in original_selection:
            obj.select_set(True)


def build_shop():
    import bpy
    from mathutils import Vector
    scene=bpy.context.scene
    if bpy.context.mode!="OBJECT":
        raise RuntimeError("Switch to Object Mode before building the coffee shop.")
    parent=scene.collection
    parts=design()
    previous=[col for col in parent.children if col.get(TAG)]
    shop=new_collection(bpy,parent,SHOP)
    views=new_collection(bpy,parent,VIEWS)
    groups={}
    cache,materials,textures={},{},{}
    try:
        for part in parts:
            if part.group not in groups:
                groups[part.group]=new_collection(bpy,shop,part.group)
            install_mesh(bpy,part,groups[part.group],cache,materials,textures)
        add_comparison_views(bpy,views)
    except Exception:
        remove_generation(bpy,shop,parent)
        remove_generation(bpy,views,parent)
        raise

    for old in previous:
        if old.users==1:
            remove_generation(bpy,old,parent)
        else:
            parent.children.unlink(old)
    for data in (bpy.data.meshes,bpy.data.cameras,bpy.data.lights,bpy.data.materials,bpy.data.images):
        for item in list(data):
            if item.get(TAG) and item.users==0:
                data.remove(item)

    for col in [shop,views,*groups.values()]:
        col.name=col["coffee_display_name"]
        for obj in col.objects:
            obj.name=obj["coffee_display_name"]
    if scene.camera is None:
        scene.camera=views.objects.get("Compare | Raised front corner")
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type=="VIEW_3D":
                view=area.spaces.active.region_3d
                if view and view.view_perspective!="CAMERA":
                    view.view_location=(0,-4,4.5)
                    view.view_rotation=Vector((-24,66,-20)).to_track_quat("-Z","Y")
                    view.view_distance=72
    print(f"Built {len(parts)} editable coffee shop meshes in {shop.name!r}.")
    if SAVE_BLEND_TO:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(SAVE_BLEND_TO))
    if EXPORT_GLB_TO:
        export_shop_glb(EXPORT_GLB_TO)
    return shop


if __name__=="__main__":
    build_shop()
