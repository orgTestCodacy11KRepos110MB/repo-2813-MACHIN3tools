import bpy
from .. utils.registration import get_addon
from .. utils.append import append_collection


meshmachine = None
decalmachine = None


class AssembleCollection(bpy.types.Operator):
    bl_idname = "machin3.assemble_collection"
    bl_label = "MACHIN3: Assemle Collection"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'EMPTY' and active.instance_collection

    def execute(self, context):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object
        icol = active.instance_collection

        # linked collection instance
        if icol.library:
            # print(" linked collection instance")

            cols = [col for col in active.users_collection]
            offset = active.matrix_world.to_translation()

            filepath = icol.library.filepath
            colname = active.name

            # remove the icol, there's no need for it anymore
            bpy.data.collections.remove(icol)

            # and the instance ollection object as well
            bpy.data.objects.remove(active)

            # append the new collection
            acol = append_collection(filepath, colname)

            # get the collections's children and root children
            children = [obj for obj in acol.objects]
            root_children = [obj for obj in children if not obj.parent]

            # remove the appended collection, we don't need it
            bpy.data.collections.remove(acol)

            # link the children to all collections the instance collection was in
            for obj in children:
                for col in cols:
                    col.objects.link(obj)

            for obj in root_children:
                obj.select_set(True)
                context.view_layer.objects.active = obj

            # sort decals into collection
            if decalmachine:
                decals = [obj for obj in children if obj.DM.isdecal]

                if decals:
                    from DECALmachine.utils.collection import sort_into_collections

                    for obj in decals:
                        sort_into_collections(context, obj, purge=False)

            # run a purge, because somehow the library still referenecs linked datablocks here, this gets rid of them
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


        # assembled collection instance
        else:
            # print(" assembling appended collection instance")

            cols = [col for col in active.users_collection]
            offset = active.matrix_world.to_translation()

            # link collection referenced by the instance collection
            for col in cols:
                if icol.name not in col.children:
                    col.children.link(icol)

            # get the collections's children and root children
            children = [obj for obj in icol.objects]
            root_children = [obj for obj in children if not obj.parent]

            # remove instance collection object
            bpy.data.objects.remove(active)

            # remove the collection itself too
            bpy.data.collections.remove(icol)

            # link the children to all collections the instance collection was in
            for obj in children:
                for col in cols:
                    col.objects.link(obj)

            # offset the collection's root children and select them
            for obj in root_children:

                obj.matrix_basis.translation += offset

                obj.select_set(True)
                context.view_layer.objects.active = obj

            # sweep decal backups
            if decalmachine:
                decalbackup = [obj for obj in context.selected_objects if obj.DM.isbackup]

                for obj in decalbackup:
                    obj.use_fake_user = True

                    for col in obj.users_collection:
                        col.objects.unlink(obj)

                # sort decals into collection
                decals = [obj for obj in children if obj.DM.isdecal]

                if decals:
                    from DECALmachine.utils.collection import sort_into_collections

                    for obj in decals:
                        sort_into_collections(context, obj, purge=False)

            # sweep stashes
            if meshmachine:
                stashobjs = [obj for obj in context.selected_objects if obj.MM.isstashobj]

                for obj in stashobjs:
                    obj.use_fake_user = True

                    for col in obj.users_collection:
                        col.objects.unlink(obj)


        return {'FINISHED'}
