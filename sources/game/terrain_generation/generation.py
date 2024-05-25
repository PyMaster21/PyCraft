import game.terrain_generation.settings as settings
import numpy as np
import random
from game.terrain_generation.perlin_noise import PerlinNoise
import game.terrain_generation.trees as trees
import os
import time


class TerrainGenerator:
    def __init__(self, top_left, bottom_right, seed, params):
        """Generateur de terrain entre top_left et bottom_right, appellé par main.py"""
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.seed = seed

        # Perlin Noises déjà calculés avant
        random_values, minerals_table, water_pixels, flat_pixels, forest_pixels, general_terrain_height, \
            out_of_bounds_tree_placeholders, biomes_pixels = params

        self.random_values = random_values
        self.minerals_table = minerals_table
        self.water_pixels = water_pixels
        self.flat_pixels = flat_pixels
        self.forest_pixels = forest_pixels
        self.biomes_pixels = biomes_pixels
        self.general_terrain_height = general_terrain_height
        self.out_of_borders_tree_placeholder = out_of_bounds_tree_placeholders

        # Calcule la taille du terrain à génerer
        self.x_range = self.bottom_right[0] - self.top_left[0]
        self.y_range = self.bottom_right[1] - self.top_left[1]

        # Check si la géneration est par chunk de 16x16 ou pas, pour optimiser dans ce cas
        if (self.x_range, self.y_range) == (settings.CHUNK_SIZE, settings.CHUNK_SIZE):
            self.is_chunkwise = True
            self.implicated_chunks = {
                top_left: np.zeros(shape=(settings.CHUNK_SIZE, settings.CHUNK_SIZE, settings.HEIGHTS_SIZE))}
        else:
            self.is_chunkwise = False
            self.implicated_chunks = {}

        # Shift pour avoir une origine des coordonnées à (0, 0)
        self.x_shift = top_left[0]
        self.y_shift = top_left[1]

        self.tree_placeholders = {}

        # Initie l'array qui contiendra tout le terrain
        self.complete_grid_array = np.zeros((self.x_range, self.y_range, settings.MAX_HEIGHT), dtype=np.int16)

    def generate(self):
        for sx in range(0, self.x_range):
            for sy in range(0, self.y_range):
                x = sx + self.x_shift
                y = sy + self.y_shift

                terrain_height = self.general_terrain_height.get((x, y))
                flat_biais = self.flat_pixels.get((x, y))
                water_biais = self.water_pixels.get((x, y))
                forest_density = self.forest_pixels.get((x, y))
                biomes_biais = self.biomes_pixels.get((x, y))

                # Inite la classe géneratrice d'1 pixel = 1 colonne z
                pixel_gen = PixelGeneration(self, x, y,
                                            (terrain_height, flat_biais, water_biais, forest_density, biomes_biais))

                # Genere le relief (dont l'eau) si le relief est activé
                pixel_gen.generate_terrain_height(settings.GENERATION["relief"])

                # Genere les biomes (plaine, desert, neige) si le relief + les biomes sont activés
                pixel_gen.generate_biomes(settings.GENERATION["relief"] and settings.GENERATION["biomes"])

                # Place la pierre en fonction de la quantité définie plus tôt,
                # place des minérais si les minérais sont activés
                pixel_gen.place_stone(True, settings.GENERATION["ores"])

                # Place les biomes (plaine, desert, neige) si le relief + les biomes sont activés
                pixel_gen.place_biomes(settings.GENERATION["relief"] and settings.GENERATION["biomes"])

                # Ajoute l'eau, si le relief est activé
                pixel_gen.add_water(settings.GENERATION["relief"])

                # Check si un arbre se trouve sur ce pixel
                tree_info = pixel_gen.check_tree(settings.GENERATION["relief"] and settings.GENERATION["trees"])
                if tree_info:
                    self.place_tree(x, y, tree_info[0], tree_info[1])  # Place l'arbre

                # Obtient et met à jour toutes les infos à propos des hauteurs
                # de la pierre, la hauteur totale, la hauteur de l'eau
                # Evite des boucles inutiles lors de plaçage de volcans ou villages
                gen_heights_info = pixel_gen.get_heights_info()
                self.update_height_data(x, y, gen_heights_info)

                # Ajoute la slice calculée à l'array principal qui contient toutes les slices
                self.complete_grid_array[sx, sy] = pixel_gen.z_slice

        self.save_height_data()

        # Place les arbres qui se situent dans la chunk (ou les bouts si l'arbre est en bordure)
        temp_out_of_bounds_tree_placeholders = self.place_inchunk_trees()

        # Place les arbres qui proviennent d'autres chunks adjacentes et qui ont un arbre en bordure
        self.place_tree_from_other_chunk()

        # Update le out_of_border_tree_placeholder,
        # afin que les arbres en bordures soient ajoutés aux chunks adjacents correspondants
        self.out_of_borders_tree_placeholder.update(temp_out_of_bounds_tree_placeholders)

        return self.complete_grid_array

    def place_tree(self, tree_x, tree_y, is_sand, height):
        """
        Place l'arbre à des coordonnées relatives tree_x, tree_y,
        avec 'height' qui est la hauteur de la base de l'arbres
        Met un arbre normal ou un palmier en fonction de s'il y a du sable
        """
        tree_map, center, size = trees.generate_tree(is_sand)
        for xy, z_column in enumerate(tree_map):
            x = tree_x + xy // size - center
            y = tree_y + xy % size - center
            for sz, item in enumerate(z_column):
                z = height + sz - 1
                if item != 0:
                    current_bloc = self.tree_placeholders.get((x, y, z))
                    if not current_bloc or current_bloc == 2 or current_bloc == 6:
                        self.tree_placeholders[(x, y, z)] = item

    def update_height_data(self, x, y, gen_heights_info):
        """Ajoute à 'implicated_chunks' les données de la hauteur au point (x, y)"""
        if self.is_chunkwise:

            self.implicated_chunks[self.top_left][x % settings.CHUNK_SIZE, y % settings.CHUNK_SIZE, :] = \
                gen_heights_info
        else:
            chunk_coords = corresponding_chunk(x), corresponding_chunk(y)
            if type(self.implicated_chunks.get(chunk_coords)) != np.ndarray:
                self.implicated_chunks[chunk_coords] = np.zeros(
                    shape=(settings.CHUNK_SIZE, settings.CHUNK_SIZE, settings.HEIGHTS_SIZE))

            self.implicated_chunks[chunk_coords][x % settings.CHUNK_SIZE, y % settings.CHUNK_SIZE, :] = \
                gen_heights_info

    def save_height_data(self):
        """Sauvegarde les données de hauteur de 'implicated_chunks'"""

        to_retry = []  # si le load de l'array a échoué, on reessaie à la fin
        for chunk_coords in self.implicated_chunks:

            norm = settings.coords_to_normalized(*chunk_coords)
            chunk = self.implicated_chunks[chunk_coords]
            if not self.is_chunkwise:
                if os.path.exists(settings.HEIGHTS_FORMAT % (*norm,)):
                    try:
                        old = np.load(settings.HEIGHTS_FORMAT % (*norm,))
                    except Exception:
                        to_retry.append(chunk_coords)
                        continue
                    new = old + chunk
                else:
                    new = chunk
            else:
                new = chunk

            np.save(settings.HEIGHTS_FORMAT % (*norm,), new)

        for chunk_coords in to_retry:
            norm = settings.coords_to_normalized(*chunk_coords)
            chunk = self.implicated_chunks[chunk_coords]
            time.sleep(0.2)
            try:
                old = np.load(settings.HEIGHTS_FORMAT % (*norm,), encoding="bytes", allow_pickle=True)

            except Exception:
                raise Exception("Failed twice to open array, it might be corrupted")

            new = old + chunk
            np.save(settings.HEIGHTS_FORMAT % (*norm,), new)


    def place_inchunk_trees(self):
        """Place les arbres qui sont DANS la chunk, même s'ils dépassent"""
        temp_out_of_border_tree_placeholders = {}
        for (x, y, z), item in list(self.tree_placeholders.items()):
            # check si le bloc est dans la chunk
            if 0 + self.top_left[0] <= x < self.x_range + self.top_left[0] \
                    and 0 + self.top_left[1] <= y < self.y_range + self.top_left[1]:
                rel_x = x - self.top_left[0]
                rel_y = y - self.top_left[1]

                # empêche le bloc d'arbre de remplacer des blocs de terrain
                if self.complete_grid_array[rel_x, rel_y, z] == 0:
                    # place l'arbre dans l'array principal
                    if item == 3:
                        self.complete_grid_array[rel_x, rel_y, z] = settings.BLOC_VERS_ID["tronc"]
                    elif item == 4:
                        self.complete_grid_array[rel_x, rel_y, z] = settings.BLOC_VERS_ID["feuille"]
            else:
                # si le bloc n'est pas dans la chunk, on l'ajoute ici, pour qu'il puisse être lui-même
                # ajouté par d'autres chunks
                temp_out_of_border_tree_placeholders[(x, y, z)] = item

        return temp_out_of_border_tree_placeholders

    def place_tree_from_other_chunk(self):
        """Place les arbres qui ont été générés sur la bordure d'une AUTRE chunk adjacente"""
        for (x, y, z), item in list(self.out_of_borders_tree_placeholder.items()):
            # check si le bloc est dans la chunk
            if 0 + self.top_left[0] <= x < self.x_range + self.top_left[0] \
                    and 0 + self.top_left[1] <= y < self.y_range + self.top_left[1]:
                rel_x = x - self.top_left[0]
                rel_y = y - self.top_left[1]
                # empêche le bloc d'arbre de remplacer des blocs de terrain
                if self.complete_grid_array[rel_x, rel_y, z] == 0:
                    # place l'arbre dans l'array principal
                    if item == 3:
                        self.complete_grid_array[rel_x, rel_y, z] = settings.BLOC_VERS_ID["tronc"]
                    elif item == 4:
                        self.complete_grid_array[rel_x, rel_y, z] = settings.BLOC_VERS_ID["feuille"]

                # supprime le bloc d'arbre du placeholder
                del self.out_of_borders_tree_placeholder[x, y, z]


class PixelGeneration:
    def __init__(self, master, x, y, perlin_noises):
        """Génère une slice z, à des coordonnées (x,y), controlé par le TerrainGenerator"""
        self.master = master
        self.x, self.y = x, y
        self.terrain_height, self.flat_biais, self.water_biais, self.forest_density, self.biomes_biais = perlin_noises

        self.z_slice = np.zeros(shape=settings.MAX_HEIGHT)  # initie la slice z qui contiendra le terrain
        self.current_z = 0

        self.final_terrain_height = 0  # hauteur totale du terrain (pierre + terre/sable/neige + eau)
        self.dirt_blocs = 0  # nombre de blocs de terre/sable/neige
        self.stone_blocs = 0  # nombre de blocs de pierre
        self.water_blocs = 0  # nombre de blocs d'eau

        self.is_sand = False

    def generate_terrain_height(self, gen_condition):
        """Fonction responsable de définir la hauteur du terrain à une coordonnée (x,y), et si il y a de l'eau"""
        if gen_condition:  # si il y a du relief
            # simule la hauteur de l'eau et détermine si il peut y avoir de l'eau
            water_level_projection = self.terrain_height + self.water_biais * 3 - settings.WATERNESS + 1
            water_height_limit = -0.5  # -0.5

            if water_level_projection <= water_height_limit:
                # à cette coordonnée, il y a de l'eau
                # Determine la profondeur de l'eau
                water_blocs = (-(water_level_projection + 0.5) * settings.WATER_HEIGHT_DECREASING_RATE * 2).__ceil__()

                self.dirt_blocs = 0
                self.final_terrain_height = settings.WATER_LEVEL
                self.stone_blocs = (self.final_terrain_height - water_blocs).__floor__()

            else:
                # à cette coordonnée, il n'y a d'eau
                water_blocs = 0

                terrain_height = water_level_projection + 0.5  # base la valeur à 0 comme valeur minimale
                terrain_height += (self.flat_biais * 3 - self.water_biais + self.biomes_biais) \
                    * sigm2(water_level_projection)  #

                # multiplie la hauteur du terrain par une constante d'amplification de terrain
                terrain_height *= settings.WORLD_AMPLIFICATION  # 0.75
                height = terrain_height
                coeff = 15

                if height <= 0.3:
                    # Si la hauteur est assez faible, ne contraste pas + la hauteur
                    final_terrain_height = settings.WATER_LEVEL + height * coeff ** 1
                else:
                    # Si la hauteur est plus grande, contraste et accentue
                    final_terrain_height = settings.WATER_LEVEL + (0.3 * coeff + (height - 0.3) * 50) ** 1

                self.final_terrain_height = int(final_terrain_height)
                self.dirt_blocs = settings.DIRT_BLOCS
                self.stone_blocs = int(final_terrain_height - self.dirt_blocs)

            self.water_blocs = water_blocs

        else:
            # si il n'y a pas de relief, fais un monde plat
            self.final_terrain_height = settings.SUPERFLAT_HEIGHT
            self.dirt_blocs = settings.DIRT_BLOCS
            self.stone_blocs = int(settings.SUPERFLAT_HEIGHT - self.dirt_blocs)
            self.water_blocs = 0

    def generate_biomes(self, condition):
        """Genere le biome à ces coordonnées, si les biomes sont activés"""
        if condition:

            # Calculs de facteurs qui influencent s'il y a du sable ou non
            biomeness = (self.biomes_biais - 0.2) * 6
            heightness = -((((self.stone_blocs + self.dirt_blocs) - settings.WATER_LEVEL) ** 4) / 2000) + 1

            # Calcul de la valeur de possibilité de sable
            sandness = biomeness * heightness - 0.1 + self.water_biais

            if sandness >= 0 and biomeness >= 0 and sandness >= 0:
                # Met du sable
                diff = ((self.stone_blocs + self.dirt_blocs) - settings.WATER_LEVEL)

                # Rend le relief plus smooth
                smooth = abs(diff) ** 0.5
                sigm = 0.25 / (1 + 2 ** (-16 * (sandness - 0.3)))
                
                # Calcule la hauteur finale du sable
                target_height = ((self.stone_blocs + self.dirt_blocs) - smooth * sigm).__ceil__()

                if self.water_blocs > 0:
                    # Si il y a de l'eau, supprime l'eau
                    self.water_blocs = 0
                    self.dirt_blocs = 4
                    self.is_sand = True
                    reverse = self.water_blocs

                    # Hauteur sable = ancienne profondeur de l'eau
                    height = max(target_height + reverse, settings.WATER_LEVEL)
                else:
                    height = max(target_height, settings.WATER_LEVEL)

                self.dirt_blocs = settings.DIRT_BLOCS
                self.stone_blocs = int(height.__floor__() - self.dirt_blocs)
                self.is_sand = True
        else:
            pass

    def place_stone(self, condition, condition_ores):
        """Place les blocs de pierre et les minérais à l'interieur, dont le nombre a été défini plus tôt"""
        if condition:

            for i in range(self.stone_blocs):
                if i == 0:
                    # Met de la bedrock tout en bas du monde
                    self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["bedrock"]
                    continue
                bloc = "pierre"
                if condition_ores:  # si la generation de minérais est activée
                    # choisis un nombre dans des valeurs aléatoires prégénérées,
                    # pour gagner du temps, car les random.randint() sont lents
                    random_number = next(self.master.random_values)
                    for mineral in ("diamant", "fer", "charbon"):
                        if self.master.minerals_table[mineral][i] > random_number:
                            bloc = mineral
                            break

                # Place le bloc
                self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID[bloc]

            self.current_z += self.stone_blocs

    def place_biomes(self, condition):
        """Place le biome (sable/herbe/neige) à ce bloc"""
        if condition:
            # Definit le seuil à partir duquel la neige est génerée
            snow_threshold = (-self.biomes_biais) * 100 + (self.stone_blocs - settings.WATER_LEVEL - 50) * 1.5

            for i in range(self.dirt_blocs):
                if self.is_sand:
                    if self.current_z + i + 1 < settings.WATER_LEVEL:
                        self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["pierre"]
                    else:

                        # Si c'est du sable
                        self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["sable"]
                else:
                    # Si c'est de l'herbe ou de la neige
                    if i == self.dirt_blocs - 1:
                        if snow_threshold > 0:
                            # Si il y a de la neige à ces coordonnées, met de la neige au dernier bloc de terre
                            self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["neige"]
                        else:
                            # Sinon met de l'herbe au dernier bloc de terre
                            self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["herbe"]
                    else:
                        # met de la terre si on est pas au dernier bloc dans tous les cas
                        self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["terre"]

        else:
            # Si il n'y a pas de biome, met seulement de l'herbe
            for i in range(self.dirt_blocs):
                self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["herbe"]

        self.current_z += self.dirt_blocs

    def add_water(self, condition):
        """Place l'eau s'il y a de l'eau (défini plus tôt) à ces coordonnées"""
        if condition:  # Si il y a du relief

            # Si il y a de l'eau, la place
            for i in range(self.water_blocs):
                self.z_slice[self.current_z + i] = settings.BLOC_VERS_ID["eau"]

            self.current_z += self.water_blocs

    def check_tree(self, condition):
        """Retourne un bool qui indique si il y a le centre d'un arbre en ces coordonnées"""
        if condition:  # si les arbres sont activés
            if self.water_blocs == 0:

                # Determine la densité d'arbres en ces coordonnées,
                # dépendant aussi de la hauteur (moins d'abres très haut)
                density_value = self.forest_density
                density = (2 ** (4 * (density_value - 0.5)) + 0.15 -
                           ((255 - self.final_terrain_height) ** 2 / 220 ** 2)) ** 2

                if self.is_sand:
                    # moins de variations de densité d'abres dans les déserts
                    threshold = density * 4 + 3
                else:
                    threshold = density * 50

                random.seed(str(self.master.seed) + str(self.y) + str(self.x))
                # Calcule s'il y a un arbre ici en fonction du seuil
                if threshold > random.randint(0, 1000):
                    return self.is_sand, self.final_terrain_height

        return False

    def get_heights_info(self):
        """Retourne les informations sur le nombre de blocs de pierre, la hauteur totale, et
        le nombre de blocs totaux excepté de l'eau"""
        return self.stone_blocs, self.final_terrain_height, self.stone_blocs + self.dirt_blocs, False


def corresponding_chunk(a):
    """Donne la chunk correspondante en coordonnées non normalisées"""
    return (a // settings.CHUNK_SIZE) * settings.CHUNK_SIZE


def sigm2(x):
    """Sigmoide responsable du fait que le terrain tend progressivement vers la
    hauteur de l'eau plus on est près de l'eau"""
    return 1 / (1 + 2 ** (-20 * x))


def generate_perlin(seeds, render):
    """Genère tous les Perlin Noises nécessaires à la géneration de terrain"""
    if settings.GENERATION["relief"]:
        # Paramètre responsable de la géneration des océans et lacs
        water = PerlinNoise(seeds[3], 200, 0, 0.5, [0.5])  # 0.3
        water.extend(*render)
        water_pixels = water.get_pixels()

        # Paramètre responsable du petit relief, à savoir les pics de montagne par exemple
        flat = PerlinNoise(seeds[2], 150, 0, 0.5, [0.7])  # 0.3
        flat.extend(*render)
        flat_pixels = flat.get_pixels()

        # Paramètre responsable des variations génerales du terrain
        terrain_main = PerlinNoise(seeds[0], 120, 6, 0.6, [0.1, 0.5])
        terrain_main.extend(*render)
        general_terrain_height = terrain_main.get_pixels()
    else:
        water_pixels, flat_pixels, general_terrain_height = {}, {}, {}

    if settings.GENERATION["trees"]:
        # Paramètre responsable de la densité des arbres et donc des forêts
        forest = PerlinNoise(seeds[1], 200, 0, 0.5, [0.8])  # 0.6
        forest.extend(*render)
        forest_pixels = forest.get_pixels()
    else:
        forest_pixels = {}

    if settings.GENERATION["biomes"]:
        # Paramètre responsable de la dispersion et positionnement des biomes
        biomes = PerlinNoise(seeds[4], 200, 5, 0.5, [0.5])
        biomes.extend(*render)
        biomes_pixels = biomes.get_pixels()
    else:
        biomes_pixels = {}

    return water_pixels, flat_pixels, general_terrain_height, forest_pixels, biomes_pixels


def concatenate_results(results, ):
    """Rassemble tous les résultats des différentes zones génerées,
    les assemble dans un même array"""
    results_ = []
    for i in results.values():
        if type(i) == np.ndarray and i.ndim == 3:
            results_.append(i)
    try:
        # Cette concatenation ne marchera pas si un des proceess a fait une erreur
        # ce n'est probablement pas une erreur de concatenation
        arr = np.concatenate((*results_,), axis=0)
    except Exception:
        raise Exception("An error occurred in at least one of the processes")
    return arr


def convert_into_chunks(arr, nb_chunk_x, nb_chunk_y, top_left):
    """Convertit un array complet en chunks de taille 16x16"""

    # Crée un array à 5 dimensions
    chunks = np.empty((nb_chunk_x, nb_chunk_y, settings.CHUNK_SIZE, settings.CHUNK_SIZE, settings.MAX_HEIGHT),
                      dtype=np.int16)

    # Decoupe l'array en chunks sur l'axe x et l'axe y
    chunks_coords = []
    for x in range(nb_chunk_x):
        for y in range(nb_chunk_y):
            coords = ((x * settings.CHUNK_SIZE + top_left[0], y * settings.CHUNK_SIZE + top_left[1]),
                      ((x + 1) * settings.CHUNK_SIZE + top_left[0], (y + 1) * settings.CHUNK_SIZE + top_left[1]))
            chunk = arr[x * settings.CHUNK_SIZE:(x + 1) * settings.CHUNK_SIZE,
                        y * settings.CHUNK_SIZE:(y + 1) * settings.CHUNK_SIZE, :]
            chunks[x, y, :] = chunk
            chunks_coords.append(coords)
    return chunks, chunks_coords


def save_chunks(nb_chunk_x, nb_chunk_y, chunks, chunks_coords, path):
    """Sauvegarde plusieurs chunks à un chemin donné"""
    for x in range(nb_chunk_x):
        for y in range(nb_chunk_y):
            chunk = chunks[x, y]

            coords = chunks_coords[x * nb_chunk_y + y]
            norm = settings.coords_to_normalized(*coords[0])
            np.save(f"{path % (*norm,)}", chunk)


def save_chunk(arr, top_left, path):
    """Sauvegarde 1 chunk à un chemin donné"""
    norm = settings.coords_to_normalized(*top_left)
    np.save(f"{path % (*norm,)}", arr)
