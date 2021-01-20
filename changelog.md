


* Modes pie
    - fix several gpenceil ("Surface Draw mode") issues due to 2.83+ API changes


* CleanUp tool
    - add option to find/select non-planar faces


* Shading pie
    - add ColorizeObjectsFromGroups tool 
         - recursively assign random colors to each group in the selection
         - `ALT` use existing group empty colors, instead of new random colors, to unify group objects colors
         - `CTRL` only colorize the active group

* add CursorSpin tool
    - in the Extrude `Alt + E` menu
    - CursorSpin basically just fixes Blender's native Spin operator
         - for Blender's native op is still stuck in a world where the Cursor had no rotation,
         - and so there is no convenient way to set the spin axis
         - while the spin center is properly initiated from the cursor location, the axis isn't
         - the only way to use Blender's spin op is using the Spin tool, which does it properly
         - CursorSpin does the same, but is also directly available from the Extrude menu, so there's no need to the Spin tool


* add Add Thread tool
    - in edit mesh context menu

 

* SelectedToCursor tool
    - support "Affect Only Parents" transform option 


* Transform pie
   - add "Affect Only Group Origin" option
       - this enables "Affect Only Parents", and disables Group Auto-Select at the same time, allowing for convenient "Group Origin" changes


* Align tool
    - support aligning active between 2 selected object
    - support groups
    - support "Affect Only Parents" transform option


* SmartEdge tool
    - add Knife Project capability
        - if the selection is separated from the rest of the mesh, run knifeproject
        - useful to quickly knife project duplicated edge or face selections

    - Offset Edges (Korean Bevel)
        - properly remove shaprs, when the Bevel tool is chosen


* Tools Pie
    - fix issue when not in Object or EDIT_MESH modes
    - fix issue when drawing tool name, if the pie's tools are customized


* M3 Theme
    - tone down outliner selection color


* CursorToSelected + SelectedToCursor tools
    - properly support group auto-selections
        - if the active object is a group empty, ignore all other selected objects
        - this means you can easily move a group to the cursor or the cursor to a group, without having to disable auto-select
 

* SmartVert tool
    - support vert bevel for single vert selections



* add comprehensive, export friendly Group tool set
    - group objects by parenting to empties
    - tools include Group `CTRL + G` , Ungroup, Groupify, Add and Remove Objects/Groups from Group, Select `SHIFT + dbl-LMB`and Duplicate Group
    - support auto-select, recursive-select and group-empty hiding - all enabled by default - and more
    - outliner shortcuts `1`, `2`,`3`, `4` to Toggle Group Mode, Expand and Collapse, and Toggle Children


* Focus tool
    - fix invert mode being initiated via ALT modifier key
 

* SurfaceSlide tool
    - fix issues with booleans, by stripping all mods from SURFACE reference object

* add SelectWireObjects tool
    - select wire objects, such as ones commonly used for booleans
    - ALT: Hide them
    - CTRL: include Empties too

* Customize tool
    - Overlays
        - disable show_fade_inactive edit mode overlay

    - Keymap
        - ensure ctrl + b bevel keymap uses OFFSET
        - change shift + ctrl + b vert bevel keymap to edge percent bevel
            - you can easily do vertbevels using SmartVert, or regular bevels switched to Vert via `V`
            - switching mode using M is cumbersome however, hence why it gets its own keymap
        - force bevel keymap profile of 0.6
           - this is helpful when alternating between Smart Edge Offset Edges, which forces a profile of 1
        - deactivavate `mesh.fill` `ALT + F` keymap
            - this means `ALT + F` can be used from edit mesh mode to center the view on the mouse, just like in object mode


* Material Picker
    - expose workspace names the button appears on in addon prefs 
    -  optionally assign material too, using ALT
