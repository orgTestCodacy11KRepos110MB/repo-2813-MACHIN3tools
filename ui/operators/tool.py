import bpy
from bpy.props import StringProperty, FloatProperty
from ... utils.tools import get_tools_from_context, get_tool_options
from ... utils.registration import get_addon_prefs, get_addon, get_prefs
from ... utils.draw import draw_label
from ... items import tool_name_mapping_dict
from ... colors import white


class SetToolByName(bpy.types.Operator):
    bl_idname = "machin3.set_tool_by_name"
    bl_label = "MACHIN3: Set Tool by Name"
    bl_options = {'INTERNAL'}

    name: StringProperty(name="Tool name/ID")

    alpha: FloatProperty(name="Alpha", default=0.5, min=0.1, max=1)

    def draw_HUD(self, args):
        context = args[0]

        alpha = self.countdown / self.time * self.alpha
        draw_label(context, title=self.name, color=white, alpha=alpha)


    def modal(self, context, event):
        context.area.tag_redraw()

        # FINISH when countdown is 0

        if self.countdown < 0:
            # print("Countdown of %d seconds finished" % (self.time))

            # remove time handler
            context.window_manager.event_timer_remove(self.TIMER)

            # remove draw handler
            bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
            return {'FINISHED'}

        # COUNT DOWN

        if event.type == 'TIMER':
            self.countdown -= 0.1

        return {'PASS_THROUGH'}

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name=self.name)

        # draw handler
        args = (context, )
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (args, ), 'WINDOW', 'POST_PIXEL')

        # time handler
        self.TIMER = context.window_manager.event_timer_add(0.1, window=context.window)

        # initalize time from prefs
        self.time = self.countdown = get_prefs().tools_HUD_fade

        self.prettify(self.name)

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def prettify(self, name):
        if self.name in tool_name_mapping_dict:
            self.name = tool_name_mapping_dict[self.name]


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
