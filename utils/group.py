import bpy
from mathutils import Vector
from . object import unparent
from . math import average_locations, get_loc_matrix


def ungroup(empty):
    for obj in empty.children:
        unparent(obj)
        obj.M3.is_group_object = False

    bpy.data.objects.remove(empty, do_unlink=True)


def get_group_matrix(context, location_type, objects):
    if location_type == 'AVERAGE':
        location = average_locations([obj.matrix_world.to_translation() for obj in objects])

    elif location_type == 'ACTIVE':
        if context.active_object:
            return context.active_object.matrix_world

        # fallback to average if no active object is present
        else:
            location = average_locations([obj.matrix_world.to_translation() for obj in objects])

    elif location_type == 'CURSOR':
        location = context.scene.cursor.location

    elif location_type == 'WORLD':
        location = Vector()

    return get_loc_matrix(location)


def select_group_children(empty, recursive=False):
    children = [c for c in empty.children if c.M3.is_group_object]

    for obj in children:
        obj.select_set(True)

        if obj.M3.is_group_empty and recursive:
            select_group_children(obj, recursive=True)
