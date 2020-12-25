import bpy
from .. utils.registration import get_prefs
from .. import bl_info


class PanelMACHIN3tools(bpy.types.Panel):
    bl_idname = "MACHIN3_PT_machin3_tools"
    bl_label = "MACHIN3tools %s" % ('.'.join([str(v) for v in bl_info['version']]))
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MACHIN3"
    bl_order = 20

    @classmethod
    def poll(cls, context):
        return get_prefs().activate_smart_drive or get_prefs().activate_unity

    def draw(self, context):
        layout = self.layout

        m3 = context.scene.M3

        if get_prefs().activate_smart_drive:
            box = layout.box()
            box.prop(m3, "show_smart_drive", text="Smart Drive", icon='TRIA_DOWN' if m3.show_smart_drive else 'TRIA_RIGHT', emboss=False)

            if m3.show_smart_drive:
                self.draw_smart_drive(m3, box)

        if get_prefs().activate_unity:
            box = layout.box()

            box.prop(m3, "show_unity", text="Unity", icon='TRIA_DOWN' if m3.show_unity else 'TRIA_RIGHT', emboss=False)

            if m3.show_unity:
                self.draw_unity(context, m3, box)

    def draw_smart_drive(self, m3, layout):
        column = layout.column()

        b = column.box()
        b.label(text="Driver")

        col = b.column(align=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Values")
        r = row.row(align=True)
        op = r.operator("machin3.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVER'
        op.value = 'START'
        r.prop(m3, 'driver_start', text='')
        r.operator("machin3.switch_driver_values", text='', icon='ARROW_LEFTRIGHT').mode = 'DRIVER'
        r.prop(m3, 'driver_end', text='')
        op = r.operator("machin3.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVER'
        op.value = 'END'

        row = col.split(factor=0.25, align=True)
        row.label(text="Transform")
        r = row.row(align=True)
        r.prop(m3, 'driver_transform', expand=True)

        row = col.split(factor=0.25, align=True)
        row.scale_y = 0.9
        row.label(text="Axis")
        r = row.row(align=True)
        r.prop(m3, 'driver_axis', expand=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Space")
        r = row.row(align=True)
        r.prop(m3, 'driver_space', expand=True)


        b = column.box()
        b.label(text="Driven")

        col = b.column(align=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Values")
        r = row.row(align=True)
        op = r.operator("machin3.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVEN'
        op.value = 'START'
        r.prop(m3, 'driven_start', text='')
        r.operator("machin3.switch_driver_values", text='', icon='ARROW_LEFTRIGHT').mode = 'DRIVEN'
        r.prop(m3, 'driven_end', text='')
        op = r.operator("machin3.set_driver_value", text='', icon='SORT_ASC')
        op.mode = 'DRIVEN'
        op.value = 'END'

        row = col.split(factor=0.25, align=True)
        row.label(text="Transform")
        r = row.row(align=True)
        r.prop(m3, 'driven_transform', expand=True)

        row = col.split(factor=0.25, align=True)
        row.scale_y = 0.9
        row.label(text="Axis")
        r = row.row(align=True)
        r.prop(m3, 'driven_axis', expand=True)

        row = col.split(factor=0.25, align=True)
        row.label(text="Limit")
        r = row.row(align=True)
        r.prop(m3, 'driven_limit', expand=True)

        r = column.row()
        r.scale_y = 1.2
        r.operator("machin3.smart_drive", text='Drive it!', icon='AUTO')

    def draw_unity(self, context, m3, layout):
        all_prepared = True if context.selected_objects and all([obj.M3.unity_exported for obj in context.selected_objects]) else False

        column = layout.column(align=True)

        row = column.split(factor=0.3)
        row.label(text="Export")
        row.prop(m3, 'unity_export', text='True' if m3.unity_export else 'False', toggle=True)

        row = column.split(factor=0.3)
        row.label(text="Triangulate")
        row.prop(m3, 'unity_triangulate', text='True' if m3.unity_triangulate else 'False', toggle=True)

        column.separator()

        if m3.unity_export:
            column.prop(m3, 'unity_export_path', text='')

            # straight export of already prepared objects
            if all_prepared:
                row = column.row(align=True)
                row.scale_y = 1.5

                if m3.unity_export_path:
                    row.operator_context = 'EXEC_DEFAULT'

                op = row.operator("export_scene.fbx", text='Export')
                op.use_selection = True
                op.apply_scale_options = 'FBX_SCALE_ALL'

                if m3.unity_export_path:
                    op.filepath = m3.unity_export_path

        if not m3.unity_export or not all_prepared:
            row = column.row(align=True)
            row.scale_y = 1.5
            row.operator("machin3.prepare_unity_export", text="Prepare + Export %s" % ('Selected' if context.selected_objects else 'Visible') if m3.unity_export else "Prepare %s" % ('Selected' if context.selected_objects else 'Visible')).prepare_only = False

        row = column.row(align=True)
        row.scale_y = 1.2
        row.operator("machin3.restore_unity_export", text="Restore Transformations")
