import os

from vpython import *
import settings

import mouse
import json

extension = ".struct"
file_directory = os.path.dirname(__file__)
save_directory = "templates"

# Create a 3D scene
scene = canvas(title="3D Block World", width=800, height=550, center=vector(0, 0, 0), background=color.white,
               fullscreen=False, userspin=False, userzoom=False, up=vector(0, 1, 0), forward=vector(1, 0, 0),
               align='left')

# List of blocks in the format (x, y, z, block_id)

# Dictionary to map block IDs to their visual representations
block_colors = {
    0: color.white,  # air
    1: color.gray(0.5),  # stone
    2: color.purple,  # dirt
    3: color.orange,  # tronc
    4: vector(125 / 255, 219 / 255, 138 / 255),  # feuille
    5: color.blue,  # water
    6: vector(0, 255 / 255, 0),  # herbe
    7: color.gray(0.8),  # fer
    11: vector(255 / 255, 0, 0),  # lave
    12: vector(1, 1, 0.3),  # sable
    13: vector(255 / 255, 200 / 255, 80 / 255),  # planche
    14.1: vector(0.8, 0.4, 0),  # porte bas
    14.2: vector(1, 0.6, 0.2),  # porte haut
    21: color.white,  # verre
    16: vector(0.95, 0.95, 0.95),  # neige
    17: vector(40 / 255, 40 / 255, 100 / 255),  # basalte
    18: vector(255 / 255, 0, 0),  # lave

    # wood
    # Add more block colors as needed
}

a = {
    0: "air",
    1: "pierre",
    2: "terre",
    3: "tronc",
    4: "feuille",
    5: "eau",
    6: "herbe",
    7: "fer",
    8: "diamand",
    9: "charbon",
    19: "cuivre",
    11: "lave",
    12: "sable",
    13: "planche",
    14.1: "porte_bas",
    14.2: "porte_haut",
    21: "verre",
    16: "neige",
    17: "basalte",
    18: "lave"
}


def relative_pos(orientation):
    gap = 0.3
    match orientation:
        case 1:
            return (-0.5, 0, 0), (1 - gap, 1, 1), (1, 0, 0)
        case 2:
            return (0.5, 0, 0), (1 - gap, 1, 1), (-1, 0, 0)
        case 3:
            return (0, -0.5, 0), (1, 1 - gap, 1), (0, 1, 0)
        case 4:
            return (0, 0.5, 0), (1, 1 - gap, 1), (0, -1, 0)


def place_block(data):
    global placed_blocks
    *coords, bloc_id, orientation = data
    block_color = block_colors[bloc_id]
    if placed_blocks.get(tuple(coords)):
        delete_block((*coords, ""))
    if orientation != 0:
        pos, size, axis = relative_pos(orientation)
        placed_blocks[*coords] = [bloc_id,
                                  pyramid(pos=vector(coords[0] + pos[0], coords[1] + pos[1], coords[2] + pos[2]),
                                          size=vector(1, 1, 1), color=block_color, canvas=scene, axis=vector(*axis)),
                                  orientation]
    else:
        placed_blocks[*coords] = [bloc_id,
                                  box(pos=vector(coords[0], coords[1], coords[2]),
                                      size=vector(1, 1, 1),
                                      color=block_color, canvas=scene), orientation]
    """box(pos=vector(coords[0]+pos[0], coords[1]+pos[1], coords[2]+pos[2]),
                                  size=vector(*size),
                                  color=color, canvas=scene)]"""
    placed_blocks[*coords][1].visible = True
    print(coords)
    print(placed_blocks[tuple(coords)])
    return placed_blocks
    # placed_blocks[*coords].visible = False
    # placed_blocks[*coords].visible = True


def empty_scene():
    global placed_blocks
    i = input("Are you sure you want to empty ? (y/n)")
    if i == "y":
        scene.empty()
        placed_blocks = {}


def delete_block(data):
    global placed_blocks, scene
    *coords, _, _ = data
    if placed_blocks.get(tuple(coords)):
        print("delete")
        print(coords)
        if isinstance(placed_blocks[tuple(coords)], tuple):
            placed_blocks[tuple(coords)] = list(placed_blocks[tuple(coords)])
        scene.visible = False
        placed_blocks[tuple(coords)][1].color = color.white

        scene.visible = True
        placed_blocks[tuple(coords)][0] = None

        # placed_blocks[tuple(coords)].size = vector(0.1, 0.1,0.1)

        # print(placed_blocks[tuple(coords)].visible)
    return placed_blocks


def change_type(m):
    global selection_bloc_coords, possible_types
    mouse.click()
    print(m.selected)
    if block_colors.get(settings.BLOC_VERS_ID[m.selected.lower()]):
        selection_bloc_coords[3] = settings.BLOC_VERS_ID[m.selected.lower()]
    else:
        m.selected = None
    # update_selection_bloc()


def clone_z():
    z0 = int(input("z plane to clone : "))
    dz = int(input("change in z : "))
    for i in list(placed_blocks.keys()):
        if i[2] == z0:
            place_block((i[0], i[1], i[2] + dz, placed_blocks[i][0]))


def clone_x():
    x0 = int(input("x plane to clone : "))
    dx = int(input("change in x : "))
    for i in list(placed_blocks.keys()):
        if i[0] == x0:
            place_block((i[0] + dx, i[1], i[2], placed_blocks[i][0]))


def clone_y():
    y0 = int(input("y plane to clone : "))
    dy = int(input("change in y : "))
    for i in list(placed_blocks.keys()):
        if i[1] == y0:
            place_block((i[0], i[1] + dy, i[2], placed_blocks[i][0]))


def save_struct():
    global placed_blocks
    print(placed_blocks)
    name = input("Name of the structure to save : ")
    complete_name = os.path.join(file_directory, save_directory, name + extension)
    blocs_list = []
    for i in list(placed_blocks.keys()):

        if placed_blocks[i][0]:
            temp = list(i)
            temp.append(placed_blocks[i][0])
            temp.append(placed_blocks[i][2])
            blocs_list.append(temp)

    with open(complete_name, 'w') as fw:
        fw.write(json.dumps(blocs_list))


def open_structure():
    name = input("Name of the structure to load: ")
    complete_name = os.path.join(file_directory, save_directory, name + extension)
    with open(complete_name, 'r') as fr:
        blocs_list = json.loads(fr.read())
    for i in blocs_list:
        if len(i) > 4:
            place_block((*i,))
        else:
            place_block((*i, 0))


def change_orientation():
    global selection_bloc_coords
    global current_orientation

    match current_orientation:
        case 0:
            current_orientation = 1
        case 1:
            current_orientation = 3
        case 2:
            current_orientation = 4
        case 3:
            current_orientation = 2
        case 4:
            current_orientation = 0

    """
    if current_orientation == 4:
        current_orientation = 0
    else:
        current_orientation += 1
    """
    selection_bloc_coords[4] = current_orientation
    update_selection_bloc()


def key_handler(keys):
    global selection_bloc_coords, pressed_keys
    k = ["z", "s", "q", "d", ' ', 'shift']

    for i in pressed_keys:
        if not (i in keys):
            pressed_keys.remove(i)
    vect_shift = (0, 0, 0)
    # print(keys)
    if k[0] in keys and not (k[0] in pressed_keys):
        vect_shift = (1, 0, 0)
    if k[1] in keys and not (k[1] in pressed_keys):
        vect_shift = (-1, 0, 0)
    if k[2] in keys and not (k[2] in pressed_keys):
        vect_shift = (0, 1, 0)
    if k[3] in keys and not (k[3] in pressed_keys):
        vect_shift = (0, -1, 0)
    if k[4] in keys and not (k[4] in pressed_keys):
        vect_shift = (0, 0, 1)
    if k[5] in keys and not (k[5] in pressed_keys):
        vect_shift = (0, 0, -1)
    if "y" in keys and not ("y" in pressed_keys):
        change_orientation()
    if "0" in keys:
        empty_scene()
    pb = placed_blocks
    if "\n" in keys:
        pb = place_block(selection_bloc_coords)
    if "delete" in keys:
        pb = delete_block(selection_bloc_coords)
    for _ in range(3):
        selection_bloc_coords[_] += vect_shift[_]
    if "n" in keys:
        save_struct()
    if "b" in keys:
        open_structure()

    if "v" in keys:
        clone_z()
    if "f" in keys:
        clone_y()
    if "r" in keys:
        clone_x()

    update_selection_bloc()
    pressed_keys += keys
    return pb


def update_selection_bloc():
    global selection_bloc, selection_bloc_coords, selection_bloc_direction
    selection_bloc.visible = False
    selection_bloc = box(opacity=1, pos=vector(*selection_bloc_coords[:3]), size=vector(1, 1, 1), color=color.black,
                         canvas=scene)
    if selection_bloc_coords[4] == 0:
        selection_bloc_direction.visible = False
    else:
        orientation = [0, 0, 0]
        match selection_bloc_coords[4]:

            case 1:
                orientation = (1, 0, 0)
            case 2:
                orientation = (-1, 0, 0)
            case 3:
                orientation = (0, 1, 0)
            case 4:
                orientation = (0, -1, 0)
            case 5:
                orientation = (1, 1, 0)
            case 6:
                orientation = (-1, -1, 0)
            case 7:
                orientation = (1, -1, 0)
            case 8:
                orientation = (-1, 1, 0)
            case 9:
                orientation = (1, 0, 1)
            case 10:
                orientation = (-1, 0, 1)
            case 11:
                orientation = (0, 1, 1)
            case 12:
                orientation = (0, -1, 1)
            case 13:
                orientation = (1, 1, 1)
            case 14:
                orientation = (-1, -1, 1)
            case 15:
                orientation = (1, -1, 1)
            case 16:
                orientation = (-1, 1, 1)
            case 17:
                orientation = (1, 0, -1)
            case 18:
                orientation = (-1, 0, -1)
            case 19:
                orientation = (0, 1, -1)
            case 20:
                orientation = (0, -1, -1)
            case 21:
                orientation = (1, 1, -1)
            case 22:
                orientation = (-1, -1, -1)
            case 23:
                orientation = (1, -1, -1)
            case 24:
                orientation = (-1, 1, -1)

        selection_bloc_direction.visible = False
        selection_bloc_direction = arrow(pos=vector(*selection_bloc_coords[:3]), axis=vector(*orientation), length=3)
        selection_bloc_direction.visible = True


current_orientation = 0
pressed_keys = []
selection_bloc_coords = [0, 0, 0, 1, 0]
selection_bloc = box(pos=vector(0, 0, 0), size=vector(1, 1, 1), color=color.black)
selection_bloc_direction = arrow(pos=vector(0, 0, 0), axis=vector(0, 0, 0))
selection_bloc_direction.visible = False
update_selection_bloc()
placed_blocks = {}

# scene.caption = "  " + settings.ID_VERS_BLOC[selection_bloc_coords[-1]].title()
possible_types = list(settings.ID_VERS_BLOC.values())
scene.append_to_caption('\n\n')
types_menu = menu(choices=possible_types, bind=change_type)

box(pos=vector(0, 0, -1), size=vector(1, 1, 1), color=color.black)
for x in range(0, 6):
    for y in range(0, 6):
        if (x + y) % 2 == 0:
            box(pos=vector(x, y, -1), size=vector(1, 1, 1), color=color.green)
        else:
            box(pos=vector(x, y, -1), size=vector(1, 1, 1), color=color.blue)

# Initial camera position
camera_pos = vector(0, 0, 0)

move_speed = 1

# Initial camera rotation angles (in radians)
x_angle = 50
z_angle = 30
y_angle = -20

# Rotation speed
rotation_speed = 0.02

# Run the 3D scene with keyboard controls
while True:

    rate(30)  # Maximum frame rate
    scene.title = str(selection_bloc_coords[:-1])
    # Check keyboard input
    keys_pressed = keysdown()
    """
    if keyboard.is_pressed("space"):
        commands_handler()
    """
    placed_blocks = key_handler(keys_pressed)
    if 'right' in keys_pressed:
        camera_pos.x += move_speed
    if 'left' in keys_pressed:
        camera_pos.x -= move_speed
    if 'down' in keys_pressed:
        camera_pos.z -= move_speed
    if 'up' in keys_pressed:
        camera_pos.z += move_speed
    if 't' in keys_pressed:
        camera_pos.y -= move_speed
    if 'g' in keys_pressed:
        camera_pos.y += move_speed

    # Update camera rotation based on key presses
    if 'l' in keys_pressed:
        z_angle -= rotation_speed
    if 'm' in keys_pressed:
        z_angle += rotation_speed
    if 'p' in keys_pressed:
        x_angle += rotation_speed
    if 'k' in keys_pressed:
        x_angle -= rotation_speed
    if 'i' in keys_pressed:
        y_angle += rotation_speed
    if 'j' in keys_pressed:
        y_angle -= rotation_speed

    # if "b" in keys:
    # print(scene.camera.pos)

    # Update camera position and rotation
    scene.camera.pos = camera_pos
    scene.camera.rotate(angle=x_angle, axis=vector(1, 0, 0))
    scene.camera.rotate(angle=z_angle, axis=vector(0, 0, 1))
    scene.camera.rotate(angle=y_angle, axis=vector(0, 1, 0))
    x_angle = 0
    z_angle = 0
    y_angle = 0
