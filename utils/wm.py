

def get_last_operators(context, debug=False):
    operators = []

    for op in context.window_manager.operators:
        idname = op.bl_idname.replace('_OT_', '.').lower()
        label = op.bl_label.replace('MACHIN3: ', '')
        prop = ''


        # skip pie menu calls

        if idname.startswith('machin3.call_'):
            continue

        # show props, special modes and custom labels

        # MACHIN3tools

        elif idname == 'machin3.set_tool_by_name':
            prop = op.properties.get('name', '')

        elif idname == 'machin3.switch_workspace':
            prop = op.properties.get('name', '')

        elif idname == 'machin3.switch_shading':
            toggled_overlays = getattr(op, 'toggled_overlays', False)
            prop = op.properties.get('shading_type', '').capitalize()

            if toggled_overlays:
                label = f"{toggled_overlays} Overlays"

        elif idname == 'machin3.edit_mode':
            toggled_object = getattr(op, 'toggled_object', False)
            label = 'Object Mode' if toggled_object else 'Edit Mesh Mode'

        elif idname == 'machin3.mesh_mode':
            mode = op.properties.get('mode', '')
            label = f"{mode.capitalize()} Mode"

        elif idname == 'machin3.smart_vert':
            if op.properties.get('slideoverride', ''):
                prop = 'SideExtend'

            elif op.properties.get('vertbevel', False):
                prop = 'VertBevel'

            else:
                modeint = op.properties.get('mode')
                mergetypeint = op.properties.get('mergetype')

                mode = 'Merge' if modeint== 0 else 'Connect'
                mergetype = 'Last' if mergetypeint == 0 else 'Center' if mergetypeint == 1 else 'Paths'
                prop = mode + mergetype

        elif idname == 'machin3.smart_edge':
            if op.properties.get('is_knife_project', False):
                prop = 'KnifeProject'

            elif op.properties.get('sharp', False):
                prop = 'ToggleSharp'

            elif op.properties.get('offset', False):
                prop = 'OffsetEdges / KoreanBevel'

        elif idname == 'machin3.focus':
            if op.properties.get('method', 0) == 1:
                prop = 'LocalView'


        # MESHmachine

        elif idname == 'machin3.select':
            if getattr(op, 'vgroup', False):
                prop = 'VertexGroup'
            elif getattr(op, 'faceloop', False):
                prop = 'FaceLoop'
            else:
                prop = 'Loop' if op.properties.get('loop', False) else 'Sharp'

        operators.append((label, idname, prop))

    if debug:
        for label, idname, prop in operators:
            print(label, f"({idname})", prop)

    return operators
