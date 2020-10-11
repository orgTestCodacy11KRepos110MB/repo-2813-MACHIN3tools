import bpy
import bmesh
from ... utils.object import parent, unparent
from ... utils.math import get_loc_matrix, get_rot_matrix, get_sca_matrix, create_rotation_matrix_from_vertex, create_rotation_matrix_from_edge, get_center_between_verts, create_rotation_matrix_from_face
from ... utils.math import average_locations, flatten_matrix
from ... utils.ui import popup_message
from ... utils.registration import get_addon


decalmachine = None
meshmachine = None


class OriginToActive(bpy.types.Operator):
    bl_idname = "machin3.origin_to_active"
    bl_label = "MACHIN3: Origin to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        if context.mode == 'OBJECT':
            return "Set Selected Objects' Origin to Active Object\nALT: only set Origin Location\nCTRL: only set Origin Rotation"
        elif context.mode == 'EDIT_MESH':
            return "Set Selected Objects' Origin to Active Vert/Edge/Face\nALT: only set Origin Location\nCTRL: only set Origin Rotation"

    @classmethod
    def poll(cls, context):
        active = context.active_object

        if active:
            if context.mode == 'OBJECT':
                return [obj for obj in context.selected_objects if obj != active and obj.type not in ['EMPTY', 'FONT']]

            elif context.mode == 'EDIT_MESH' and tuple(context.scene.tool_settings.mesh_select_mode) in [(True, False, False), (False, True, False), (False, False, True)]:
                bm = bmesh.from_edit_mesh(active.data)
                return [v for v in bm.verts if v.select]

    def invoke(self, context, event):
        if event.alt and event.ctrl:
            popup_message("Hold down ATL, CTRL or neither, not both!", title="Invalid Modifier Keys")
            return {'CANCELLED'}

        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object

        if context.mode == 'OBJECT':
            self.origin_to_active_object(context, only_location=event.alt, only_rotation=event.ctrl, decalmachine=decalmachine, meshmachine=meshmachine)

        elif context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.ed.undo_push(message="Flush Edit Mode Changes")
            bpy.ops.object.mode_set(mode='EDIT')

            self.origin_to_editmesh(active, only_location=event.alt, only_rotation=event.ctrl, decalmachine=decalmachine, meshmachine=meshmachine)

        return {'FINISHED'}

    def origin_to_editmesh(self, active, only_location, only_rotation, decalmachine, meshmachine):
        mx = active.matrix_world.copy()

        # unparent all the children before changing the origin
        children = self.unparent_children(active.children)

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        if tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (True, False, False):
            verts = [v for v in bm.verts if v.select]
            co = average_locations([v.co for v in verts])

            # create vertex world matrix components
            if not only_rotation:
                loc = get_loc_matrix(mx @ co)

            if not only_location:
                v = bm.select_history[-1] if bm.select_history else verts[0]
                rot = create_rotation_matrix_from_vertex(active, v)

        elif tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, True, False):
            edges = [e for e in bm.edges if e.select]
            center = average_locations([get_center_between_verts(*e.verts) for e in edges])

            # create edge world matrix components
            if not only_rotation:
                loc = get_loc_matrix(mx @ center)

            if not only_location:
                e = bm.select_history[-1] if bm.select_history else edges[0]
                rot = create_rotation_matrix_from_edge(active, e)

        elif tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, False, True):
            faces = [f for f in bm.faces if f.select]
            center = average_locations([f.calc_center_median_weighted() for f in faces])

            # create face world matrix components
            if not only_rotation:
                loc = get_loc_matrix(mx @ center)

            if not only_location:
                f = bm.faces.active if bm.faces.active and bm.faces.active in faces else faces[0]
                rot = create_rotation_matrix_from_face(mx, f)

        # with alt pressed, ignore vert/edge/face rotation
        if only_location:
            rot = get_rot_matrix(mx.to_quaternion())

        # with ctrl pressed, ignore vert/edge/face location
        if only_rotation:
            loc = get_loc_matrix(mx.to_translation())

        sca = get_sca_matrix(mx.to_scale())
        selmx = loc @ rot @ sca

        # active's mx expresed in selmx's local space, this is the "difference matrix" representing the origin change
        deltamx = selmx.inverted_safe() @ active.matrix_world

        # move the object and compensate on the meh level for it
        bmesh.ops.transform(bm, verts=bm.verts, matrix=deltamx)
        active.matrix_world = selmx

        bmesh.update_edit_mesh(active.data)

        # reparent children
        self.reparent_children(children, active)

        # update the backupmx to compensate for the change in parent object origin
        if decalmachine:
            for child in children:
                # update decal origin and decal backup's backupmx, but only for projected/sliced decals!
                if child.DM.isdecal and child.DM.decalbackup:
                    child.data.transform(deltamx)
                    child.matrix_world = mx
                    child.data.update()

                    # update the decal backup's backupmx
                    if child.DM.decalbackup:
                        backup = child.DM.decalbackup
                        backup.DM.backupmx = flatten_matrix(deltamx @ backup.DM.backupmx)

        # adjust stashes and stash matrices
        if meshmachine:

            # the following originally immitated stash retrieval and then re-creation, it just chained both events together. this could then be simplifed further and further. setting stash.obj.matrix_world is optional
            for stash in active.MM.stashes:

                # stashmx in stashtargetmx's local space, aka the stash difference matrix(which is all that's actually needed for stashes, just like for decal backups)
                stashdeltamx = stash.obj.MM.stashtargetmx.inverted() @ stash.obj.MM.stashmx

                stash.obj.data.transform(deltamx)
                stash.obj.matrix_world = selmx

                stash.obj.MM.stashmx = flatten_matrix(mx @ stashdeltamx)
                stash.obj.MM.stashtargetmx = flatten_matrix(selmx)

    def origin_to_active_object(self, context, only_location, only_rotation, decalmachine, meshmachine):
        sel = [obj for obj in context.selected_objects if obj != context.active_object and obj.type not in ['EMPTY', 'FONT']]

        aloc, arot, asca = context.active_object.matrix_world.decompose()

        for obj in sel:

            # unparent all the children before changing the origin
            children = self.unparent_children(obj.children)

            # pre-origin adjusted object matrix
            omx = obj.matrix_world.copy()
            oloc, orot, osca = omx.decompose()

            if only_location:
                mx = get_loc_matrix(aloc) @ get_rot_matrix(orot) @ get_sca_matrix(osca)

            elif only_rotation:
                mx = get_loc_matrix(oloc) @ get_rot_matrix(arot) @ get_sca_matrix(osca)

            else:
                mx = context.active_object.matrix_world

            # obj mx expressed in active object's local space, this is the "difference matrix" representing the orignn change
            deltamx = mx.inverted_safe() @ obj.matrix_world

            obj.data.transform(deltamx)
            obj.matrix_world = mx

            if obj.type == 'MESH':
                obj.data.update()

            # reparent children
            self.reparent_children(children, obj)

            # the decal origin needs to be chanegd too and the backupmx needs to be compensated for the change in parent object origin
            if decalmachine and children:
                for child in children:

                    # update decal origin and decal backup's backupmx, but only for projected/sliced decals!
                    if child.DM.isdecal and child.DM.decalbackup:
                        child.data.transform(deltamx)
                        child.matrix_world = mx
                        child.data.update()

                        # update the decal backup's backupmx
                        if child.DM.decalbackup:
                            backup = child.DM.decalbackup
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


    def unparent_children(self, children):
        children = [o for o in children]

        for c in children:
            unparent(c)

        return children

    def reparent_children(self, children, obj):
        for c in children:
            parent(c, obj)
