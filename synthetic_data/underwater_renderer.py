import bpy
import random
import math
import os

# Output folder
OUTPUT_DIR = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\synthetic_data\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "labels"), exist_ok=True)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_underwater_world():
    world = bpy.context.scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    # Deep underwater blue-green color
    bg.inputs[0].default_value = (0.01, 0.05, 0.08, 1.0)
    bg.inputs[1].default_value = 0.3  # dim light

def add_pipeline():
    # Main pipeline cylinder
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.3,
        depth=6.0,
        location=(0, 0, 0),
        rotation=(0, math.pi/2, 0)
    )
    pipe = bpy.context.active_object
    pipe.name = "Pipeline"

    # Add blue-grey material
    mat = bpy.data.materials.new(name="PipeMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.3, 0.35, 0.4, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.8
    pipe.data.materials.append(mat)
    return pipe

def add_leakage():
    # Particle cloud to simulate leakage
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(random.uniform(-1,1), 0.35, random.uniform(-0.5,0.5)))
    leak = bpy.context.active_object
    leak.name = "Leakage"
    mat = bpy.data.materials.new(name="LeakMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.6, 0.8, 0.9, 1.0)
    bsdf.inputs['Alpha'].default_value = 0.5
    mat.blend_method = 'BLEND'
    leak.data.materials.append(mat)
    return leak

def add_pipe_coupling():
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.35,
        minor_radius=0.08,
        location=(random.uniform(-1.5, 1.5), 0, 0),
        rotation=(0, math.pi/2, 0)
    )
    coupling = bpy.context.active_object
    coupling.name = "PipeCoupling"
    mat = bpy.data.materials.new(name="CouplingMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.5, 0.4, 0.3, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.9
    coupling.data.materials.append(mat)
    return coupling

def add_camera():
    bpy.ops.object.camera_add(location=(0, -4, 0))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.pi/2, 0, 0)
    bpy.context.scene.camera = cam
    return cam

def add_lighting():
    # Dim underwater light
    bpy.ops.object.light_add(type='AREA', location=(0, -2, 2))
    light = bpy.context.active_object
    light.data.energy = 200
    light.data.color = (0.4, 0.7, 1.0)  # blue tint

def setup_render(width=640, height=640):
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32  # low samples = fast render

def get_bbox_yolo(obj, cam, scene):
    """Get YOLO format bounding box for object"""
    from bpy_extras.object_utils import world_to_camera_view
    render = scene.render
    res_x = render.resolution_x
    res_y = render.resolution_y

    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs = []
    ys = []
    for co in coords:
        co_2d = world_to_camera_view(scene, cam, co)
        xs.append(co_2d.x)
        ys.append(co_2d.y)

    min_x, max_x = max(0, min(xs)), min(1, max(xs))
    min_y, max_y = max(0, min(ys)), min(1, max(ys))

    cx = (min_x + max_x) / 2
    cy = 1 - (min_y + max_y) / 2
    w = max_x - min_x
    h = max_y - min_y

    if w <= 0 or h <= 0:
        return None
    return cx, cy, w, h

# Class mapping
CLASS_MAP = {"Pipeline": 0, "Leakage": 1, "PipeCoupling": 2}

def render_scene(index):
    scene = bpy.context.scene
    cam = scene.camera

    # Random camera angle
    cam.location.x = random.uniform(-1, 1)
    cam.location.z = random.uniform(-0.5, 0.5)
    cam.location.y = random.uniform(-5, -3)
    cam.rotation_euler = (
        math.pi/2 + random.uniform(-0.2, 0.2),
        random.uniform(-0.1, 0.1),
        random.uniform(-0.1, 0.1)
    )

    # Render image
    img_path = os.path.join(OUTPUT_DIR, "images", f"synthetic_{index:04d}.jpg")
    scene.render.filepath = img_path
    bpy.ops.render.render(write_still=True)

    # Generate YOLO labels
    label_path = os.path.join(OUTPUT_DIR, "labels", f"synthetic_{index:04d}.txt")
    with open(label_path, 'w') as f:
        for obj in bpy.context.scene.objects:
            if obj.name in CLASS_MAP and obj.type == 'MESH':
                bbox = get_bbox_yolo(obj, cam, scene)
                if bbox:
                    cx, cy, w, h = bbox
                    cls = CLASS_MAP[obj.name]
                    f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    print(f"Rendered {index+1}/10 → {img_path}")

# ===== MAIN =====
print("Starting NautiCAI Underwater Synthetic Data Generator...")
clear_scene()
setup_underwater_world()
setup_render()
add_lighting()
add_camera()
add_pipeline()
add_leakage()
add_pipe_coupling()

for i in range(10):  # Generate 10 images first as test
    render_scene(i)

print(f"Done! Images saved to {OUTPUT_DIR}")