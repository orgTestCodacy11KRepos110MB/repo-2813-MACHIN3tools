

def get_last_operators(context, debug=False):
    operators = []

    for op in context.window_manager.operators:
        operators.append((op.bl_idname.replace('_OT_', '.').lower(), op.bl_label.replace('MACHIN3: ', ''), op.bl_description))

    if debug:
        for idname, label, description in operators:
            print(label, f"({idname})")

    return operators
