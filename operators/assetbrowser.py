import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty
from .. utils.registration import get_addon, get_prefs
from .. utils.append import append_collection
from .. utils.ui import popup_message


decalmachine = None
meshmachine = None

# TODO: options to hide slectino wires etc?


class CreateAssembly(bpy.types.Operator):
    bl_idname = "machin3.create_assembly"
    bl_label = "MACHIN3: Creaste Assembly Asset"
    bl_description = "Create Assembly Asset from the selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Asset Name")
    move: BoolProperty(name="Move instead of Copy", description="Move Objects into Asset Collection, instead of copying\nThis will unlink them from any existing collections", default=True)

    remove_decal_backups: BoolProperty(name="Remove Decal Backups", description="Remove DECALmachine's Decal Backups, if present", default=False)
    remove_stashes: BoolProperty(name="Remove Stashes", description="Remove MESHmachine's Stashes, if present", default=False)

    thumbnail_lens: FloatProperty(name="Thumbnail Lens", default=100)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and len(context.selected_objects) > 1

    def draw(self, context):
        global decalmachine, meshmachine

        layout = self.layout

        column = layout.column(align=True)
        column.prop(self, 'name')

        column.separator()
        column.prop(self, 'move', toggle=True)

        if decalmachine or meshmachine:
            row = column.row(align=True)

            if decalmachine:
                row.prop(self, 'remove_decal_backups', toggle=True)

            if meshmachine:
                row.prop(self, 'remove_stashes', toggle=True)

        column.prop(self, 'thumbnail_lens')

    # """
    def invoke(self, context, event):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        return context.window_manager.invoke_props_dialog(self)
    # """

    def execute(self, context):
        global decalmachine, meshmachine

        name = self.name.strip()
        # name = "Test"

        # decalmachine = True
        # self.remove_decal_backups = True

        # meshmachine = True
        # self.remove_stashes = True

        if name:
            print(f"INFO: Creation Assembly Asset: {name}")

            objects = context.selected_objects

            if decalmachine and self.remove_decal_backups:
                decals_with_backups = [obj for obj in objects if obj.DM.isdecal and obj.DM.decalbackup]

                for decal in decals_with_backups:
                    print(f"WARNING: Removing {decal.name}'s backup")

                    if decal.DM.decalbackup:
                        bpy.data.meshes.remove(decal.DM.decalbackup.data, do_unlink=True)

            if meshmachine and self.remove_stashes:
                objs_with_stashes = [obj for obj in objects if obj.MM.stashes]

                for obj in objs_with_stashes:
                    print(f"WARNING: Removing {obj.name}'s {len(obj.MM.stashes)} stashes")

                    for stash in obj.MM.stashes:
                        stashobj = stash.obj

                        if stashobj:
                            print(" *", stash.name, stashobj.name)
                            bpy.data.meshes.remove(stashobj.data, do_unlink=True)

                    obj.MM.stashes.clear()


            mcol = context.scene.collection
            acol = bpy.data.collections.new(name)

            mcol.children.link(acol)

            if self.move:
                for obj in objects:
                    for col in obj.users_collection:
                        col.objects.unlink(obj)

            for obj in objects:
                acol.objects.link(obj)

            instance = bpy.data.objects.new(name, object_data=None)
            instance.instance_collection = acol
            instance.instance_type = 'COLLECTION'

            mcol.objects.link(instance)
            instance.hide_set(True)
            instance.asset_mark()

            asset_browser_workspace = get_prefs().preferred_assetbrowser_workspace_name

            # switch to the preferred asset browser workspace,if one is defined in the addon preferences
            if asset_browser_workspace:
                ws = bpy.data.workspaces.get(asset_browser_workspace)

                if ws and ws != context.workspace:
                    print("INFO: Switching to preffered Asset Browser Workspace")
                    bpy.ops.machin3.switch_workspace('INVOKE_DEFAULT', name=asset_browser_workspace)

                    # then ensure is shows the LOCAL library
                    # note, this is done separately here, becasue the context.workspace isn't updating to the new workspac
                    self.switch_asset_browser_to_LOCAL(ws)

                    # render the viewport too
                    self.render_viewport(context)

                    return {'FINISHED'}

            # if an asset browser is present on the current workspace, ensure it's set to LOCAL
            ws = context.workspace
            self.switch_asset_browser_to_LOCAL(ws)

            # render the viewport too
            self.render_viewport(context)

            return {'FINISHED'}
        else:
            popup_message("The chosen asset name can't be empty", title="Illegal Name")

        return {'CANCELLED'}

    def switch_asset_browser_to_LOCAL(self, workspace):
        for screen in workspace.screens:
            for area in screen.areas:
                if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                    for space in area.spaces:
                        if space.type == 'FILE_BROWSER':
                            if space.params.asset_library_ref != 'LOCAL':
                                space.params.asset_library_ref = 'LOCAL'

                            # ensure the tool props are shown too, so you can set the thumbnail
                            space.show_region_tool_props = True

    def render_viewport(self, context):
        '''
        render asset thumb
        '''

        # fetch current settings
        resolution = (context.scene.render.resolution_x, context.scene.render.resolution_y)
        file_format = context.scene.render.image_settings.file_format
        lens = context.space_data.lens


        # adjsut for thumbnail rendering
        context.scene.render.resolution_x = 500
        context.scene.render.resolution_y = 500
        context.scene.render.image_settings.file_format = 'JPEG'

        context.space_data.lens = self.thumbnail_lens

        # render
        bpy.ops.render.opengl()

        # fetch the render result and save it
        thumb = bpy.data.images.get('Render Result')

        if thumb:
            thumb.save_render(filepath='thumb.jpg')

        # resstore original settings
        context.scene.render.resolution_x = resolution[0]
        context.scene.render.resolution_y = resolution[1]
        context.space_data.lens = lens

        context.scene.render.image_settings.file_format = file_format


class AssembleCollectionInstance(bpy.types.Operator):
    bl_idname = "machin3.assemble_collection_instance"
    bl_label = "MACHIN3: Assemle Collection"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION'

    def execute(self, context):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object

        instances = {active} | {obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection}
        all_decals = []

        for instance in instances:
            collection = instance.instance_collection

            # linked collection instance
            if collection.library:
                # print(" linked collection instance")

                decals = self.assemble_linked_collection_instance(context, instance, collection, decalmachine)

                if decals:
                    all_decals.extend(decals)

            # assembled collection instance
            else:
                # print(" assembling appended collection instance")

                self.assemble_appended_collection_instance(context, instance, collection)

        # sweep decal backups
        if decalmachine:

            # this avoids checking if backups exist, which is already done in the poll and the op
            # so I feel like its stupid to do it again, just to ensure the poll doesnt error out
            try:
                bpy.ops.machin3.sweep_decal_backups()
            except:
                pass

            if all_decals:
                from DECALmachine.utils.collection import sort_into_collections

                for obj in all_decals:
                    sort_into_collections(context, obj, purge=False)

        # sweep stashes
        if meshmachine:
            try:
                bpy.ops.machin3.sweep_stashes()
            except:
                pass

        # run a purge, because somehow for linked libraries, there will still be linked datablocks here, this gets rid of them
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        return {'FINISHED'}

    def assemble_linked_collection_instance(self, context, instance, collection, decalmachine):
        '''
        assemble linked collection instance
        '''

        cols = [col for col in instance.users_collection]

        filepath = collection.library.filepath
        colname = instance.name

        # remove the icol, there's no need for it anymore
        bpy.data.collections.remove(collection)

        # and the instance ollection object as well
        bpy.data.objects.remove(instance)

        # append the new collection
        appended_collection = append_collection(filepath, colname)

        # get the collections's children and root children
        children = [obj for obj in appended_collection.objects]
        root_children = [obj for obj in children if not obj.parent]

        # remove the appended collection, we don't need it
        bpy.data.collections.remove(appended_collection)

        # link the children to all collections the instance collection was in
        for obj in children:
            for col in cols:
                col.objects.link(obj)

        # select them
        for obj in root_children:
            obj.select_set(True)
            context.view_layer.objects.active = obj

        # get decals if there are any, and return them
        if decalmachine:
            return [obj for obj in children if obj.DM.isdecal]

    def assemble_appended_collection_instance(self, context, instance, collection):
        '''
        assemble appended collection instance
        '''

        cols = [col for col in instance.users_collection]
        offset = instance.matrix_world.to_translation()

        # link collection referenced by the instance collection object
        for col in cols:
            if collection.name not in col.children:
                col.children.link(collection)

        # get the collections's children and root children
        children = [obj for obj in collection.objects]
        root_children = [obj for obj in children if not obj.parent]

        # remove instance collection object
        bpy.data.objects.remove(instance)

        # remove the collection itself too
        bpy.data.collections.remove(collection)

        # link the children to all collections the instance collection was in
        for obj in children:
            for col in cols:
                col.objects.link(obj)

        # offset the collection's root children and select them
        for obj in root_children:
            obj.matrix_basis.translation += offset

            obj.select_set(True)
            context.view_layer.objects.active = obj
