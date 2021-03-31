import bpy
from bpy.props import BoolProperty
import bmesh
from math import degrees, radians


is_angle = 30
has_smoothed = None


class ToggleSmooth(bpy.types.Operator):
    bl_idname = "machin3.toggle_smooth"
    bl_label = "MACHIN3: Toggle Smooth"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'MESH'

    def execute(self, context):
        global is_angle, has_smoothed


        active = context.active_object
        subd = [mod for mod in active.modifiers if mod.type == 'SUBSURF']

        if subd:
            print("SubD Workflow")


        else:
            # print("Korean Bevel Workflow")
            angle, has_smoothed = self.toggle_korean_bevel(context, active, is_angle, has_smoothed)

            # store the current(pre-smooth) angle
            if angle is not None:
                is_angle = angle

        return {'FINISHED'}


    def toggle_korean_bevel(self, context, active, is_angle, has_smoothed):
        overlay = context.space_data.overlay

        # enabled auto_smooth if it isn't already
        if not active.data.use_auto_smooth:
            active.data.use_auto_smooth = True

        # get the currentl auto smooth angle
        angle = degrees(active.data.auto_smooth_angle)

        if active.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

        else:
            bm = bmesh.new()
            bm.from_mesh(active.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()


        # ENABLE

        if angle < 180:

            # change the auto-smooth angle
            active.data.auto_smooth_angle = radians(180)

            # enable face smoothing if necessary
            if not has_smoothed:
                face = bm.faces[0]

                if not face.smooth:
                    for f in bm.faces:
                        f.smooth = True

                    if active.mode == 'EDIT':
                        bmesh.update_edit_mesh(active.data)
                    else:
                        bm.to_mesh(active.data)
                        bm.free()

                    has_smoothed = True

            # disable overlays
            overlay.show_overlays = False

            return angle, has_smoothed


        # DISABLE

        else:
            # change the auto-smooth angle
            active.data.auto_smooth_angle = radians(is_angle)

            # disable face smoothing if it was enabled before
            if has_smoothed:
                for f in bm.faces:
                    f.smooth = False

                if active.mode == 'EDIT':
                    bmesh.update_edit_mesh(active.data)

                else:
                    bm.to_mesh(active.data)
                    bm.free()

                has_smoothed = False

            # re-enable overlays
            overlay.show_overlays = True

            return None, has_smoothed
