import numpy as np
import os
import json

current = os.path.dirname(__file__)
templates_folder = os.path.join(current, "templates")
# rotated_folder = os.path.join(current, "rotated")
rotated_folder = os.path.join(current, "palmiers")

def turn_structure(array_to_turn):
    size_y, size_x = array_to_turn.shape[0], array_to_turn.shape[1]
    size = max(size_x, size_y)
    if len(array_to_turn.shape) > 2:
        nw_array = np.zeros((size, size, array_to_turn.shape[2]))
    else:
        nw_array = np.zeros((size, size))
    for Y in range(size_y):
        for X in range(size_x):
            nw_array[size - 1 - X, Y] = array_to_turn[Y, X]
    return nw_array


with open(os.path.join(current, "palm_generated.json"), "r") as fr:
    data = json.load(fr)


files = [i[0] for i in data]
for file in files:
    path = os.path.join(templates_folder, file)
    with open(path, "r") as fr:
        data = json.load(fr)
    arr_dict = {}
    for i in data:
        arr_dict[i[0], i[1], i[2]] = i[3]
    xs, ys, zs = [i[0] for i in data], [i[1] for i in data], [i[2] for i in data]
    x_range = max(xs)-min(xs)+1
    y_range = max(ys)-min(ys)+1
    z_range = max(zs)-min(zs)+1
    x_min, y_min, z_min = min(xs), min(ys), min(zs)
    array = np.zeros((x_range, y_range, z_range))
    print(arr_dict)
    print(x_min, y_min, z_min)
    print(17 in list(arr_dict.values()))

    for x in range(x_range):
        for y in range(y_range):
            for z in range(z_range):
                if arr_dict.get((x+x_min, y+y_min, z+z_min)) == 17:
                    print("-------------------------- STOP ---------------------")
                if arr_dict.get((x+x_min, y+y_min, z+z_min)):
                    array[x, y, z] = int(arr_dict[x+x_min, y+y_min, z+z_min])

    print(array)
    arrays = [array]
    print(arrays)
    for i in range(3):
        arrays.append(turn_structure(arrays[-1]))
    for i, item in enumerate(arrays):
        file_name = file.replace(".struct", "")
        file_name = file_name + f"_rotation_[{i}].struct"
        np.save(os.path.join(rotated_folder, file_name), item)
