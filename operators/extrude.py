import bpy
import bmesh
from bpy.props import FloatProperty, IntProperty, EnumProperty
from math import radians
from .. items import axis_vector_mappings, axis_items


class PunchItALittle(bpy.types.Operator):
    bl_idname = "machin3.punch_it_a_little"
    bl_label = "MACHIN3: Punch It (a little)"
    bl_description = "Manifold Extruding that works, somewhwat"
    bl_options = {'REGISTER', 'UNDO'}

    amount: FloatProperty(name="Amount", description="Extrusion Depth", default=0.1, min=0, precision=4, step=0.1)

    def execute(self, context):
        if self.amount:
            active = context.active_object

            bpy.ops.mesh.duplicate()

            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()

            original_verts = [v for v in bm.verts if v.select]
            original_faces = [f for f in bm.faces if f.select]
            # print(original_faces)

            geo = bmesh.ops.extrude_face_region(bm, geom=original_faces, use_normal_flip=False)
            extruded_verts = [v for v in geo['geom'] if isinstance(v, bmesh.types.BMVert)]

            # move out the original faces
            normal = original_faces[0].normal

            for v in original_verts:
                v.co += normal * self.amount

            # select te extruded verts then flush the selection to select the entire extruded part
            for v in extruded_verts:
                v.select_set(True)

            bm.select_flush(True)

            # from the selectino get all the faces of the extuded part (incl. the side faces)
            all_faces = [f for f in bm.faces if f.select]

            # then recalc the normals in preparatino for the boolean
            bmesh.ops.recalc_face_normals(bm, faces=all_faces)

            bmesh.update_edit_mesh(active.data)

            bpy.ops.mesh.intersect_boolean(use_self=True)
        return {'FINISHED'}


class CursorSpin(bpy.types.Operator):
    bl_idname = "machin3.cursor_spin"
    bl_label = "MACHIN3: Cursor Spin"
    bl_description = "Cursor Spin"
    bl_options = {'REGISTER', 'UNDO'}

    angle: FloatProperty(name="Angle", default=45)
    steps: IntProperty(name="Steps", default=1, min=1)
    axis: EnumProperty(name="Axis", items=axis_items, default='Y')

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'angle')
        row.prop(self, 'steps')

        row = column.row(align=True)
        row.prop(self, 'axis', expand=True)

    def execute(self, context):
        cmx = context.scene.cursor.matrix

        bpy.ops.mesh.spin(angle=radians(-self.angle), steps=self.steps, center=cmx.to_translation(), axis=cmx.to_quaternion() @ axis_vector_mappings[self.axis])
        return {'FINISHED'}
