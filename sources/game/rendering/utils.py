
def print_gpu_data(data: str, byte_sep, byte_group_sep, element_size, elements_per_vertex, vertex_per_mesh):
    byte_group_size = element_size * 2
    newline_spacing = elements_per_vertex * element_size * 2
    new_vertex_spacing = vertex_per_mesh * newline_spacing
    vertex_number = 0

    txt = ""

    for i, letter in enumerate(data):
        if i % new_vertex_spacing == 0:
            txt += "\n"
        if i % newline_spacing == 0:
            txt += "\n" + "vertex " + str(vertex_number) + " :  "
            vertex_number += 1
        elif i % byte_group_size == 0:
            txt += byte_group_sep
        elif i & 1 == 0:
            txt += byte_sep
        txt += letter

    print(txt)
