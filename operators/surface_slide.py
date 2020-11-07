import bpy
from .. utils.modifier import add_shrinkwrap


# TODO: add to context menu? only if modes pie is not active?


class SurfaceSlide(bpy.types.Operator):
    bl_idname = "machin3.surface_slide"
    bl_label = "MACHIN3: Surface Slide"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            return not [mod for mod in context.active_object.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

    def execute(self, context):
        active = context.active_object

        # create copy of active object to serve as surface
        surface = active.copy()
        surface.data = active.data.copy()
        surface.name = '%s_SURFACE' % (active.name)
        surface.data.name = '%s_SURFACE' % (active.data.name)
        surface.use_fake_user = True

        # add shrinkwrap mod
        shrinkwrap = add_shrinkwrap(active, surface)
        shrinkwrap.name = 'SurfaceSlide'

        # move it to the beginning of the stack
        if active.modifiers[0] != shrinkwrap:
            bpy.ops.object.modifier_move_to_index(modifier=shrinkwrap.name, index=0)

        return {'FINISHED'}


class FinishSurfaceSlide(bpy.types.Operator):
    bl_idname = "machin3.finish_surface_slide"
    bl_label = "MACHIN3: "
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return [mod for mod in context.active_object.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name]

    def execute(self, context):
        active = context.active_object

        # get shrinkwrap mod and target surface
        surfaceslide = self.get_surface_slide(active)
        surface = surfaceslide.target

        # remember if in edit mode
        editmode = context.mode == 'EDIT_MESH'

        # mods can only be applied in object mode, so switch to it if necessary
        if editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        # apply shrinkwrap mod
        bpy.ops.object.modifier_apply(modifier=surfaceslide.name)

        # go back into edit mode
        if editmode:
            bpy.ops.object.mode_set(mode='EDIT')

        # remove the target surface
        if surface:
            bpy.data.meshes.remove(surface.data, do_unlink=True)

        return {'FINISHED'}

    def get_surface_slide(self, obj):
        surfaceslide = obj.modifiers.get('SurfaceSlide')

        if not surfaceslide:
            surfaceslide = [mod for mod in obj.modifiers if mod.type == 'SHRINKWRAP' and 'SurfaceSlide' in mod.name][0]

        return surfaceslide
