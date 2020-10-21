import bpy
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
import bmesh
from mathutils.bvhtree import BVHTree as BVH
import sys


# RAYCASTING BVH

def cast_bvh_ray_from_mouse(mousepos, candidates=None, debug=False):
    region = bpy.context.region
    region_data = bpy.context.region_data

    origin_3d = region_2d_to_origin_3d(region, region_data, mousepos)
    vector_3d = region_2d_to_vector_3d(region, region_data, mousepos)

    objects = [(obj, None) for obj in candidates if obj.type == "MESH"]

    hitobj = None
    hitlocation = None
    hitnormal = None
    hitindex = None
    hitdistance = sys.maxsize

    for obj, src in objects:
        mx = obj.matrix_world
        mxi = mx.inverted_safe()

        ray_origin = mxi @ origin_3d
        ray_direction = mxi.to_3x3() @ vector_3d

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        bvh = BVH.FromBMesh(bm)
        location, normal, index, distance = bvh.ray_cast(ray_origin, ray_direction)

        # recalculate distance in worldspace
        if distance:
            distance = (mx @ location - origin_3d).length

        bm.free()

        if debug:
            print("candidate:", obj.name, location, normal, index, distance)

        if distance and distance < hitdistance:
            hitobj, hitlocation, hitnormal, hitindex, hitdistance = obj, mx @ location, mx.to_3x3() @ normal, index, distance


    if debug:
        print("best hit:", hitobj.name if hitobj else None, hitlocation, hitnormal, hitindex, hitdistance if hitobj else None)
        print()

    if hitobj:
        return hitobj, hitlocation, hitnormal, hitindex, hitdistance

    return None, None, None, None, None
