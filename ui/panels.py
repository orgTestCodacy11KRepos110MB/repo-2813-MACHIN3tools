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
        return get_prefs().activate_smart_drive

    def draw(self, context):
        layout = self.layout

        m3 = context.scene.M3

        box = layout.box()
        box.label(text="Smart Drive")

        column = box.column()

        row = column.split(factor=0.25, align=True)
        row.label(text="Driver")
        row.prop(m3, 'driver_start', text='Start')
        row.prop(m3, 'driver_end', text='End')

        row = column.split(factor=0.25, align=True)
        row.label(text="Driven")
        row.prop(m3, 'driven_start', text='Start')
        row.prop(m3, 'driven_end', text='End')

        r = column.row()
        r.scale_y = 1.2
        r.operator("machin3.smart_drive", text='Drive it!')
