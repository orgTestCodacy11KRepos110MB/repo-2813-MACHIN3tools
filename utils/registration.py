import bpy
from bpy.utils import register_class, unregister_class, previews
import os
from .. registration import keys as keysdict
from .. registration import classes as classesdict


def get_path():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def get_name():
    return os.path.basename(get_path())


def get_prefs():
    return bpy.context.preferences.addons[get_name()].preferences


def get_addon(addon, debug=False):
    """
    look for addon by name
    return registration status, foldername, version and path
    """
    import addon_utils


    for mod in addon_utils.modules():
        name = mod.bl_info["name"]
        version = mod.bl_info.get("version", None)
        foldername = mod.__name__
        path = mod.__file__
        enabled = addon_utils.check(foldername)[1]

        if name == addon:
            if debug:
                print(name)
                print("  enabled:", enabled)
                print("  folder name:", foldername)
                print("  version:", version)
                print("  path:", path)
                print()

            return enabled, foldername, version, path
    return False, None, None, None


def get_addon_prefs(addon):
    _, foldername, _, _ = get_addon(addon)
    return bpy.context.preferences.addons.get(foldername).preferences


# CLASS REGISTRATION

def register_classes(classlists, debug=False):
    classes = []

    for classlist in classlists:
        for fr, imps in classlist:
            impline = "from ..%s import %s" % (fr, ", ".join([i[0] for i in imps]))
            classline = "classes.extend([%s])" % (", ".join([i[0] for i in imps]))

            exec(impline)
            exec(classline)

    for c in classes:
        if debug:
            print("REGISTERING", c)

        register_class(c)

    return classes


def unregister_classes(classes, debug=False):
    for c in classes:
        if debug:
            print("UN-REGISTERING", c)

        unregister_class(c)


def get_classes(classlist):
    classes = []

    for fr, imps in classlist:
        if "operators" in fr:
            type = "OT"
        elif "pies" in fr or "menus" in fr:
            type = "MT"

        for imp in imps:
            idname = imp[1]
            rna_name = "MACHIN3_%s_%s" % (type, idname)

            c = getattr(bpy.types, rna_name, False)

            if c:
                classes.append(c)

    return classes


# KEYMAP REGISTRATION

def register_keymaps(keylists):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    # kc = wm.keyconfigs.user

    keymaps = []


    for keylist in keylists:
        for item in keylist:
            keymap = item.get("keymap")
            space_type = item.get("space_type", "EMPTY")

            if keymap:
                km = kc.keymaps.new(name=keymap, space_type=space_type)

                if km:
                    idname = item.get("idname")
                    type = item.get("type")
                    value = item.get("value")

                    shift = item.get("shift", False)
                    ctrl = item.get("ctrl", False)
                    alt = item.get("alt", False)

                    kmi = km.keymap_items.new(idname, type, value, shift=shift, ctrl=ctrl, alt=alt)

                    if kmi:
                        properties = item.get("properties")

                        if properties:
                            for name, value in properties:
                                setattr(kmi.properties, name, value)

                        keymaps.append((km, kmi))
    return keymaps


def unregister_keymaps(keymaps):
    for km, kmi in keymaps:
        km.keymap_items.remove(kmi)


def get_keymaps(keylist):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    # kc = wm.keyconfigs.user

    keymaps = []

    for item in keylist:
        keymap = item.get("keymap")

        if keymap:
            km = kc.keymaps.get(keymap)

            if km:
                idname = item.get("idname")

                for kmi in km.keymap_items:
                    if kmi.idname == idname:
                        properties = item.get("properties")

                        if properties:
                            if all([getattr(kmi.properties, name, None) == value for name, value in properties]):
                                keymaps.append((km, kmi))

                        else:
                            keymaps.append((km, kmi))

    return keymaps


# ICON REGISTRATION


def register_icons():
    path = os.path.join(get_prefs().path, "icons")
    icons = previews.new()

    for i in sorted(os.listdir(path)):
        if i.endswith(".png"):
            iconname = i[:-4]
            filepath = os.path.join(path, i)

            icons.load(iconname, filepath, 'IMAGE')

    return icons


def unregister_icons(icons):
    previews.remove(icons)


# CONTEXT MENU ADDITION

def object_context_menu(self, context):
    layout = self.layout

    if get_prefs().activate_object_context_menu:
        layout.menu("MACHIN3_MT_machin3tools_object_context_menu")
        layout.separator()

    if get_prefs().activate_group:
        group_empties = [obj for obj in context.visible_objects if obj.M3.is_group_empty]
        groupable = len([obj for obj in context.selected_objects if not obj.parent]) > 1

        if group_empties:
            layout.prop(context.scene.M3, "group_select")

        if groupable:
            layout.operator("machin3.group", text="Group")


        if group_empties:
            ungroupable = [obj for obj in context.selected_objects if obj.M3.is_group_empty]

            if ungroupable:
                # set op context
                # NOTE: why the the op context necessary here, and not in the MACHIN3tools sub menu?
                # ####: looks like the menue is automatically INVOKE_REGION_WIN for some reason
                layout.operator_context = "INVOKE_REGION_WIN"

                layout.operator("machin3.ungroup", text="Un-Group")

                # reset op context just to be sure
                layout.operator_context = "EXEC_REGION_WIN"

        if group_empties or groupable:
            layout.separator()


# ADD OBJECTS ADDITION

def add_object_buttons(self, context):
    self.layout.operator("machin3.quadsphere", text="Quad Sphere", icon='SPHERE')


# MATERIAL PICKER

def material_pick_button(self, context):
    workspaces = [ws.strip() for ws in get_prefs().matpick_workspace_names.split(',')]

    if any([s in context.workspace.name for s in workspaces]):
        if getattr(bpy.types, 'MACHIN3_OT_material_picker', False):
            row = self.layout.row()
            row.scale_x = 1.25
            row.scale_y = 1.1
            row.separator(factor=get_prefs().matpick_spacing_obj if context.mode == 'OBJECT' else get_prefs().matpick_spacing_edit)
            row.operator("machin3.material_picker", text="", icon="EYEDROPPER")


# RUNTIME TOOL (DE)ACTIVATION

def activate(self, register, tool):
    debug=True
    debug=False

    name = tool.replace("_", " ").title()

    # REGISTER

    if register:
        classlist, keylist, _ = eval("get_%s()" % (tool))


        # CLASSES

        # register tool/pie class
        classes = register_classes(classlist, debug=debug)


        # update classes registered in __init__.py at startup, necessary for addon unregistering
        from .. import classes as startup_classes

        for c in classes:
            if c not in startup_classes:
                startup_classes.append(c)


        # KEYMAPS

        # register tool keymaps
        keymaps = register_keymaps(keylist)

        # update keymaps registered in __init__.py at startup, necessary for addon unregistering
        from .. import keymaps as startup_keymaps
        for k in keymaps:
            if k not in startup_keymaps:
                startup_keymaps.append(k)

        if classes:
            print("Registered MACHIN3tools' %s" % (name))

        classlist.clear()
        keylist.clear()


    # UN-REGISTER

    else:
        # KEYMAPS

        # not every tool has keymappings, so check for it
        keylist = keysdict.get(tool.upper())

        if keylist:
            keymaps = get_keymaps(keylist)

            # update keymaps registered in __init__.py at startup, necessary for addon unregistering
            from .. import keymaps as startup_keymaps
            for k in keymaps:
                if k in startup_keymaps:
                    startup_keymaps.remove(k)

            # unregister tool keymaps
            unregister_keymaps(keymaps)


        # CLASSES

        classlist = classesdict[tool.upper()]


        classes = get_classes(classlist)

        # update classes registered in __init__.py at startup, necessary for addon unregistering
        from .. import classes as startup_classes

        for c in classes:
            if c in startup_classes:
                startup_classes.remove(c)

        # unregister tool classes

        unregister_classes(classes, debug=debug)

        if classes:
            print("Unregistered MACHIN3tools' %s" % (name))


# GET CORE, TOOLS and PIES - CLASSES and KEYMAPS - for startup registration

def get_core():
    return [classesdict["CORE"]]


def get_tools():
    classlists = []
    keylists = []
    count = 0


    # SMART VERT
    classlists, keylists, count = get_smart_vert(classlists, keylists, count)


    # SMART EDGE
    classlists, keylists, count = get_smart_edge(classlists, keylists, count)


    # SMART FACE
    classlists, keylists, count = get_smart_face(classlists, keylists, count)


    # CLEAN UP
    classlists, keylists, count = get_clean_up(classlists, keylists, count)


    # CLIPPING TOGGLE
    classlists, keylists, count = get_clipping_toggle(classlists, keylists, count)


    # FOCUS
    classlists, keylists, count = get_focus(classlists, keylists, count)


    # MIRROR
    classlists, keylists, count = get_mirror(classlists, keylists, count)


    # ALIGN
    classlists, keylists, count = get_align(classlists, keylists, count)


    # APPLY
    classlists, keylists, count = get_apply(classlists, keylists, count)


    # SELECT
    classlists, keylists, count = get_select(classlists, keylists, count)


    # MESH CUT
    classlists, keylists, count = get_mesh_cut(classlists, keylists, count)


    # SURFACE SLIDE
    classlists, keylists, count = get_surface_slide(classlists, keylists, count)


    # FILEBROWSER TOOLS
    classlists, keylists, count = get_filebrowser(classlists, keylists, count)


    # SMART DRIVE
    classlists, keylists, count = get_smart_drive(classlists, keylists, count)


    # UNITY TOOLS
    classlists, keylists, count = get_unity(classlists, keylists, count)


    # MATERIAL PICKER
    classlists, keylists, count = get_material_picker(classlists, keylists, count)


    # GROUP
    classlists, keylists, count = get_group(classlists, keylists, count)


    # CUSTOMIZE
    classlists, keylists, count = get_customize(classlists, keylists, count)

    return classlists, keylists, count


def get_pie_menus():
    classlists = []
    keylists = []
    count = 0

    # MODES

    classlists, keylists, count = get_modes_pie(classlists, keylists, count)


    # SAVE

    classlists, keylists, count = get_save_pie(classlists, keylists, count)


    # SHADING

    classlists, keylists, count = get_shading_pie(classlists, keylists, count)


    # VIEWS

    classlists, keylists, count = get_views_pie(classlists, keylists, count)


    # ALIGN

    classlists, keylists, count = get_align_pie(classlists, keylists, count)


    # CURSOR + ORIGIN

    classlists, keylists, count = get_cursor_pie(classlists, keylists, count)


    # TRANSFORM

    classlists, keylists, count = get_transform_pie(classlists, keylists, count)


    # SNAP

    classlists, keylists, count = get_snapping_pie(classlists, keylists, count)


    # COLLECTIONS

    classlists, keylists, count = get_collections_pie(classlists, keylists, count)


    # WORKSPACE

    classlists, keylists, count = get_workspace_pie(classlists, keylists, count)


    # TOOLS

    classlists, keylists, count = get_tools_pie(classlists, keylists, count)

    return classlists, keylists, count


def get_menus():
    classlists = []
    keylists = []
    count = 0

    # OBJECT CONTEXT MENU

    classlists, keylists, count = get_object_context_menu(classlists, keylists, count)

    return classlists, keylists, count


# GET SPECIFIC TOOLS

def get_smart_vert(classlists=[], keylists=[], count=0):
    if get_prefs().activate_smart_vert:
        from .. operators.smart_vert import SmartVert

        classlists.append(classesdict["SMART_VERT"])
        keylists.append(keysdict["SMART_VERT"])
        count +=1

    return classlists, keylists, count


def get_smart_edge(classlists=[], keylists=[], count=0):
    if get_prefs().activate_smart_edge:
        from .. operators.smart_edge import SmartEdge

        classlists.append(classesdict["SMART_EDGE"])
        keylists.append(keysdict["SMART_EDGE"])
        count +=1

    return classlists, keylists, count


def get_smart_face(classlists=[], keylists=[], count=0):
    if get_prefs().activate_smart_face:
        classlists.append(classesdict["SMART_FACE"])
        keylists.append(keysdict["SMART_FACE"])
        count +=1

    return classlists, keylists, count


def get_clean_up(classlists=[], keylists=[], count=0):
    if get_prefs().activate_clean_up:
        classlists.append(classesdict["CLEAN_UP"])
        keylists.append(keysdict["CLEAN_UP"])
        count +=1

    return classlists, keylists, count


def get_clipping_toggle(classlists=[], keylists=[], count=0):
    if get_prefs().activate_clipping_toggle:
        classlists.append(classesdict["CLIPPING_TOGGLE"])
        keylists.append(keysdict["CLIPPING_TOGGLE"])
        count +=1

    return classlists, keylists, count


def get_focus(classlists=[], keylists=[], count=0):
    if get_prefs().activate_focus:
        classlists.append(classesdict["FOCUS"])
        keylists.append(keysdict["FOCUS"])
        count +=1

    return classlists, keylists, count


def get_mirror(classlists=[], keylists=[], count=0):
    if get_prefs().activate_mirror:
        classlists.append(classesdict["MIRROR"])
        keylists.append(keysdict["MIRROR"])
        count +=1

    return classlists, keylists, count


def get_align(classlists=[], keylists=[], count=0):
    if get_prefs().activate_align:
        classlists.append(classesdict["ALIGN"])
        keylists.append(keysdict["ALIGN"])
        count +=1

    return classlists, keylists, count


def get_apply(classlists=[], keylists=[], count=0):
    if get_prefs().activate_apply:
        classlists.append(classesdict["APPLY"])
        count +=1

    return classlists, keylists, count


def get_select(classlists=[], keylists=[], count=0):
    if get_prefs().activate_select:
        classlists.append(classesdict["SELECT"])
        # keylists.append(keysdict["ALIGN"])
        count +=1

    return classlists, keylists, count


def get_mesh_cut(classlists=[], keylists=[], count=0):
    if get_prefs().activate_mesh_cut:
        classlists.append(classesdict["MESH_CUT"])
        # keylists.append(keysdict["ALIGN"])
        count +=1

    return classlists, keylists, count


def get_surface_slide(classlists=[], keylists=[], count=0):
    if get_prefs().activate_surface_slide:
        classlists.append(classesdict["SURFACE_SLIDE"])
        # keylists.append(keysdict["ALIGN"])
        count +=1

    return classlists, keylists, count


def get_filebrowser(classlists=[], keylists=[], count=0):
    if get_prefs().activate_filebrowser_tools:
        classlists.append(classesdict["FILEBROWSER"])
        keylists.append(keysdict["FILEBROWSER"])
        count +=1

    return classlists, keylists, count


def get_smart_drive(classlists=[], keylists=[], count=0):
    if get_prefs().activate_smart_drive:
        classlists.append(classesdict["SMART_DRIVE"])
        count +=1

    return classlists, keylists, count


def get_unity(classlists=[], keylists=[], count=0):
    if get_prefs().activate_unity:
        classlists.append(classesdict["UNITY"])
        count +=1

    return classlists, keylists, count


def get_material_picker(classlists=[], keylists=[], count=0):
    if get_prefs().activate_material_picker:
        classlists.append(classesdict["MATERIAL_PICKER"])
        count +=1

    return classlists, keylists, count


def get_group(classlists=[], keylists=[], count=0):
    if get_prefs().activate_group:
        classlists.append(classesdict["GROUP"])
        count +=1

    return classlists, keylists, count


def get_customize(classlists=[], keylists=[], count=0):
    if get_prefs().activate_customize:
        classlists.append(classesdict["CUSTOMIZE"])
        count += 1

    return classlists, keylists, count


# GET SPECIFIC PIES

def get_modes_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_modes_pie:
        classlists.append(classesdict["MODES_PIE"])
        keylists.append(keysdict["MODES_PIE"])
        count += 1

    return classlists, keylists, count


def get_save_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_save_pie:
        classlists.append(classesdict["SAVE_PIE"])
        keylists.append(keysdict["SAVE_PIE"])
        count += 1

    return classlists, keylists, count


def get_shading_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_shading_pie:
        classlists.append(classesdict["SHADING_PIE"])
        keylists.append(keysdict["SHADING_PIE"])
        count += 1

    return classlists, keylists, count


def get_views_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_views_pie:
        # from .. ui.pies import PieViews
        # from .. ui.operators.views_and_cams import ViewAxis, MakeCamActive, SmartViewCam

        # classes.append(PieViews)
        # classes.extend([ViewAxis, MakeCamActive, SmartViewCam])

        classlists.append(classesdict["VIEWS_PIE"])
        keylists.append(keysdict["VIEWS_PIE"])
        count += 1

    return classlists, keylists, count


def get_align_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_align_pie:
        classlists.append(classesdict["ALIGN_PIE"])
        keylists.append(keysdict["ALIGN_PIE"])
        count += 1

    return classlists, keylists, count


def get_cursor_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_cursor_pie:
        classlists.append(classesdict["CURSOR_PIE"])
        keylists.append(keysdict["CURSOR_PIE"])
        count += 1

    return classlists, keylists, count


def get_transform_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_transform_pie:
        classlists.append(classesdict["TRANSFORM_PIE"])
        keylists.append(keysdict["TRANSFORM_PIE"])
        count += 1

    return classlists, keylists, count


def get_snapping_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_snapping_pie:
        classlists.append(classesdict["SNAPPING_PIE"])
        keylists.append(keysdict["SNAPPING_PIE"])
        count += 1

    return classlists, keylists, count


def get_collections_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_collections_pie:
        classlists.append(classesdict["COLLECTIONS_PIE"])
        keylists.append(keysdict["COLLECTIONS_PIE"])
        count += 1

    return classlists, keylists, count


def get_workspace_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_workspace_pie:
        classlists.append(classesdict["WORKSPACE_PIE"])
        keylists.append(keysdict["WORKSPACE_PIE"])
        count += 1

    return classlists, keylists, count


def get_tools_pie(classlists=[], keylists=[], count=0):
    if get_prefs().activate_tools_pie:
        classlists.append(classesdict["TOOLS_PIE"])
        keylists.append(keysdict["TOOLS_PIE"])
        count += 1

    return classlists, keylists, count


# GET OBJECT SPECIALS MENU

def get_object_context_menu(classlists=[], keylists=[], count=0):
    if get_prefs().activate_object_context_menu:
        classlists.append(classesdict["OBJECT_CONTEXT_MENU"])
        count += 1

    return classlists, keylists, count
