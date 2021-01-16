import bpy
from bpy.props import FloatProperty, IntProperty, EnumProperty
from math import radians
from .. items import axis_vector_mappings, axis_items


class CursorSpin(bpy.types.Operator):
    bl_idname = "machin3.cursor_spin"
    bl_label = "MACHIN3: Cursor Spin"
    bl_description = "Cursor Spin"
    bl_options = {'REGISTER', 'UNDO'}

    angle: FloatProperty(name="Angle", default=45)
    steps: IntProperty(name="Steps", default=4)
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
