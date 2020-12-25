import bpy
from bl_ui.space_statusbar import STATUSBAR_HT_header as statusbar
from .. utils.raycast import cast_obj_ray_from_mouse, cast_bvh_ray_from_mouse


def draw_material_pick_status(self, context):
    layout = self.layout

    row = layout.row(align=True)
    row.label(text=f"Material Picker")

    row.label(text="", icon='MOUSE_LMB')
    row.label(text="Pick Material")

    row.label(text="", icon='MOUSE_RMB')
    row.label(text="Cancel")


class MaterialPicker(bpy.types.Operator):
    bl_idname = "machin3.material_picker"
    bl_label = "MACHIN3: Material Picker"
    bl_description = "Pick a Material from the 3D View"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE':
            mousepos = (event.mouse_region_x, event.mouse_region_y)

            if context.mode == 'OBJECT':
                hitobj, hitobj_eval, _, _, hitindex, _ = cast_obj_ray_from_mouse(mousepos, depsgraph=context.evaluated_depsgraph_get(), debug=False)

            elif context.mode == 'EDIT_MESH':
                hitobj, _, _, hitindex, _, _ = cast_bvh_ray_from_mouse(mousepos, candidates=[obj for obj in context.visible_objects if obj.mode == 'EDIT'])

            if hitobj:
                if context.mode == 'OBJECT':
                    matindex = hitobj_eval.data.polygons[hitindex].material_index
                elif context.mode == 'EDIT_MESH':
                    matindex = hitobj.data.polygons[hitindex].material_index

                context.view_layer.objects.active = hitobj
                hitobj.active_material_index = matindex

                if hitobj.material_slots and hitobj.material_slots[matindex].material:
                    mat = hitobj.material_slots[matindex].material

                    bpy.ops.machin3.draw_label(text=mat.name, coords=mousepos, alpha=1, time=0.5)

                else:
                    bpy.ops.machin3.draw_label(text="Empty", coords=mousepos, color=(0.5, 0.5, 0.5), alpha=1, time=0.7)

            else:
                bpy.ops.machin3.draw_label(text="None", coords=mousepos, color=(1, 0, 0), alpha=1, time=0.7)

            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        context.window.cursor_set("DEFAULT")

        statusbar.draw = self.bar_orig

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

    def invoke(self, context, event):

        # change mouse cursor
        context.window.cursor_set("EYEDROPPER")

        # draw statusbar info
        self.bar_orig = statusbar.draw
        statusbar.draw = draw_material_pick_status

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
