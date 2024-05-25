import random
import numpy as np
import game.terrain_generation.settings as settings
from game.terrain_generation.villages import Village
import game.terrain_generation.villages as villages
from game.terrain_generation.volcano import Volcano
import game.terrain_generation.volcano as volcans


chunks_done = {Village: set(), Volcano: set()}

volcano_table = set()
to_check = (
    (0, 1),
    (0, -1),
    (1, 0),
    (-1, 0),
    (1, 1),
    (-1, 1),
    (1, -1),
    (-1, -1)
)


def generate_positions(entity, top_left, bottom_right, seed, player_pos, par_1000x1000, step):
    """Genere les positions d'une structure dans une zone qui va de top_left à bottom_right,
    avec une seed donnée, et un nombre theorique de structure par 1000x1000"""
    global chunks_done

    # calcule la chance 1/proba qu'il y ait une structure par itération, evite de faire ce calcul de manière redondante
    proba = ((1000 / step) * (1000 / step)) / par_1000x1000
    positions = []

    for x in range(top_left[0], bottom_right[0], step):
        for y in range(top_left[1], bottom_right[1], step):
            
            if (x, y) not in chunks_done[entity]:  # Check si la chunk a déjà été scannée
                chunks_done[entity].add((x, y))
                if entity == Volcano:
                    # Fais un check qui évite d'avoir plusieurs volcans à côté
                    check = True
                    for add_x, add_y in to_check:
                        if (x+add_x*step, y+add_y*step) in volcano_table:
                            check = False

                    if not check:
                        continue
                    volcano_table.add((x, y))

                # place au centre d'un chunk
                sx = x + 8
                sy = y + 8
                custom_seed = str(seed) + "_" + str(sx) + "_" + str(sy)
                random.seed(custom_seed)
                # teste si il y a une entité à ces coordonnées
                rd = random.randint(0, int(proba - 1))
                if rd == 0:
                    positions.append((sx, sy))
    seeds = settings.setSeeds(seed, len(positions))
    for i, (sx, sy) in enumerate(positions):
        # décale un peu la position pour pas que les structures ne soient tout le temps au même endroit
        random.seed(seed + str(sx) + str(sy))
        x = sx + random.randint(-3, 3) * settings.CHUNK_SIZE
        random.seed(seed + str(sx) + str(sy) + "_")
        y = sy + random.randint(-3, 3) * settings.CHUNK_SIZE
        # place l'entité
        entity([x, y], seeds[i], player_pos)


def pregenerate(top_left, bottom_right, seeds, player_pos, is_initial_scan=False):
    """Pregenere les positions structures lors d'un scan"""
    global chunks_done
    if not is_initial_scan:
        if not(chunks_done[Village] or chunks_done[Volcano]):
            # Si ce n'est pas le scan initial et que les chunks_done sont vide
            # On a déjà fait un préscan auparavant lors de la géneration initiale, pour éviter de le refaire,
            # on va artificiellement ajouter les chunks déjà scannées à chunks_done
            for x in range(settings.INITIAL_PRESCAN[0][0], settings.INITIAL_PRESCAN[1][0],
                           settings.STRUCTURES_CHECK_STEP):
                for y in range(settings.INITIAL_PRESCAN[0][1], settings.INITIAL_PRESCAN[1][1],
                               settings.STRUCTURES_CHECK_STEP):
                    chunks_done[Village].add((x, y))
                    chunks_done[Volcano].add((x, y))
        coeff = 1.2
    else:
        coeff = 1


    if settings.GENERATION["volcanos"]:
        if not is_initial_scan:
            coeff *= 1.1
        # genere les position des volcans
        generate_positions(Volcano, top_left, bottom_right, seeds[0], player_pos,
                           settings.VOLCANOS_BY_1000x1000 * coeff* 1.5, settings.STRUCTURES_CHECK_STEP)
    if settings.GENERATION["villages"]:
        # genere les position des villages
        generate_positions(Village, top_left, bottom_right, seeds[1], player_pos,
                           settings.VILLAGES_BY_1000x1000 * coeff * 0.8, settings.STRUCTURES_CHECK_STEP)


def check_out_of_bounds(top_left):
    """Verifie si une structure est située dans la chunk"""
    current_map_2 = np.load(settings.CHUNKS_FORMAT % (settings.coords_to_normalized(*top_left)))
    new_current_map = volcans.check_chunk(current_map_2, top_left)
    np.save(settings.CHUNKS_FORMAT % (settings.coords_to_normalized(*top_left)), new_current_map)
    villages.check_chunk(new_current_map, top_left)
