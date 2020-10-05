import bpy
from bpy.props import StringProperty, BoolProperty


class SetSnappingPreset(bpy.types.Operator):
    bl_idname = "machin3.set_snapping_preset"
    bl_label = "MACHIN3: Set Snapping Preset"
    bl_description = "Set Snapping Preset"
    bl_options = {'REGISTER', 'UNDO'}

    element: StringProperty(name="Snap Element")
    target: StringProperty(name="Snap Target")
    align_rotation: BoolProperty(name="Align Rotation")

    def draw(self, context):
        layout = self.layout
        column = layout.column()

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        context.scene.tool_settings.snap_elements = {self.element}
        context.scene.tool_settings.snap_target = self.target
        context.scene.tool_settings.use_snap_align_rotation = self.align_rotation

        return {'FINISHED'}
