import bpy
from bpy.utils import register_class, unregister_class, previews
import os
from importlib import import_module
from .. registration import keys as keysdict
from .. registration import classes as classesdict
from .. msgbus import group_name_change, group_color_change


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


def get_addon_operator_idnames(addon):
    if addon in ['MACHIN3tools', 'DECALmachine', 'MESHmachine', 'HyperCursor', 'PUNCHit']:
        if addon in ['DECALmachine', 'MESHmachine', 'HyperCursor', 'PUNCHit']:
            if not get_addon(addon)[0]:
                return []

        classes = import_module(f'{addon}.registration').classes

        idnames = []

        for imps in classes.values():
            op_imps = [imp for imp in imps if 'operators' in imp[0] or 'macros' in imp[0]]
            idnames.extend([f"machin3.{idname}" for _, cls in op_imps for _, idname in cls])

        return idnames


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

    if kc:
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
    else:
        print("WARNING: Keyconfig not availabe, skipping MACHIN3tools keymaps")

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


# MSGBUS


def register_msgbus(owner):
    bpy.msgbus.subscribe_rna(key=(bpy.types.Object, 'color'), owner=owner, args=(), notify=group_color_change)
    bpy.msgbus.subscribe_rna(key=(bpy.types.Object, 'name'), owner=owner, args=(), notify=group_name_change)


def unregister_msgbus(owner):
    bpy.msgbus.clear_by_owner(owner)


def reload_msgbus():
    from .. import owner

    unregister_msgbus(owner)
    register_msgbus(owner)


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


    # ASSETBROWSER TOOLS
    classlists, keylists, count = get_assetbrowser(classlists, keylists, count)


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


    # THREADS
    classlists, keylists, count = get_thread(classlists, keylists, count)


    # EXTRUDE
    classlists, keylists, count = get_extrude(classlists, keylists, count)


    # SMOOTH
    classlists, keylists, count = get_smooth(classlists, keylists, count)

    # RENDER
    classlists, keylists, count = get_render(classlists, keylists, count)



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
        # keylists.append(keysdict["SELECT"])
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


def get_assetbrowser(classlists=[], keylists=[], count=0):
    if get_prefs().activate_assetbrowser_tools:
        classlists.append(classesdict["ASSETBROWSER"])
        # keylists.append(keysdict["FILEBROWSER"])
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
        keylists.append(keysdict["GROUP"])
        count +=1

    return classlists, keylists, count


def get_thread(classlists=[], keylists=[], count=0):
    if get_prefs().activate_thread:
        classlists.append(classesdict["THREAD"])
        count +=1

    return classlists, keylists, count


def get_extrude(classlists=[], keylists=[], count=0):
    if get_prefs().activate_extrude:
        classlists.append(classesdict["EXTRUDE"])
        count +=2

    return classlists, keylists, count


def get_smooth(classlists=[], keylists=[], count=0):
    if get_prefs().activate_smooth:
        classlists.append(classesdict["SMOOTH"])
        keylists.append(keysdict["SMOOTH"])
        count +=1

    return classlists, keylists, count


def get_render(classlists=[], keylists=[], count=0):
    if get_prefs().activate_render:
        classlists.append(classesdict["RENDER"])
        keylists.append(keysdict["RENDER"])
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
