import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector
from .. utils.registration import get_addon, get_prefs
from .. utils.tools import get_active_tool
from .. utils.object import parent, unparent, get_eval_bbox
from .. utils.math import compare_matrix
from .. utils.mesh import get_coords
from .. utils.modifier import remove_mod
from .. utils.ui import get_zoom_factor, get_flick_direction, init_status, finish_status
from .. utils.draw import draw_vector, draw_circle, draw_point, draw_label, draw_bbox, draw_cross_3d
from .. utils.system import printd
from .. utils.property import step_list
from .. utils.view import get_loc_2d
from .. colors import red, green, blue, white, yellow
from .. items import axis_items, axis_index_mapping


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

        if not op.remove:
            row.label(text="", icon='EVENT_C')
            row.label(text=f"Cursor: {op.cursor}")

            if op.cursor and op.cursor_empty:
                row.separator(factor=1)

                row.label(text="", icon='EVENT_E')
                row.label(text=f"Use Existing: {op.use_existing_cursor}")


        if op.sel_mirror_mods:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_A')
            row.label(text=f"Remove All + Finish")

        if op.mirror_mods:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Remove Mirror: {op.remove}")

            if op.remove and op.misaligned:
                if not op.misaligned['isallmisaligned']:
                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_Q')
                    row.label(text="Togggle Mirror Object")

                row.separator(factor=1)

                row.label(text="", icon='MOUSE_MMB')
                row.label(text="Cycle Mirror Object")

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
    use_existing_cursor: BoolProperty(name="Use existing Cursor Empty", default=False)

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

        if self.meshes_present and len(context.selected_objects) == 1 and self.active in context.selected_objects:
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

            if self.remove and self.misaligned:
                name = 'Cursor Empty' if self.usemisalign and self.mirror_obj.type == 'EMPTY' else self.mirror_obj.name if self.usemisalign else 'None'
                alpha = 1 if self.usemisalign else 0.3
                color = blue if self.usemisalign and self.mirror_obj.type == 'EMPTY' else yellow if self.usemisalign else white

                # draw_label(context, title=f"misaligned: {name}", coords=(self.init_mouse[0], self.init_mouse[1] + self.flick_distance - (45 * self.scale)), center=True, color=color, alpha=alpha)
                draw_label(context, title=name, coords=(self.init_mouse[0], self.init_mouse[1] - self.flick_distance + (15 * self.scale)), center=True, color=color, alpha=alpha)

            elif not self.remove and self.cursor or len(self.sel) > 1:
                    title, color = ('New Cursor', green) if self.cursor and not self.use_existing_cursor else ('Existing Cursor', blue) if self.cursor else (self.active.name, yellow)
                    draw_label(context, title=title, coords=(self.init_mouse[0], self.init_mouse[1] - self.flick_distance + (15 * self.scale)), center=True, alpha=1, color=color)

            title = self.flick_direction.split('_')[1] if self.remove else self.flick_direction.replace('_', ' ').title()
            draw_label(context, title=title, coords=(self.init_mouse[0], self.init_mouse[1] - self.flick_distance), center=True, alpha=0.4)


        # draw chosen misaligned mirror obj (cant be drawn when passing through, as we cant update the cursor location then)
        if self.remove and self.misaligned and self.usemisalign:

            if self.mirror_obj.type == 'EMPTY':

                # when passing through, update 2d cursor here, as the modal isn't running then
                if self.passthrough:
                    self.mirror_obj_2d = get_loc_2d(context, self.mirror_obj.matrix_world.to_translation())

                draw_circle(self.mirror_obj_2d, size=10 * self.scale, width=2 * self.scale, color=blue, alpha=0.99)

    def draw_VIEW3D(self, context):
        for direction, axis, color in zip(self.axes.keys(), self.axes.values(), self.colors):
            positive = 'POSITIVE' in direction

            # draw_vector(axis * self.zoom / 2, origin=self.origin, color=color, width=2 if positive else 1, alpha=0.99 if positive else 0.3)
            width, alpha = (2, 0.99) if positive or self.remove else (1, 0.3)
            draw_vector(axis * self.zoom / 2, origin=self.init_mouse_3d, color=color, width=width, alpha=alpha)

        # draw axis highlight
        draw_point(self.init_mouse_3d + self.axes[self.flick_direction] * self.zoom / 2 * 1.2, size=5, alpha=0.8)

        # draw chosen misaligned mirror obj
        if self.remove and self.misaligned and self.usemisalign:
            mx = self.misaligned['matrices'][self.mirror_obj]

            if self.mirror_obj.type == 'MESH':
                bbox = get_eval_bbox(self.mirror_obj)
                draw_bbox(bbox, mx=mx, color=yellow, corners=0.1, width=2 * self.scale, alpha=0.5)

            elif self.mirror_obj.type == 'EMPTY':
                # get cursor's local space location haha
                loc = mx.inverted_safe() @ mx.to_translation()
                draw_cross_3d(loc, mx=mx, color=blue, width=2 * self.scale, length=2 * self.cursor_empty_zoom, alpha=0.99)

    def modal(self, context, event):
        context.area.tag_redraw()

        self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y, 0))

        events = ['MOUSEMOVE']

        if not self.remove:
            events.append('C')

            if self.cursor and self.cursor_empty:
                events.append('E')

        if self.mirror_mods:
            events.extend(['X', 'D', 'R'])

            if self.remove and self.misaligned:
                events.extend(['Q', 'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'ONE', 'TWO'])

        if self.sel_mirror_mods:
            events.append('A')

        if event.type in events:
            if self.passthrough:
                self.passthrough = False
                self.init_mouse = self.mousepos
                self.init_mouse_3d = region_2d_to_location_3d(context.region, context.region_data, self.init_mouse, self.origin)
                self.zoom = get_zoom_factor(context, depth_location=self.origin, scale=self.flick_distance, ignore_obj_scale=True)

                if self.mirror_obj and self.mirror_obj.type == 'EMPTY':
                    loc = self.mirror_obj.matrix_world.to_translation()
                    self.mirror_obj_2d = get_loc_2d(context, loc)

                    # self.cursor_empty_zoom = get_zoom_factor(context, depth_location=self.cmx.to_translation(), scale=10, ignore_obj_scale=True)
                    self.cursor_empty_zoom = get_zoom_factor(context, depth_location=loc, scale=10, ignore_obj_scale=True)


            # GET flick direction

            if event.type == 'MOUSEMOVE':

                self.flick_vector = self.mousepos - self.init_mouse
                # print(self.flick_vector.length)

                # get/set the best fitting direction
                if self.flick_vector.length:
                    self.flick_direction = get_flick_direction(context, self.init_mouse_3d, self.flick_vector, self.axes)
                    # print(self.flick_direction)

                    # get/set the direction used by the symmetrize op, which is oppositite of what you pick when flicking(sel.matched_direction)
                    self.set_mirror_props()

                if self.flick_vector.length > self.flick_distance:
                    self.finish()

                    self.execute(context)
                    return {'FINISHED'}


            # REMOVE mod + misaligned object selection

            elif event.type in {'C', 'E', 'A', 'X', 'D', 'R', 'Q', 'WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'ONE', 'TWO'} and event.value == 'PRESS':

                # TOGGLE remove mode

                if event.type in {'X', 'D', 'R'}:
                    self.remove = not self.remove
                    self.active.select_set(True)


                # TOGGLE cursor

                elif event.type == 'C':
                    self.cursor = not self.cursor
                    self.active.select_set(True)

                # TOGGLE use_cursor_cursor

                elif event.type == 'E':
                    self.use_existing_cursor = not self.use_existing_cursor
                    self.active.select_set(True)


                if self.misaligned:

                    # TOGGLE use misalignment (but only if not all mods are using misaligned objects, otherwise it will be forcibly enabled in invoke() already)

                    if not self.misaligned['isallmisaligned'] and event.type == 'Q' and event.value == 'PRESS':
                        self.usemisalign = not self.usemisalign
                        self.active.select_set(True)


                    # CYCLE misaligned object

                    if event.type in ['WHEELDOWNMOUSE', 'WHEELUPMOUSE', 'ONE', 'TWO'] and event.value == 'PRESS':
                        if self.usemisalign:
                            if event.type in ['WHEELDOWNMOUSE', 'ONE']:
                                self.mirror_obj = step_list(self.mirror_obj, self.misaligned['sorted_objects'], step=-1, loop=True)

                            elif event.type in ['WHEELUPMOUSE', 'tWO']:
                                self.mirror_obj = step_list(self.mirror_obj, self.misaligned['sorted_objects'], step=1, loop=True)
                        else:
                            self.usemisalign = True
                            self.active.select_set(True)


                # update HUD axes
                if self.remove and self.misaligned and self.usemisalign:
                    mo_mx = self.misaligned['matrices'][self.mirror_obj]
                    self.axes = self.get_axes(mo_mx)

                elif not self.remove and self.cursor:
                    self.axes = self.get_axes(self.cmx)

                else:
                    self.axes = self.get_axes(self.mx)

                if self.misaligned and self.mirror_obj.type == 'EMPTY':
                    loc = self.mirror_obj.matrix_world.to_translation()
                    self.mirror_obj_2d = get_loc_2d(context, loc)
                    self.cursor_empty_zoom = get_zoom_factor(context, depth_location=loc, scale=10, ignore_obj_scale=True)


                # FINISH REMOVE ALL (and on all selected objects)

                if event.type == 'A':
                    self.finish()

                    for mod in self.sel_mirror_mods:
                        obj = mod.id_data
                        remove_mod(mod.name, objtype=obj.type, context=context, object=obj)

                    return {'FINISHED'}


        # PASS THROUGH

        if event.type in {'MIDDLEMOUSE'} or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}) or event.type.startswith('NDOF'):
            self.passthrough = True
            return {'PASS_THROUGH'}


        elif event.type in {'LEFTMOUSE', 'SPACE'}:
                self.finish()

                self.execute(context)
                return {'FINISHED'}


        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish()

            # force statusbar update
            self.active.select_set(True)

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

        active_tool = get_active_tool(context).idname
        self.cursor = hypercursor and 'machin3.tool_hyper_cursor' in active_tool and hc and hc.show_gizmos

        self.active = context.active_object
        self.sel = context.selected_objects
        self.meshes_present = True if any([obj for obj in self.sel if obj.type == 'MESH']) else False
        self.decals_present = True if self.decalmachine and any([obj for obj in self.sel if obj.DM.isdecal]) else False

        if len(self.sel) > 1:
            self.bisect_x = self.bisect_y = self.bisect_z = False
            self.flip_x = self.flip_y = self.flip_z = False

        if self.flick:
            self.mx = self.active.matrix_world
            self.cmx = scene.cursor.matrix

            # initialize
            self.scale = context.preferences.view.ui_scale * get_prefs().HUD_scale
            self.flick_distance = get_prefs().mirror_flick_distance * self.scale

            self.mirror_obj = None
            self.mirror_mods = self.get_mirror_mods([self.active])
            self.sel_mirror_mods = self.get_mirror_mods(self.sel)
            self.cursor_empty = self.get_matching_cursor_empty(context)

            # always default to using an existing cursor empty, if present
            self.use_existing_cursor = True if self.cursor_empty else False

            # init mislalignment
            self.misaligned = self.get_misaligned_mods(context, self.active, self.mx, debug=False)
            # printd(self.misaligned)

            if self.misaligned:

                # if all mods use a misaligned mirror object
                self.usemisalign = self.misaligned['isallmisaligned']
                self.mirror_obj = self.misaligned['sorted_objects'][-1]

                if self.mirror_obj.type == 'EMPTY':
                    loc = self.mirror_obj.matrix_world.to_translation()
                    self.mirror_obj_2d = get_loc_2d(context, loc)
                    self.cursor_empty_zoom = get_zoom_factor(context, depth_location=loc, scale=10, ignore_obj_scale=True)

            # get self.origin, which is a point under the mouse and always ahead of the view in 3d space
            self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y, 0))

            view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
            view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)

            # self.origin = view_origin + view_dir * context.space_data.clip_start
            # turns out using the clip_start also has issues?, view_dir * 10 seems to work for all 3 clip start values
            self.origin = view_origin + view_dir * 10
            self.zoom = get_zoom_factor(context, depth_location=self.origin, scale=self.flick_distance, ignore_obj_scale=True)

            self.init_mouse = self.mousepos
            self.init_mouse_3d = region_2d_to_location_3d(context.region, context.region_data, self.init_mouse, self.origin)

            self.flick_vector = self.mousepos - self.init_mouse
            self.flick_direction = 'NEGATIVE_X'

            # get object axes in world space
            self.axes = self.get_axes(self.cmx if self.cursor else self.mx)

            # and the axes colors
            self.colors = [red, red, green, green, blue, blue]

            # statusbar
            init_status(self, context, func=draw_mirror(self))
            self.active.select_set(True)

            # handlers
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.mirror(context, self.active, self.sel)
            return {'FINISHED'}

    def execute(self, context):
        self.active = context.active_object
        self.sel = context.selected_objects

        if self.flick and self.remove:
            self.remove_mirror(self.active)

        else:
            self.mirror(context, self.active, self.sel)

        return {'FINISHED'}


    # MODAL

    def get_axes(self, mx):
        '''
        return axis dict based on passed in matrix
        '''

        axes = {'POSITIVE_X': mx.to_quaternion() @ Vector((1, 0, 0)),
                'NEGATIVE_X': mx.to_quaternion() @ Vector((-1, 0, 0)),
                'POSITIVE_Y': mx.to_quaternion() @ Vector((0, 1, 0)),
                'NEGATIVE_Y': mx.to_quaternion() @ Vector((0, -1, 0)),
                'POSITIVE_Z': mx.to_quaternion() @ Vector((0, 0, 1)),
                'NEGATIVE_Z': mx.to_quaternion() @ Vector((0, 0, -1))}

        return axes

    def get_matching_cursor_empty(self, context):
        '''
        find empties in the scene, that match the current cursor matrix
        '''

        scene = context.scene

        matching_empties = [obj for obj in scene.objects if obj.type == 'EMPTY' and compare_matrix(obj.matrix_world, self.cmx, precision=5)]

        if matching_empties:
            return matching_empties[0]

    def get_mirror_mods(self, objects):
        '''
        fetch mirror mods from passed in objects
        NOTE: treat grease pencil objects differently
        '''

        mods = []

        for obj in objects:
            if obj.type == 'GPENCIL':
                mods.extend([mod for mod in obj.grease_pencil_modifiers if mod.type == 'GP_MIRROR'])

            else:
                mods.extend([mod for mod in obj.modifiers if mod.type == 'MIRROR'])

        return mods


    # MIRROR

    def mirror(self, context, active, sel):
        '''
        mirror one or multiple objects, optionally across an cursor empty
        '''

        # create mirror empty
        if self.cursor:
            if self.cursor_empty and self.use_existing_cursor:
                # print("reusing existing empty")
                empty = self.cursor_empty

            else:
                # print("creating new empty")
                empty = bpy.data.objects.new(name=f"{active.name} Mirror", object_data=None)
                context.collection.objects.link(empty)
                empty.matrix_world = self.cmx

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


    # REMOVE MIRROR

    def remove_mirror(self, obj):
        '''
        remove the last mirror mod in that stack that matches the axis of the flick_direction
        '''

        axis = self.flick_direction.split('_')[1]

        if self.misaligned and self.usemisalign:
            if obj.type == 'GPENCIL':
                mods = [mod for mod in self.misaligned['object_mods'][self.mirror_obj] if getattr(mod, f'use_axis_{axis.lower()}')]
            else:
                mods = [mod for mod in self.misaligned['object_mods'][self.mirror_obj] if mod.use_axis[axis_index_mapping[axis]]]

        else:
            if obj.type == 'GPENCIL':
                mods = [mod for mod in obj.grease_pencil_modifiers if mod.type == 'GP_MIRROR' and getattr(mod, f'use_axis_{axis.lower()}')]
            else:
                mods = [mod for mod in obj.modifiers if mod.type == 'MIRROR' and mod.use_axis[axis_index_mapping[axis]]]

        if mods:
            remove_mod(mods[-1].name, objtype=obj.type)
            return True

    def get_misaligned_mods(self, context, active, mx, debug=False):
        '''
        get mirror mods with mirror_objs who are mis-aligned with the mirrored object
        '''

        object_mirror_mods = [mod for mod in self.mirror_mods if (mod.type == 'MIRROR' and mod.mirror_object) or (mod.type == 'GP_MIRROR' and mod.object)]

        if debug:
            print(object_mirror_mods)

        misaligned = {'sorted_mods': [],
                      'sorted_objects': [],
                      'object_mods': {},
                      'matrices': {},
                      'isallmisaligned': False}

        # check if mis-alinged
        for mod in object_mirror_mods:
            mirror_obj = mod.mirror_object if mod.type == 'MIRROR' else mod.object

            mo_mx = mirror_obj.matrix_world

            origin = mx.to_translation()

            # compare the x axes of the mirrored and mirror objects
            x = mx.to_3x3().normalized() @ Vector((1, 0, 0))
            mo_x = mo_mx.to_3x3().normalized() @ Vector((1, 0, 0))

            if debug:
                draw_vector(x * 1.1, origin=origin, color=yellow, modal=False)
                draw_vector(mo_x, origin=origin, color=blue, modal=False)
                context.area.tag_redraw()

            dot = round(x.dot(mo_x), 6)

            # if there is a misalignment, populate the dictionary
            if dot != 1:
                if debug:
                    print(mod.name, dot, "is mis-aligned")

                misaligned['sorted_mods'].append(mod)

                # collect the order of the objects in the stack
                if mirror_obj not in misaligned['sorted_objects']:
                    misaligned['sorted_objects'].append(mirror_obj)

                # and for each object, collect the mods using it
                if mirror_obj in misaligned['object_mods']:
                    misaligned['object_mods'][mirror_obj].append(mod)

                else:
                    misaligned['object_mods'][mirror_obj] = [mod]
                    misaligned['matrices'][mirror_obj] = mirror_obj.matrix_world

        # determine if all the mirror mods are misaligned, in that case the self.use_misalign will be enabled by default
        if len(self.mirror_mods) == len(misaligned['sorted_mods']):
            misaligned['isallmisaligned'] = True

        if debug:
            printd(misaligned)

        # only returned if the dict was actually populated
        if misaligned['sorted_mods']:
            return misaligned


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
