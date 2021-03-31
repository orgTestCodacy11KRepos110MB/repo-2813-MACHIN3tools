import bpy
from bpy.props import BoolProperty, StringProperty
import bmesh
from math import degrees, radians


class ToggleSmooth(bpy.types.Operator):
    bl_idname = "machin3.toggle_smooth"
    bl_label = "MACHIN3: Toggle Smooth"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    toggle_subd_overlays: BoolProperty(name="Toggle Overlays", default=False)
    toggle_korean_bevel_overlays: BoolProperty(name="Toggle Overlays", default=True)

    mode: StringProperty(name="Smooth Mode", default='SUBD')

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'MESH'

    def draw(self, context):
        layout = self.layout

        column = layout.column()
        row = column.split(factor=0.3)

        if self.mode == 'SUBD':
            row.label(text='SubD')
            row.prop(self, 'toggle_subd_overlays', toggle=True)
        else:
            row.label(text='Korean Bevel')
            row.prop(self, 'toggle_korean_bevel_overlays', toggle=True)

    def execute(self, context):
        global is_angle, has_smoothed

        active = context.active_object
        subds = [mod for mod in active.modifiers if mod.type == 'SUBSURF']

        if subds:
            # print("SubD Workflow")
            self.toggle_subd(context, active, subds)

        else:
            # print("Korean Bevel Workflow")
            self.toggle_korean_bevel(context, active)

        return {'FINISHED'}

    def toggle_subd(self, context, active, subds):
        self.mode = 'SUBD'

        if active.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

        else:
            bm = bmesh.new()
            bm.from_mesh(active.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

        overlay = context.space_data.overlay

        subd = subds[0]

        if not subd.show_on_cage:
            subd.show_on_cage = True


        # ENABLE

        if not (subd.show_in_editmode and subd.show_viewport):
            subd.show_in_editmode = True
            subd.show_viewport = True

            # enable face smoothing if necessary
            if not bm.faces[0].smooth:
                for f in bm.faces:
                    f.smooth = True

                if active.mode == 'EDIT':
                    bmesh.update_edit_mesh(active.data)
                else:
                    bm.to_mesh(active.data)
                    bm.free()

                active.M3.has_smoothed = True

            # disable overlays
            if self.toggle_subd_overlays:
                overlay.show_overlays = False


        # DISABLE

        else:
            subd.show_in_editmode = False
            subd.show_viewport = False

            # disable face smoothing if it was enabled before
            if active.M3.has_smoothed:
                for f in bm.faces:
                    f.smooth = False

                if active.mode == 'EDIT':
                    bmesh.update_edit_mesh(active.data)

                else:
                    bm.to_mesh(active.data)
                    bm.free()

                active.M3.has_smoothed = False

            # re-enable overlays
            overlay.show_overlays = True

    def toggle_korean_bevel(self, context, active):
        self.mode = 'KOREAN'

        overlay = context.space_data.overlay

        # enabled auto_smooth if it isn't already
        if not active.data.use_auto_smooth:
            active.data.use_auto_smooth = True

        # get the currentl auto smooth angle
        angle = active.data.auto_smooth_angle

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

        if degrees(angle) < 180:
            active.M3.smooth_angle = angle

            # change the auto-smooth angle
            active.data.auto_smooth_angle = radians(180)

            # enable face smoothing if necessary
            if not bm.faces[0].smooth:
                for f in bm.faces:
                    f.smooth = True

                if active.mode == 'EDIT':
                    bmesh.update_edit_mesh(active.data)
                else:
                    bm.to_mesh(active.data)
                    bm.free()

                active.M3.has_smoothed = True

            # disable overlays
            if self.toggle_korean_bevel_overlays:
                overlay.show_overlays = False


        # DISABLE

        else:

            # change the auto-smooth angle
            active.data.auto_smooth_angle = active.M3.smooth_angle

            # disable face smoothing if it was enabled before
            if active.M3.has_smoothed:
                for f in bm.faces:
                    f.smooth = False

                if active.mode == 'EDIT':
                    bmesh.update_edit_mesh(active.data)

                else:
                    bm.to_mesh(active.data)
                    bm.free()

                active.M3.has_smoothed = False

            # re-enable overlays
            overlay.show_overlays = True
