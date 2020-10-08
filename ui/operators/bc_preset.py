import bpy
from bpy.props import StringProperty
from ... utils.tools import get_tools_from_context, get_tool_options
from ... utils.registration import get_addon_prefs


class SetBCPreset(bpy.types.Operator):
    bl_idname = "machin3.set_boxcutter_preset"
    bl_label = "MACHIN3: Set BoxCutter Preset"
    bl_description = "Quickly enable/switch BC tool in/to various modes"
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty()
    shape_type: StringProperty()
    set_origin: StringProperty(default='MOUSE')

    @classmethod
    def poll(cls, context):
        return 'BC' in get_tools_from_context(context)

    def execute(self, context):
        tools = get_tools_from_context(context)
        bcprefs = get_addon_prefs('BoxCutter')

        # ensure the BC tool is active
        if not tools['BC']['active']:
            bpy.ops.wm.tool_set_by_id(name='BC')

        options = get_tool_options(context, 'BC', 'bc.shape_draw')

        if options:
            options.mode = self.mode
            options.shape_type = self.shape_type

            bcprefs.behavior.set_origin = self.set_origin
            bcprefs.snap.enable = True

        return {'FINISHED'}
