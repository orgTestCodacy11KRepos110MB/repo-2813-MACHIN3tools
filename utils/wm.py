

def get_last_operators(context, debug=False):
    operators = []

    for op in context.window_manager.operators:
        idname = op.bl_idname.replace('_OT_', '.').lower()
        label = op.bl_label.replace('MACHIN3: ', '')
        prop = ''


        # skip pie menu calls

        if idname.startswith('machin3.call_'):
            continue


        # show props and special modes

        elif idname == 'machin3.set_tool_by_name':
            prop = op.properties.get('name', '')

        elif idname == 'machin3.smart_vert':
            if op.properties.get('slideoverride', ''):
                prop = 'SideExtend'

        elif idname == 'machin3.smart_edge':
            if op.properties.get('is_knife_project', ''):
                prop = 'KnifeProject'

            elif op.properties.get('sharp', ''):
                prop = 'ToggleSharp'

            elif op.properties.get('offset', ''):
                prop = 'OffsetEdges / KoreanBevel'

        elif idname == 'machin3.focus':
            if op.properties.get('method', '') == 1:
                prop = 'LocalView'


        operators.append((label, idname, prop))

    if debug:
        for label, idname, prop in operators:
            print(label, f"({idname})", prop)

    return operators
