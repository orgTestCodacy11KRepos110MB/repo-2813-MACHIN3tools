import os
from . system import printd


def get_catalogs_from_asset_libraries(context, debug=False):
    '''
    scan cat files of all asset libraries and get the uuid for each catalog
    if different catalogs share a name, only take the first one
    '''

    asset_libraries = context.preferences.filepaths.asset_libraries
    all_catalogs = []

    for lib in asset_libraries:
        name = lib.name
        path = lib.path

        cat_path = os.path.join(path, 'blender_assets.cats.txt')

        if os.path.exists(cat_path):
            if debug:
                print(name, cat_path)

            with open(cat_path) as f:
                lines = f.readlines()

            for line in lines:
                if line != '\n' and not any([line.startswith(skip) for skip in ['#', 'VERSION']]) and len(line.split(':')) == 3:
                    all_catalogs.append(line[:-1])

    catalogs = {}

    for cat in all_catalogs:
        uuid, catalog, simple_name = cat.split(':')

        if catalog not in catalogs:
            catalogs[catalog] = {'uuid': uuid,
                                   'simple_name': simple_name}

    if debug:
        printd(catalogs)

    return catalogs
