import bpy
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
import bmesh
from mathutils.bvhtree import BVHTree as BVH
import sys


# RAYCASTING BVH

def cast_bvh_ray_from_mouse(mousepos, candidates=None, bmeshes={}, bvhs={}, debug=False):
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

    cache = {'bmesh': {},
             'bvh': {}}

    for obj, src in objects:
        mx = obj.matrix_world
        mxi = mx.inverted_safe()

        ray_origin = mxi @ origin_3d
        ray_direction = mxi.to_3x3() @ vector_3d

        # use cached bmesh if possible
        if obj.name in bmeshes:
            # print("fetching existing bmesh")
            bm = bmeshes[obj.name]
        else:
            # print("creating new bmesh")
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            cache['bmesh'][obj.name] = bm

        # use cached bvh if possible
        if obj.name in bvhs:
            # print("fetching exsiting BVH")
            bvh = bvhs[obj.name]
        else:
            # print("creating new BVH")
            bvh = BVH.FromBMesh(bm)
            cache['bvh'][obj.name] = bvh

        location, normal, index, distance = bvh.ray_cast(ray_origin, ray_direction)

        # recalculate distance in worldspace
        if distance:
            distance = (mx @ location - origin_3d).length

        if debug:
            print("candidate:", obj.name, location, normal, index, distance)

        if distance and distance < hitdistance:
            hitobj, hitlocation, hitnormal, hitindex, hitdistance = obj, mx @ location, mx.to_3x3() @ normal, index, distance


    if debug:
        print("best hit:", hitobj.name if hitobj else None, hitlocation, hitnormal, hitindex, hitdistance if hitobj else None)
        print()

    if hitobj:
        return hitobj, hitlocation, hitnormal, hitindex, hitdistance, cache

    # the cache is always returned!
    return None, None, None, None, None, cache
