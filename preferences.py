import bpy
from bpy.props import IntProperty, StringProperty, CollectionProperty, BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty
import os
from . properties import AppendMatsCollection
from . utils.ui import get_icon, draw_keymap_items
from . utils.registration import activate, get_path, get_name, get_addon
from . items import preferences_tabs, matcap_background_type_items


decalmachine = None
meshmachine = None


# TODO: check if the append world/materials paths exist and make them absolute


has_settings = ['OT_smart_vert',
                'OT_clean_up',
                'OT_clipping_toggle',
                'OT_transform_edge_constrained',
                'OT_clipping_toggle',
                'OT_focus',
                'OT_group',
                'OT_material_picker',
                'OT_surface_slide',
                'OT_customize',
                'MT_cursor_pie',
                'MT_modes_pie',
                'MT_save_pie',
                'MT_shading_pie',
                'MT_snapping_pie',
                'MT_tools_pie',
                'MT_viewport_pie']


class MACHIN3toolsPreferences(bpy.types.AddonPreferences):
    path = get_path()
    bl_idname = get_name()


    # APPENDMATS

    def update_appendmatsname(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        else:
            if self.appendmatsname and self.appendmatsname not in self.appendmats:
                am = self.appendmats.add()
                am.name = self.appendmatsname

                self.appendmatsIDX = len(self.appendmats) - 1

            self.avoid_update = True
            self.appendmatsname = ""


    # CHECKS

    def update_switchmatcap1(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        matcaps = [mc.name for mc in context.preferences.studio_lights if os.path.basename(os.path.dirname(mc.path)) == "matcap"]
        if self.switchmatcap1 not in matcaps:
            self.avoid_update = True
            self.switchmatcap1 = "NOT FOUND"

    def update_switchmatcap2(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        matcaps = [mc.name for mc in context.preferences.studio_lights if os.path.basename(os.path.dirname(mc.path)) == "matcap"]
        if self.switchmatcap2 not in matcaps:
            self.avoid_update = True
            self.switchmatcap2 = "NOT FOUND"

    def update_custom_preferences_keymap(self, context):
        if self.custom_preferences_keymap:
            kc = context.window_manager.keyconfigs.user

            for km in kc.keymaps:
                if km.is_user_modified:
                    self.custom_preferences_keymap = False
                    self.dirty_keymaps = True
                    return

            self.dirty_keymaps = False


    # RUNTIME TOOL ACTIVATION

    def update_activate_smart_vert(self, context):
        activate(self, register=self.activate_smart_vert, tool="smart_vert")

    def update_activate_smart_edge(self, context):
        activate(self, register=self.activate_smart_edge, tool="smart_edge")

    def update_activate_smart_face(self, context):
        activate(self, register=self.activate_smart_face, tool="smart_face")

    def update_activate_clean_up(self, context):
        activate(self, register=self.activate_clean_up, tool="clean_up")

    def update_activate_clipping_toggle(self, context):
        activate(self, register=self.activate_clipping_toggle, tool="clipping_toggle")

    def update_activate_focus(self, context):
        activate(self, register=self.activate_focus, tool="focus")

    def update_activate_mirror(self, context):
        activate(self, register=self.activate_mirror, tool="mirror")

    def update_activate_align(self, context):
        activate(self, register=self.activate_align, tool="align")

    def update_activate_apply(self, context):
        activate(self, register=self.activate_apply, tool="apply")

    def update_activate_select(self, context):
        activate(self, register=self.activate_select, tool="select")

    def update_activate_mesh_cut(self, context):
        activate(self, register=self.activate_mesh_cut, tool="mesh_cut")

    def update_activate_surface_slide(self, context):
        activate(self, register=self.activate_surface_slide, tool="surface_slide")

    def update_activate_filebrowser_tools(self, context):
        activate(self, register=self.activate_filebrowser_tools, tool="filebrowser")

    def update_activate_smart_drive(self, context):
        activate(self, register=self.activate_smart_drive, tool="smart_drive")

    def update_activate_unity(self, context):
        activate(self, register=self.activate_unity, tool="unity")

    def update_activate_material_picker(self, context):
        activate(self, register=self.activate_material_picker, tool="material_picker")

    def update_activate_group(self, context):
        activate(self, register=self.activate_group, tool="group")

    def update_activate_thread(self, context):
        activate(self, register=self.activate_thread, tool="thread")

    def update_activate_spin(self, context):
        activate(self, register=self.activate_spin, tool="spin")

    def update_activate_smooth(self, context):
        activate(self, register=self.activate_smooth, tool="smooth")

    def update_activate_customize(self, context):
        activate(self, register=self.activate_customize, tool="customize")


    # RUNTIME PIE ACTIVATION

    def update_activate_modes_pie(self, context):
        activate(self, register=self.activate_modes_pie, tool="modes_pie")

    def update_activate_save_pie(self, context):
        activate(self, register=self.activate_save_pie, tool="save_pie")

    def update_activate_shading_pie(self, context):
        activate(self, register=self.activate_shading_pie, tool="shading_pie")

    def update_activate_views_pie(self, context):
        activate(self, register=self.activate_views_pie, tool="views_pie")

    def update_activate_align_pie(self, context):
        activate(self, register=self.activate_align_pie, tool="align_pie")

    def update_activate_cursor_pie(self, context):
        activate(self, register=self.activate_cursor_pie, tool="cursor_pie")

    def update_activate_transform_pie(self, context):
        activate(self, register=self.activate_transform_pie, tool="transform_pie")

    def update_activate_snapping_pie(self, context):
        activate(self, register=self.activate_snapping_pie, tool="snapping_pie")

    def update_activate_collections_pie(self, context):
        activate(self, register=self.activate_collections_pie, tool="collections_pie")

    def update_activate_workspace_pie(self, context):
        activate(self, register=self.activate_workspace_pie, tool="workspace_pie")

    def update_activate_tools_pie(self, context):
        activate(self, register=self.activate_tools_pie, tool="tools_pie")


    # PROPERTIES

    appendworldpath: StringProperty(name="World Source .blend", subtype='FILE_PATH')
    appendworldname: StringProperty(name="Name of World")

    appendmatspath: StringProperty(name="Materials Source .blend", subtype='FILE_PATH')
    appendmats: CollectionProperty(type=AppendMatsCollection)
    appendmatsIDX: IntProperty()
    appendmatsname: StringProperty(name="Name of Material to append", update=update_appendmatsname)

    switchmatcap1: StringProperty(name="Matcap 1", update=update_switchmatcap1)
    switchmatcap2: StringProperty(name="Matcap 2", update=update_switchmatcap2)
    matcap2_force_single: BoolProperty(name="Force Single Color Shading for Matcap 2", default=True)
    matcap2_disable_overlays: BoolProperty(name="Disable Overlays for Matcap 2", default=True)

    matcap_switch_background: BoolProperty(name="Switch Background too", default=False)
    matcap1_switch_background_type: EnumProperty(name="Matcap 1 Background Type", items=matcap_background_type_items, default="THEME")
    matcap1_switch_background_viewport_color: FloatVectorProperty(name="Matcap 1 Background Color", subtype='COLOR', default=[0.05, 0.05, 0.05], size=3, min=0, max=1)

    matcap2_switch_background_type: EnumProperty(name="Matcap 2 Background Type", items=matcap_background_type_items, default="THEME")
    matcap2_switch_background_viewport_color: FloatVectorProperty(name="Matcap 2 Background Color", subtype='COLOR', default=[0.05, 0.05, 0.05], size=3, min=0, max=1)

    obj_mode_rotate_around_active: BoolProperty(name="Rotate Around Selection, but only in Object Mode", default=False)
    custom_views_use_trackball: BoolProperty(name="Force Trackball Navigation when using Custom Views", default=True)
    custom_views_set_transform_preset: BoolProperty(name="Set Transform Preset when using Custom Views", default=True)
    custom_views_toggle_axes_drawing: BoolProperty(name="Toggle Custom View Axes Drawing", default=True)
    show_orbit_selection: BoolProperty(name="Show Orbit around Active", default=True)
    show_orbit_method: BoolProperty(name="Show Orbit Method Selection", default=True)

    cursor_show_to_grid: BoolProperty(name="Show Cursor and Selected to Grid", default=False)
    cursor_set_transform_preset: BoolProperty(name="Set Transform Preset when Setting Cursor", default=True)
    cursor_toggle_axes_drawing: BoolProperty(name="Toggle Cursor Axes Drawing", default=True)

    snap_show_absolute_grid: BoolProperty(name="Show Absolute Grid Snapping", default=False)

    toggle_cavity: BoolProperty(name="Toggle Cavity/Curvature OFF in Edit Mode, ON in Object Mode", default=True)
    sync_tools: BoolProperty(name="Sync Tool if possible, when switching Modes", default=True)
    focus_view_transition: BoolProperty(name="Viewport Tweening", default=True)

    tools_show_boxcutter_presets: BoolProperty(name="Show BoxCutter Presets", default=True)
    tools_show_hardops_menu: BoolProperty(name="Show Hard Ops Menu", default=True)
    tools_show_quick_favorites: BoolProperty(name="Show Quick Favorites", default=False)
    tools_show_tool_bar: BoolProperty(name="Show Tool Bar", default=False)

    matpick_workspace_names: StringProperty(name="Workspaces the Material Picker should appear on", default="Shading, Material")
    matpick_spacing_obj: FloatProperty(name="Object Mode Spacing", min=0, default=20)
    matpick_spacing_edit: FloatProperty(name="Edit Mode Spacing", min=0, default=5)

    screencast_operator_count: IntProperty(name="Operator Count", description="Maximum number of Operators displayed when Screen Casting", default=12, min=1, max=100)
    screencast_fontsize: IntProperty(name="Font Size", default=12, min=2)
    screencast_highlight_machin3: BoolProperty(name="Highlight MACHIN3 operators", description="Highlight Operators from MACHIN3 addons", default=True)
    screencast_show_addon: BoolProperty(name="Display Operator's Addons", description="Display Operator's Addon", default=True)
    screencast_show_idname: BoolProperty(name="Display Operator's idnames", description="Display Operator's bl_idname properties", default=False)

    custom_startup: BoolProperty(name="Startup Scene", default=False)
    custom_theme: BoolProperty(name="Theme", default=True)
    custom_matcaps: BoolProperty(name="Matcaps", default=True)
    custom_shading: BoolProperty(name="Shading", default=False)
    custom_overlays: BoolProperty(name="Overlays", default=False)
    custom_outliner: BoolProperty(name="Outliner", default=False)
    custom_preferences_interface: BoolProperty(name="Preferences: Interface", default=False)
    custom_preferences_viewport: BoolProperty(name="Preferences: Viewport", default=False)
    custom_preferences_navigation: BoolProperty(name="Preferences: Navigation", default=False)
    custom_preferences_keymap: BoolProperty(name="Preferences: Keymap", default=False, update=update_custom_preferences_keymap)
    custom_preferences_system: BoolProperty(name="Preferences: System", default=False)
    custom_preferences_save: BoolProperty(name="Preferences: Save & Load", default=False)

    group_auto_name: BoolProperty(name="Auto Name Groups", description="Automatically add a Prefix and/or Suffix to any user-set Group Name", default=True)
    group_basename: StringProperty(name="Group Basename", default="GROUP")
    group_prefix: StringProperty(name="Prefix to add to Group Names", default="_")
    group_suffix: StringProperty(name="Suffix to add to Group Names", default="_grp")
    group_size: FloatProperty(name="Group Empty Draw Size", description="Default Group Size", default=0.2)
    group_fade_sizes: BoolProperty(name="Fade Group Empty Sizes", description="Make Sub Group's Emtpies smaller than their Parents", default=True)
    group_fade_factor: FloatProperty(name="Fade Group Size Factor", description="Factor by which to decrease each Group Empty's Size", default=0.8, min=0.1, max=0.9)


    # MACHIN3tools

    activate_smart_vert: BoolProperty(name="Smart Vert", default=False, update=update_activate_smart_vert)
    activate_smart_edge: BoolProperty(name="Smart Edge", default=False, update=update_activate_smart_edge)
    activate_smart_face: BoolProperty(name="Smart Face", default=False, update=update_activate_smart_face)
    activate_clean_up: BoolProperty(name="Clean Up", default=False, update=update_activate_clean_up)
    activate_clipping_toggle: BoolProperty(name="Clipping Toggle", default=False, update=update_activate_clipping_toggle)
    activate_focus: BoolProperty(name="Focus", default=True, update=update_activate_focus)
    activate_mirror: BoolProperty(name="Mirror", default=False, update=update_activate_mirror)
    activate_align: BoolProperty(name="Align", default=False, update=update_activate_align)
    activate_apply: BoolProperty(name="Apply", default=False, update=update_activate_apply)
    activate_select: BoolProperty(name="Select", default=False, update=update_activate_select)
    activate_mesh_cut: BoolProperty(name="Mesh Cut", default=False, update=update_activate_mesh_cut)
    activate_surface_slide: BoolProperty(name="Surface Slide", default=False, update=update_activate_surface_slide)
    activate_filebrowser_tools: BoolProperty(name="Filebrowser Tools", default=False, update=update_activate_filebrowser_tools)
    activate_smart_drive: BoolProperty(name="Smart Drive", default=False, update=update_activate_smart_drive)
    activate_unity: BoolProperty(name="Unity", default=False, update=update_activate_unity)
    activate_material_picker: BoolProperty(name="Material Picker", default=False, update=update_activate_material_picker)
    activate_group: BoolProperty(name="Group", default=False, update=update_activate_group)
    activate_thread: BoolProperty(name="Thread", default=False, update=update_activate_thread)
    activate_spin: BoolProperty(name="Spin", default=False, update=update_activate_spin)
    activate_smooth: BoolProperty(name="Smooth", default=False, update=update_activate_smooth)
    activate_customize: BoolProperty(name="Customize", default=False, update=update_activate_customize)


    # MACHIN3pies

    activate_modes_pie: BoolProperty(name="Modes Pie", default=True, update=update_activate_modes_pie)
    activate_save_pie: BoolProperty(name="Save Pie", default=False, update=update_activate_save_pie)
    activate_shading_pie: BoolProperty(name="Shading Pie", default=False, update=update_activate_shading_pie)
    activate_views_pie: BoolProperty(name="Views Pie", default=False, update=update_activate_views_pie)
    activate_align_pie: BoolProperty(name="Align Pies", default=False, update=update_activate_align_pie)
    activate_cursor_pie: BoolProperty(name="Cursor and Origin Pie", default=False, update=update_activate_cursor_pie)
    activate_transform_pie: BoolProperty(name="Transform Pie", default=False, update=update_activate_transform_pie)
    activate_snapping_pie: BoolProperty(name="Snapping Pie", default=False, update=update_activate_snapping_pie)
    activate_collections_pie: BoolProperty(name="Collections Pie", default=False, update=update_activate_collections_pie)
    activate_workspace_pie: BoolProperty(name="Workspace Pie", default=False, update=update_activate_workspace_pie)
    activate_tools_pie: BoolProperty(name="Tools Pie", default=False, update=update_activate_tools_pie)


    # SUB MENUS

    use_group_sub_menu: BoolProperty(name="Use Group Sub-Menu", default=False)
    use_group_outliner_toggles: BoolProperty(name="Show Group Outliner Toggles", default=True)


    # VIEW3D

    use_legacy_line_smoothing: BoolProperty(name="Use Legacy Line Smoothing", description="Legacy Line Smoothing using the depreciated bgl module\nIf this is disabled, lines drawn by MACHIN3tools won't be anti aliased.", default=False)


    # HUD

    HUD_scale: FloatProperty(name="HUD Scale", description="Scale of HUD elements", default=1, min=0.1)
    HUD_fade_clean_up: FloatProperty(name="Clean Up HUD Fade Time (seconds)", default=1, min=0.1, max=3)
    HUD_fade_clipping_toggle: FloatProperty(name="Clipping Toggle HUD Fade Time (seconds)", default=1, min=0.1)
    HUD_fade_material_picker: FloatProperty(name="Material Picker HUD Fade Time (seconds)", default=0.5, min=0.1)
    HUD_fade_group: FloatProperty(name="Group HUD Fade Time (seconds)", default=1, min=0.1)
    HUD_fade_tools_pie: FloatProperty(name="Tools Pie HUD Fade Time (seconds)", default=0.75, min=0.1)


    # hidden

    tabs: EnumProperty(name="Tabs", items=preferences_tabs, default="GENERAL")
    avoid_update: BoolProperty(default=False)
    dirty_keymaps: BoolProperty(default=False)


    def draw(self, context):
        layout=self.layout


        # TAB BAR

        column = layout.column(align=True)
        row = column.row()
        row.prop(self, "tabs", expand=True)

        box = column.box()

        if self.tabs == "GENERAL":
            self.draw_general(box)

        elif self.tabs == "KEYMAPS":
            self.draw_keymaps(box)

        elif self.tabs == "ABOUT":
            self.draw_about(box)

    def draw_general(self, box):
        split = box.split()

        # LEFT

        b = split.box()
        b.label(text="Activate")


        # MACHIN3tools

        bb = b.box()
        bb.label(text="Tools")

        column = bb.column(align=True)

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_smart_vert", toggle=True)
        row.label(text="Smart Vertex Merging, Connecting and Sliding.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_smart_edge", toggle=True)
        row.label(text="Smart Edge Creation, Manipulation, Projection and Selection Conversion.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_smart_face", toggle=True)
        row.label(text="Smart Face Creation and Object-from-Face Creation.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_clean_up", toggle=True)
        row.label(text="Quick Geometry Clean-up.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_clipping_toggle", toggle=True)
        row.label(text="Viewport Clipping Plane Toggle.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_focus", toggle=True)
        row.label(text="Object Focus and Multi-Level Isolation.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_mirror", toggle=True)
        row.label(text="Object Mirroring and Un-Mirroring.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_align", toggle=True)
        row.label(text="Object per-axis Location, Rotation and Scale Alignment.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_apply", toggle=True)
        row.label(text="Apply Transformations while keeping the Bevel Width as well as the Child Transformations unchanged.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_select", toggle=True)
        row.label(text="Select Center Objects or Wire Objects.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_mesh_cut", toggle=True)
        row.label(text="Knife Intersect a Mesh-Object, using another one.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_surface_slide", toggle=True)
        row.label(text="Easily modify Mesh Topology, while maintaining Form.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_filebrowser_tools", toggle=True)
        row.label(text="Additional Tools/Shortcuts for the Filebrowser.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_smart_drive", toggle=True)
        row.label(text="Use one Object to drive another.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_unity", toggle=True)
        row.label(text="Unity related Tools.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_material_picker", toggle=True)
        row.label(text="Pick Materials from the Material Workspace's 3D View.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_group", toggle=True)
        row.label(text="Group Objects using Empties as Parents.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_thread", toggle=True)
        row.label(text="Easily turn Cylinder Faces into Thread.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_spin", toggle=True)
        row.label(text="Fixing Blender's Spin Operator.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_smooth", toggle=True)
        row.label(text="Toggle Smoothing in Korean Bevel and SubD workflows.")

        row = column.split(factor=0.25)
        row.prop(self, "activate_customize", toggle=True)
        row.label(text="Customize various Blender preferences, settings and keymaps.")


        # MACHIN3pies

        bb = b.box()
        bb.label(text="Pie Menus")

        column = bb.column(align=True)

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_modes_pie", toggle=True)
        row.label(text="Quick mode changing.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_save_pie", toggle=True)
        row.label(text="Save, Open, Append and Link. Load Recent, Previous and Next. Purge and Clean Out. ScreenCast.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_shading_pie", toggle=True)
        row.label(text="Control shading, overlays, eevee and some object properties.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_views_pie", toggle=True)
        row.label(text="Control views. Create and manage cameras.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_align_pie", toggle=True)
        row.label(text="Edit mesh and UV alignments.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_cursor_pie", toggle=True)
        row.label(text="Cursor and Origin manipulation.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_transform_pie", toggle=True)
        row.label(text="Transform Orientations and Pivots.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_snapping_pie", toggle=True)
        row.label(text="Snapping.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_collections_pie", toggle=True)
        row.label(text="Collection management.")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_workspace_pie", toggle=True)
        r = row.split(factor=0.4)
        r.label(text="Switch Workplaces.")
        r.label(text="If enabled, customize it in ui/pies.py", icon="INFO")

        row = column.split(factor=0.25, align=True)
        row.prop(self, "activate_tools_pie", toggle=True)
        row.label(text="Switch Tools, used primarily for BoxCutter/HardOps.")


        # RIGHT

        b = split.box()
        b.label(text="Settings")

        if any([getattr(bpy.types, "MACHIN3_" + name, False) for name in ["OT_material_picker", "OT_surface_slide", "OT_clean_up", "OT_clipping_toggle", "OT_group", "OT_transform_edge_constrained", "OT_focus", "MT_tools_pie"]]):
            bb = b.box()
            bb.label(text="HUD")

            column = bb.column()
            row = column.row()
            r = row.split(factor=0.2)
            r.prop(self, "HUD_scale", text="")
            r.label(text="HUD Scale")

            if any([getattr(bpy.types, "MACHIN3_" + name, False) for name in ["OT_material_picker", "OT_clean_up", "OT_clipping_toggle", "OT_group", "MT_tools_pie"]]):
                column = bb.column()
                column.label(text="Fade time")

                column = bb.column()
                row = column.row(align=True)

                if getattr(bpy.types, "MACHIN3_OT_clean_up", False):
                    row.prop(self, "HUD_fade_clean_up", text="Clean Up")

                if getattr(bpy.types, "MACHIN3_OT_clipping_toggle", False):
                    row.prop(self, "HUD_fade_clipping_toggle", text="Clipping Toggle")

                if getattr(bpy.types, "MACHIN3_OT_material_picker", False):
                    row.prop(self, "HUD_fade_material_picker", text="Material Picker")

                if getattr(bpy.types, "MACHIN3_OT_group", False):
                    row.prop(self, "HUD_fade_group", text="Group")

                if getattr(bpy.types, "MACHIN3_MT_tools_pie", False):
                    row.prop(self, "HUD_fade_tools_pie", text="Tools Pie")


        # VIEW 3D settings

        if getattr(bpy.types, "MACHIN3_OT_smart_vert", False):
            bb = b.box()
            bb.label(text="View 3D")

            column = bb.column()
            column.prop(self, "use_legacy_line_smoothing")


        # FOCUS

        if getattr(bpy.types, "MACHIN3_OT_focus", False):
            bb = b.box()
            bb.label(text="Focus")

            column = bb.column()
            column.prop(self, "focus_view_transition")


        # MATERIAL PICKER

        if getattr(bpy.types, "MACHIN3_OT_material_picker", False):
            bb = b.box()
            bb.label(text="Material Picker")

            column = bb.column(align=True)
            row = column.row(align=True)
            r = row.split(factor=0.2, align=True)
            r.prop(self, "matpick_workspace_names", text="")
            r.label(text="Workspace Names")

            row = column.row(align=True)
            r = row.split(factor=0.2, align=True)
            r.prop(self, "matpick_spacing_obj", text="")
            r.label(text="Object Mode fpacing")

            row = column.row(align=True)
            r = row.split(factor=0.2, align=True)
            r.prop(self, "matpick_spacing_edit", text="")
            r.label(text="Edit Mode Spacing")


        # GROUP

        if getattr(bpy.types, "MACHIN3_OT_group", False):
            bb = b.box()
            bb.label(text="Group")

            column = bb.column(align=True)

            row = column.split(factor=0.2, align=True)
            row.prop(self, "use_group_sub_menu", text='Sub Menu', toggle=True)
            row.label(text="Use Group Sub Menu in Object Context Menu.")

            row = column.split(factor=0.2, align=True)
            row.prop(self, "use_group_outliner_toggles", text='Outliner Toggles', toggle=True)
            row.label(text="Show Group Toggles in Outliner Header.")

            column.separator()

            row = column.row()
            r = row.split(factor=0.2)
            r.label(text="Basename")
            r.prop(self, "group_basename", text="")

            row = column.row()
            r = row.split(factor=0.2)
            r.prop(self, "group_auto_name", text='Auto Name', toggle=True)

            rr = r.row()
            rr.active = self.group_auto_name
            rr.prop(self, "group_prefix", text="Prefix")
            rr.prop(self, "group_suffix", text="Suffix")

            column.separator()

            row = column.row()
            r = row.split(factor=0.2)
            r.prop(self, "group_size", text="")
            r.label(text="Default Empty Draw Size")

            r.prop(self, "group_fade_sizes", text='Fade Sub Group Sizes')
            rr = r.row()
            rr.active = self.group_fade_sizes
            rr.prop(self, "group_fade_factor", text='Factor')


        # CUSTOMIZE

        if getattr(bpy.types, "MACHIN3_OT_customize", False):
            bb = b.box()
            bb.label(text="Customize")

            bbb = bb.box()
            column = bbb.column()

            row = column.row()
            row.prop(self, "custom_theme")
            row.prop(self, "custom_matcaps")
            row.prop(self, "custom_shading")

            row = column.row()
            row.prop(self, "custom_overlays")
            row.prop(self, "custom_outliner")
            row.prop(self, "custom_startup")

            bbb = bb.box()
            column = bbb.column()

            row = column.row()

            col = row.column()
            col.prop(self, "custom_preferences_interface")
            col.prop(self, "custom_preferences_keymap")

            col = row.column()
            col.prop(self, "custom_preferences_viewport")
            col.prop(self, "custom_preferences_system")

            col = row.column()
            col.prop(self, "custom_preferences_navigation")
            col.prop(self, "custom_preferences_save")

            if self.dirty_keymaps:
                row = column.row()
                row.label(text="Keymaps have been modified, restore them first.", icon="ERROR")
                row.operator("machin3.restore_keymaps", text="Restore now")
                row.label()

            column = bb.column()
            row = column.row()

            row.label()
            row.operator("machin3.customize", text="Customize")
            row.label()


        # MODES PIE

        if getattr(bpy.types, "MACHIN3_MT_modes_pie", False):
            bb = b.box()
            bb.label(text="Modes Pie")

            column = bb.column()

            column.prop(self, "toggle_cavity")
            column.prop(self, "sync_tools")


        # SAVE PIE

        if getattr(bpy.types, "MACHIN3_MT_save_pie", False):
            bb = b.box()
            bb.label(text="Save Pie: Append World and Materials")

            column = bb.column()

            column.prop(self, "appendworldpath")
            column.prop(self, "appendworldname")
            column.separator()

            column.prop(self, "appendmatspath")


            column = bb.column()

            row = column.row()
            rows = len(self.appendmats) if len(self.appendmats) > 6 else 6
            row.template_list("MACHIN3_UL_append_mats", "", self, "appendmats", self, "appendmatsIDX", rows=rows)

            c = row.column(align=True)
            c.operator("machin3.move_appendmat", text="", icon='TRIA_UP').direction = "UP"
            c.operator("machin3.move_appendmat", text="", icon='TRIA_DOWN').direction = "DOWN"

            c.separator()
            c.operator("machin3.clear_appendmats", text="", icon='LOOP_BACK')
            c.operator("machin3.remove_appendmat", text="", icon_value=get_icon('cancel'))
            c.separator()
            c.operator("machin3.populate_appendmats", text="", icon='MATERIAL')
            c.operator("machin3.rename_appendmat", text="", icon='OUTLINER_DATA_FONT')


            row = column.row()
            row.prop(self, "appendmatsname")
            row.operator("machin3.add_separator", text="", icon_value=get_icon('separator'))


            bb = b.box()
            bb.label(text="Save Pie: Screen Cast")

            split = bb.split(factor=0.5)

            col = split.column(align=True)

            row = col.row(align=True)
            r = row.split(factor=0.4, align=True)
            r.prop(self, "screencast_operator_count", text="")
            r.label(text="Operator Count")

            row = col.row(align=True)
            r = row.split(factor=0.4, align=True)
            r.prop(self, "screencast_fontsize", text="")
            r.label(text="Font Size")

            col = split.column()
            col.prop(self, "screencast_highlight_machin3")
            col.prop(self, "screencast_show_addon")
            col.prop(self, "screencast_show_idname")


        # SHADING PIE

        if getattr(bpy.types, "MACHIN3_MT_shading_pie", False):
            bb = b.box()
            bb.label(text="Shading Pie: Matcap Switch")

            column = bb.column()

            row = column.row()
            row.prop(self, "switchmatcap1")
            row.prop(self, "switchmatcap2")

            row = column.split(factor=0.5)
            row.prop(self, "matcap_switch_background")

            col = row.column()
            col.prop(self, "matcap2_force_single")
            col.prop(self, "matcap2_disable_overlays")

            if self.matcap_switch_background:
                row = column.row()
                row.prop(self, "matcap1_switch_background_type", expand=True)
                row.prop(self, "matcap2_switch_background_type", expand=True)

                if any([bg == 'VIEWPORT' for bg in [self.matcap1_switch_background_type, self.matcap2_switch_background_type]]):
                    row = column.split(factor=0.5)

                    if self.matcap1_switch_background_type == 'VIEWPORT':
                        row.prop(self, "matcap1_switch_background_viewport_color", text='')

                    else:
                        row.separator()

                    if self.matcap2_switch_background_type == 'VIEWPORT':
                        row.prop(self, "matcap2_switch_background_viewport_color", text='')

                    else:
                        row.separator()


        # VIEWPORT PIE

        if getattr(bpy.types, "MACHIN3_MT_viewport_pie", False):
            bb = b.box()
            bb.label(text="Views Pie: Custom views")

            column = bb.column()
            column.prop(self, "custom_views_use_trackball")

            if self.activate_transform_pie:
                column.prop(self, "custom_views_set_transform_preset")

            if self.activate_shading_pie:
                column.prop(self, "custom_views_toggle_axes_drawing")

            column.prop(self, "show_orbit_selection")
            column.prop(self, "show_orbit_method")


        # CURSOR and ORIGIN PIE

        if getattr(bpy.types, "MACHIN3_MT_cursor_pie", False):
            bb = b.box()
            bb.label(text="Cursor and Origin Pie")
            column = bb.column()

            column.prop(self, "cursor_show_to_grid")

            if self.activate_transform_pie or self.activate_shading_pie:
                    if self.activate_transform_pie:
                        column.prop(self, "cursor_set_transform_preset")

                    if self.activate_shading_pie:
                        column.prop(self, "cursor_toggle_axes_drawing")


        if getattr(bpy.types, "MACHIN3_MT_snapping_pie", False):
            bb = b.box()
            bb.label(text="Snapping Pie")
            column = bb.column()

            column.prop(self, "snap_show_absolute_grid")


        # TOOLS PIE

        if getattr(bpy.types, "MACHIN3_MT_tools_pie", False):
            bb = b.box()
            bb.label(text="Tools Pie")

            split = bb.split(factor=0.5)

            col = split.column()
            col.prop(self, "tools_show_boxcutter_presets")
            col.prop(self, "tools_show_hardops_menu")

            col = split.column()
            col.prop(self, "tools_show_quick_favorites")
            col.prop(self, "tools_show_tool_bar")


        # NO SETTINGS

        if not any([getattr(bpy.types, "MACHIN3_" + name, False) for name in has_settings]):
            b.label(text="No tools or pie menus with settings have been activated.")

    def draw_keymaps(self, box):
        wm = bpy.context.window_manager
        # kc = wm.keyconfigs.addon
        kc = wm.keyconfigs.user

        from . registration import keys

        split = box.split()

        b = split.box()
        b.label(text="Tools")

        if not self.draw_tool_keymaps(kc, keys, b):
            b.label(text="No keymappings available, because none of the tools have been activated.")


        b = split.box()
        b.label(text="Pie Menus")

        if not self.draw_pie_keymaps(kc, keys, b):
            b.label(text="No keymappings created, because none of the pies have been activated.")

    def draw_about(self, box):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        column = box.column(align=True)

        row = column.row(align=True)

        row.scale_y = 1.5
        row.operator("wm.url_open", text='MACHIN3tools', icon='INFO').url = 'https://machin3.io/MACHIN3tools/'
        row.operator("wm.url_open", text='MACHINƎ.io', icon='WORLD').url = 'https://machin3.io'
        row.operator("wm.url_open", text='blenderartists', icon_value=get_icon('blenderartists')).url = 'https://blenderartists.org/t/machin3tools/1135716/'

        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text='Twitter', icon_value=get_icon('twitter')).url = 'https://twitter.com/machin3io'
        row.operator("wm.url_open", text='Youtube', icon_value=get_icon('youtube')).url = 'https://www.youtube.com/c/MACHIN3/'
        row.operator("wm.url_open", text='Artstation', icon_value=get_icon('artstation')).url = 'https://www.artstation.com/machin3'

        column.separator()

        row = column.row(align=True)
        row.scale_y = 1.5
        row.operator("wm.url_open", text='DECALmachine', icon_value=get_icon('save' if decalmachine else 'cancel_grey')).url = 'https://decal.machin3.io'
        row.operator("wm.url_open", text='MESHmachine', icon_value=get_icon('save' if meshmachine else 'cancel_grey')).url = 'https://mesh.machin3.io'

    def draw_tool_keymaps(self, kc, keysdict, layout):
        drawn = False

        for name in keysdict:
            if "PIE" not in name:
                keylist = keysdict.get(name)

                if draw_keymap_items(kc, name, keylist, layout):
                    drawn = True

        return drawn

    def draw_pie_keymaps(self, kc, keysdict, layout):
        drawn = False

        for name in keysdict:
            if "PIE" in name:
                keylist = keysdict.get(name)

                if draw_keymap_items(kc, name, keylist, layout):
                    drawn = True

        return drawn
