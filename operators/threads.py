import bpy


class Threads(bpy.types.Operator):
    bl_idname = "machin3.add_threads"
    bl_label = "MACHIN3: Threads"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("threading")

        return {'FINISHED'}
