"""Generate the editable Veranda scenes, optimized walkthroughs and scene data."""
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "assets" / "walkthrough"
SOURCE = ROOT / "blender"
HEIGHT = 2.7
GROUPS = ("Floors", "Low walls", "Upper walls", "Glazing", "Doors", "Ceiling",
          "Furnishings", "Existing wet areas", "Interior lighting")
MAT = {}
FURNITURE = {}
collections = {}
solids = []
floors = []


def rgb(value):
    channels = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c < .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels)


def image_node(mat, path, data=False):
    node=mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image=bpy.data.images.load(str(path),check_existing=True)
    node.image.pack()
    if data:
        node.image.colorspace_settings.name="Non-Color"
    return node


def material(name,color,rough=.6,metal=0,glow=0,alpha=1,maps=None,tint=None):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    p=nodes.get("Principled BSDF")
    col=(*rgb(color),1)
    mat.diffuse_color=(*rgb(color),alpha)
    p.inputs["Base Color"].default_value=col
    p.inputs["Roughness"].default_value=rough
    p.inputs["Metallic"].default_value=metal
    p.inputs["Alpha"].default_value=alpha
    p.inputs["Emission Color"].default_value=col
    p.inputs["Emission Strength"].default_value=glow
    if alpha<1:
        mat.surface_render_method="BLENDED"
    if maps:
        for channel,filename in maps.items():
            node=image_node(mat,SOURCE/"materials"/filename,data=channel!="Base Color")
            if channel=="Normal":
                normal=nodes.new("ShaderNodeNormalMap")
                normal.inputs["Strength"].default_value=.34 if name=="Ivory plaster" else .58
                links.new(node.outputs["Color"],normal.inputs["Color"])
                links.new(normal.outputs["Normal"],p.inputs["Normal"])
            elif channel=="Base Color" and tint:
                multiply_color(mat,p,node.outputs["Color"],tint)
            else:
                links.new(node.outputs["Color"],p.inputs[channel])
    MAT[name]=mat


def multiply_color(mat,shader,socket,tint):
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    multiply=nodes.new("ShaderNodeMix")
    multiply.data_type="RGBA"
    multiply.blend_type="MULTIPLY"
    multiply.inputs[0].default_value=1
    multiply.inputs[6].default_value=(*tint,1)
    links.new(socket,multiply.inputs[7])
    links.new(multiply.outputs[2],shader.inputs["Base Color"])


def palette():
    material("Ivory plaster", "ece4d8", .83, maps={"Normal":"beige_wall_001_nor_gl.jpg",
             "Roughness":"beige_wall_001_Rough.jpg"})
    material("Warm white millwork", "f5efe5", .62)
    material("Walnut veneer","654933",.55,tint=(.42,.35,.30),maps={"Base Color":"smoked_walnut_veneer_Diffuse.jpg",
             "Normal":"smoked_walnut_veneer_nor_gl.jpg","Roughness":"smoked_walnut_veneer_Rough.jpg"})
    material("Espresso oak", "4a3325", .54)
    material("Travertine","d6c9b6",.53,maps={"Base Color":"travertine_Color.jpg",
             "Normal":"travertine_NormalGL.jpg","Roughness":"travertine_Roughness.jpg"})
    material("Warm stone tile","e2d7c6",.59,maps={"Normal":"travertine_NormalGL.jpg","Roughness":"travertine_Roughness.jpg"})
    material("Honed gray granite floor","6d6a65",.49,maps={"Base Color":"granite_tile_Diffuse.jpg",
             "Normal":"granite_tile_nor_gl.jpg","Roughness":"granite_tile_Rough.jpg"})
    material("Tile seam", "b4a897", .9)
    material("Linen","e4dbcd",.86,maps={"Base Color":"terlenka_Diffuse.jpg",
             "Normal":"terlenka_nor_gl.jpg","Roughness":"terlenka_Rough.jpg"})
    material("White linen bedding","fcfaf7",.90,maps={"Normal":"terlenka_nor_gl.jpg"})
    p=MAT["White linen bedding"].node_tree.nodes.get("Principled BSDF")
    p.inputs["Sheen Weight"].default_value=.20
    p.inputs["Sheen Roughness"].default_value=.72
    material("Warm cotton", "ede4d7", .85)
    material("Taupe wool","9c8b76",.94,maps={"Normal":"terlenka_nor_gl.jpg"})
    material("Blackened bronze", "46392f", .38, .64)
    material("Brushed brass", "8f6a3d", .43, .60)
    material("Brushed stainless", "a8a6a1", .33, .62)
    material("Cooktop glass", "171818", .22, .35)
    material("Screen", "181c1a", .25, .24)
    material("Window glass", "d1e6e6", .19, alpha=.17)
    material("Ceramic", "f1ede4", .26)
    material("Opal light", "ffead0", .35, glow=.8)
    material("Olive foliage", "526248", .81)
    material("Sage foliage", "78866a", .84)
    material("Paper", "e4d6c3", .9)
    material("Clay", "ac795c", .82)
    material("Stone plinth", "887e72", .8)
    material("Retained balcony deck","896c54",.71,maps={"Normal":"natural_walnut_veneer_nor_gl.jpg"})
    for i,color in enumerate(("604737","654b3b","6c503f","705443","775944")):
        material(f"Wood-look SPC plank {i}",color,.66,maps={"Normal":"natural_walnut_veneer_nor_gl.jpg",
                 "Roughness":"natural_walnut_veneer_Rough.jpg"})


def xyz(x, d, h):
    return (x, -d, h)


def finish(obj, name, mat, group):
    obj.name = name
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    collections[group].objects.link(obj)
    obj.data.materials.append(MAT[mat])
    return obj


def box(name, x, d, h, w, depth, height, mat, group="Furnishings", bevel=.009, yaw=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz(x, d, h + height / 2))
    obj = bpy.context.object
    for v in obj.data.vertices:
        v.co.x *= w
        v.co.y *= depth
        v.co.z *= height
    for face in obj.data.polygons:
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        u, v = ((1, 2), (0, 2), (0, 1))[axis]
        if mat=="Walnut veneer" and axis!=2:
            u,v=v,u
        scale = {"Walnut veneer":1.02,"Linen":3.6,"Warm stone tile":.78,
                 "Travertine":1.05,"Taupe wool":4.25}.get(mat,.6)
        for i in face.loop_indices:
            p = obj.data.vertices[obj.data.loops[i].vertex_index].co
            obj.data.uv_layers.active.data[i].uv = (p[u] * scale + .5, p[v] * scale + .5)
    obj.rotation_euler.z = -yaw
    if bevel:
        mod = obj.modifiers.new("Eased edges", "BEVEL")
        mod.width = min(bevel, w*.24, depth*.24, height*.24)
        mod.segments = 1 if bevel <= .002 else 3
        normal = obj.modifiers.new("Face-weighted normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return finish(obj, name, mat, group)


def cylinder(name, x, d, h, radius, height, mat, group="Furnishings", scale=(1, 1)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=height,
                                       location=xyz(x, d, h + height/2))
    obj = bpy.context.object
    obj.scale.x, obj.scale.y = scale
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return finish(obj, name, mat, group)


def oval(name, x, d, h, scale, mat, group="Furnishings", tilt=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, location=xyz(x,d,h))
    obj = bpy.context.object
    obj.scale = scale
    obj.rotation_euler.y = tilt
    for p in obj.data.polygons:
        p.use_smooth = True
    return finish(obj, name, mat, group)


def bounds(name, x1, d1, x2, d2, kind="furniture"):
    solids.append({"name": name, "kind": kind, "rect": [round(n, 3) for n in (x1, d1, x2, d2)]})


def asset_meshes(key):
    if key in FURNITURE:
        return FURNITURE[key]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE/"furniture"/f"{key}.glb"))
    imported=[o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes=[]
    for obj in imported:
        if obj.type=="MESH":
            mesh=obj.data.copy()
            mesh.transform(obj.matrix_world)
            meshes.append(mesh)
    for obj in imported:
        bpy.data.objects.remove(obj,do_unlink=True)
    lo=[min(v.co[i] for mesh in meshes for v in mesh.vertices) for i in range(3)]
    hi=[max(v.co[i] for mesh in meshes for v in mesh.vertices) for i in range(3)]
    translation=Matrix.Translation((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
    for mesh in meshes:
        mesh.transform(translation)
    size=Vector([hi[i]-lo[i] for i in range(3)])
    FURNITURE[key]=(meshes,size)
    return FURNITURE[key]


def recolor(source,name,color,rough=None):
    existing=bpy.data.materials.get(name)
    if existing:
        return existing
    mat=source.copy()
    mat.name=name
    p=next(node for node in mat.node_tree.nodes if node.type=="BSDF_PRINCIPLED")
    for link in list(p.inputs["Base Color"].links):
        mat.node_tree.links.remove(link)
    p.inputs["Base Color"].default_value=(*rgb(color),1)
    if rough is not None:
        for link in list(p.inputs["Roughness"].links):
            mat.node_tree.links.remove(link)
        p.inputs["Roughness"].default_value=rough
    mat.diffuse_color=(*rgb(color),1)
    return mat


def furniture(key,name,x,d,w,depth,height,rotation=0,bar_seat=False):
    meshes,span=asset_meshes(key)
    transform=Matrix.Rotation(rotation,4,"Z") @ Matrix.Diagonal((w/span.x,depth/span.y,height/span.z,1))
    points=[]
    for source in meshes:
        mesh=source.copy()
        mesh.transform(transform)
        if bar_seat:
            # Increase leg height while preserving the curved leather back and seat.
            for vertex in mesh.vertices:
                h=vertex.co.z
                vertex.co.z=h*.66/.52 if h<.52 else .66+(h-.52)*.37/(height-.52)
        if key=="sofa":
            linen=recolor(mesh.materials[0],"Sofa • ivory upholstery","e3d8c7")
            mesh.materials.append(linen)
            for face in mesh.polygons:
                if min(mesh.vertices[j].co.z for j in face.vertices)>.176:
                    face.material_index=1
        if key=="bed":
            original=mesh.materials[0]
            top=max(v.co.z for v in mesh.vertices)
            if top>.89*height:
                mesh.materials[0]=recolor(original,"Bed • taupe upholstery","a99a89",.81)
            elif top>.41*height:
                mesh.materials[0]=MAT["White linen bedding"]
        if key=="dining-chair":
            leather=bpy.data.materials.get("Seating • saddle leather and bronze")
            if leather is None:
                leather=mesh.materials[0].copy()
                leather.name="Seating • saddle leather and bronze"
                shader=next(n for n in leather.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
                texture=shader.inputs["Base Color"].links[0].from_socket
                multiply_color(leather,shader,texture,(.55,.48,.43))
            mesh.materials[0]=leather
        obj=bpy.data.objects.new(name,mesh)
        collections["Furnishings"].objects.link(obj)
        obj.location=xyz(x,d,0)
        points.extend((x+v.co.x,d-v.co.y) for v in mesh.vertices)
    bounds(name,min(a for a,b in points),min(b for a,b in points),
           max(a for a,b in points),max(b for a,b in points))


def rounded_slab(name,x,d,h,w,l,height,r,mat):
    vertices=[]
    for z in (0,height):
        for sx,sy,start in [(1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)]:
            for i in range(9):
                t=math.radians(start+90*i/8)
                vertices.append((sx*(w/2-r)+r*math.cos(t),sy*(l/2-r)+r*math.sin(t),z))
    n=len(vertices)//2
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    uv=mesh.uv_layers.new()
    for face in mesh.polygons:
        for j in face.loop_indices:
            px,py,pz=mesh.vertices[mesh.loops[j].vertex_index].co
            uv.data[j].uv=(px+.5,py+pz+.5)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.location=xyz(x,d,h)
    bevel=obj.modifiers.new("Honed eased edge","BEVEL")
    bevel.width=min(.013,height/4)
    bevel.segments=3
    obj.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    return finish(obj,name,mat,"Furnishings")


def slab(x1,d1,x2,d2,finish_type="granite"):
    floors.append([x1, d1, x2, d2])
    x, d = (x1+x2)/2, (d1+d2)/2
    box("Floor substrate", x, d, -.135, x2-x1, d2-d1, .12,
        "Tile seam", "Floors", 0)
    if finish_type=="granite":
        obj=box("Honed gray granite flooring",x,d,-.015,x2-x1,d2-d1,.015,
                "Honed gray granite floor","Floors",0)
        # World-aligned tiling continues through open thresholds.
        for i,loop in enumerate(obj.data.loops):
            v=obj.data.vertices[loop.vertex_index].co
            obj.data.uv_layers.active.data[i].uv=((x+v.x)/2.3,(d-v.y)/2.3)
        return
    if finish_type == "deck":
        step, row = .16, 0
        while x1+row*step < x2-.008:
            left = x1+row*step
            w = min(step, x2-left)-.007
            box("Balcony deck board", left+w/2, d, -.015, w, d2-d1, .015,
                "Retained balcony deck","Floors",.001)
            row += 1
        return
    if finish_type=="spc":
        row, depth = 0, .19
        while d1+row*depth < d2-.007:
            top = d1+row*depth
            length = min(depth,d2-top)-.003
            start = x1 - (row%3)*.48
            col = 0
            while start < x2-.007:
                a, b = max(x1,start), min(x2,start+1.44)
                if b-a > .006:
                    box("Staggered wood-look SPC floor", (a+b)/2, top+length/2, -.015,
                        b-a-.003, length, .015, f"Wood-look SPC plank {(col*3+row*7)%5}", "Floors", .001)
                start += 1.44
                col += 1
            row += 1
        return
    for i in range(math.floor(x1/.9), math.ceil(x2/.9)):
        for j in range(math.floor(d1/.9), math.ceil(d2/.9)):
            a,b=max(x1,i*.9),min(x2,(i+1)*.9)
            c,e=max(d1,j*.9),min(d2,(j+1)*.9)
            if min(b-a,e-c) > .008:
                box("Honed porcelain tile", (a+b)/2,(c+e)/2,-.015,
                    b-a-.004,e-c-.004,.015,"Warm stone tile","Floors",.001)


def segment(name, a, b, bottom, height, thickness, mat, group, bevel=0):
    x1,d1 = a
    x2,d2 = b
    return box(name,(x1+x2)/2,(d1+d2)/2,bottom,math.hypot(x2-x1,d2-d1),
               thickness,height,mat,group,bevel,math.atan2(d2-d1,x2-x1))


def wall(a, b, thickness=.12, start=0, top=HEIGHT, mat="Ivory plaster"):
    x1,d1 = a
    x2,d2 = b
    if start < 1:
        segment("Wall below cutaway", a,b,start,min(top,1)-start,thickness,mat,"Low walls")
    if top > 1:
        low = max(1,start)
        segment("Wall above cutaway", a,b,low,top-low,thickness,mat,"Upper walls")
    if start == 0:
        segment("Painted skirting",a,b,.01,.085,thickness+.022,"Warm white millwork","Low walls",.002)
    if start < 1.63 and top > .05:
        # All circulation walls are orthogonal. Add half thickness only normal to the wall.
        hx, hd = (thickness/2, 0) if x1 == x2 else (0, thickness/2)
        bounds("Wall", min(x1,x2)-hx,min(d1,d2)-hd,max(x1,x2)+hx,max(d1,d2)+hd,"architecture")


def opening(a,b,sill=.82,head=2.43, panels=2, open_panel=None):
    if sill:
        wall(a,b,start=0,top=sill)
    wall(a,b,start=head)
    segment("Window head frame",a,b,head-.038,.038,.083,"Blackened bronze","Glazing",.002)
    if sill:
        segment("Window sill frame",a,b,sill,.041,.083,"Blackened bronze","Glazing",.002)
    else:
        segment("Flush door track",a,b,.003,.018,.087,"Blackened bronze","Floors",.001)
    for i in range(panels+1):
        t=i/panels
        x,d=(a[k]+t*(b[k]-a[k]) for k in range(2))
        box("Window mullion",x,d,sill,.04,.045,head-sill,"Blackened bronze","Glazing",.002)
    for i in range(panels):
        if i == open_panel:
            continue
        p,q=[tuple(a[k]+(b[k]-a[k])*t/panels for k in range(2)) for t in (i,i+1)]
        segment("Glazed panel",p,q,sill+.022,head-sill-.048,.012,"Window glass","Glazing")
        hx, hd = (.025,0) if p[0]==q[0] else (0,.025)
        bounds("Glazing",p[0]-hx,p[1]-hd,q[0]+hx,q[1]+hd,"architecture")


def door(a,b, swing, leaf=True):
    """Model a retained opening with its leaf parked against the adjacent wall."""
    wall(a,b,start=2.15)
    x,d=a
    for x0,d0 in (a,b):
        box("Door casing",x0,d0,0,.055,.055,2.16,"Walnut veneer","Doors",.004)
    segment("Door head casing",a,b,2.12,.045,.07,"Walnut veneer","Doors",.004)
    if leaf:
        length=math.dist(a,b)-.045
        dx,dd=swing
        end=(x+dx*length,d+dd*length)
        segment("Open walnut door",a,end,.02,2.08,.048,"Walnut veneer","Doors",.006)
        hx, hd = (.024,0) if not dx else (0,.024)
        bounds("Open door leaf",min(x,end[0])-hx,min(d,end[1])-hd,
               max(x,end[0])+hx,max(d,end[1])+hd,"architecture")
        for offset in (-.038,.038):
            box("Door lever",x+dx*(length-.13)+dd*offset,d+dd*(length-.13)+dx*offset,
                1.02,.08 if dx else .027,.027 if dx else .08,.019,"Blackened bronze","Doors",.004)


def ceiling(x1,d1,x2,d2):
    box("Ceiling slab", (x1+x2)/2,(d1+d2)/2,HEIGHT,x2-x1,d2-d1,.11,"Warm white millwork","Ceiling",0)


def curtain(x,d,width,axis="x"):
    for i in range(12):
        t=width*(i/11-.5)
        wave=.022*math.sin(i*2.2)
        px,pd=(x+t,d+wave) if axis=="x" else (x+wave,d+t)
        box("Linen curtain fold",px,pd,.08,width/9 if axis=="x" else .065,
            .065 if axis=="x" else width/9,2.47,"Linen","Upper walls",.021)
    a,b=((x-width/2,d),(x+width/2,d)) if axis=="x" else ((x,d-width/2),(x,d+width/2))
    segment("Recessed curtain track",a,b,2.56,.032,.085,"Warm white millwork","Ceiling",.003)


def column(x,d,w,l):
    for z,h,g in [(0,1,"Low walls"),(1,HEIGHT-1,"Upper walls")]:
        box("Existing structure",x,d,z,w,l,h,"Ivory plaster",g,.002)
    bounds("Existing column",x-w/2,d-l/2,x+w/2,d+l/2,"architecture")


def aim(obj,target):
    obj.rotation_euler=(Vector(xyz(*target))-obj.location).to_track_quat("-Z","Y").to_euler()


def light(name, loc, target, watts, size, color=(1,.88,.73)):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=watts
    data.size=size
    data.color=color
    obj=bpy.data.objects.new(name,data)
    collections["Interior lighting"].objects.link(obj)
    obj.location=xyz(*loc)
    aim(obj,target)


def pendant(x,d,h=2.05,r=.115):
    cylinder("Pendant stem",x,d,h,.007,HEIGHT-h,"Blackened bronze","Ceiling")
    cylinder("Ceiling canopy",x,d,2.665,.044,.035,"Brushed brass","Ceiling")
    oval("Opal pendant",x,d,h,(r,r,r*.88),"Opal light","Ceiling")
    cylinder("Pendant cap",x,d,h+r*.63,r*.25,.038,"Brushed brass","Ceiling")


def downlight(x,d):
    cylinder("Recessed brass downlight",x,d,2.68,.045,.02,"Brushed brass","Ceiling")
    cylinder("Diffuser",x,d,2.676,.033,.006,"Opal light","Ceiling")


def panel(x,d,z,w,h,mat="Walnut veneer",axis="x",group="Furnishings"):
    """A shallow applied frame, set proud of a joinery front or feature wall."""
    for t in (-1,1):
        if axis=="x":
            box("Panel stile",x+t*w/2,d,z,.018,.022,h,mat,group,bevel=.003)
            box("Panel rail",x,d,z+(h-.018)*(t+1)/2,w,.022,.018,mat,group,bevel=.003)
        else:
            box("Panel stile",x,d+t*w/2,z,.022,.018,h,mat,group,bevel=.003)
            box("Panel rail",x,d,z+(h-.018)*(t+1)/2,.022,w,.018,mat,group,bevel=.003)


def art(x,d,h,w,l,flip=1,name="Dark timber art frame"):
    g="Upper walls"
    box(name,x,d,h,w,.038,l,"Espresso oak",g,bevel=.012)
    box("Linen artwork canvas",x,d+.020*flip,h+.035,w-.065,.006,l-.07,"Paper",g)
    colors=("Paper","Clay","Warm cotton","Sage foliage")
    for i in range(13):
        px=x+w*(.22*math.sin(i*.63)-.06)
        z=h+l*(.22+i*.043)
        angle=i*.39
        depth=d+flip*(.024+i*.00042)
        vertices=[]
        for j in range(32):
            t=2*math.pi*j/32
            u=w*.105*math.cos(t)
            v=l*.057*math.sin(t)
            vertices.append(xyz(px+u*math.cos(angle)-v*math.sin(angle),depth,
                                z+u*math.sin(angle)+v*math.cos(angle)))
        mesh=bpy.data.meshes.new("Flat pigment on canvas")
        mesh.from_pydata(vertices,[],[tuple(range(len(vertices)))])
        pigment=bpy.data.objects.new("Abstract pigment",mesh)
        bpy.context.collection.objects.link(pigment)
        finish(pigment,"Abstract pigment",colors[i%len(colors)],g)


def plant(x,d,size=1):
    cylinder("Stoneware planter",x,d,0,.18*size,.31*size,"Stone plinth")
    cylinder("Potting soil",x,d,.31*size,.16*size,.01,"Espresso oak")
    for i in range(22):
        a=i*2.39996
        r=(.09+.21*(i%6)/5)*size
        h=(.48+.56*(i%10)/9)*size
        leaf=oval("Ficus leaf",x+math.cos(a)*r,d+math.sin(a)*r,h,
                  (.115*size,.04*size,.024*size),
                  "Olive foliage" if i%4 else "Sage foliage",tilt=.43*math.cos(a))
        leaf.rotation_euler.z=a
    bounds("Planter",x-.20*size,d-.20*size,x+.20*size,d+.20*size)


def rug(x,d,w,l):
    box("Flatwoven rug",x,d,.003,w,l,.014,"Taupe wool",bevel=.012)
    for s in (-1,1):
        box("Bound rug edge",x+s*(w/2-.045),d,.015,.017,l-.065,.003,"Warm cotton")
        box("Bound rug edge",x,d+s*(l/2-.045),.015,w-.065,.017,.003,"Warm cotton")


def sofa(x,d,w,face):
    furniture("sofa","Tailored three-seat sofa",x,d,w,.92,.92,0 if face==1 else math.pi)


def chair(x,d,face=1):
    furniture("dining-chair","Leather dining chair",x,d,.45,.48,.84,0 if face==1 else math.pi)


def bar_stool(x,d):
    furniture("dining-chair","Leather counter stool",x,d,.375,.39,1.0,
              math.pi/2,bar_seat=True)
    box("Bronze counter stool footrest",x+.105,d,.228,.022,.30,.021,"Blackened bronze")


def coffee(x,d,w=.54):
    cylinder("Oval travertine tabletop",x,d,.38,w,.065,"Travertine",scale=(1,.6))
    for i in (-1,1):
        cylinder("Travertine pedestal",x+i*.18,d,0,.17,.39,"Stone plinth",scale=(.8,1))
    box("Coffee-table book",x-.12,d-.03,.446,.23,.15,.028,"Paper",yaw=.14)
    cylinder("Ceramic vessel",x+.19,d+.055,.446,.082,.115,"Clay")
    bounds("Coffee table",x-w,d-w*.6,x+w,d+w*.6)


def media_wall(x,d,w):
    g="Upper walls"
    # A slim continuous cabinet mounts to the wall behind a recessed shadow line.
    box("Recessed floating cabinet support",x,d+.085,.10,w-.13,.17,.16,"Espresso oak")
    box("Floating walnut carcass",x,d,.185,w,.345,.31,"Walnut veneer",bevel=.009)
    box("Honed stone media ledge",x,d,.495,w+.038,.376,.033,"Travertine",bevel=.005)
    for i in (-1,0,1):
        px=x+i*w/3
        box("Inset walnut media drawer",px,d-.179,.214,w/3-.017,.026,.252,
            "Walnut veneer",bevel=.006)
        panel(px,d-.194,.230,w/3-.077,.212,"Espresso oak")
        box("Slim aged brass pull",px,d-.207,.424,.115,.014,.012,"Brushed brass",bevel=.004)
    bounds("Floating media cabinet",x-w/2-.019,d-.214,x+w/2+.019,d+.188)

    column_w=.44
    shelf_x=x-w/2+column_w/2
    reveal_x=x+column_w/2
    reveal_w=w-column_w-.035
    box("Recessed walnut TV surround",reveal_x,d+.123,.545,reveal_w,.118,1.765,
        "Walnut veneer",g,.007)
    box("Ivory panel inside walnut reveal",reveal_x,d+.055,.602,reveal_w-.13,.055,1.648,
        "Ivory plaster",g,.009)
    panel(reveal_x,d+.019,.675,reveal_w-.29,1.49,"Warm white millwork",group=g)
    tv_w=min(1.55,reveal_w-.29)
    box("Flush TV mount",reveal_x,d-.006,.90,tv_w-.20,.045,.61,"Espresso oak",g,.012)
    box("Thin bronze screen bezel",reveal_x,d-.030,.835,tv_w,.044,.827,"Blackened bronze",g,.009)
    box("Television display",reveal_x,d-.055,.853,tv_w-.035,.009,.791,"Screen",g,.004)

    box("Display niche walnut back",shelf_x,d+.132,.528,column_w,.055,1.782,"Walnut veneer",g)
    for dx in (-1,1):
        box("Display niche end panel",shelf_x+dx*(column_w/2-.018),d+.029,.528,.036,.245,1.782,
            "Walnut veneer",g,.004)
    for h in (.528,.961,1.400,1.837,2.274):
        box("Recessed walnut display shelf",shelf_x,d+.025,h,column_w-.061,.24,.036,
            "Walnut veneer",g,.004)
    box("Concealed shelf diffuser",shelf_x,d-.044,2.254,column_w-.09,.018,.012,"Opal light",g,.002)
    for i,height in enumerate((.207,.235,.198,.219)):
        box("Cloth-bound book",shelf_x-.116+i*.042,d-.03,1.435,.033,.113,height,
            ["Warm cotton","Espresso oak","Paper","Taupe wool"][i],g,.003)
    cylinder("Small stoneware urn",shelf_x,d-.009,.996,.081,.145,"Clay",g)
    cylinder("Small stoneware urn neck",shelf_x,d-.009,1.14,.042,.047,"Clay",g)
    box("Display book on shelf",shelf_x,d-.01,.567,.218,.128,.035,"Paper",g)
    oval("Ceramic display bowl",shelf_x+.031,d-.004,1.908,(.10,.065,.035),"Ceramic",g)
    light("Media niche wash",(shelf_x,d-.09,2.245),(shelf_x,d+.01,1.36),13,.20)


def lounge_cove(a,b):
    segment("Plaster ceiling cornice",a,b,2.60,.10,.102,"Warm white millwork","Upper walls",.003)
    segment("Cornice lower bead",a,b,2.572,.034,.072,"Warm white millwork","Upper walls",.003)


def bed(x,d,w,face=1,length=2.02):
    furniture("bed","Upholstered bed and folded linens",x,d,w+.10,length+.12,1.06,
              0 if face==1 else math.pi)


def bedside(x,d):
    box("Floating bedside drawer",x,d,.19,.38,.36,.28,"Walnut veneer",bevel=.023)
    box("Bedside top",x,d,.47,.39,.37,.027,"Travertine")
    cylinder("Bedside brass lamp",x,d,.50,.06,.16,"Brushed brass")
    oval("Bedside opal globe",x,d,.75,(.096,.096,.10),"Opal light")
    bounds("Bedside drawer",x-.20,d-.19,x+.20,d+.19)


def wardrobe(x,d,width,axis="x",face=1):
    w,l=(width,.55) if axis=="x" else (.55,width)
    box("Walnut wardrobe carcass",x,d,0,w,l,2.42,"Walnut veneer")
    doors=math.ceil(width/.56)
    for i in range(doors):
        off=(i+.5)*width/doors-width/2
        px,pd=(x+off,d+face*.278) if axis=="x" else (x+face*.278,d+off)
        panel(px,pd,.11,width/doors-.052,2.23,"Espresso oak",axis=axis)
        hx,hd=(px+.13,pd+face*.022) if axis=="x" else (px+face*.022,pd+.13)
        box("Wardrobe pull",hx,hd,1.0,.016,.018,.21,"Brushed brass",bevel=.004)
    bounds("Wardrobe",x-w/2-.018,d-l/2-.018,x+w/2+.018,d+l/2+.018)


def desk(x,d,w=.95,face=1):
    box("Writing surface",x,d,.72,w,.44,.05,"Warm white millwork",bevel=.017)
    for i in (-1,1):
        box("Walnut desk end",x+i*(w/2-.043),d,.025,.052,.37,.70,"Walnut veneer")
    box("Open book",x-.13,d,.77,.22,.15,.02,"Paper",yaw=.1)
    bounds("Desk",x-w/2,d-.22,x+w/2,d+.22)
    chair(x,d+.47*face,-face)


def refrigerator(x,d,face):
    box("Refrigerator",x,d,.01,.62,.64,1.81,"Brushed stainless",bevel=.034)
    for z in (.08,.70):
        h=.55 if z<.5 else 1.095
        box("Refrigerator door",x+face*.327,d,z,.055,.615,h,"Brushed stainless",bevel=.018)
        box("Refrigerator pull",x+face*.366,d-.195,z+.30,.027,.021,.20,
            "Blackened bronze")
    bounds("Refrigerator",x-.38,d-.32,x+.38,d+.32)


def kitchen(x,d1,d2,face,hob,sink):
    # Worktop is physically open over the inset sink.
    left,right=x-.325,x+.325
    box("Walnut kitchen carcass",x,(d1+d2)/2,.085,.58,d2-d1,.751,"Walnut veneer")
    box("Recessed plinth",x,(d1+d2)/2,0,.49,d2-d1,.09,"Espresso oak")
    for a,b in ((d1,sink-.22),(sink+.22,d2)):
        box("Honed stone worktop",x,(a+b)/2,.836,.65,b-a,.055,"Travertine",bevel=.006)
    for a,b in ((left,x-.211),(x+.211,right)):
        box("Stone sink return",(a+b)/2,sink,.836,b-a,.44,.055,"Travertine",bevel=.005)
    box("Inset sink basin bottom",x,sink,.843,.421,.43,.01,"Brushed stainless")
    for s in (-1,1):
        box("Inset basin rim",x+s*.207,sink,.85,.023,.445,.039,"Brushed stainless")
        box("Inset basin rim",x,sink+s*.212,.85,.414,.02,.039,"Brushed stainless")
    cylinder("Sink drain",x,sink,.854,.034,.006,"Blackened bronze")
    tap_x=x-face*.26
    cylinder("Mixer column",tap_x,sink,.89,.014,.207,"Brushed brass")
    box("Mixer spout",tap_x+face*.071,sink,1.071,.16,.025,.024,"Brushed brass",bevel=.01)
    cylinder("Mixer aerator",tap_x+face*.14,sink,1.045,.014,.032,"Brushed brass")
    count=round((d2-d1)/.53)
    for i in range(count):
        dep=d1+(d2-d1)*(i+.5)/count
        span=(d2-d1)/count-.014
        for z in (.105,.343,.585):
            box("Shaker drawer front",x+face*.301,dep,z,.035,span,.231,"Walnut veneer")
            panel(x+face*.322,dep,z+.025,span-.070,.175,"Espresso oak",axis="d")
            box("Brass drawer pull",x+face*.338,dep,z+.16,.028,.14,.018,"Brushed brass")
        box("Ivory wall cabinet",x-face*.113,dep,1.48,.38,span,.69,"Warm white millwork","Upper walls")
        panel(x+face*.083,dep,1.51,span-.060,.62,"Ivory plaster",axis="d",group="Upper walls")
        box("Wall cabinet pull",x+face*.103,dep+.12,1.54,.02,.021,.11,"Brushed brass","Upper walls")
    box("Full stone splashback",x-face*.30,(d1+d2)/2,.89,.026,d2-d1,.60,"Travertine")
    box("Under-cabinet task strip",x+face*.031,(d1+d2)/2,1.468,.024,d2-d1-.06,.012,"Opal light","Upper walls")
    box("Cooktop glass",x,hob,.891,.49,.45,.022,"Cooktop glass",bevel=.011)
    for a in (-1,1):
        for b in (-1,1):
            cylinder("Induction zone",x+a*.114,hob+b*.102,.913,.064,.002,"Blackened bronze")
    box("Integrated extractor trim",x-face*.058,hob,1.459,.32,.53,.035,"Blackened bronze","Upper walls")
    bounds("Kitchen worktop",left,d1,right,d2)
    bounds("Stove cabinet",left,hob-.25,right,hob+.25,"fixture")
    return left if face<0 else right


def bar(x,d):
    rounded_slab("Recessed island plinth",x+.075,d,.014,.245,.86,.068,.069,"Espresso oak")
    rounded_slab("Walnut island base",x+.075,d,.077,.300,.895,.815,.081,"Walnut veneer")
    for i in range(17):
        box("Fluted island face",x+.228,d+(i-8)*.043,.081,.021,.018,.803,"Walnut veneer",bevel=.006)
    rounded_slab("Radius-edge travertine island top",x,d,.886,.49,1.00,.054,.115,"Travertine")
    bounds("Breakfast island",x-.245,d-.50,x+.245,d+.50)
    # Low seats tuck beneath the overhang. Their backs sit west of the worktop edge.
    for delta in (-.248,.248):
        bar_stool(x-.33,d+delta)
        pendant(x,d+delta,2.02,.093)


def dining(x,d):
    box("Rounded walnut dining table",x,d,.738,1.57,.83,.056,"Walnut veneer",bevel=.025)
    for a in (-1,1):
        for b in (-1,1):
            cylinder("Dining table leg",x+a*.63,d+b*.29,.01,.042,.738,"Espresso oak")
    bounds("Dining table",x-.785,d-.415,x+.785,d+.415)
    for a in (-1,1):
        for b in (-1,1):
            chair(x+a*.4,d+b*.69,-b)
    cylinder("Table stoneware vase",x,d,.795,.084,.145,"Clay")
    for i in (-1,0,1):
        pendant(x+i*.44,d,2.07+abs(i)*.10,.095)


def bath_fixture(x,d,kind,axis="d"):
    g="Existing wet areas"
    if kind=="wc":
        box("Retained cistern",x,d-.12,.06,.36,.155,.69,"Ceramic",g)
        oval("Retained toilet",x,d+.13,.29,(.185,.27,.18),"Ceramic",g)
        oval("Closed toilet seat",x,d+.15,.44,(.166,.229,.047),"Ceramic",g)
        bounds("Existing toilet",x-.19,d-.20,x+.19,d+.40)
    elif kind=="tub":
        w,l=(1.40,.73) if axis=="x" else (.75,1.53)
        box("Retained tub apron",x,d,0,w,l,.52,"Ceramic",g,.055)
        box("Retained tub interior",x,d,.517,w-.16,l-.18,.014,"Warm stone tile",g,.015)
        if axis=="x":
            box("Existing bath screen",x-.24,d-l/2+.028,.54,.63,.018,1.29,"Window glass",g)
        else:
            box("Existing bath screen",x-w/2+.028,d-.30,.54,.018,.76,1.29,"Window glass",g)
        bounds("Existing tub",x-w/2,d-l/2,x+w/2,d+l/2)
    else:
        box("Retained vanity",x,d,.05,.44,.64,.74,"Warm stone tile",g)
        box("Retained ceramic basin",x,d,.79,.46,.62,.068,"Ceramic",g)
        cylinder("Retained tap",x-.12,d,.85,.012,.18,"Brushed stainless",g)
        bounds("Existing vanity",x-.23,d-.32,x+.23,d+.32)


def balcony(x, d1, d2):
    segment("Balcony handrail",(x,d1),(x,d2),1.05,.045,.06,"Blackened bronze","Low walls")
    segment("Balcony safety glazing",(x,d1),(x,d2),.12,.93,.018,"Window glass","Low walls")
    n=math.ceil((d2-d1)/1.4)
    for i in range(n+1):
        box("Balcony railing post",x,d1+(d2-d1)*i/n,.02,.042,.042,1.05,
            "Blackened bronze","Low walls")
    bounds("Balcony guard",x-.03,d1,x+.03,d2,"architecture")


def schedule_slabs(items):
    for x1,d1,x2,d2,mat in items:
        slab(x1,d1,x2,d2,mat)
        if mat!="deck":
            ceiling(x1,d1,x2,d2)



def layout_2br():
    schedule_slabs([
        (0,0,6,3,"granite"),(6,1.45,6.7,3,"granite"),(-1,0,0,3,"deck"),
        (0,3,3.7,5.5,"spc"),(3.7,3,8.5,4.9,"granite"),(3.7,4.9,5,5.5,"granite"),
        (0,5.5,3.7,5.77,"spc"),(3.7,5.5,5,5.77,"granite"),(0,5.77,5,8.5,"spc"),(5,4.9,6.5,7.5,"tile"),(6.5,4.9,8.5,5.5,"granite"),(6.5,5.5,8.5,7.5,"tile"),
        (5,7.5,8.5,8.5,"tile"),
    ])
    for a,b in [
        ((0,0),(6,0)),((6,0),(6,1.45)),((6,1.45),(6.7,1.45)),((6.7,2.56),(6.7,3)),
        ((6.7,3),(8.5,3)),((8.5,3),(8.5,8.5)),((3.82,8.5),(8.5,8.5)),
        ((0,3),(0,3.82)),((0,4.8),(0,6.24)),((0,7.15),(0,8.5)),((0,8.5),(.95,8.5)),
        ((0,3),(3.7,3)),((3.7,3),(3.7,4.43)),((3.7,5.28),(3.7,5.77)),
        ((0,5.5),(3.7,5.5)),((3.7,5.77),(3.88,5.77)),((4.80,5.77),(5,5.77)),
        ((5,4.9),(5,5.77)),((5,4.9),(5.12,4.9)),((5.91,4.9),(6.5,4.9)),((5,5.77),(5,8.5)),
        ((6.5,4.9),(6.5,5.5)),((6.5,5.5),(6.95,5.5)),((7.79,5.5),(8.5,5.5)),
        ((6.5,5.5),(6.5,7.5)),((5,7.5),(7.07,7.5)),((7.87,7.5),(8.5,7.5)),
        ((6.5,7.5),(6.5,8.5)),
    ]:
        wall(a,b)
    door((5.12,4.9),(5.91,4.9),(0,1))
    door((6.7,1.45),(6.7,2.56),(-1,0))
    door((3.7,4.43),(3.7,5.28),(-1,0))
    door((3.88,5.77),(4.80,5.77),(0,1))
    door((6.95,5.5),(7.79,5.5),(0,1))
    door((7.07,7.5),(7.87,7.5),(0,1))
    opening((0,0),(0,3),sill=0,panels=3,open_panel=1)
    for a,b in [((0,3.82),(0,4.8)),((0,6.24),(0,7.15)),((.95,8.5),(3.82,8.5))]:
        opening(a,b)
    balcony(-1,0,3)
    wall((-1,0),(0,0),.1,top=1.1)
    wall((-1,3),(0,3),.1,top=1.1)
    column(.39,3.03,.78,.29)
    column(.48,8.27,.88,.34)
    column(8.13,3.13,.62,.24)
    curtain(.115,.32,.43,"d")
    curtain(.115,2.68,.42,"d")
    curtain(1.19,8.37,.44)
    curtain(3.56,8.37,.40)
    sofa(2.21,.56,2.55,1)
    rug(2.22,1.72,3.20,1.92)
    coffee(2.21,1.64,.51)
    media_wall(2.10,2.77,2.55)
    lounge_cove((.12,.093),(5.88,.093))
    lounge_cove((.11,.13),(.11,2.86))
    for x in (.73,2.11,3.49):
        panel(x,.075,.20,1.15,2.28,"Warm white millwork",group="Upper walls")
    art(2.21,.079,1.30,1.06,.69)
    plant(.32,2.34,.90)
    plant(4.63,.33,.85)
    furniture("armchair","Woven cane lounge chair",4.24,1.67,.70,.61,.81,math.radians(42))
    stove_front=kitchen(8.11,3.27,4.72,-1,3.56,4.40)
    bar_x=6.44
    bar_d=3.98
    bar(bar_x,bar_d)
    refrigerator(8.06,5.105,-1)
    bed(1.11,4.22,1.18,length=1.90)
    bedside(1.99,3.48)
    wardrobe(3.35,3.65,1.06,"d",-1)
    desk(2.63,3.32,.88)
    bed(1.98,6.80,1.60)
    for x in (.88,3.08):
        bedside(x,5.92)
    panel(1.98,5.575,.21,2.62,2.27,"Warm white millwork",group="Upper walls")
    art(1.98,5.587,1.29,.91,.63)
    wardrobe(4.66,7.72,1.37,"d",-1)
    box("Floating vanity",.29,7.45,.72,.40,.84,.08,"Walnut veneer",bevel=.017)
    box("Bronze vanity mirror",.078,7.45,1.05,.024,.57,.70,"Brushed brass","Upper walls",bevel=.019)
    box("Vanity mirror glass",.097,7.45,1.081,.014,.52,.64,"Brushed stainless","Upper walls",bevel=.011)
    cylinder("Vanity stool",.78,7.45,0,.18,.44,"Linen")
    bounds("Vanity",.09,7.03,.49,7.87)
    bounds("Vanity stool",.60,7.27,.96,7.63)
    bath_fixture(5.75,7.04,"tub","x")
    bath_fixture(6.09,5.50,"vanity")
    bath_fixture(6.13,6.15,"wc")
    bath_fixture(7.71,8.02,"wc")
    box("Existing utility appliance",8.02,7.03,0,.60,.63,.86,"Ceramic","Existing wet areas")
    for x,d in [(1.3,1.25),(3.54,1.3),(4.53,3.70),(7.23,3.7),(7.27,4.74),
                (1.35,4.1),(2.57,4.5),(1.3,6.46),(3.32,7.28)]:
        downlight(x,d)
    light("Balcony soft daylight",(-.44,1.5,2.23),(2.95,1.6,.82),520,2.3,(.82,.91,1))
    light("Living ceiling bounce",(3.1,1.64,2.61),(2.2,1.4,.4),135,1.9)
    light("Kitchen ceiling bounce",(6.88,4.07,2.58),(7.3,4.10,.8),195,1.25)
    light("Guest window daylight",(.19,4.35,2.04),(2.2,4.46,.83),185,1.04,(.86,.94,1))
    light("Main bedroom daylight",(2.5,8.32,2.12),(1.7,6.64,.80),290,1.55,(.88,.94,1))
    light("Main bedroom ceiling bounce",(3.42,6.92,2.58),(1.7,6.14,.82),105,1.30)
    return {
        "label":"2BR", "center":[3.7,4.05], "span":10.5,
        "checks":[{"label":"Island to cooktop counter","metres":round(stove_front-(bar_x+.245),2),
                   "zone":[bar_x+.245,bar_d-.50,stove_front,bar_d+.50]}],
        "views":[
            ("Entry",(6.20,2.26,1.62),(2.54,1.66,1.32)),
            ("Living",(4.87,2.37,1.60),(2.02,1.17,1.17)),
            ("Media wall",(4.92,2.38,1.62),(2.35,2.66,1.12)),
            ("Kitchen",(7.16,5.14,1.65),(7.15,3.91,1.00)),
            ("Island",(4.65,3.47,1.62),(7.02,4.20,1.18)),
            ("Bath access",(4.60,4.27,1.61),(5.51,4.99,1.13)),
            ("Bedroom 1",(3.82,7.91,1.61),(1.93,6.08,1.16)),
            ("Bedroom 2",(3.22,4.92,1.58),(1.28,3.55,1.09)),
            ("Balcony",(-.50,1.66,1.61),(2.14,1.36,1.2)),
        ],
        "routes":[[(6.20,2.26),(4.87,2.37),(4.36,2.55),(4.36,4.88),
                   (3.22,4.92)],[(4.36,4.88),(4.34,6.28),(4.12,6.87),(3.82,7.91)],
                  [(6.20,2.26),(6.14,2.93),(6.36,3.27),(7.20,3.27),(7.16,5.14)],
                  [(4.87,2.37),(3.62,2.40),(3.45,2.30),(3.17,2.30),(.76,2.27),(.51,1.69),(-.50,1.66)],
                  [(4.36,2.55),(4.36,4.28),(4.60,4.27),(5.53,4.40),(5.53,5.26)]],
    }


def layout_3br():
    schedule_slabs([
        (0,0,3,3,"spc"),(3,0,6,3,"spc"),(6,0,9.5,4.5,"spc"),
        (0,3,1.78,5,"tile"),(1.78,4,3.12,5,"tile"),(1.78,3,6,4,"granite"),
        (3.12,4,6,6.8,"granite"),(0,5,2.3,5.85,"tile"),(0,5.85,2.3,9,"granite"),(2.3,5,3.12,6.8,"granite"),
        (0,9,2.3,10.5,"granite"),(2.3,6.8,3.22,10.5,"granite"),
        (3.22,6.8,9.5,12.5,"granite"),(6,6.5,9.5,6.8,"granite"),
        (6,4.5,7.7,6.5,"spc"),(7.7,4.5,10.7,6.5,"tile"),(9.5,6.5,10.5,12.5,"deck"),
    ])
    for a,b in [
        ((0,0),(0,9)),((3,0),(3,3)),((6,0),(6,3.15)),((6,4.10),(6,6.5)),
        ((0,3),(1.92,3)),((2.84,3),(3.15,3)),((4.07,3),(6,3)),
        ((0,5),(3.12,5)),((1.78,3),(1.78,3.15)),((1.78,3.91),(1.78,4)),
        ((1.78,4),(3.12,4)),((3.12,4),(3.12,5)),
        ((0,5.85),(.75,5.85)),((1.44,5.85),(2.3,5.85)),((1.44,5),(1.44,5.85)),
        ((2.3,5),(2.3,8.14)),((2.3,8.94),(2.3,9.24)),((0,9),(2.3,9)),
        ((0,9),(0,10.5)),((0,10.5),(2.3,10.5)),((2.3,10.5),(3.22,10.5)),
        ((3.22,10.5),(3.22,12.5)),((3.22,12.5),(9.5,12.5)),
        ((9.5,0),(9.5,.64)),((9.5,4.05),(9.5,4.5)),((9.5,4.5),(10.7,4.5)),
        ((10.7,4.5),(10.7,6.5)),((6,6.5),(10.7,6.5)),((7.7,4.5),(9.5,4.5)),
        ((7.7,5.38),(7.7,6.5)),
    ]:
        wall(a,b)
    for a,b,s in [
        ((2.84,3),(1.92,3),(0,-1)),((3.15,3),(4.07,3),(0,-1)),
        ((6,3.15),(6,4.1),(1,0)),((1.78,3.15),(1.78,3.91),(-1,0)),
        ((7.7,4.5),(7.7,5.38),(1,0)),((.75,5.85),(1.44,5.85),(0,-1)),
        ((2.3,8.14),(2.3,8.94),(-1,0)),((2.3,10.35),(2.3,9.24),(-1,0)),
    ]:
        door(a,b,s)
    wall((2.3,10.35),(2.3,10.50))
    for left,right in [(0,3),(3,6),(6,9.5)]:
        wall((left,0),(left+.48,0))
        opening((left+.48,0),(right-.43,0))
        wall((right-.43,0),(right,0))
        curtain(left+.62,.125,.38)
        curtain(right-.54,.125,.38)
    opening((9.5,.64),(9.5,4.05))
    opening((9.5,6.5),(9.5,12.5),sill=0,panels=5,open_panel=3)
    balcony(10.5,6.5,12.5)
    wall((9.5,12.5),(10.5,12.5),.12,top=1.1)
    column(.30,.48,.37,.93)
    column(8.98,.29,.97,.48)
    column(.40,6.14,.66,.56)
    curtain(9.37,6.87,.62,"d")
    curtain(9.37,12.12,.53,"d")
    bed(1.23,1.38,1.04,length=1.91)
    pendant(1.86,.50,1.77,.082)
    wardrobe(.35,2.35,.91,"d",1)
    desk(2.28,.48,.93)
    bed(4.09,1.32,1.18,length=1.94)
    bedside(4.95,.57)
    wardrobe(5.65,1.32,1.05,"d",-1)
    desk(5.19,2.67,.91,-1)
    bed(7.77,1.67,1.63)
    for x in (6.66,8.89):
        bedside(x,.79)
    wardrobe(6.34,5.36,1.10,"d",1)
    desk(8.57,4.13,1.05,-1)
    art(8.52,4.421,1.36,.88,.57,flip=-1)
    bath_fixture(.36,3.62,"vanity")
    bath_fixture(.45,4.51,"wc")
    box("Existing shower tray",2.47,4.54,0,1.16,.84,.07,"Ceramic","Existing wet areas")
    bath_fixture(.43,5.36,"wc")
    bath_fixture(8.23,6.07,"vanity")
    bath_fixture(9.19,5.92,"wc")
    bath_fixture(10.14,5.51,"tub")
    box("Existing service appliance",.39,8.22,0,.57,.59,.86,"Ceramic","Existing wet areas")
    stove_front=kitchen(2.68,5.10,7.11,1,5.45,6.35)
    refrigerator(1.85,6.48,-1)
    dining(4.86,7.43)
    sofa(6.58,9.63,2.58,1)
    rug(6.59,10.97,3.51,2.75)
    coffee(6.59,10.79,.56)
    media_wall(6.54,12.27,2.97)
    lounge_cove((3.40,12.398),(9.34,12.398))
    lounge_cove((9.39,6.68),(9.39,12.30))
    plant(8.83,11.98,1)
    furniture("armchair","Woven cane lounge chair",8.35,11.14,.68,.60,.81,math.radians(66))
    box("Fitted foyer console",3.394,11.14,.57,.226,.85,.277,"Walnut veneer",bevel=.01)
    box("Foyer console stone top",3.399,11.14,.847,.241,.878,.027,"Travertine",bevel=.006)
    panel(3.509,11.14,.61,.73,.186,"Espresso oak",axis="d")
    box("Foyer console pull",3.524,11.14,.78,.024,.127,.015,"Brushed brass",bevel=.004)
    box("Foyer mirror brass frame",3.294,11.14,1.02,.036,.655,.887,"Brushed brass","Upper walls",.016)
    box("Foyer mirror",3.318,11.14,1.045,.019,.605,.837,"Brushed stainless","Upper walls",.011)
    bounds("Fitted foyer console",3.28,10.701,3.536,11.579)
    # The living/dining partition starts at x=6.0. Mount the complete frame
    # on its room-side face (depth 6.56) with no unsupported overhang.
    art(7.48,6.579,1.36,1.16,.64,name="3BR living artwork • flush wall mount")
    for x,d in [(4.2,6.0),(3.53,7.62),(6.42,7.37),(7.3,9.08),(5.54,11.0),
                (8.21,10.24),(1.52,1.46),(4.32,1.62),(7.88,2.55),(6.94,4.63)]:
        downlight(x,d)
    light("Balcony soft daylight",(9.95,9.68,2.18),(6.21,9.43,.80),690,3.2,(.82,.91,1))
    light("Living ceiling bounce",(6.42,10.83,2.58),(6.74,10.79,.4),165,1.85)
    light("Kitchen ceiling bounce",(3.69,6.25,2.57),(3.04,6.13,.8),180,1.44)
    light("Dining soft fill",(5.48,7.42,2.61),(4.86,7.5,.9),135,1.2)
    for x,d in [(1.58,1.55),(4.43,1.55),(7.84,1.65)]:
        light("Bedroom window daylight",(x,.18,2.17),(x,d,.8),225,1.45,(.85,.94,1))
    light("Main bedroom side window",(9.33,2.16,2.19),(7.73,2,.8),225,1.8,(.85,.94,1))
    return {
        "label":"3BR", "center":[5.1,6.2], "span":13.6,
        "checks":[{"label":"Kitchen run to dining table",
                   "metres":round(4.075-stove_front,2),
                   "zone":[stove_front,7.11,4.075,7.84]}],
        "views":[
            ("Entry",(1.66,9.72,1.61),(5.73,9.60,1.25)),
            ("Living",(9.10,11.55,1.63),(6.28,9.78,1.06)),
            ("Media wall",(8.83,10.10,1.62),(6.46,12.19,1.13)),
            ("Dining",(6.22,8.65,1.64),(6.47,6.98,1.16)),
            ("Kitchen",(3.65,7.48,1.63),(2.72,5.61,1.17)),
            ("Bedroom 1",(8.88,3.16,1.61),(7.55,.82,1.16)),
            ("Bedroom 2",(4.44,2.72,1.60),(4.02,.72,1.12)),
            ("Bedroom 3",(2.37,2.53,1.60),(1.16,.88,1.12)),
            ("Balcony",(10.04,10.44,1.61),(7.44,10.85,1.14)),
        ],
        "routes":[[(1.66,9.72),(3.35,9.71),(3.55,8.62),(3.65,7.48),(3.61,5.65),
                   (3.66,3.55),(3.65,2.72),(4.44,2.72)],
                  [(3.66,3.55),(2.42,3.55),(2.37,2.53)],
                  [(3.66,3.55),(6.65,3.67),(7.24,3.45),(8.15,3.13),(8.88,3.16)],
                  [(3.55,8.62),(6.66,8.72),(6.67,7.19)],
                  [(6.66,8.72),(8.85,8.79),(8.85,10.09),(9.18,10.64),(10.04,10.44)],
                  [(9.18,10.64),(9.10,11.55)]],
    }


def camera(name, loc, target, lens=26, ortho=None):
    data=bpy.data.cameras.new(name)
    obj=bpy.data.objects.new(name,data)
    collections["Cameras"].objects.link(obj)
    obj.location=xyz(*loc)
    aim(obj,target)
    data.lens=lens
    if ortho:
        data.type="ORTHO"
        data.ortho_scale=ortho
    return obj


def export_web(path):
    # Join per collection/material for small WebGL draw counts while the .blend retains parts.
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    batches={}
    for name in GROUPS:
        for obj in list(collections[name].objects):
            if obj.type!="MESH":
                continue
            mat=obj.data.materials[0]
            evaluated=obj.evaluated_get(depsgraph)
            mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=depsgraph)
            mesh.transform(obj.matrix_world)
            temp=bpy.data.objects.new(obj.name,mesh)
            bpy.context.scene.collection.objects.link(temp)
            batches.setdefault((name,mat.name),[]).append(temp)
    export_groups={}
    for (name,mat),objects in batches.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        first=objects[0]
        bpy.context.view_layer.objects.active=first
        if len(objects)>1:
            bpy.ops.object.join()
        if name not in export_groups:
            parent=bpy.data.objects.new(name.replace(" ","_"),None)
            bpy.context.scene.collection.objects.link(parent)
            export_groups[name]=parent
        first.parent=export_groups[name]
        first.name=mat
    bpy.ops.object.select_all(action="DESELECT")
    for parent in export_groups.values():
        parent.select_set(True)
        for obj in parent.children:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,
                              export_yup=True,export_apply=False,export_cameras=False,export_lights=False,
                              export_meshopt_compression_enable=True,export_image_format="JPEG",
                              export_image_quality=87)


def run(unit,builder):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collections.clear()
    solids.clear()
    floors.clear()
    MAT.clear()
    FURNITURE.clear()
    for name in (*GROUPS,"Cameras"):
        collection=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name]=collection
    palette()
    data=builder()
    data.update({"floors":floors,"solids":solids})
    data["lights"]=[
        {"position":[obj.location.x,obj.location.z,-obj.location.y],
         "kind":"window" if "daylight" in obj.name.lower() else "interior",
         "power":round(obj.data.energy/24,2)}
        for obj in collections["Interior lighting"].objects
    ]
    scene=bpy.context.scene
    scene.name="Veranda • "+data["label"]
    scene.unit_settings.system="METRIC"
    scene["Drawing basis"]="UNIT "+data["label"]+" PDF datums. Traced openings, assumed 2.7 m ceiling and concept furniture."
    scene["Existing wet areas"]="Context only. No proposed changes."
    scene["Kitchen clearance"]="; ".join(f'{c["label"]}: {c["metres"]:.2f} m' for c in data["checks"])
    cameras={name:camera(name,loc,target) for name,loc,target in data["views"]}
    x,d=data["center"]
    camera("Full apartment • roof hidden for plan review",(x+9,d+9,12),(x,d,.3),ortho=data["span"])
    scene.camera=cameras["Living"]
    scene.world=bpy.data.worlds.new("Soft resort daylight")
    scene.world.use_nodes=True
    world=scene.world.node_tree
    environment=world.nodes.new("ShaderNodeTexEnvironment")
    environment.image=bpy.data.images.load(str(WEB/"studio-garden.hdr"),check_existing=True)
    environment.image.pack()
    background=world.nodes.get("Background")
    world.links.new(environment.outputs["Color"],background.inputs["Color"])
    background.inputs["Strength"].default_value=.44
    scene.render.engine="CYCLES"
    scene.cycles.samples=36
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1280
    scene.render.resolution_y=800
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform="AgX"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective="CAMERA"
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/f"Veranda-{data['label']}.blend"),compress=True)
    export_web(WEB/f"{unit}.glb")
    (WEB/f"{unit}.json").write_text(json.dumps(data,separators=(",",":"))+"\n")
    print(f"VERIFIED EXPORT {unit} {len(solids)} collision envelopes",flush=True)


if __name__=="__main__":
    for unit,builder in (("2br",layout_2br),("3br",layout_3br)):
        if os.environ.get("VERANDA_UNIT",unit)==unit:
            run(unit,builder)
