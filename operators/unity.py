import bpy
from math import radians
from mathutils import Matrix
from .. utils.math import get_loc_matrix, get_rot_matrix, get_sca_matrix, flatten_matrix


class PrepareExport(bpy.types.Operator):
    bl_idname = "machin3.prepare_unity_export"
    bl_label = "MACHIN3: Prepare Unity Export"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not [obj for obj in context.visible_objects if obj.M3.unity_exported]

    def invoke(self, context, event):
        print("\nINFO: Preparing Unity Export")

        path = context.scene.M3.unity_export_path

        # force 'use_selection' mode, otherwise hidden, child objects will be exported too if nothing is selected
        if not context.selected_objects:
            for obj in context.visible_objects:
                obj.select_set(True)

        sel = context.selected_objects

        # collect all current world matrices and obj data blocks
        matrices = {obj: obj.matrix_world.copy() for obj in sel}

        # get root objects
        roots = [obj for obj in sel if not obj.parent]

        for obj in roots:
            self.prepare_for_export(obj, sel, matrices)

        if not event.alt:
            bpy.ops.export_scene.fbx('EXEC_DEFAULT' if path else 'INVOKE_DEFAULT', filepath=path, use_selection=True)

        return {'FINISHED'}

    def prepare_for_export(self, obj, sel, matrices, depth=0, child=False):
        '''
        recursively rotate and scale an object and its children 90 degrees along world X and scale them down to 1/100
        for meshes, compensate by invert the rotation and scaling 100x again
        also for meshes, store the original meshes for 2 reasons
        1. to easily restore the original mesh rotation
        2. to deal with instanced objects and also be able to restore them
        '''

        if obj in sel:
            print("INFO: %sadjusting %s object: %s" % (depth * '  ', 'child' if child else 'root', obj.name))
            obj.M3.unity_exported = True

            # get and store the current matrix
            mx = matrices[obj]
            obj.M3.pre_unity_export_mx = flatten_matrix(mx)

            loc, rot, sca = matrices[obj].decompose()
            rotation = Matrix.Rotation(radians(90), 4, 'X')
            scale = get_sca_matrix(sca / 100)

            obj.matrix_world = get_loc_matrix(loc) @ get_rot_matrix(rot) @ rotation @ scale

            if obj.type == 'EMPTY':
                print("INFO: %sadjusting %s's empty display size to compensate" % (depth * '  ', obj.name))
                obj.empty_display_size *= 100

            elif obj.type == 'MESH':

                # store the original meshes
                obj.M3.pre_unity_export_mesh = obj.data
                obj.data = obj.data.copy()

                print("INFO: %sadjusting %s's mesh to compensate" % (depth * '  ', obj.name))
                rotation = Matrix.Rotation(radians(-90), 4, 'X')
                scale = Matrix.Scale(100, 4)

                obj.data.transform(rotation @ scale)
                obj.data.update()

            if obj.children:
                depth += 1

                for child in obj.children:
                    if child in sel:
                        self.prepare_for_export(child, sel, matrices, depth, child=True)


class RestoreExport(bpy.types.Operator):
    bl_idname = "machin3.restore_unity_export"
    bl_label = "MACHIN3: Restore Unity Export"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return [obj for obj in context.visible_objects if obj.M3.unity_exported]

    def execute(self, context):
        print("\nINFO: Restoring Pre-Unity-Export Transformations")

        exported = [obj for obj in context.visible_objects if obj.M3.unity_exported]
        meshes = []

        # get root objects
        roots = [obj for obj in exported if not obj.parent]

        for obj in roots:
            self.restore_exported(obj, exported, meshes)


        # remove the unique meshes
        bpy.data.batch_remove(meshes)

        return {'FINISHED'}

    def restore_exported(self, obj, exported, meshes, depth=0, child=False):
        '''
        recursively restore an the original transformation and mesh of an exported object and its children
        '''

        if obj in exported:
            print("INFO: %srestoring %s object's transformation: %s" % (depth * '  ', 'child' if child else 'root', obj.name))

            obj.matrix_world = obj.M3.pre_unity_export_mx
            obj.M3.pre_unity_export_mx = flatten_matrix(Matrix())
            obj.M3.unity_exported = False

            if obj.type == 'EMPTY':
                print("INFO: %srestoring %s's original empty display size" % (depth * '  ', obj.name))
                obj.empty_display_size /= 100

            elif obj.type == 'MESH' and obj.M3.pre_unity_export_mesh:
                print("INFO: %srestoring %s's original pre-export mesh" % (depth * '  ', obj.name))
                meshes.append(obj.data)

                obj.data = obj.M3.pre_unity_export_mesh
                obj.M3.pre_unity_export_mesh = None

            if obj.children:
                depth += 1

                for child in obj.children:
                    if child in exported:
                        self.restore_exported(child, exported, meshes, depth, child=True)
