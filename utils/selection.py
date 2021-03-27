

# SORTING

def get_selected_vert_sequences(verts, ensure_seq_len=False, debug=False):
    '''
    return sorted lists of vertices, where vertices are considered connected if their edges are selected, and faces are not selected
    '''

    sequences = []

    # if edge loops are non-cyclic, it matters at what vert you start the sorting
    noncyclicstartverts = [v for v in verts if len([e for e in v.link_edges if e.select]) == 1]

    if noncyclicstartverts:
        v = noncyclicstartverts[0]

    # in cyclic edge loops, any vert works
    else:
        v = verts[0]

    seq = []

    while verts:
        seq.append(v)

        # safty precaution,for EPanel, where people may select intersecting edge loops
        if v not in verts:
            break

        else:
            verts.remove(v)

        if v in noncyclicstartverts:
            noncyclicstartverts.remove(v)

        nextv = [e.other_vert(v) for e in v.link_edges if e.select and e.other_vert(v) not in seq]

        # next vert in sequence
        if nextv:
            v = nextv[0]

        # finished a sequence
        else:
            # determine cyclicity
            cyclic = True if len([e for e in v.link_edges if e.select]) == 2 else False

            # store sequence and cyclicity
            sequences.append((seq, cyclic))

            # start a new sequence, if there are still verts left
            if verts:
                if noncyclicstartverts:
                    v = noncyclicstartverts[0]
                else:
                    v = verts[0]

                seq = []

    # again for EPanel, make sure sequences are longer than one vert
    if ensure_seq_len:
        seqs = []

        for seq, cyclic in sequences:
            if len(seq) > 1:
                seqs.append((seq, cyclic))

        sequences = seqs

    if debug:
        for seq, cyclic in sequences:
            print(cyclic, [v.index for v in seq])

    return sequences


def get_edges_vert_sequences(verts, edges, debug=False):
    """
    return sorted lists of vertices, where vertices are considered connected if they are verts of the passed in edges
    selection states are completely ignored.
    """
    sequences = []

    # if edge loops are non-cyclic, it matters at what vert you start the sorting
    noncyclicstartverts = [v for v in verts if len([e for e in v.link_edges if e in edges]) == 1]

    if noncyclicstartverts:
        v = noncyclicstartverts[0]

    # in cyclic edge loops, any vert works
    else:
        v = verts[0]

    seq = []

    while verts:
        seq.append(v)
        verts.remove(v)

        if v in noncyclicstartverts:
            noncyclicstartverts.remove(v)

        nextv = [e.other_vert(v) for e in v.link_edges if e in edges and e.other_vert(v) not in seq]

        # next vert in sequence
        if nextv:
            v = nextv[0]

        # finished a sequence
        else:
            # determine cyclicity
            cyclic = True if len([e for e in v.link_edges if e in edges]) == 2 else False

            # store sequence and cyclicity
            sequences.append((seq, cyclic))

            # start a new sequence, if there are still verts left
            if verts:
                if noncyclicstartverts:
                    v = noncyclicstartverts[0]
                else:
                    v = verts[0]

                seq = []

    if debug:
        for verts, cyclic in sequences:
            print(cyclic, [v.index for v in verts])

    return sequences


# REGIONS

def get_selection_islands(faces, debug=False):
    '''
    return island tuples (verts, edges, faces), sorted by amount of faces in each, highest first
    '''

    if debug:
        print("selected:", [f.index for f in faces])

    face_islands = []

    while faces:
        island = [faces[0]]
        foundmore = [faces[0]]

        if debug:
            print("island:", [f.index for f in island])
            print("foundmore:", [f.index for f in foundmore])

        while foundmore:
            for e in foundmore[0].edges:
                # get unseen selected border faces
                bf = [f for f in e.link_faces if f.select and f not in island]
                if bf:
                    island.append(bf[0])
                    foundmore.append(bf[0])

            if debug:
                print("popping", foundmore[0].index)

            foundmore.pop(0)

        face_islands.append(island)

        for f in island:
            faces.remove(f)

    if debug:
        print()
        for idx, island in enumerate(face_islands):
            print("island:", idx)
            print(" » ", ", ".join([str(f.index) for f in island]))


    islands = []

    for fi in face_islands:
        vi = set()
        ei = set()

        for f in fi:
            vi.update(f.verts)
            ei.update(f.edges)

            # f.select = False

        islands.append((list(vi), list(ei), fi))

    return sorted(islands, key=lambda x: len(x[2]), reverse=True)


def get_boundary_edges(faces, region_to_loop=False):
    """
    return boundary edges of selected faces
    as boundary, non-manifold edges, as well as edges, haveing any unselected face
    this is faster than mesh.region_to_loop() btw, even with region_to_loop True
    """

    boundary_edges = [e for f in faces for e in f.edges if (not e.is_manifold) or (any(not f.select for f in e.link_faces))]

    if region_to_loop:
        for f in faces:
            f.select_set(False)

        for e in boundary_edges:
            e.select_set(True)

    return boundary_edges
