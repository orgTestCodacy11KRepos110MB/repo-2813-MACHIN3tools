import bpy
import bmesh
from mathutils import Matrix
from . math import flatten_matrix


def parent(obj, parentobj):
    if not parentobj.parent and parentobj.matrix_parent_inverse != Matrix():
        print("WARNING: Resetting %s's parent inverse matrix, as no parent is defined." % (parentobj.name))
        parentobj.matrix_parent_inverse = Matrix()

    p = parentobj
    while p.parent:
        p = p.parent

    obj.parent = parentobj
    obj.matrix_world = p.matrix_parent_inverse @ obj.matrix_world


def unparent(obj):
    if obj.parent:
        p = obj.parent
        while p.parent:
            p = p.parent

        obj.parent = None
        obj.matrix_world = p.matrix_parent_inverse.inverted_safe() @ obj.matrix_world


def unparent_children(obj):
    children = []

    for c in obj.children:
        unparent(c)
        children.append(c)

    return children


def compensate_children(obj, oldmx, newmx):
    '''
    compensate object's childen, for instance, if obj's world matrix is about to be changed and "affect parents only" is enabled
    '''

    # the delta matrix, aka the old mx expressed in the new one's local space
    deltamx = newmx.inverted_safe() @ oldmx
    children = [c for c in obj.children]

    for c in children:
        pmx = c.matrix_parent_inverse
        c.matrix_parent_inverse = deltamx @ pmx


def flatten(obj, depsgraph=None):
    if not depsgraph:
        depsgraph = bpy.context.evaluated_depsgraph_get()

    oldmesh = obj.data

    obj.data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.clear()

    # remove the old mesh
    bpy.data.meshes.remove(oldmesh, do_unlink=True)


def add_vgroup(obj, name="", ids=[], weight=1, debug=False):
    vgroup = obj.vertex_groups.new(name=name)

    if debug:
        print(" » Created new vertex group: %s" % (name))

    if ids:
        vgroup.add(ids, weight, "ADD")

    # from selection
    else:
        obj.vertex_groups.active_index = vgroup.index
        bpy.ops.object.vertex_group_assign()

    return vgroup


def add_facemap(obj, name="", ids=[]):
    fmap = obj.face_maps.new(name=name)

    if ids:
        fmap.add(ids)

    return fmap


def set_obj_origin(obj, mx, bm=None, decalmachine=False, meshmachine=False):
    '''
    change object origin to supplied matrix, support doing it in edit mode when bmesh is passed in
    also update decal backups and stashes if decalmachine or meshmachine are True
    '''

    # pre-origin adjusted object matrix
    omx = obj.matrix_world.copy()

    # get children and compensate for the parent transform
    children = [c for c in obj.children]
    compensate_children(obj, omx, mx)

    # object mx expressed in new mx's local space, this is the "difference matrix" representing the origin change
    deltamx = mx.inverted_safe() @ obj.matrix_world

    obj.matrix_world = mx

    if bm:
        bmesh.ops.transform(bm, verts=bm.verts, matrix=deltamx)
        bmesh.update_edit_mesh(obj.data)
    else:
        obj.data.transform(deltamx)

    if obj.type == 'MESH':
        obj.data.update()

    # the decal origin needs to be chanegd too and the backupmx needs to be compensated for the change in parent object origin
    if decalmachine and children:

        # decal backup's backup matrices, but only for projected/sliced decals!
        for c in [c for c in children if c.DM.isdecal and c.DM.decalbackup]:
            backup = c.DM.decalbackup
            backup.DM.backupmx = flatten_matrix(deltamx @ backup.DM.backupmx)

    # adjust stashes and stash matrices
    if meshmachine:

        # the following originally immitated stash retrieval and then re-creation, it just chained both events together. this could then be simplifed further and further. setting stash.obj.matrix_world is optional
        for stash in obj.MM.stashes:

            # stashmx in stashtargetmx's local space, aka the stash difference matrix(which is all that's actually needed for stashes, just like for decal backups)
            stashdeltamx = stash.obj.MM.stashtargetmx.inverted() @ stash.obj.MM.stashmx

            stash.obj.data.transform(deltamx)
            stash.obj.matrix_world = mx

            stash.obj.MM.stashmx = flatten_matrix(omx @ stashdeltamx)
            stash.obj.MM.stashtargetmx = flatten_matrix(mx)
