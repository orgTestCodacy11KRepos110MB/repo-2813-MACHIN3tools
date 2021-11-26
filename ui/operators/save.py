import bpy
from bpy.props import StringProperty, BoolProperty
import bmesh
import os
import time
from ... utils.registration import get_prefs, get_addon
from ... utils.append import append_material, append_world
from ... utils.system import add_path_to_recent_files, get_incremented_paths
from ... utils.ui import popup_message, get_icon


class New(bpy.types.Operator):
    bl_idname = "machin3.new"
    bl_label = "Current file is unsaved. Start a new file anyway?"
    bl_description = "Start new .blend file"
    bl_options = {'REGISTER'}


    def execute(self, context):
        bpy.ops.wm.read_homefile(app_template="", load_ui=True)

        return {'FINISHED'}

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event)
        else:
            bpy.ops.wm.read_homefile(app_template="", load_ui=True)
            return {'FINISHED'}


# TODO: file size output

class Save(bpy.types.Operator):
    bl_idname = "machin3.save"
    bl_label = "Save"
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        currentblend = bpy.data.filepath

        if currentblend:
            return f"Save {currentblend}"
        return "Save unsaved file as..."

    def execute(self, context):
        currentblend = bpy.data.filepath

        if currentblend:
            bpy.ops.wm.save_mainfile()

            t = time.time()
            localt = time.strftime('%H:%M:%S', time.localtime(t))
            print("%s | Saved blend: %s" % (localt, currentblend))
            self.report({'INFO'}, 'Saved "%s"' % (os.path.basename(currentblend)))

        else:
            bpy.ops.wm.save_mainfile('INVOKE_DEFAULT')

        return {'FINISHED'}


class SaveIncremental(bpy.types.Operator):
    bl_idname = "machin3.save_incremental"
    bl_label = "Incremental Save"
    bl_options = {'REGISTER'}

    @classmethod
    def description(cls, context, properties):
        currentblend = bpy.data.filepath

        if currentblend:
            incrpaths = get_incremented_paths(currentblend)

            if incrpaths:
                return f"Save {currentblend} incrementally to {os.path.basename(incrpaths[0])}\nALT: Save to {os.path.basename(incrpaths[1])}"

        return "Save unsaved file as..."

    def invoke(self, context, event):
        currentblend = bpy.data.filepath

        if currentblend:
            incrpaths = get_incremented_paths(currentblend)
            savepath = incrpaths[1] if event.alt else incrpaths[0]

            if os.path.exists(savepath):
                self.report({'ERROR'}, "File '%s' exists already!\nBlend has NOT been saved incrementally!" % (savepath))
                return {'CANCELLED'}

            else:

                # add it to the recent files list
                add_path_to_recent_files(savepath)

                bpy.ops.wm.save_as_mainfile(filepath=savepath)

                t = time.time()
                localt = time.strftime('%H:%M:%S', time.localtime(t))
                print(f"{localt} | Saved {os.path.basename(currentblend)} incrementally to {savepath}")
                self.report({'INFO'}, f"Incrementally saved to {os.path.basename(savepath)}")

        else:
            bpy.ops.wm.save_mainfile('INVOKE_DEFAULT')

        return {'FINISHED'}


class LoadMostRecent(bpy.types.Operator):
    bl_idname = "machin3.load_most_recent"
    bl_label = "Load Most Recent"
    bl_description = "Load most recently used .blend file"
    bl_options = {"REGISTER"}

    def execute(self, context):
        recent_path = bpy.utils.user_resource('CONFIG', path="recent-files.txt")

        try:
            with open(recent_path) as file:
                recent_files = file.read().splitlines()
        except (IOError, OSError, FileNotFoundError):
            recent_files = []

        if recent_files:
            most_recent = recent_files[0]

            if os.path.exists(most_recent):
                bpy.ops.wm.open_mainfile(filepath=most_recent, load_ui=True)
                self.report({'INFO'}, 'Loaded most recent "%s"' % (os.path.basename(most_recent)))

            else:
                popup_message("File %s does not exist" % (most_recent), title="File not found")

        return {'FINISHED'}


class AppendWorld(bpy.types.Operator):
    bl_idname = "machin3.append_world"
    bl_label = "Append World"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_prefs().appendworldpath and get_prefs().appendworldname

    def draw(self, context):
        layout = self.layout

        column = layout.column()

    def execute(self, context):
        path = get_prefs().appendworldpath
        name = get_prefs().appendworldname

        world = append_world(path, name)

        if world:
            bpy.context.scene.world = world
        else:
            self.report({'ERROR'}, "World '%s' could not be appended.\nMake sure a world of that name exists in the world source file." % (name))

        return {'FINISHED'}


decalmachine = None


class AppendMaterial(bpy.types.Operator):
    bl_idname = "machin3.append_material"
    bl_label = "Append Material"
    bl_description = "Append material, or apply if it's already in the scene.\nSHIFT: Force append material, even if it's already in the scene."
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name='Append Name')


    def draw(self, context):
        layout = self.layout
        column = layout.column()

    @classmethod
    def poll(cls, context):
        return get_prefs().appendmatspath

    def invoke(self, context, event):
        path = get_prefs().appendmatspath
        name = self.name

        if name == "ALL":
            all_names = [mat.name for mat in get_prefs().appendmats]

            for name in all_names:
                if name != "---":
                    append_material(path, name)
        else:
            mat = bpy.data.materials.get(name)

            if not mat or event.shift:
                mat = append_material(path, name)

            if mat:
                matobjs = [obj for obj in context.selected_objects if obj.type in ['MESH', 'SURFACE', 'CURVE', 'FONT', 'META']]

                # filter out decals, never apply materials to the this way
                global decalmachine

                if decalmachine is None:
                    decalmachine, _, _, _ = get_addon('DECALmachine')

                if decalmachine:
                    matobjs = [obj for obj in matobjs if not obj.DM.isdecal]

                for obj in matobjs:

                    # without any slots, create a new one and assign the material
                    if not obj.material_slots:
                        obj.data.materials.append(mat)

                    # with slots, but without any materials, clear all slots, create a new one and assign the material
                    elif not any(mat for mat in obj.data.materials):
                        obj.data.materials.clear()
                        obj.data.materials.append(mat)

                    # with slots and with existing materials and in edit mesh mode, assign the material to the selection
                    elif context.mode == 'EDIT_MESH':

                        # but first check if the material already is assigned to another slot
                        slot_idx = None

                        for idx, slot in enumerate(obj.material_slots):
                            if slot.material == mat:
                                slot_idx = idx
                                break

                        # append the mat, if it's not already in the stack
                        if slot_idx is None:
                            obj.data.materials.append(mat)
                            slot_idx = len(obj.material_slots) - 1


                        # update the selected faces material_index accordingly
                        bm = bmesh.from_edit_mesh(obj.data)
                        bm.normal_update()

                        faces = [f for f in bm.faces if f.select]

                        for face in faces:
                            face.material_index = slot_idx

                        bmesh.update_edit_mesh(obj.data)

                    # otherwise just apply it to the first slot
                    else:
                        obj.material_slots[0].material = mat

            else:
                self.report({'ERROR'}, "Material '%s' could not be appended.\nMake sure a material of that name exists in the material source file." % (name))

        return {'FINISHED'}


class LoadWorldSource(bpy.types.Operator):
    bl_idname = "machin3.load_world_source"
    bl_label = "Load World Source"
    bl_description = "Load World Source File"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return get_prefs().appendworldpath


    def execute(self, context):
        appendworldpath = get_prefs().appendworldpath

        if os.path.exists(appendworldpath):
            bpy.ops.wm.open_mainfile(filepath=appendworldpath, load_ui=True)

        return {'FINISHED'}


class LoadMaterialsSource(bpy.types.Operator):
    bl_idname = "machin3.load_materials_source"
    bl_label = "Load Materials Source"
    bl_description = "Load Materials Source File"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return get_prefs().appendmatspath

    def execute(self, context):
        appendmatspath = get_prefs().appendmatspath

        if os.path.exists(appendmatspath):
            bpy.ops.wm.open_mainfile(filepath=appendmatspath, load_ui=True)

        return {'FINISHED'}


class LoadPrevious(bpy.types.Operator):
    bl_idname = "machin3.load_previous"
    bl_label = "Current file is unsaved. Load previous blend in folder anyway?"
    bl_description = "Load Previous Blend File in Current Folder\nALT: Don't load ui"
    bl_options = {'REGISTER'}

    load_ui: BoolProperty()

    @classmethod
    def poll(cls, context):
        return bpy.data.filepath

    def invoke(self, context, event):
        self.load_ui = not event.alt

        if bpy.data.filepath:
            path, _, idx = self.get_data(bpy.data.filepath)

            if idx >= 0:
                if bpy.data.is_dirty:
                    return context.window_manager.invoke_confirm(self, event)

                else:
                    self.execute(context)

            else:
                popup_message("You've reached the first file in the current foler: %s." % (path), title="Info")

        return {'FINISHED'}

    def execute(self, context):
        path, files, idx = self.get_data(bpy.data.filepath)

        loadpath = os.path.join(path, files[idx])

        # add the path to the recent files list, for some reason it's not done automatically
        add_path_to_recent_files(loadpath)

        bpy.ops.wm.open_mainfile(filepath=loadpath, load_ui=self.load_ui)
        self.report({'INFO'}, 'Loaded previous file "%s" (%d/%d)' % (os.path.basename(loadpath), idx + 1, len(files)))

        return {'FINISHED'}

    def get_data(self, filepath):
        """
        return path of current blend, all blend files in the folder or the current file as well as the index of the previous blend
        """
        currentpath = os.path.dirname(filepath)
        currentblend = os.path.basename(filepath)

        blendfiles = [f for f in sorted(os.listdir(currentpath)) if f.endswith(".blend")]
        index = blendfiles.index(currentblend)
        previousidx = index - 1

        return currentpath, blendfiles, previousidx


class LoadNext(bpy.types.Operator):
    bl_idname = "machin3.load_next"
    bl_label = "Current file is unsaved. Load next blend in folder anyway?"
    bl_description = "Load Next Blend File in Current Folder\nALT: Don't load ui"
    bl_options = {'REGISTER'}

    load_ui: BoolProperty()

    @classmethod
    def poll(cls, context):
        return bpy.data.filepath

    def invoke(self, context, event):
        self.load_ui = not event.alt

        if bpy.data.filepath:
            path, files, idx = self.get_data(bpy.data.filepath)

            if idx < len(files):
                if bpy.data.is_dirty:
                    return context.window_manager.invoke_confirm(self, event)

                else:
                    self.execute(context)
            else:
                popup_message("You've reached the last file in the current foler: %s." % (path), title="Info")

        return {'FINISHED'}

    def execute(self, context):
        path, files, idx = self.get_data(bpy.data.filepath)

        loadpath = os.path.join(path, files[idx])

        # add the path to the recent files list, for some reason it's not done automatically
        add_path_to_recent_files(loadpath)

        bpy.ops.wm.open_mainfile(filepath=loadpath, load_ui=self.load_ui)
        self.report({'INFO'}, 'Loaded next file "%s" (%d/%d)' % (os.path.basename(loadpath), idx + 1, len(files)))

        return {'FINISHED'}

    def get_data(self, filepath):
        """
        return path of current blend, all blend files in the folder or the current file as well as the index of the next file
        """
        currentpath = os.path.dirname(filepath)
        currentblend = os.path.basename(filepath)

        blendfiles = [f for f in sorted(os.listdir(currentpath)) if f.endswith(".blend")]
        index = blendfiles.index(currentblend)
        previousidx = index + 1

        return currentpath, blendfiles, previousidx


class Purge(bpy.types.Operator):
    bl_idname = "machin3.purge_orphans"
    bl_label = "MACHIN3: Purge Orphans"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return "Purge Orphans\nALT: Purge Orphans Recursively"

    def invoke(self, context, event):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=event.alt)

        return {'FINISHED'}


class Clean(bpy.types.Operator):
    bl_idname = "machin3.clean_out_blend_file"
    bl_label = "Clean out entire .blend file!"
    bl_description = "Clean out entire .blend file"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.data.objects or bpy.data.materials or bpy.data.images

    def draw(self, context):
        layout = self.layout

        column = layout.column()
        column.label(text='This will remove everything in the current .blend file!', icon_value=get_icon('error'))

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

        for mat in bpy.data.materials:
            bpy.data.materials.remove(mat, do_unlink=True)

        for img in bpy.data.images:
            bpy.data.images.remove(img, do_unlink=True)

        for col in bpy.data.collections:
            bpy.data.collections.remove(col, do_unlink=True)

        for i in range(5):
            bpy.ops.outliner.orphans_purge()

        if context.space_data.local_view:
            bpy.ops.view3d.localview(frame_selected=False)

        return {'FINISHED'}


class ReloadLinkedLibraries(bpy.types.Operator):
    bl_idname = "machin3.reload_linked_libraries"
    bl_label = "MACHIN3: Reload Linked Liraries"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.data.libraries

    def execute(self, context):
        reloaded = []

        for lib in bpy.data.libraries:
            lib.reload()
            reloaded.append(lib.name)
            print(f"Reloaded Library: {lib.name}")

        self.report({'INFO'}, f"Reloaded {'Library' if len(reloaded) == 1 else f'{len(reloaded)} Libraries'}: {', '.join(reloaded)}")

        return {'FINISHED'}


class ScreenCast(bpy.types.Operator):
    bl_idname = "machin3.screen_cast"
    bl_label = "MACHIN3: Screen Cast"
    bl_description = "Screen Cast Operators"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        screencast_keys = get_addon('Screencast Keys')[0]

        if screencast_keys:
            return "Screen Cast recent Operators and Keys"
        return "Screen Cast Recent Operators"

    def execute(self, context):
        # context.scene.M3.screen_cast = not context.scene.M3.screen_cast

        wm = context.window_manager
        setattr(wm, 'M3_screen_cast', not getattr(wm, 'M3_screen_cast', False))

        screencast_keys = get_addon('Screencast Keys')[0]

        if screencast_keys:

            # switch workspaces back and forth
            # this prevents "internal error: modal gizmo-map handler has invalid area" errors when maximizing the view

            current = context.workspace
            other = [ws for ws in bpy.data.workspaces if ws != current]

            if other:
                context.window.workspace = other[0]
                context.window.workspace = current

            bpy.ops.wm.sk_screencast_keys('INVOKE_DEFAULT')

        # force handler update via selection event
        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

        return {'FINISHED'}
