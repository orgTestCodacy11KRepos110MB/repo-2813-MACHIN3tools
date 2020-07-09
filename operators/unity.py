import bpy
from math import radians
from mathutils import Matrix
from .. utils.math import get_loc_matrix, get_rot_matrix, get_sca_matrix, flatten_matrix


class PrepareExport(bpy.types.Operator):
    bl_idname = "machin3.prepare_unity_export"
    bl_label = "MACHIN3: Prepare Unity Export"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not [obj for obj in context.visible_objects if obj.M3.unity_exported]

    @classmethod
    def description(cls, context, properties):
        if context.scene.M3.unity_export:
            return "Prepare and Export %s objects" % ("selected" if context.selected_objects else "visible")
        else:
            return "Prepare %s objects for Export to Unity" % ("selected" if context.selected_objects else "visible")

    def invoke(self, context, event):
        print("\nINFO: Preparing Unity Export")

        path = context.scene.M3.unity_export_path
        triangulate = context.scene.M3.unity_triangulate
        export = context.scene.M3.unity_export

        # force 'use_selection' mode, otherwise hidden, child objects will be exported too if nothing is selected
        if not context.selected_objects:
            for obj in context.visible_objects:
                obj.select_set(True)

        sel = context.selected_objects

        # collect all current world matrices
        matrices = {obj: obj.matrix_world.copy() for obj in sel}

        # get root objects
        roots = [obj for obj in sel if not obj.parent]

        # prepare object transformations and modifiers
        for obj in roots:
            self.prepare_for_export(obj, sel, matrices, triangulate=triangulate)

        # export
        if export:
            bpy.ops.export_scene.fbx('EXEC_DEFAULT' if path else 'INVOKE_DEFAULT', filepath=path, use_selection=True)

        return {'FINISHED'}

    def prepare_for_export(self, obj, sel, matrices, triangulate=False, depth=0, child=False):
        '''
        recursively rotate and scale an object and its children 90 degrees along world X and scale them down to 1/100
        for meshes, compensate by inverting the rotation and scaling 100x again
        also for meshes, store the original meshes for 2 reasons
        1. to easily restore the original mesh rotation
        2. to deal with instanced objects and also be able to restore themA
        deal with modifers affecting by the rotations/scaling too
        '''

        def prepare_object(obj, mx, depth, child):
            print("%sINFO: %sadjusting %s object's TRANSFORMATIONS: %s" % ('' if child else '\n', depth * '  ', 'child' if child else 'root', obj.name))
            obj.M3.unity_exported = True

            # get and store the current matrix
            mx = matrices[obj]
            obj.M3.pre_unity_export_mx = flatten_matrix(mx)

            loc, rot, sca = mx.decompose()

            # swivel y and z scale, scale down to 1/100th, and add 90 degree X rotation
            sca[1:3] = sca[2], sca[1]
            scale = get_sca_matrix(sca / 100)
            rotation = Matrix.Rotation(radians(90), 4, 'X')

            # rebuild world mx
            obj.matrix_world = get_loc_matrix(loc) @ get_rot_matrix(rot) @ rotation @ scale

        def prepare_modifiers(obj, triangulate, depth):
            '''
            prepare/add modifiers
            '''

            # DISPLACE MODS

            displace = [mod for mod in obj.modifiers if mod.type == 'DISPLACE' and mod.show_viewport]

            if displace:
                print("INFO: %sadjusting %s's DISPLACE modifiers" % (depth * '  ', obj.name))

                for mod in displace:
                    mod.strength *= 100


            # MIRROR MODS

            mirrors = [mod for mod in obj.modifiers if mod.type == 'MIRROR' and mod.show_viewport]

            if mirrors:
                print("INFO: %sadjusting %s's MIRROR modifiers" % (depth * '  ', obj.name))

                for mod in mirrors:
                    mod.use_axis[1:3] = mod.use_axis[2], mod.use_axis[1]
                    mod.use_bisect_axis[1:3] = mod.use_bisect_axis[2], mod.use_bisect_axis[1]
                    mod.use_bisect_flip_axis[1:3] = mod.use_bisect_flip_axis[2], mod.use_bisect_flip_axis[1]


            # BEVEL MODS

            bevels = [mod for mod in obj.modifiers if mod.type == 'BEVEL' and mod.show_viewport]

            if bevels:
                print("INFO: %sadjusting %s's BEVEL modifiers" % (depth * '  ', obj.name))

                for mod in bevels:
                    mod.width *= 100


            # TRIANGULATION MOD

            if triangulate and obj.type == 'MESH':
                print("INFO: %sadding %s's TRIANGULATE modifier" % (depth * '  ', obj.name))

                mod = obj.modifiers.new(name="Triangulate", type="TRIANGULATE")
                mod.keep_custom_normals = True
                mod.quad_method = 'FIXED'
                mod.show_expanded = False

        def prepare_empty(obj, depth):
            print("INFO: %sadjusting %s's EMPTY DISPLAY SIZE to compensate" % (depth * '  ', obj.name))
            obj.empty_display_size *= 100

        def prepare_mesh(obj, depth):
            '''
            apply the inverted transformation to the mesh to compensate for object transformation
            '''

            # store the original mesh and use a duplicate to be able to deal with instanced object
            obj.M3.pre_unity_export_mesh = obj.data
            obj.data = obj.data.copy()

            print("INFO: %sadjusting %s's MESH to compensate" % (depth * '  ', obj.name))
            rotation = Matrix.Rotation(radians(-90), 4, 'X')
            scale = Matrix.Scale(100, 4)

            obj.data.transform(rotation @ scale)
            obj.data.update()


        if obj in sel:

            # OBJECT TRANSFORM

            prepare_object(obj, matrices[obj], depth, child)


            # MODIFIERS

            prepare_modifiers(obj, triangulate, depth)


            # OBJECT DATA

            if obj.type == 'EMPTY':
                prepare_empty(obj, depth)

            elif obj.type == 'MESH':
                prepare_mesh(obj, depth)


            # OBJECT CHILDREN

            if obj.children:
                depth += 1

                for child in obj.children:
                    if child in sel:
                        self.prepare_for_export(child, sel, matrices, triangulate=triangulate, depth=depth, child=True)


class RestoreExport(bpy.types.Operator):
    bl_idname = "machin3.restore_unity_export"
    bl_label = "MACHIN3: Restore Unity Export"
    bl_description = "Restore Pre-Export Object Transformations, Meshes and Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return [obj for obj in context.visible_objects if obj.M3.unity_exported]

    def execute(self, context):
        print("\nINFO: Restoring Pre-Unity-Export Status")

        detriangulate = context.scene.M3.unity_triangulate

        exported = [obj for obj in context.visible_objects if obj.M3.unity_exported]
        meshes = []

        # get root objects
        roots = [obj for obj in exported if not obj.parent]

        # restore objects, meshesand modifiers
        for obj in roots:
            self.restore_exported(obj, exported, meshes, detriangulate=detriangulate)

        # remove the unique meshes
        bpy.data.batch_remove(meshes)

        return {'FINISHED'}

    def restore_exported(self, obj, exported, meshes, detriangulate=True, depth=0, child=False):
        '''
        recursively restore an the original transformation and mesh of an exported object and its children
        '''

        def restore_object(obj, depth, child):
            print("INFO: %srestoring %s object's TRANSFORMATIONS: %s" % (depth * '  ', 'child' if child else 'root', obj.name))

            obj.matrix_world = obj.M3.pre_unity_export_mx
            obj.M3.pre_unity_export_mx = flatten_matrix(Matrix())
            obj.M3.unity_exported = False

        def restore_modifiers(obj, detriangulate, depth):
            '''
            restore/remove modifiers
            '''

            # DISPLACE MODS

            displace = [mod for mod in obj.modifiers if mod.type == 'DISPLACE' and mod.show_viewport]

            if displace:
                print("INFO: %srestoring %s's DISPLACE modifiers" % (depth * '  ', obj.name))

                for mod in displace:
                    mod.strength /= 100


            # MIRROR MODS

            mirrors = [mod for mod in obj.modifiers if mod.type == 'MIRROR' and mod.show_viewport]

            if mirrors:
                print("INFO: %srestoring %s's mirror modifiers" % (depth * '  ', obj.name))

                for mod in mirrors:
                    mod.use_axis[1:3] = mod.use_axis[2], mod.use_axis[1]
                    mod.use_bisect_axis[1:3] = mod.use_bisect_axis[2], mod.use_bisect_axis[1]
                    mod.use_bisect_flip_axis[1:3] = mod.use_bisect_flip_axis[2], mod.use_bisect_flip_axis[1]


            # BEVEL MODS

            bevels = [mod for mod in obj.modifiers if mod.type == 'BEVEL' and mod.show_viewport]

            if bevels:
                print("INFO: %srestoring %s's BEVEL modifiers" % (depth * '  ', obj.name))

                for mod in bevels:
                    mod.width /= 100


            # TRIANGULATION MOD

            if detriangulate:
                lastmod = obj.modifiers[-1] if obj.modifiers else None

                if lastmod and lastmod.type == 'TRIANGULATE':
                    print("INFO: %sremoving %s's TRIANGULATE modifier" % (depth * '  ', obj.name))
                    obj.modifiers.remove(lastmod)

        def restore_empty(obj, depth):
            print("INFO: %srestoring %s's original EMPTY DISPLAY SIZE" % (depth * '  ', obj.name))
            obj.empty_display_size /= 100

        def restore_mesh(obj, depth):
            print("INFO: %srestoring %s's original pre-export MESH" % (depth * '  ', obj.name))
            meshes.append(obj.data)

            obj.data = obj.M3.pre_unity_export_mesh
            obj.M3.pre_unity_export_mesh = None


        if obj in exported:

            # OBJECT TRANSFORM

            restore_object(obj, depth, child)


            # MODIFIERS

            restore_modifiers(obj, detriangulate, depth)


            # OBJECT DATA

            if obj.type == 'EMPTY':
                restore_empty(obj, depth)

            elif obj.type == 'MESH' and obj.M3.pre_unity_export_mesh:
                restore_mesh(obj, depth)


            # OBJECT CHILDREN

            if obj.children:
                depth += 1

                for child in obj.children:
                    if child in exported:
                        self.restore_exported(child, exported, meshes, detriangulate=detriangulate, depth=depth, child=True)
