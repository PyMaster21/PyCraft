import itertools
import os
import random
import math

import numpy as np
import multiprocessing

import game.terrain_generation.settings as settings
import game.preferences as prefs
import game.terrain_generation.floating_island as floating_island
import game.terrain_generation.structures as structures
import game.terrain_generation.generation as generation
import game.terrain_generation.renderables as renderables
import game.terrain_generation.caves as caves

MAX_PROCESSES = multiprocessing.cpu_count()
max_processes_by_method = {"Init": min(MAX_PROCESSES, prefs.INITIAL_TERRAIN_SIZE),  "default": 1}


# --------------------- GENERATION FUNCTIONS ---------------------

def compute_minerals_proba():
    """Précalcule les probabilités de spawn des minéraux pour chaque hauteur z,
    pour éviter de faire les calculs en real time"""
    minerals = {"fer": [], "diamant": [], "charbon": []}
    for z in range(0, settings.MAX_HEIGHT):
        for mineral, (chance, curve) in settings.MINERAIS_DATA(z):
            minerals[mineral].append(1 / chance * curve * 1000)

    return minerals


def compute_chunk(top_left, bottom_right, result_dict, out_of_bounds_tree_placeholders):
    """Fais tous les calculs de géneration d'un bout du monde, défini par son top_left bottom_right,
    avec le dictionnaire de résultats qui stocke les résultats génerés"""

    seeds = settings.setSeeds(settings.SEED, 10, length=9)  # Génère 10 seeds à partir de la seed principale
    minerals_table = compute_minerals_proba()   # Précalcule les probas des minéraux
    render = (top_left, bottom_right)

    water_pixels, flat_pixels, general_terrain_height, forest_pixels, biomes_pixels = \
        generation.generate_perlin(seeds, render)  # Génère les perlin noises

    # Génère le vrai terrain à l'aide de ces perlin noises (=paramètres)
    terrain_generator = generation.TerrainGenerator(*render,
                                                    seeds[-1],
                                                    (random_values, minerals_table, water_pixels,
                                                     flat_pixels, forest_pixels, general_terrain_height,
                                                     out_of_bounds_tree_placeholders, biomes_pixels))

    data = terrain_generator.generate()

    if settings.GENERATION["floating islands"] and settings.GENERATION["relief"]:
        #  Ajoute les iles flottantes
        data = floating_island.FloatingIsland(seeds[6], data, top_left,
                                              terrain=general_terrain_height,
                                              water=water_pixels,
                                              flat=flat_pixels,
                                              forest=forest_pixels).get_map()
        
    if settings.GENERATION["caves"] and settings.GENERATION["relief"]:
        cave = caves.Cave(top_left, bottom_right, seeds[7])
        data = cave.place(data)


    if result_dict != "return":
        # Met à jour le dictionnaire commun à tous les processes avec la data calculée
        result_dict[(top_left, bottom_right)] = data
    else:
        return data


def generate_world_1_chunk(map_coords):
    """
    Génère le terrain pour 1 chunk
    :param map_coords: tuple top_left, bottom_right
    """

    top_left = map_coords[0]
    bottom_right = map_coords[1]
    out_of_bounds_tree_placeholders = {}

    # Calcule le terrain de la chunk
    results = compute_chunk(top_left, bottom_right, "return", out_of_bounds_tree_placeholders)

    # Sauvegarde la chunk
    generation.save_chunk(results, top_left, f"{settings.CHUNKS_FORMAT}")

    # Ajoute les structures à la chunk
    structures.check_out_of_bounds(top_left)


def generate_world(map_coords, method="default"):
    """Génère le terrain pour beaucoup de chunks, en utilisant si besoin du multiprocessing pour optimiser au maximum"""

    if __name__ == '__main__' or __name__ == 'game.terrain_generation.main':

        top_left = map_coords[0]

        # Definit le nombre de process à utiliser, si c'est au début lors de la géneration intiale,
        # tous les processes disponibles sur l'ordinateur seront utilisés
        processes = max_processes_by_method[method]

        # Définit le range de la géneration
        x_range = map_coords[1][0] - map_coords[0][0]
        y_range = map_coords[1][1] - map_coords[0][1]

        # Determine le nombre de chunks entières de la zone génerée
        nb_chunk_x = (x_range // settings.CHUNK_SIZE)
        nb_chunk_y = (y_range // settings.CHUNK_SIZE)

        # Divise le travail sur l'axe x, faisant des slices verticales pour chaque process
        x_size = x_range / processes
        y_size = y_range

        # Dictionnaire commun à tous les processes qui va éviter les arbres coupés lors de la géneration intiale
        out_of_bounds_tree_placeholders = multiprocessing.Manager().dict()

        # Dictionnaire qui stockera les résultats
        result_dict = multiprocessing.Manager().dict()

        processes_list = []
        for i in range(processes):
            # Calcule les coordonnées à génerer pour chaque process
            chunk_coords = (
                (math.ceil(map_coords[0][0] + x_size * i), map_coords[0][1]),
                (math.ceil(map_coords[0][0] + x_size * (i + 1)), map_coords[0][1] + y_size)
            )

            # Initie l'emplacement du dictionnaire "result_dict" pour le process
            result_dict[(chunk_coords[0], chunk_coords[1])] = None

            # Crée le process
            p = multiprocessing.Process(target=compute_chunk, args=(chunk_coords[0], chunk_coords[1], result_dict,
                                                                    out_of_bounds_tree_placeholders))
            processes_list.append(p)

            p.start()  # Lance le process

        # Lie ce thread aux processes avec .join(), qui va donc attendre jusqu'à ce que tout le monde ait fini
        for p in processes_list:
            p.join()

        results = dict(result_dict)

        # Rassemble les résultats trouvés par les autres processes en un seul grand array
        world = generation.concatenate_results(results)

        # Découpe le grand array en chunks
        world, chunks_coords = generation.convert_into_chunks(world, nb_chunk_x, nb_chunk_y, top_left)

        # Sauvegarde les chunks
        generation.save_chunks(nb_chunk_x, nb_chunk_y, world, chunks_coords, f"{settings.CHUNKS_FORMAT}")

        # Verifie les structures dans la zone
        check_for_structures(*map_coords)


# ------------------- ARTIFICAL STRUCTURES CHECK -------------------


def check_for_structures(top_left, bottom_right):
    """Verifie si il y a des structures dans la zone"""
    norm_top_left = settings.coords_to_normalized(*top_left)
    norm_bottom_right = settings.coords_to_normalized(*bottom_right)
    for x in range(norm_top_left[0], norm_bottom_right[0]):
        for y in range(norm_top_left[1], norm_bottom_right[1]):
            temp_top_left = settings.normalized_to_coords(x, y)
            structures.check_out_of_bounds(temp_top_left)


# ---------------------- RENDERABLES FUNCTIONS ----------------------

def get_renderables_1_chunk(top_left):
    """
    (Voir renderables.py pour l'explication de 'renderables')
    Pour 1 chunk donnée et ses coordonnées, génère les renderables
    """
    norm = settings.coords_to_normalized(*top_left)

    # Check si la chunk de base existe
    path = f"{settings.CHUNKS_FORMAT % (*norm,)}"
    if os.path.exists(path):
        chunk = np.load(path)
    else:
        print(f"Non existing chunk at {top_left}")
        return False

    coords = top_left
    border_chunks_coords = renderables.load_border_chunks(coords)  # load les chunks adjacents
    if not border_chunks_coords:
        # si un chunk adjacent ne peut pas être load,
        # alors les renderables ne peuvent pas être entièrement géneré pour la chunk
        return False

    # Crée le grand array étendu de 1 dans les 6 directions (-x +x -y +y -z +z)
    extended_chunk = np.zeros((settings.CHUNK_SIZE + 2, settings.CHUNK_SIZE + 2, settings.MAX_HEIGHT+2),
                              dtype=chunk.dtype)

    # Remplis le centre (sans les bordures) du grand array
    extended_chunk[1:-1, 1:-1, 1:-1] = chunk

    # Remplis les bordures du grand array
    extended_chunk = renderables.load_in_extended_chunk(extended_chunk, border_chunks_coords)

    # Calcule les blocs renderables
    blocs_renderables = renderables.find_renderables(extended_chunk)

    # Sauvegarde les renderables calculés
    renderables.save(blocs_renderables, coords, f"{settings.RENDERABLES_FORMAT}")

    return True


# ---------------------- MAIN FUNCTIONS ----------------------

def generate_chunk_norm(chunks: list):
    """
    Generation real-time appellée par data_manager_generation.py, génère 1 chunk de 16*16
    :param chunks: [[chunk1_x, chunk1_y], [chunk2_x...] sous format normalisé
    """
    for chunk_x, chunk_y in chunks:
        print(f"GENERATING : {chunk_x}, {chunk_y}")
        top_left = settings.normalized_to_coords(chunk_x, chunk_y)
        bottom_right = settings.normalized_to_coords(chunk_x+1, chunk_y+1)

        if not os.path.exists(settings.CHUNKS_FORMAT % (chunk_x, chunk_y)):  # evite d'overwrite un chunk déjà géneré
            generate_world_1_chunk((top_left, bottom_right))


def get_renderables_norm(chunk_x: int, chunk_y: int):
    """
    Calcul des 'renderables', appellé par data_manager_generation.py
    :param chunk_x: chunk0_x, normalisé
    :param chunk_y: chunk0_y, normalisé
    """
    print(f"GETTING RENDERABLES : {chunk_x}, {chunk_y}")
    chunk_x, chunk_y = int(chunk_x), int(chunk_y)
    top_left = settings.normalized_to_coords(chunk_x, chunk_y)
    are_renderables_computed = get_renderables_1_chunk(top_left)
    return are_renderables_computed


def generate_initial_terrain(map_coords):
    """ S'occupe de la generation initiale du monde, avec un multiprocessing pour accélerer cette géneration"""
    print(f"GENERATING INITIAL STRUCTURES")

    # Prégénère artificiellement les structures au début
    center = (int(map_coords[0][0] - map_coords[1][0]), int(map_coords[0][1] - map_coords[1][1]))

    # prégénère des structures pour gagner de la performance après en real-time
    structures.pregenerate(settings.INITIAL_PRESCAN[0], settings.INITIAL_PRESCAN[1],
                           settings.setSeeds(settings.SEED, 2), center, is_initial_scan=True)

    print("GENERATING INITIAL WORLD")

    # Génère le monde avec la methode "Init" qui va indiquer
    # qu'on peut utiliser tous les processes disponibles sur l'ordi
    generate_world(map_coords, method="Init")

    print("INITIAL GENERATION DONE")


# -------------------- INIT FUNCTIONS --------------------
def init_seed(SEED):
    """Initialise des valeurs aléatoires pour accélerer le calcul des random très couteux en real-time"""
    global random_values
    random.seed(SEED)
    random_values = itertools.cycle([random.randint(0, 1000) for _ in range(378_241)])


random_values = []
init_seed(settings.SEED)
