import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty
from .. utils.registration import get_addon, get_prefs
from .. utils.append import append_collection
from .. utils.ui import popup_message
from .. utils.system import printd
from .. utils.asset import get_catalogs_from_asset_libraries
from .. utils.object import parent


decalmachine = None
meshmachine = None

# TODO: options to hide slectino wires etc?


class CreateAssemblyAsset(bpy.types.Operator):
    bl_idname = "machin3.create_assembly_asset"
    bl_label = "MACHIN3: Creaste Assembly Asset"
    bl_description = "Create Assembly Asset from the selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Asset Name", default="AssemblyAsset")
    move: BoolProperty(name="Move instead of Copy", description="Move Objects into Asset Collection, instead of copying\nThis will unlink them from any existing collections", default=True)

    remove_decal_backups: BoolProperty(name="Remove Decal Backups", description="Remove DECALmachine's Decal Backups, if present", default=False)
    remove_stashes: BoolProperty(name="Remove Stashes", description="Remove MESHmachine's Stashes, if present", default=False)

    render_thumbnail: BoolProperty(name="Render Thumbnail", default=True)
    thumbnail_lens: FloatProperty(name="Thumbnail Lens", default=100)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

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

        row = column.row(align=True)
        row.prop(self, 'render_thumbnail', toggle=True)
        r = row.row(align=True)
        r.active = self.render_thumbnail
        r.prop(self, 'thumbnail_lens', text='Lens')

        column.separator()
        column.prop(context.window_manager, 'M3_asset_catalogs', text='Catalog')

    # """
    def invoke(self, context, event):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        self.update_asset_catalogs(context)

        # return {'FINISHED'}
        return context.window_manager.invoke_props_dialog(self)
    # """

    def execute(self, context):
        global decalmachine, meshmachine

        name = self.name.strip()

        # decalmachine = True
        # self.remove_decal_backups = True

        # meshmachine = True
        # self.remove_stashes = True

        if name:
            print(f"INFO: Creation Assembly Asset: {name}")

            objects = self.get_assembly_asset_objects(context)

            if decalmachine and self.remove_decal_backups:
                self.delete_decal_backups(objects)

            if meshmachine and self.remove_stashes:
                self.delete_stashes(objects)

            # create the asset
            self.create_asset_instance_collection(context, name, objects)

            # switch to an asset browser workspac and set it to LOCAL
            self.adjust_workspace(context)

            # render the viewport
            if self.render_thumbnail:
                self.render_viewport(context)

        else:
            popup_message("The chosen asset name can't be empty", title="Illegal Name")

        return {'CANCELLED'}

    def update_asset_catalogs(self, context):
        self.catalogs = get_catalogs_from_asset_libraries(context, debug=False)

        items = [('NONE', 'None', '')]

        for catalog in self.catalogs:
            # print(catalog)
            items.append((catalog, catalog, ""))

        default = get_prefs().preferred_default_catalog if get_prefs().preferred_default_catalog in self.catalogs else 'NONE'
        bpy.types.WindowManager.M3_asset_catalogs = bpy.props.EnumProperty(name="Asset Categories", items=items, default=default)

    def get_assembly_asset_objects(self, context):
        '''
        from the import selection, collect all objects for this assemtly asset, including unselected objects referecenced by boolean and mirror mods
        '''

        sel = context.selected_objects
        mod_objects = set()

        for obj in sel:
            booleans = [mod for mod in obj.modifiers if mod.type == 'BOOLEAN']
            mirrors = [mod for mod in obj.modifiers if mod.type == 'MIRROR']

            for mod in booleans:
                if mod.object and mod.object not in sel:
                    mod_objects.add(mod.object)

            for mod in mirrors:
                if mod.mirror_object and mod.mirror_object not in sel:
                    mod_objects.add(mod.mirror_object)

        return list(mod_objects) + sel

    def delete_decal_backups(self, objects):
        decals_with_backups = [obj for obj in objects if obj.DM.isdecal and obj.DM.decalbackup]

        for decal in decals_with_backups:
            print(f"WARNING: Removing {decal.name}'s backup")

            if decal.DM.decalbackup:
                bpy.data.meshes.remove(decal.DM.decalbackup.data, do_unlink=True)

    def delete_stashes(self, objects):
        objs_with_stashes = [obj for obj in objects if obj.MM.stashes]

        for obj in objs_with_stashes:
            print(f"WARNING: Removing {obj.name}'s {len(obj.MM.stashes)} stashes")

            for stash in obj.MM.stashes:
                stashobj = stash.obj

                if stashobj:
                    print(" *", stash.name, stashobj.name)
                    bpy.data.meshes.remove(stashobj.data, do_unlink=True)

            obj.MM.stashes.clear()

    def create_asset_instance_collection(self, context, name, objects):
        mcol = context.scene.collection
        acol = bpy.data.collections.new(name)

        mcol.children.link(acol)

        if self.move:
            for obj in objects:
                for col in obj.users_collection:
                    col.objects.unlink(obj)

        for obj in objects:
            acol.objects.link(obj)

            if get_prefs().hide_wire_objects_when_creating_assembly_asset and obj.display_type == 'WIRE':
                obj.hide_set(True)

        instance = bpy.data.objects.new(name, object_data=None)
        instance.instance_collection = acol
        instance.instance_type = 'COLLECTION'

        mcol.objects.link(instance)
        instance.hide_set(True)
        instance.asset_mark()

        # printd(self.catalogs)

        catalog = context.window_manager.M3_asset_catalogs

        if catalog and catalog != 'NONE':
            instance.asset_data.catalog_id = self.catalogs[catalog]['uuid']

            # simple name is read only for some reason
            # instance.asset_data.catalog_simple_name = self.catalogs[catalog]['simple_name']

    def adjust_workspace(self, context):
        asset_browser_workspace = get_prefs().preferred_assetbrowser_workspace_name

        # switch to the preferred asset browser workspace, if one is defined in the addon preferences
        if asset_browser_workspace:
            ws = bpy.data.workspaces.get(asset_browser_workspace)

            if ws and ws != context.workspace:
                print("INFO: Switching to preffered Asset Browser Workspace")
                bpy.ops.machin3.switch_workspace('INVOKE_DEFAULT', name=asset_browser_workspace)

                # then ensure is shows the LOCAL library
                # note, this is done separately here, because the context.workspace isn't updating to the new workspac after the switch op
                self.switch_asset_browser_to_LOCAL(ws)
                return

        # if an asset browser is present on the current workspace, ensure it's set to LOCAL
        ws = context.workspace
        self.switch_asset_browser_to_LOCAL(ws)

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
    bl_label = "MACHIN3: Assemle Collection Instance"
    bl_description = "Make Collection Instance objects accessible\nALT: Keep Empty as Root"
    bl_options = {'REGISTER'}

    keep_empty: BoolProperty(name="Keep Empty as Root", default=False)

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION'

    def invoke(self, context, event):
        self.keep_empty = event.alt
        return self.execute(context)

    def execute(self, context):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object

        instances = {active} | {obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection}

        # linked collection instances need to be made local first
        if any((i.instance_collection.library for i in instances)):
            # print(" linked collection instance present")
            bpy.ops.object.make_local(type='ALL')

            # the op will leave them unselected thought
            for instance in instances:
                instance.select_set(True)

        for instance in instances:
            collection = instance.instance_collection

            # assembled collection instance
            root_children = self.assemble_collection_instance(context, instance, collection)

            if self.keep_empty:
                for child in root_children:
                    parent(child, instance)

                    instance.select_set(True)
                    context.view_layer.objects.active = instance
            else:
                bpy.data.objects.remove(instance, do_unlink=True)

        # sweep decal backups
        if decalmachine:
            decals = [obj for obj in context.scene.objects if obj.DM.isdecal]
            backups = [obj for obj in decals if obj.DM.isbackup]

            if decals:
                from DECALmachine.utils.collection import sort_into_collections

                for obj in decals:
                    sort_into_collections(context, obj, purge=False)

            if backups:
                # print("removing decal backups")
                bpy.ops.machin3.sweep_decal_backups()

        # sweep stashes
        if meshmachine:
            stashobjs = [obj for obj in context.scene.objects if obj.MM.isstashobj]

            if stashobjs:
                bpy.ops.machin3.sweep_stashes()

        # run a purge, because somehow for linked libraries, there will still be linked datablocks here, this gets rid of them
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        return {'FINISHED'}

    def assemble_collection_instance(self, context, instance, collection):
        '''
        assemble appended collection instance

        NOTE: we are using the blender duplicate op here, becaue it massively simplies object duplication
        ####: not only do we need to duplicate the collections objects, but we also need to update all references
        ####: to parents objects, modifier objects, and driver objets. the later seems particulary laborous
        ####: but the duplicate op takes care of that for us
        '''

        cols = [col for col in instance.users_collection]
        imx = instance.matrix_world

        # get the collections's children and root children
        children = [obj for obj in collection.objects]
        # print("children:", [obj.name for obj in children])

        bpy.ops.object.select_all(action='DESELECT')

        for obj in children:
            for col in cols:
                col.objects.link(obj)
            obj.select_set(True)

        # for multi-user collections, duplicate the contensand unlink originals again
        if len(collection.users_dupli_group) > 1:
            # print("WARNING: multi user collection, duplicating contents")

            bpy.ops.object.duplicate()

            for obj in children:
                for col in cols:
                    col.objects.unlink(obj)

            children = [obj for obj in context.selected_objects]
            # print("new children:", [obj.name for obj in children])

        root_children = [obj for obj in children if not obj.parent]
        # print("root children", [obj.name for obj in root_children])

        # offset the collection's root children and select them
        for obj in root_children:
            obj.matrix_world = imx @ obj.matrix_world

            obj.select_set(True)
            context.view_layer.objects.active = obj

        # turn collection instance object into normal empty
        # this then lowers the user count of the collection accordingly
        instance.instance_type = 'NONE'
        instance.instance_collection = None

        if len(collection.users_dupli_group) == 0:
            # print("removing collection", collection.name)
            bpy.data.collections.remove(collection)

        return root_children
