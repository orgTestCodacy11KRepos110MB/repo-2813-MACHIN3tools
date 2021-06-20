import bpy
from bpy.props import StringProperty
from .. utils.system import abspath, open_folder
from .. utils.property import step_list


class Open(bpy.types.Operator):
    bl_idname = "machin3.filebrowser_open"
    bl_label = "MACHIN3: Open in System's filebrowser"
    bl_description = "Open the current location in the System's own filebrowser"

    path: StringProperty(name="Path")

    @classmethod
    def poll(cls, context):
        return context.area.type == 'FILE_BROWSER'

    def execute(self, context):
        params = context.space_data.params

        directory = abspath(params.directory.decode())

        open_folder(directory)

        return {'FINISHED'}


class Toggle(bpy.types.Operator):
    bl_idname = "machin3.filebrowser_toggle"
    bl_label = "MACHIN3: Toggle Filebrowser"
    bl_description = ""

    type: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.area.type == 'FILE_BROWSER'

    def execute(self, context):

        if self.type == 'DISPLAY_TYPE':
            if context.space_data.params.display_type == 'LIST_VERTICAL':
                context.space_data.params.display_type = 'THUMBNAIL'

            else:
                context.space_data.params.display_type = 'LIST_VERTICAL'

        elif self.type == 'SORT':
            if context.space_data.params.sort_method == 'FILE_SORT_ALPHA':
                context.space_data.params.sort_method = 'FILE_SORT_TIME'

            else:
                context.space_data.params.sort_method = 'FILE_SORT_ALPHA'

        elif self.type == 'HIDDEN':
            context.space_data.params.show_hidden = not context.space_data.params.show_hidden

        return {'FINISHED'}


class CycleThumbs(bpy.types.Operator):
    bl_idname = "machin3.filebrowser_cycle_thumbnail_size"
    bl_label = "MACHIN3: Cycle Thumbnail Size"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'FILE_BROWSER' and context.space_data.params.display_type == 'THUMBNAIL'

    def execute(self, context):
        sizes = ['TINY', 'SMALL', 'NORMAL', 'LARGE']
        size = bpy.context.space_data.params.display_size
        bpy.context.space_data.params.display_size = step_list(size, sizes, 1, loop=True)

        return {'FINISHED'}
