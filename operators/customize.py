import bpy
import os
import shutil
from .. utils.registration import get_prefs
from .. utils.system import makedir
from .. utils.view import reset_viewport
from .. utils.ui import kmi_to_string


class Customize(bpy.types.Operator):
    bl_idname = "machin3.customize"
    bl_label = "MACHIN3: Customize"
    bl_description = "Customize various Blender preferences, settings and keymaps."
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        scriptspath = bpy.utils.user_resource('SCRIPTS')
        datafilespath = bpy.utils.user_resource('DATAFILES')

        resourcespath = os.path.join(get_prefs().path, "resources")

        # basic customization
        if not any([event.alt, event.ctrl]):

            # PREFERENCES
            self.preferences(context)

            # THEME
            if get_prefs().custom_theme:
                self.theme(scriptspath, resourcespath)

            # MATCAPS
            if get_prefs().custom_matcaps:
                self.matcaps(context, resourcespath, datafilespath)

            # SHADING
            if get_prefs().custom_shading:
                self.shading(context)

            # OVERLAYS
            if get_prefs().custom_overlays:
                self.overlays(context)

            # OUTLINER
            if get_prefs().custom_outliner:
                self.outliner(context)

            # STARTUP SCENE
            if get_prefs().custom_startup:
                self.startup(context)


        # HIDDEN

        else:

            # copy custom exrs, setup bookmarks and remove workspaces
            if event.alt:
                self.worlds(context, resourcespath, datafilespath)

                self.bookmarks(context)

                self.clear_workspaces(context)

            # just duplicate the workspace
            elif event.ctrl:
                self.add_workspaces(context)


        return {'FINISHED'}

    def customize_keymap(self, context):
        def modify_keymaps(kc):
            '''
            modify existing keymap items
            '''

            # WINDOW
            km = kc.keymaps.get("Window")
            print("\n Window Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "wm.open_mainfile":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

                if kmi.idname == "wm.doc_view_manual_ui_context":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

            for kmi in km.keymap_items:
                if kmi.idname == "wm.save_as_mainfile":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

            # SCREEN

            km = kc.keymaps.get("Screen")
            print("\n Screen Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "ed.undo":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "F1"
                    kmi.ctrl = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "ed.redo":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "F2"
                    kmi.ctrl = False
                    kmi.shift = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "ed.undo_history":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "F1"
                    kmi.ctrl = False
                    kmi.alt = True
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "screen.redo_last":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "BUTTON4MOUSE"
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "screen.repeat_history":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.ctrl = False
                    kmi.shift = True
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "screen.screen_full_area":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False


            # SCREEN EDITING

            km = kc.keymaps.get("Screen Editing")
            print("\n Screen Editing Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "screen.screen_full_area":
                    if kmi.properties.use_hide_panels:
                        print("  Changed", kmi_to_string(kmi))
                        kmi.shift = True
                        kmi.alt = False
                        kmi.ctrl = False
                        kmi.type = 'SPACE'
                        kmi.value = 'PRESS'
                        print("       to", kmi_to_string(kmi))

                    # NOTE: doesn't seem necessary anymore
                    else:
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

            # FRAMES

            km = kc.keymaps.get("Frames")
            print("\n Frames Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "screen.animation_play":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False


            # OUTLINER

            km = kc.keymaps.get("Outliner")
            print("\n Outliner Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "outliner.show_active":
                    if kmi.type == "PERIOD":
                        print("  Changed", kmi_to_string(kmi))
                        kmi.type = "F"
                        print("       to", kmi_to_string(kmi))


            # 3D VIEW

            km = kc.keymaps.get("3D View")
            print("\n 3D View Keymap")

            for kmi in km.keymap_items:
                # """
                if kmi.idname == "view3d.view_selected":

                    # NOTE: technically no longer necessary IF the Focus tool is activated and mapped to F in view selected mode
                    if kmi.type == "NUMPAD_PERIOD" and not kmi.properties.use_all_regions:
                        print("  Changed", kmi_to_string(kmi))
                        kmi.type = "F"
                        print("       to", kmi_to_string(kmi))

                if kmi.idname == "view3d.cursor3d":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "RIGHTMOUSE"
                    kmi.alt = True
                    kmi.shift = False
                    kmi.properties.orientation = "GEOM"
                    print("       to", kmi_to_string(kmi))

                # NOTE: changing these from  CLICK to PRESS seems to introduce weird behavior where blender always selects the object in the back, not in the front
                # ####: this applies only to the new "just select"/Tweak tool. it seems that for it to work properly, it needs to remain at CLICK - but it still acts as it PRESS was set, odd
                # ####: also the new box select tool, can now be set to PRESS and will still work just fine, so it should be used instead
                # NOTE: also, the script looks for view3d.select kmi's which are set to CLICK, and it will find them too. however, the UI wil actually only show PRESS if you manually change the keymap to 279
                # ####: changin it via the script seems to caus this
                if kmi.idname == "view3d.select":
                    if kmi.value == "CLICK":
                        if not any([getattr(kmi.properties, name, False) for name in ["extend", "deselect", "toggle", "center", "enumerate", "object"]]):
                            print("  Changed", kmi_to_string(kmi))
                            kmi.value = "PRESS"
                            print("       to", kmi_to_string(kmi))

                        elif kmi.properties.toggle and not any([getattr(kmi.properties, name, False) for name in ["extend", "deselect", "center", "enumerate", "object"]]):
                            print("  Changed", kmi_to_string(kmi))
                            kmi.value = "PRESS"
                            print("       to", kmi_to_string(kmi))

                        elif kmi.properties.enumerate and not any([getattr(kmi.properties, name, False) for name in ["extend", "deselect", "toggle", "center", "object"]]):
                            print("  Changed", kmi_to_string(kmi))
                            kmi.value = "PRESS"
                            print("       to", kmi_to_string(kmi))

                        else:
                            print("  Deactivated", kmi_to_string(kmi))
                            kmi.active = False

                if kmi.idname == "transform.translate":
                    if kmi.map_type == "TWEAK":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "view3d.view_axis":
                    if kmi.map_type == "TWEAK":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "transform.tosphere":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.properties.value = 1
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "transform.translate":
                    if kmi.properties.texture_space:
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False


            # 3D VIEW TOOLS

            km = kc.keymaps.get("3D View Tool: Cursor")
            print("\n 3D View Tool: Cursor Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "view3d.cursor3d":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

                if kmi.idname == "transform.translate":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False


            # OBJECT MODE

            km = kc.keymaps.get("Object Mode")
            print("\n Object Mode Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "object.select_all":
                    if kmi.properties.action == "SELECT":
                        print("  Changed", kmi_to_string(kmi))
                        kmi.properties.action = "TOGGLE"
                        print("       to", kmi_to_string(kmi))

                    elif kmi.properties.action == "DESELECT":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "object.delete":
                    if kmi.type == "X" and kmi.shift:
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                    elif kmi.type == "DEL":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False


                if kmi.idname == "object.move_to_collection":
                    if kmi.type == "M":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "object.link_to_collection":
                    if kmi.type == "M" and kmi.shift:
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False


            # OBJECT NON-MODAL

            km = kc.keymaps.get("Object Non-modal")
            print("\n Object Non-modal Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "object.mode_set":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

                if kmi.idname == "view3d.object_mode_pie_or_toggle":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False


            # IMAGE

            km = kc.keymaps.get("Image")
            print("\n Image Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "object.mode_set":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

            for kmi in km.keymap_items:
                if kmi.idname == "image.view_selected":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "F"
                    print("       to", kmi_to_string(kmi))

            # MESH

            km = kc.keymaps.get("Mesh")
            print("\n Mesh Keymap")

            for kmi in km.keymap_items:

                if kmi.idname == "mesh.bevel":
                    if kmi.properties.affect == "EDGES":
                        print("  Changed", kmi_to_string(kmi))
                        kmi.properties.offset_type = 'OFFSET'
                        kmi.properties.profile = 0.6
                        print("       to", kmi_to_string(kmi))

                    elif kmi.properties.affect == "VERTICES":
                        print("  Changed", kmi_to_string(kmi))
                        kmi.properties.affect = "EDGES"
                        kmi.properties.offset_type = 'PERCENT'
                        kmi.properties.profile = 0.6
                        print("       to", kmi_to_string(kmi))


                if kmi.idname == "wm.call_menu":
                    if kmi.properties.name == "VIEW3D_MT_edit_mesh_select_mode":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "mesh.fill":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False


                """
                # not longer necessary as of 2.83, maybe earlier?
                if kmi.idname == "mesh.select_all":
                    if kmi.properties.action == "SELECT":
                        print("  Changed", kmi_to_string(kmi))
                        kmi.properties.action = "TOGGLE"
                        print("       to", kmi_to_string(kmi))

                    elif kmi.properties.action == "DESELECT":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False
                # """


                if kmi.idname == "mesh.edge_face_add" and kmi.type == "F":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

                """
                # not longer necessary as of 2.83, maybe earlier?
                if kmi.idname == "mesh.select_mode" and kmi.type in ["ONE", "TWO", "THREE"]:
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False
                """

                if kmi.idname == "mesh.loop_select":
                    if not any([getattr(kmi.properties, name, False) for name in ["extend", "deselect", "toggle", "ring"]]):
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                    elif kmi.properties.toggle:
                        print("  Changed", kmi_to_string(kmi))
                        kmi.value = "PRESS"
                        kmi.shift = False
                        print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.edgering_select":
                    if kmi.properties.ring and not any([getattr(kmi.properties, name, False) for name in ["extend", "deselect", "toggle"]]):
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                    elif kmi.properties.toggle:
                        print("  Changed", kmi_to_string(kmi))
                        kmi.value = "PRESS"
                        kmi.shift = False
                        print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.shortest_path_pick":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.value = "PRESS"
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.select_more":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "WHEELUPMOUSE"
                    kmi.shift = True
                    kmi.ctrl = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.select_less":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "WHEELDOWNMOUSE"
                    kmi.shift = True
                    kmi.ctrl = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.select_next_item":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "WHEELUPMOUSE"
                    kmi.shift = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.select_prev_item":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "WHEELDOWNMOUSE"
                    kmi.shift = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.select_linked":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "LEFTMOUSE"
                    kmi.value = "DOUBLE_CLICK"
                    kmi.ctrl = False
                    kmi.shift = True
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "mesh.select_linked_pick":
                    if kmi.properties.deselect:
                        print("  Changed", kmi_to_string(kmi))
                        kmi.type = "LEFTMOUSE"
                        kmi.value = "DOUBLE_CLICK"
                        kmi.alt = True
                        print("       to", kmi_to_string(kmi))

                    else:
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "object.subdivision_set":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

                if kmi.idname == "wm.call_menu":
                    if kmi.properties.name == "VIEW3D_MT_edit_mesh_merge":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "wm.call_menu":
                    if kmi.properties.name == "VIEW3D_MT_edit_mesh_split":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False




            # CURVE

            """
            # not longer necessary as of 2.83, maybe earlier?
            km = kc.keymaps.get("Curve")
            print("\n Curve Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "curve.select_all":
                    if kmi.properties.action == "SELECT":
                        kmi.properties.action = "TOGGLE"

                    elif kmi.properties.action == "DESELECT":
                        kmi.active = False



            # ARMATURE
            print("\n Curve Keymap")

            km = kc.keymaps.get("Armature")
            for kmi in km.keymap_items:
                if kmi.idname == "armature.select_all":
                    if kmi.properties.action == "SELECT":
                        kmi.properties.action = "TOGGLE"

                    elif kmi.properties.action == "DESELECT":
                        kmi.active = False


            # POSE
            print("\n Pose Keymap")

            km = kc.keymaps.get("Pose")
            for kmi in km.keymap_items:
                if kmi.idname == "pose.select_all":
                    if kmi.properties.action == "SELECT":
                        kmi.properties.action = "TOGGLE"

                    elif kmi.properties.action == "DESELECT":
                        kmi.active = False
            """


            # UV EDITOR

            km = kc.keymaps.get("UV Editor")
            print("\n UV Editor Keymap")

            for kmi in km.keymap_items:

                """
                # not longer necessary as of 2.83, maybe earlier?
                if kmi.idname == "uv.select_all":
                    if kmi.properties.action == "SELECT":
                        kmi.properties.action = "TOGGLE"

                    elif kmi.properties.action == "DESELECT":
                        kmi.active = False

                if kmi.idname == "mesh.select_mode":
                    kmi.active = False

                if kmi.idname == "wm.context_set_enum":
                    kmi.active = False
                """

                if kmi.idname == "uv.select":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.value = "PRESS"
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "uv.select_loop":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.value = "PRESS"
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "uv.select_more":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "WHEELUPMOUSE"
                    kmi.shift = True
                    kmi.ctrl = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "uv.select_less":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "WHEELDOWNMOUSE"
                    kmi.shift = True
                    kmi.ctrl = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "transform.translate":
                    if kmi.map_type == "TWEAK":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "uv.cursor_set":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.alt = True
                    kmi.shift = False
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "uv.shortest_path_pick":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.value = "PRESS"
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "uv.select_linked":
                    print("  Changed", kmi_to_string(kmi))
                    kmi.type = "LEFTMOUSE"
                    kmi.value = "DOUBLE_CLICK"
                    kmi.ctrl = False
                    kmi.shift = True
                    print("       to", kmi_to_string(kmi))

                if kmi.idname == "uv.select_linked_pick":
                    if kmi.properties.deselect:
                        print("  Changed", kmi_to_string(kmi))
                        kmi.type = "LEFTMOUSE"
                        kmi.value = "DOUBLE_CLICK"
                        kmi.alt = True
                        print("       to", kmi_to_string(kmi))

                    else:
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False



            # IMAGE EDITOR TOOL: UV, CURSOR

            km = kc.keymaps.get("Image Editor Tool: Uv, Cursor")
            print("\n Image Editor Tool: Uv, Cursor  Keymap")

            for kmi in km.keymap_items:
                if kmi.idname == "transform.translate":
                    if kmi.map_type == "TWEAK":
                        print("  Deactivated", kmi_to_string(kmi))
                        kmi.active = False

                if kmi.idname == "uv.cursor_set":
                    print("  Deactivated", kmi_to_string(kmi))
                    kmi.active = False

        def add_keymaps(kc):
            '''
            add new keymap items
            '''

            # MESH
            km = kc.keymaps.get("Mesh")
            print("\n Mesh Keymap")

            kmi = km.keymap_items.new("mesh.loop_multi_select", "LEFTMOUSE", "SOUTH", alt=True)
            kmi.map_type = 'TWEAK'
            kmi.type = 'EVT_TWEAK_L'
            kmi.value = 'SOUTH'
            kmi.properties.ring = False
            print("  Added", kmi_to_string(kmi))

            kmi = km.keymap_items.new("mesh.loop_multi_select", "LEFTMOUSE", "SOUTH", alt=True, ctrl=True)
            kmi.map_type = 'TWEAK'
            kmi.type = 'EVT_TWEAK_L'
            kmi.value = 'SOUTH'
            kmi.properties.ring = True
            print("  Added", kmi_to_string(kmi))

            kmi = km.keymap_items.new("mesh.subdivide", "TWO", "PRESS", alt=True)
            kmi.properties.smoothness = 0
            print("  Added", kmi_to_string(kmi))

        kc = context.window_manager.keyconfigs.user

        modify_keymaps(kc)

        add_keymaps(kc)

        get_prefs().custom_keymaps = False

    def preferences(self, context):
        prefs = context.preferences

        # turn off auto-save

        prefs.use_preferences_save = False

        if get_prefs().custom_preferences_interface:
            print("\n» Changing Preferences: Interface")

            v = prefs.view

            print(" Disabled Splash Screen")
            v.show_splash = False

            print(" Enabled Tool Tips")
            v.show_tooltips = True

            print(" Enabled Python Tool Tips")
            v.show_tooltips_python = True

            print(" Enabled Developer Extras")
            v.show_developer_ui = True

            print(" Changed Header Position to BOTTOM")
            v.header_align = 'BOTTOM'

            print(" Disabled Navigation Controls")
            v.show_navigate_ui = False

            print(" Changed Color Picker to SQUARE_SV")
            v.color_picker_type = "SQUARE_SV"

            print(" Changed Pie Menu Animation Timeout to 0")
            v.pie_animation_timeout = 0

            if bpy.app.version >= (2, 90, 0):
                print(" Enabled Status Bar System Memory")
                v.show_statusbar_memory = True

                print(" Enabled Status Bar Video Memory")
                v.show_statusbar_vram = True

        if get_prefs().custom_preferences_viewport:
            print("\n» Changing Preferences: Viewport")

            v = prefs.view

            print(" Changed 3D Viewport Axis to MINIMAL")
            v.mini_axis_type = 'MINIMAL'

        if get_prefs().custom_preferences_navigation:
            print("\n» Changing Preferences: Navigation")

            i = prefs.inputs

            print(" Inverted Mouse Zoom")
            i.invert_mouse_zoom = True

            print(" Enabled Zoom to Mouse Position")
            i.use_zoom_to_mouse = True

            print(" Changed Double Click Speed to 200")
            i.mouse_double_click_time = 200

        if get_prefs().custom_preferences_keymap:
            print("\n» Changing Preferences: Keymap")

            keyconfigpath = bpy.utils.preset_paths(subdir='keyconfig')

            if keyconfigpath:
                keymappath = os.path.join(keyconfigpath[0], "blender_27x.py")

                print(" Set 2.7X keymap")
                bpy.ops.preferences.keyconfig_activate(filepath=keymappath)

                print(" Changed Select Mouse to LEFT")
                kcprefs = context.window_manager.keyconfigs.active.preferences
                kcprefs.select_mouse = "LEFT"

                # """
                # for some weird reason doing this 2 times is required if you edit the keymaps afterwards
                # otherwise middle mouse mappings for zoom, pan, rotate and dolly will be missing, perhaps some other things as well
                # it seems to be related to doing ANY change in the 3D View keymap, see 3D View notes for some more details
                bpy.ops.preferences.keyconfig_activate(filepath=keymappath)

                kcprefs = context.window_manager.keyconfigs.active.preferences
                kcprefs.select_mouse = "LEFT"
                # """

            self.customize_keymap(context)

        if get_prefs().custom_preferences_system:
            print("\n» Changing Preferences: System")

            c = prefs.addons['cycles'].preferences
            e = prefs.edit

            print(" Changed Cylces Render Decive to CUDA")
            c.compute_device_type = "CUDA"

            # TODO: as of c59370bf643f, likely a bit earlier, the c.devices collection won't update until the user switches to the SYSTEM prefs panel manually
            # ####: as a consequence, the integrated gpu won't be activated, in fact they can't even be listed and so the following doesn't work anymore

            for d in c.devices:
                d.use = True

            print(" Changed Undo Steps to 64")
            e.undo_steps = 64

        if get_prefs().custom_preferences_save:
            print("\n» Changing Preferences: Save & Load")

            v = prefs.view
            f = prefs.filepaths

            print(" Disabled Save Prompt")
            v.use_save_prompt = False

            print(" Enabled File Compression")
            f.use_file_compression = True

            print(" Disabled UI Loading")
            f.use_load_ui = False

            print(" Changed Save Versions to 3")
            f.save_version = 3

            print(" Changed Recent Files to 20")
            f.recent_files = 20

    def theme(self, scriptspath, resourcespath):
        print("\n» Installing and Enabling M3 theme (a merger of Flatty Dark Blueberry + rTheme)")

        themesourcepath = os.path.join(resourcespath, "theme", "m3.xml")
        themetargetpath = makedir(os.path.join(scriptspath, "presets", "interface_theme"))

        filepath = shutil.copy(themesourcepath, themetargetpath)
        bpy.ops.script.execute_preset(filepath=filepath, menu_idname="USERPREF_MT_interface_theme_presets")

    def matcaps(self, context, resourcespath, datafilespath):
        print("\n» Adding Matcaps")

        matcapsourcepath = os.path.join(resourcespath, "matcaps")
        matcaptargetpath = makedir(os.path.join(datafilespath, "studiolights", "matcap"))
        matcaps = os.listdir(matcapsourcepath)

        for matcap in sorted(matcaps):
            shutil.copy(os.path.join(matcapsourcepath, matcap), matcaptargetpath)
            print("  %s -> %s" % (matcap, matcaptargetpath))

        context.preferences.studio_lights.refresh()

        if all([mc in matcaps for mc in ["matcap_base.exr", "matcap_shiny_red.exr"]]):
            get_prefs().switchmatcap1 = "matcap_base.exr"
            get_prefs().switchmatcap2 = "matcap_shiny_red.exr"

    def shading(self, context):
        print("\n» Setting up Shading and Rendering")

        areas = [area for screen in context.workspace.screens for area in screen.areas if area.type == "VIEW_3D"]

        for area in areas:
            shading = area.spaces[0].shading

            print(" Changed shading.type to SOLID")
            shading.type = "SOLID"

            print(" Changed shading.light to MATCAP")
            shading.light = "MATCAP"

            print(" Changed shading.color_type to SINGLE")
            shading.color_type = "SINGLE"

            print(" Changed shading.single_color to #838387")
            shading.single_color = (0.2270, 0.2270, 0.2423)  # hex 838387

            if 'matcap_base.exr' in context.preferences.studio_lights:
                print(" Changed shading.studio_light to matcap_base.exr")
                shading.studio_light = "matcap_base.exr"

            print(" Changed shading.studiolight_background_alpha to 0")
            shading.studiolight_background_alpha = 0

            print(" Changed shading.studiolight_background_blur to 1")
            shading.studiolight_background_blur = 1

            print(" Enabled shading.show_cavity")
            shading.show_cavity = True

            print(" Changed shading.cavity_type to WORLD")
            shading.cavity_type = 'WORLD'

            print(" Changed shading.cavity_ridge_factor to 0")
            shading.cavity_ridge_factor = 0

            print(" Changed shading.cavity_valley_factor to 2")
            shading.cavity_valley_factor = 2

            print(" Enabled shading.show_backface_culling")
            shading.show_backface_culling = True

            # mimic LOW eevee preset

            print(" Enabled shading.use_scene_lights")
            shading.use_scene_lights = True

            print(" Enabled shading.use_scene_lights_render")
            shading.use_scene_lights_render = True

            print(" Disabled shading.use_scene_world_render")
            shading.use_scene_world_render = False

            eevee = context.scene.eevee

            print(" Enabled eevee.use_ssr")
            eevee.use_ssr = True

            print(" Enabled eevee.use_gtao")
            eevee.use_gtao = True

            print(" Disabled eevee.use_volumetric_lights")
            eevee.use_volumetric_lights = False

            print(" Changed Render Engine to CYCLES")
            context.scene.render.engine = 'CYCLES'

            print(" Changed Cycles Devices to GPU")
            context.scene.cycles.device = 'GPU'

    def overlays(self, context):
        print("\n» Modifying Overlays")

        areas = [area for screen in context.workspace.screens for area in screen.areas if area.type == "VIEW_3D"]

        for area in areas:
            overlay = area.spaces[0].overlay

            print(" Enabled overlay.show_face_center")
            overlay.show_face_center = True

            print(" Disabled overlay.show_relationship_lines")
            overlay.show_relationship_lines = False

            print(" Changed overlay.wireframe_threshold to 0.99")
            overlay.wireframe_threshold = 0.99

            print(" Changed overlay.vertex_opacity to 1")
            overlay.vertex_opacity = 1

            print(" Disabled overlay.show_fade_inactive")
            overlay.show_fade_inactive = False

    def outliner(self, context):
        print("\n» Modifying Outliner")

        areas = [area for screen in context.workspace.screens for area in screen.areas if area.type == "OUTLINER"]

        for area in areas:
            space = area.spaces[0]

            print(" Disabled outliner.use_filter_children")
            space.use_filter_children = False

            print(" Enabled outliner.show_restrict_column_select")
            space.show_restrict_column_select = True

            print(" Enabled outliner.show_restrict_column_viewport")
            space.show_restrict_column_viewport = True

            print(" Enabled outliner.show_restrict_column_render")
            space.show_restrict_column_render = True

    def startup(self, context):
        print("\n» Modifying Startup Scene")

        # enable uv selection sync
        print(" Enabled tool_settings.use_uv_select_sync")
        context.scene.tool_settings.use_uv_select_sync = True

        # remove default objects
        light = bpy.data.lights.get('Light')
        if light:

            print(" Removed default Light")
            bpy.data.lights.remove(light, do_unlink=True)

        cube = bpy.data.meshes.get('Cube')
        if cube:
            print(" Removed default Cube")
            bpy.data.meshes.remove(cube, do_unlink=True)

        cam = bpy.data.cameras.get('Camera')
        if cam:
            print(" Removed default Camera")
            bpy.data.cameras.remove(cam, do_unlink=True)

        mat = bpy.data.materials.get('Material')
        if mat:
            print(" Removed default Material")
            bpy.data.materials.remove(mat, do_unlink=True)

        # set view matrix
        print(" Aligned Viewport with Y Axis")
        reset_viewport(context, disable_toolbar=True)
        print(" Disabled Tool Bar")

    def worlds(self, context, resourcespath, datafilespath):
        print("\n» Adding Custom EXRs")

        worldssourcepath = os.path.join(resourcespath, "worlds")
        worldstargetpath = makedir(os.path.join(datafilespath, "studiolights", "world"))
        worlds = os.listdir(worldssourcepath)

        for world in sorted(worlds):
            shutil.copy(os.path.join(worldssourcepath, world), worldstargetpath)
            print("  %s -> %s" % (world, worldstargetpath))

    def bookmarks(self, context):
        print("\n» Setting Custom Bookmarks")

        path = bpy.utils.user_resource('CONFIG', "bookmarks.txt")

        lines = ['[Bookmarks]',
                 '!Archive',
                 '/home/x/Archive/blender',
                 '!TEMP',
                 '/home/x/TEMP/blender',
                 '!Addons',
                 '/home/x/TEMP/blender/Addons',
                 '!Output',
                 '/home/x/TEMP/blender/Output',
                 '[Recent]',
                 '!DECALmachine',
                 '/home/x/TEMP/blender/Addons/DECALmachine',
                 '!MESHmachine',
                 '/home/x/TEMP/blender/Addons/MESHmachine',
                 ]

        with open(path, mode='w') as f:
            f.write('\n'.join(lines))

    def clear_workspaces(self, context):
        print("\n» Clearing Workspaces")

        # remove all but one Layout
        workspaces = [ws for ws in bpy.data.workspaces if ws != context.workspace]
        bpy.data.batch_remove(ids=workspaces)

        # name the basic 3d workspace
        bpy.data.workspaces[-1].name = "General"

        # remove the dope sheet editor
        screens = [screen for screen in context.workspace.screens if screen.name == 'Layout']


        if screens:
            screen = screens[0]
            areas = [area for area in screen.areas if area.type == 'VIEW_3D']

            if areas:
                area = areas[0]

                override = {'screen': screen,
                            'area': area}

                areas = [area for area in screen.areas if area.type == 'DOPESHEET_EDITOR']

                if areas:
                    area = areas[0]

                    bpy.ops.screen.area_join(override, cursor=(area.x, area.y + area.height))

    def add_workspaces(self, context):
        print("\n» Adding Workspaces")

        areas = [area for screen in context.workspace.screens for area in screen.areas if area.type == "VIEW_3D"]
        override = {'area': areas[0]}

        # TODO: whatever I try, I can't get them sorted properly, not even with the reorder op
        # ####: also, running this will turn the prefs into a 3d view for some reason

        names = ['General.alt', 'UVs', 'UVs.alt', 'Material', 'World', 'Scripting', 'Scripting.alt']

        for idx, name in enumerate(names):
            bpy.ops.workspace.duplicate(override)

        for name, ws in zip(names, bpy.data.workspaces[1:]):
            ws.name = name


class RestoreKeymaps(bpy.types.Operator):
    bl_idname = "machin3.restore_keymaps"
    bl_label = "MACHIN3: Restore Keymaps"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        kc = context.window_manager.keyconfigs.user

        for km in kc.keymaps:
            if km.is_user_modified:
                km.restore_to_default()

        get_prefs().dirty_keymaps = False

        return {'FINISHED'}
