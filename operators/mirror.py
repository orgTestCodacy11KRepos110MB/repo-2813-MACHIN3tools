import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector
from .. utils.registration import get_addon
from .. utils.tools import get_active_tool
from .. utils.object import parent, unparent
from .. utils.ui import get_zoom_factor, get_flick_direction, init_status, finish_status
from .. utils.draw import draw_vector, draw_circle, draw_point, draw_label
from .. colors import red, green, blue, white
from .. items import axis_items


decalmachine = None
hypercursor = None


def draw_mirror(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Mirror')

        row.label(text="", icon='MOUSE_MOVE')
        row.label(text="Pick Axis")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_X')
        row.label(text=f"Mode: {'Remove' if op.remove else 'Mirror'}")

    return draw


class Mirror(bpy.types.Operator):
    bl_idname = "machin3.mirror"
    bl_label = "MACHIN3: Mirror"
    bl_options = {'REGISTER', 'UNDO'}

    # modal
    flick: BoolProperty(name="Flick", default=False)
    remove: BoolProperty(name="Remove", default=False)

    axis: EnumProperty(name="Axis", items=axis_items, default="X")
    # direction: EnumProperty(name="Direction", items=direction_items, default="POSITIVE")

    # mirror
    use_x: BoolProperty(name="X", default=True)
    use_y: BoolProperty(name="Y", default=False)
    use_z: BoolProperty(name="Z", default=False)

    bisect_x: BoolProperty(name="Bisect", default=False)
    bisect_y: BoolProperty(name="Bisect", default=False)
    bisect_z: BoolProperty(name="Bisect", default=False)

    flip_x: BoolProperty(name="Flip", default=False)
    flip_y: BoolProperty(name="Flip", default=False)
    flip_z: BoolProperty(name="Flip", default=False)

    # decalmachine
    DM_mirror_u: BoolProperty(name="U", default=True)
    DM_mirror_v: BoolProperty(name="V", default=False)

    # (hyper)cursor
    cursor: BoolProperty(name="Mirror across Cursor", default=False)

    # hidden
    passthrough = None

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        row = column.row(align=True)
        row.prop(self, 'cursor', toggle=True)

        row = column.row(align=True)
        row.prop(self, "use_x", toggle=True)
        row.prop(self, "use_y", toggle=True)
        row.prop(self, "use_z", toggle=True)

        if self.meshes_present and len(context.selected_objects) == 1 and context.active_object in context.selected_objects:
            row = column.row(align=True)
            r = row.row()
            r.active = self.use_x
            r.prop(self, "bisect_x")
            r = row.row()
            r.active = self.use_y
            r.prop(self, "bisect_y")
            r = row.row()
            r.active = self.use_z
            r.prop(self, "bisect_z")

            row = column.row(align=True)
            r = row.row()
            r.active = self.use_x
            r.prop(self, "flip_x")
            r = row.row()
            r.active = self.use_y
            r.prop(self, "flip_y")
            r = row.row()
            r.active = self.use_z
            r.prop(self, "flip_z")

        if self.decals_present:
            column.separator()

            column.label(text="DECALmachine - UVs")
            row = column.row(align=True)
            row.prop(self, "DM_mirror_u", toggle=True)
            row.prop(self, "DM_mirror_v", toggle=True)

    @classmethod
    def poll(cls, context):
        if context.mode == "OBJECT":
            return context.active_object

    def draw_HUD(self, context):
        if not self.passthrough:
            # draw_point(self.init_mouse, color=(1, 1, 1), size=4)
            # draw_point(self.mousepos, color=(0, 1, 0))

            draw_vector(self.flick_vector, origin=self.init_mouse, alpha=0.99)

            color = red if self.remove else white
            alpha = 0.2 if self.remove else 0.02
            draw_circle(self.init_mouse, size=self.flick_distance, width=3, color=color, alpha=alpha)

            title = 'Remove' if self.remove else 'Mirror'
            alpha = 1 if self.remove else 0.8
            draw_label(context, title=title, coords=(self.init_mouse[0], self.init_mouse[1] + self.flick_distance - (30 * self.scale)), center=True, color=color, alpha=alpha)

            draw_label(context, title=self.flick_direction.replace('_', ' ').title(), coords=(self.init_mouse[0], self.init_mouse[1] - self.flick_distance), center=True, alpha=0.4)

    def draw_VIEW3D(self, context):
        for direction, axis, color in zip(self.axes.keys(), self.axes.values(), self.colors):
            positive = 'POSITIVE' in direction

            # draw_vector(axis * self.zoom / 2, origin=self.origin, color=color, width=2 if positive else 1, alpha=0.99 if positive else 0.3)
            draw_vector(axis * self.zoom / 2, origin=self.init_mouse_3d, color=color, width=2 if positive else 1, alpha=0.99 if positive else 0.3)

        # draw axis highlight
        # draw_point(self.origin + self.axes[self.flick_direction] * self.zoom / 2 * 1.2, size=5, alpha=0.8)
        draw_point(self.init_mouse_3d + self.axes[self.flick_direction] * self.zoom / 2 * 1.2, size=5, alpha=0.8)

    def modal(self, context, event):
        context.area.tag_redraw()

        self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y, 0))

        events = ['MOUSEMOVE', 'X', 'D', 'R']

        if event.type in events:

            if self.passthrough:
                self.passthrough = False
                self.init_mouse = self.mousepos
                self.init_mouse_3d = region_2d_to_location_3d(context.region, context.region_data, self.init_mouse, self.origin)
                self.zoom = get_zoom_factor(context, depth_location=self.origin, scale=self.flick_distance)

            self.flick_vector = self.mousepos - self.init_mouse
            # print(self.flick_vector.length)

            # get/set the best fitting direction
            if self.flick_vector.length:
                self.flick_direction = get_flick_direction(self, context)
                # print(self.flick_direction)

                # get/set the direction used by the symmetrize op, which is oppositite of what you pick when flicking(sel.matched_direction)
                self.set_mirror_props()

            if self.flick_vector.length > self.flick_distance:
                self.finish()

                self.execute(context)
                return {'FINISHED'}

        if event.type in {'MIDDLEMOUSE'} or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}) or event.type.startswith('NDOF'):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in {'X', 'D', 'R'} and event.value == 'PRESS':
            self.remove = not self.remove
            context.active_object.select_set(True)

        elif event.type in {'LEFTMOUSE', 'SPACE'}:
                self.finish()

                self.execute(context)
                return {'FINISHED'}


        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            print("cancelling")

            self.finish()

            # force statusbar update
            context.active_object.select_set(True)

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

    def invoke(self, context, event):
        global decalmachine, hypercursor

        if decalmachine is None:
            decalmachine = get_addon("DECALmachine")[0]

        if hypercursor is None:
            hypercursor = get_addon("HyperCursor")[0]

        self.decalmachine = decalmachine

        scene = context.scene
        hc = scene.HC if hypercursor else None

        active = context.active_object

        active_tool = get_active_tool(context).idname
        self.cursor = hypercursor and 'machin3.tool_hyper_cursor' in active_tool and hc and hc.show_gizmos

        self.sel = context.selected_objects
        self.meshes_present = True if any([obj for obj in self.sel if obj.type == 'MESH']) else False
        self.decals_present = True if self.decalmachine and any([obj for obj in self.sel if obj.DM.isdecal]) else False

        if len(self.sel) > 1:
            self.bisect_x = self.bisect_y = self.bisect_z = False
            self.flip_x = self.flip_y = self.flip_z = False

        if self.flick:
            mx = active.matrix_world

            # initialize
            # self.scale = context.preferences.view.ui_scale * get_prefs().modal_hud_scale
            # self.flick_distance = get_prefs().symmetrize_flick_distance * self.scale
            self.scale = 1
            self.flick_distance = 75

            # get self.origin, which is a point under the mouse and always ahead of the view in 3d space
            self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y, 0))

            view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
            view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)

            # self.origin = view_origin + view_dir * context.space_data.clip_start
            # turns out using the clip_start also has issues?, view_dir * 10 seems to work for all 3 clip start values
            self.origin = view_origin + view_dir * 10

            self.zoom = get_zoom_factor(context, depth_location=self.origin, scale=self.flick_distance)

            self.init_mouse = self.mousepos
            self.init_mouse_3d = region_2d_to_location_3d(context.region, context.region_data, self.init_mouse, self.origin)

            self.flick_vector = self.mousepos - self.init_mouse
            self.flick_direction = 'NEGATIVE_X'

            # get object axes in world space
            self.axes = {'POSITIVE_X': mx.to_quaternion() @ Vector((1, 0, 0)),
                         'NEGATIVE_X': mx.to_quaternion() @ Vector((-1, 0, 0)),
                         'POSITIVE_Y': mx.to_quaternion() @ Vector((0, 1, 0)),
                         'NEGATIVE_Y': mx.to_quaternion() @ Vector((0, -1, 0)),
                         'POSITIVE_Z': mx.to_quaternion() @ Vector((0, 0, 1)),
                         'NEGATIVE_Z': mx.to_quaternion() @ Vector((0, 0, -1))}

            # and the axes colors
            self.colors = [red, red, green, green, blue, blue]

            # statusbar
            init_status(self, context, func=draw_mirror(self))
            context.active_object.select_set(True)

            # handlers
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.mirror(context, active, self.sel)
            return {'FINISHED'}

    def execute(self, context):
        active = context.active_object
        self.sel = context.selected_objects

        self.mirror(context, active, self.sel)

        return {'FINISHED'}

    def mirror(self, context, active, sel):
        '''
        mirror one or multiple objects, optionally across an cursor empty
        '''

        # create mirror empty
        if self.cursor:
            empty = bpy.data.objects.new(name=f"{active.name} Mirror", object_data=None)
            context.collection.objects.link(empty)
            empty.matrix_world = context.scene.cursor.matrix
            empty.show_in_front = True
            empty.empty_display_type = 'ARROWS'
            empty.empty_display_size = (context.scene.cursor.location - sel[0].matrix_world.to_translation()).length / 10
            empty.hide_set(True)

        if len(sel) == 1 and active in sel:
            if active.type in ["MESH", "CURVE"]:
                self.mirror_mesh_obj(context, active, mirror_object=empty if self.cursor else None)

            elif active.type == "GPENCIL":
                self.mirror_gpencil_obj(context, active, mirror_object=empty if self.cursor else None)

            elif active.type == "EMPTY" and active.instance_collection:
                self.mirror_instance_collection(context, active, mirror_object=empty if self.cursor else None)

        elif len(sel) > 1 and active in sel:

            # mirror across the active object, so remove it from the selection
            if not self.cursor:
                sel.remove(active)

            for obj in sel:
                if obj.type in ["MESH", "CURVE"]:
                    self.mirror_mesh_obj(context, obj, mirror_object=empty if self.cursor else active)

                elif obj.type == "GPENCIL":
                    self.mirror_gpencil_obj(context, obj, mirror_object=empty if self.cursor else active)

                elif obj.type == "EMPTY" and obj.instance_collection:
                    self.mirror_instance_collection(context, obj, mirror_object=empty if self.cursor else active)

    def mirror_mesh_obj(self, context, obj, mirror_object=None):
        mirror = obj.modifiers.new(name="Mirror", type="MIRROR")
        mirror.use_axis = (self.use_x, self.use_y, self.use_z)
        mirror.use_bisect_axis = (self.bisect_x, self.bisect_y, self.bisect_z)
        mirror.use_bisect_flip_axis = (self.flip_x, self.flip_y, self.flip_z)

        if mirror_object:
            mirror.mirror_object = mirror_object
            # parent(obj, mirror_object)

        if self.decalmachine:
            if obj.DM.isdecal:
                mirror.use_mirror_u = self.DM_mirror_u
                mirror.use_mirror_v = self.DM_mirror_v

                # move normal transfer mod to the end of the stack
                nrmtransfer = obj.modifiers.get("NormalTransfer")

                if nrmtransfer:
                    bpy.ops.object.modifier_move_to_index({'object': obj}, modifier=nrmtransfer.name, index=len(obj.modifiers) - 1)

    def mirror_gpencil_obj(self, context, obj, mirror_object=None):
        mirror = obj.grease_pencil_modifiers.new(name="Mirror", type="GP_MIRROR")
        mirror.use_axis_x = self.use_x
        mirror.use_axis_y = self.use_y
        mirror.use_axis_z = self.use_z

        if mirror_object:
            mirror.object = mirror_object
            # parent(obj, mirror_object)

    def mirror_instance_collection(self, context, obj, mirror_object=None):
        '''
        for instance collections, don't mirror the collection empty itself, even if it were possible
        instead create a new empty and mirror the collection objects themselves across the empty empty
        '''

        mirror_empty = bpy.data.objects.new("mirror_empty", object_data=None)

        col = obj.instance_collection

        if mirror_object:
            mirror_empty.matrix_world = mirror_object.matrix_world

        mirror_empty.matrix_world = obj.matrix_world.inverted_safe() @ mirror_empty.matrix_world

        col.objects.link(mirror_empty)

        meshes = [obj for obj in col.objects if obj.type == "MESH"]

        for obj in meshes:
            self.mirror_mesh_obj(context, obj, mirror_empty)

    def set_mirror_props(self):
        '''
        # NOTE: the direction Blender's symmetrize op expects, is inverted to what you choose in the 3d view when flicking
        # POSITIVE_X, means mirror positive x into the negative x, but when flicking we pick the direction we intend to symmetrize into
        '''

        # init
        self.use_x = self.use_y = self.use_z = False
        self.bisect_x = self.bisect_y = self.bisect_z = False
        self.flip_x = self.flip_y = self.flip_z = False

        # get direction and axis
        direction, axis = self.flick_direction.split('_')
        # print(direction, axis.lower())

        setattr(self, f'use_{axis.lower()}', True)

        if len(self.sel) == 1:
            setattr(self, f'bisect_{axis.lower()}', True)

        if direction == 'POSITIVE':
            setattr(self, f'flip_{axis.lower()}', True)


class Unmirror(bpy.types.Operator):
    bl_idname = "machin3.unmirror"
    bl_label = "MACHIN3: Unmirror"
    bl_description = "Removes the last modifer in the stack of the selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout

        column = layout.column()

    @classmethod
    def poll(cls, context):
        mirror_meshes = [obj for obj in context.selected_objects if obj.type == "MESH" and any(mod.type == "MIRROR" for mod in obj.modifiers)]
        if mirror_meshes:
            return True

        mirror_gpencils = [obj for obj in context.selected_objects if obj.type == "GPENCIL" and any(mod.type == "GP_MIRROR" for mod in obj.grease_pencil_modifiers)]
        if mirror_gpencils:
            return True

    def execute(self, context):
        targets = set()

        for obj in context.selected_objects:
            if obj.type in ["MESH", "CURVE"]:
                target = self.unmirror_mesh_obj(obj)

                if target and target.type == "EMPTY" and not target.children:
                    targets.add(target)

            elif obj.type == "GPENCIL":
                self.unmirror_gpencil_obj(obj)

            elif obj.type == "EMPTY" and obj.instance_collection:
                col = obj.instance_collection
                instance_col_targets = set()

                for obj in col.objects:
                    target = self.unmirror_mesh_obj(obj)

                    if target and target.type == "EMPTY":
                        instance_col_targets.add(target)

                if len(instance_col_targets) == 1:
                    bpy.data.objects.remove(list(targets)[0], do_unlink=True)

        if targets:

            # check if the targets are used in any other mirror mods, unfortunately obj.users is of no use here, so we need to check all objects in the file
            targets_in_use = {mod.mirror_object for obj in bpy.data.objects for mod in obj.modifiers if mod.type =='MIRROR' and mod.mirror_object and mod.mirror_object.type == 'EMPTY'}

            for target in targets:
                if target not in targets_in_use:
                    bpy.data.objects.remove(target, do_unlink=True)

        return {'FINISHED'}

    def unmirror_mesh_obj(self, obj):
        mirrors = [mod for mod in obj.modifiers if mod.type == "MIRROR"]

        if mirrors:
            target = mirrors[-1].mirror_object
            obj.modifiers.remove(mirrors[-1])

            return target

    def unmirror_gpencil_obj(self, obj):
        mirrors = [mod for mod in obj.grease_pencil_modifiers if mod.type == "GP_MIRROR"]

        if mirrors:
            obj.grease_pencil_modifiers.remove(mirrors[-1])
