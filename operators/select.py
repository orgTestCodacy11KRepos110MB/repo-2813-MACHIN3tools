import bpy
import bmesh
from bpy.props import EnumProperty, BoolProperty, IntProperty
from mathutils import Vector
from .. utils.registration import get_addon


axis_items = [("0", "X", ""),
              ("1", "Y", ""),
              ("2", "Z", "")]


class SelectCenterObjects(bpy.types.Operator):
    bl_idname = "machin3.select_center_objects"
    bl_label = "MACHIN3: Select Center Objects"
    bl_description = "Selects Objects in the Center, objects, that have verts on both sides of the X, Y or Z axis."
    bl_options = {'REGISTER', 'UNDO'}

    axis: EnumProperty(name="Axis", items=axis_items, default="0")

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row()
        row.prop(self, "axis", expand=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        visible = [obj for obj in context.visible_objects if obj.type == "MESH"]

        if visible:

            bpy.ops.object.select_all(action='DESELECT')

            for obj in visible:
                mx = obj.matrix_world

                coords = [(mx @ Vector(co))[int(self.axis)] for co in obj.bound_box]

                if min(coords) < 0 and max(coords) > 0:
                    obj.select_set(True)

        return {'FINISHED'}


class SelectWireObjects(bpy.types.Operator):
    bl_idname = "machin3.select_wire_objects"
    bl_label = "MACHIN3: Select Wire Objects"
    bl_description = "Select Objects set to WIRE display type\nALT: Hide Objects\nCLTR: Include Empties"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.visible_objects if obj.display_type == 'WIRE' or obj.type == 'EMPTY']

    def invoke(self, context, event):
        bpy.ops.object.select_all(action='DESELECT')

        # fix objects without proper display_type
        for obj in context.visible_objects:
            if obj.display_type == '':
                obj.display_type = 'WIRE'


        # get all wire objects, optionally including empties
        if event.ctrl:
            objects = [obj for obj in context.visible_objects if obj.display_type == 'WIRE' or obj.type == 'EMPTY']
        else:
            objects = [obj for obj in context.visible_objects if obj.display_type == 'WIRE']

        for obj in objects:
            if event.alt:
                obj.hide_set(True)
            else:
                obj.select_set(True)

        return {'FINISHED'}


class SelectLoop(bpy.types.Operator):
    bl_idname = "machin3.select_loop"
    bl_label = "MACHIN3: Select Loop"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    loop: BoolProperty(name="Loop Select", default=False)
    min_angle: IntProperty(name="Min Angle", default=120)

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row(align=True)
        row.prop(self, "loop", text="Loop Select" if self.loop else "Sharp Select", toggle=True)

        r = row.row(align=True)
        r.active = self.loop
        r.prop(self, 'min_angle')

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        self.loop = False

        self.select_type = self.get_meshmachine_select(context)

        if self.select_type:
            if self.select_type == 'LOOP':
                self.loop = True
                bpy.ops.machin3.lselect(min_angle=self.min_angle)
            elif self.select_type == 'SHARP':
                bpy.ops.machin3.sselect()
            return {'FINISHED'}

        else:
            return {'PASS_THROUGH'}

    def execute(self, context):
        if self.select_type:

            # force loop select, so the user can't toggle from loop to sharp, if the selected edge isn't sharp
            if self.select_type == 'LOOP' and not self.loop:
                self.loop = True

            if self.loop:
                bpy.ops.machin3.lselect(min_angle=self.min_angle)
            else:
                bpy.ops.machin3.sselect()
            return {'FINISHED'}

        else:
            return {'PASS_THROUGH'}

    def get_meshmachine_select(self, context):
        meshmachine = get_addon('MESHmachine')[0]

        if meshmachine:
            if tuple(context.scene.tool_settings.mesh_select_mode) == (False, True, False):
                bm = bmesh.from_edit_mesh(context.active_object.data)

                edges = [e for e in bm.edges if e.select]

                if len(edges) == 1:
                    return 'LOOP' if edges[0].smooth else 'SHARP'
