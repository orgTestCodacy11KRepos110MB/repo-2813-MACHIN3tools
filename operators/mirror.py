import bpy
from bpy.props import BoolProperty
from .. utils.registration import get_addon
from .. utils.tools import get_active_tool
from .. utils.object import parent, unparent


decalmachine = None
hypercursor = None


class Mirror(bpy.types.Operator):
    bl_idname = "machin3.mirror"
    bl_label = "MACHIN3: Mirror"
    bl_options = {'REGISTER', 'UNDO'}

    use_x: BoolProperty(name="X", default=True)
    use_y: BoolProperty(name="Y", default=False)
    use_z: BoolProperty(name="Z", default=False)

    bisect_x: BoolProperty(name="Bisect", default=False)
    bisect_y: BoolProperty(name="Bisect", default=False)
    bisect_z: BoolProperty(name="Bisect", default=False)

    flip_x: BoolProperty(name="Flip", default=False)
    flip_y: BoolProperty(name="Flip", default=False)
    flip_z: BoolProperty(name="Flip", default=False)

    DM_mirror_u: BoolProperty(name="U", default=True)
    DM_mirror_v: BoolProperty(name="V", default=False)

    cursor: BoolProperty(name="Mirror across Cursor", default=False)

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
        return context.mode == "OBJECT"

    def invoke(self, context, event):
        global decalmachine, hypercursor

        if decalmachine is None:
            decalmachine = get_addon("DECALmachine")[0]

        if hypercursor is None:
            hypercursor = get_addon("HyperCursor")[0]

        self.dm = decalmachine

        active = context.active_object
        # active_tool = get_active_tool(context).idname
        # self.cursor = hypercursor and 'machin3.tool_hyper_cursor' in active_tool

        self.sel = context.selected_objects
        self.meshes_present = True if any([obj for obj in self.sel if obj.type == 'MESH']) else False
        self.decals_present = True if self.dm and any([obj for obj in self.sel if obj.DM.isdecal]) else False

        if len(self.sel) > 1:
            self.bisect_x = self.bisect_y = self.bisect_z = False
            self.flip_x = self.flip_y = self.flip_z = False

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

        if self.dm:
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

        groups = [obj for obj in context.selected_objects if obj.type == "EMPTY" and obj.instance_collection]
        if groups:
            return [empty for empty in groups if any(obj for obj in empty.instance_collection.objects if any(mod.type == "MIRROR" for mod in obj.modifiers))]

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
