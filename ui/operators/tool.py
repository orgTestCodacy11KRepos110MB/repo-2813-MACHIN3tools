import bpy
from bpy.props import StringProperty, FloatProperty
from ... utils.tools import get_tools_from_context, get_tool_options, get_active_tool
from ... utils.registration import get_addon_prefs, get_addon, get_prefs
from ... items import tool_name_mapping_dict
from ... colors import white


class SetToolByName(bpy.types.Operator):
    bl_idname = "machin3.set_tool_by_name"
    bl_label = "MACHIN3: Set Tool by Name"
    bl_description = "Set Tool by Name"
    bl_options = {'INTERNAL'}

    name: StringProperty(name="Tool name/ID")
    alpha: FloatProperty(name="Alpha", default=0.5, min=0.1, max=1)

    def execute(self, context):

        # re-enable the cursor if switching away from the simple hyper cursor
        active_tool = get_active_tool(context)

        if active_tool == 'machin3.tool_hyper_cursor_simple':
            context.space_data.overlay.show_cursor = True

        # switch to the passed in tool
        bpy.ops.wm.tool_set_by_id(name=self.name)

        # draw a prettified version of the new tool in a fading HUD
        name = self.prettify(self.name)

        coords = (context.region.width / 2, 100)
        bpy.ops.machin3.draw_label(text=name, coords=coords, color=white, time=get_prefs().tools_HUD_fade)

        return {'RUNNING_MODAL'}

    def prettify(self, name):
        if name in tool_name_mapping_dict:
            return tool_name_mapping_dict[name]
        return name


boxcutter = None


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
        global boxcutter

        if boxcutter is None:
            _, boxcutter, _, _ = get_addon("BoxCutter")

        return boxcutter in get_tools_from_context(context)

    def execute(self, context):
        global boxcutter

        if boxcutter is None:
            _, boxcutter, _, _ = get_addon("BoxCutter")

        tools = get_tools_from_context(context)
        bcprefs = get_addon_prefs('BoxCutter')

        # ensure the BC tool is active
        if not tools[boxcutter]['active']:
            bpy.ops.wm.tool_set_by_id(name=boxcutter)

        options = get_tool_options(context, boxcutter, 'bc.shape_draw')

        if options:
            options.mode = self.mode
            options.shape_type = self.shape_type

            bcprefs.behavior.set_origin = self.set_origin
            bcprefs.snap.enable = True

        return {'FINISHED'}
