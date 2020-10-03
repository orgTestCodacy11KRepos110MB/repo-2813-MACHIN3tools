import bpy
import bmesh
from ... utils.object import parent, unparent
from ... utils.math import get_loc_matrix, get_rot_matrix, get_sca_matrix, create_rotation_matrix_from_vertex, create_rotation_matrix_from_edge, get_center_between_verts, create_rotation_matrix_from_face
from ... utils.ui import popup_message


# TODO: update decal backup matrices


class OriginToActive(bpy.types.Operator):
    bl_idname = "machin3.origin_to_active"
    bl_label = "MACHIN3: Origin to Active"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        if context.mode == 'OBJECT':
            return "Set Selected Objects' Origin to Active Object"
        elif context.mode == 'EDIT_MESH':
            return "Set Selected Objects' Origin to Active Vert/Edge/Face\nALT: only set Origin Location\nCTRL: only set Origin Rotation"

    @classmethod
    def poll(cls, context):
        active = context.active_object

        if active:
            if context.mode == 'OBJECT':
                return [obj for obj in context.selected_objects if obj != active and obj.type not in ['EMPTY', 'FONT']]

            elif context.mode == 'EDIT_MESH':
                bm = bmesh.from_edit_mesh(active.data)
                return [v for v in bm.verts if v.select]

    def invoke(self, context, event):
        active = context.active_object

        if context.mode == 'OBJECT':
            self.origin_to_object(context, context.active_object.matrix_world)

        elif context.mode == 'EDIT_MESH':
            if event.alt and event.ctrl:
                popup_message("Hold down ATL, CTRL or neither, not both!", title="Invalid Modifier Keys")
                return {'CANCELLED'}

            ret = self.origin_to_editmesh(active, only_location=event.alt, only_rotation=event.ctrl)

            if not ret:
                popup_message("Select a single Vert, Edge or Face!", title="Illegal Selection")
                return {'CANCELLED'}

        return {'FINISHED'}

    def origin_to_editmesh(self, active, only_location, only_rotation):
        mx = active.matrix_world

        children = self.unparent_children(active.children)

        bm = bmesh.from_edit_mesh(active.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        verts = [v for v in bm.verts if v.select]
        edges = [e for e in bm.edges if e.select]
        faces = [f for f in bm.faces if f.select]

        if len(verts) == 1:
            v = verts[0]

            # create vertex world matrix components
            if not only_rotation:
                loc = get_loc_matrix(mx @ v.co)

            if not only_location:
                rot = create_rotation_matrix_from_vertex(active, v)


        elif len(edges) == 1:
            e = edges[0]
            center = get_center_between_verts(*e.verts)

            # create edge world matrix components
            if not only_rotation:
                loc = get_loc_matrix(mx @ center)

            if not only_location:
                rot = create_rotation_matrix_from_edge(active, e)

        elif len(faces) == 1:
            f = faces[0]
            center = f.calc_center_bounds()

            # create face world matrix components
            if not only_rotation:
                loc = get_loc_matrix(mx @ center)

            if not only_location:
                rot = create_rotation_matrix_from_face(mx, f)

        else:
            return False

        # with alt pressed, ignore vert/edge/face rotation
        if only_location:
            rot = get_rot_matrix(mx.to_quaternion())

        # with ctrl pressed, ignore vert/edge/face location
        if only_rotation:
            loc = get_loc_matrix(mx.to_translation())

        sca = get_sca_matrix(mx.to_scale())
        selmx = loc @ rot @ sca

        # move the object and compensate on the meh level for it
        bmesh.ops.transform(bm, verts=bm.verts, matrix=selmx.inverted_safe() @ mx)
        active.matrix_world = selmx

        bmesh.update_edit_mesh(active.data)

        self.reparent_children(children, active)
        return True

    def origin_to_object(self, context, mx):
        sel = [obj for obj in context.selected_objects if obj != context.active_object and obj.type not in ['EMPTY', 'FONT']]

        for obj in sel:
            children = self.unparent_children(obj.children)

            obj.data.transform(mx.inverted_safe() @ obj.matrix_world)
            obj.matrix_world = mx

            if obj.type == 'MESH':
                obj.data.update()

            self.reparent_children(children, obj)

    def unparent_children(self, children):
        children = [o for o in children]

        for c in children:
            unparent(c)

        return children

    def reparent_children(self, children, obj):
        for c in children:
            parent(c, obj)
