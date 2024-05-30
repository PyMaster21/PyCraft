import random
import math

import numpy as np
import game.terrain_generation.settings as settings
import os
import json


last_id = 0
top_left = [[], []]


class Village:

    def __init__(self, coords, seed, player_pos):
        """Classe qui va génerer le village et sauvegarder ses données
        Le village sera ainsi géneré seulement sur la chunk quand une chunk du volcan est checkée (check_chunk)
        Cependant, le village ne sauvegarde que les maisons individuelles, et pas le village en tant qu'entité"""
        global top_left
        self.houses_rectangle = []
        self.center = coords
        self.seeds = settings.setSeeds(seed, 10)

        self.last_radius = 0
        self.houses_types = []
        self.village_id = ""

        # self.max_radius = settings.VILLAGES_MAX_RADIUS

        # Calcule la distance qui sépare le centre du village du joueur
        dist_from_player = ((self.center[0] - player_pos[0]) ** 2 + (self.center[1] - player_pos[1]) ** 2) ** (1 / 2)

        if dist_from_player > settings.VILLAGES_MIN_DISTANCE_FROM_PLAYER:
            # Si le village est suffisament loin du player, on peut génerer
            self.max_radius = dist_from_player

            # On place le village
            self.place_village()
            print(f"Village {self.village_id} placed at {self.center}")

    def place_village(self):
        """Place le village et ses maisons"""

        random.seed(self.seeds[0])

        # Determine le nombre de maisons que le village aura
        num_houses = random.randint(*settings.VILLAGES_RANDOM_NUMBER_OF_HOUSES)

        # Ouvre la liste des types de maison
        with open(os.path.join(settings.VILLAGES_FILE_DIRECTORY, settings.VILLAGES_STRUCT_DIRECTORY, "generated.json"),
                  "r") as fr:
            data = json.load(fr)

        self.houses_types = data[1:]

        # Calcule les probabilités pour chacune des maisons de spawner
        probas = []
        total_probas = 0
        total_weight = 0
        for name, weight in self.houses_types:
            total_weight += weight
        for name, weight in self.houses_types:
            proba = math.floor(weight/total_weight * 1000)
            probas.append((total_probas+proba, name))
            total_probas = total_probas+proba

        # Genere d'abord la tour centrale du village
        houses = []
        house = House((data[0][0].replace(".struct", ""), 0), self)
        if not house.def_house_coordinates():
            return
        self.houses_rectangle.append(house.get_info())

        self.last_radius = house.dist_from_center
        house.categorize_out_of_bounds()
        houses.append(house)

        # Ajoute toutes les autres maisons
        for i in range(num_houses-1):
            # Choisis le type de maison
            rd = random.randint(0, 999)
            for j, name in probas:
                if j >= rd:
                    house_name = name
                    break
            else:
                house_name = self.houses_types[0][0]

            # Choisis l'orientation de la maison
            orientation = random.randint(0, 3)

            # Crée l'instance de maison
            house = House((house_name.replace(".struct", ""), orientation), self)

            # Definit les coordonnées de la maison dans le village
            if not house.def_house_coordinates():
                # La maison est plus loin que le max radius, elle ne peut pas être placée
                continue

            # Definit le rectangle de la maison
            self.houses_rectangle.append(house.get_info())
            self.last_radius = house.dist_from_center

            # Sauvegarde la maison pour être utilisée ensuite par check_chunk
            house.categorize_out_of_bounds()
            houses.append(house)


class House:

    def __init__(self, house_id, master_village: Village):
        """Classe responsable du placement d'une maison et de sa sauvegarde,
        dépendant directement de son village parent"""
        self.name, self.orientation = house_id
        self.village = master_village

        self.dist_from_center = 0
        self.house_x = 0
        self.house_y = 0
        self.relative_square = []
        self.blocs_list = []

        self.house_id = ""

        # Load la maison selon le nom et l'orientation donnés
        self.load_house()

        # Definit le rectangle relatif de la maison
        self.relative_position = self.rectangle()

    def get_info(self):
        """"""
        return self.relative_square

    def def_house_coordinates(self):
        """Definit la position et le placement de la maison en fonction des autres maisons du village"""

        houses = self.village.houses_rectangle
        village_center = self.village.center
        init_r = self.village.last_radius

        # Simulation de positions de la maison jusqu'à ce qu'une position convienne
        for i in range(10000):  # valeur arbitrairement grande
            angle = random.uniform(0, 2 * math.pi)  # Angle aléatoire en radiants
            # Distance aléatoire depuis le centre du village, qui augmente progressivement
            distance = random.uniform(init_r + i, init_r + 5 + i)
            if distance > self.village.max_radius*1.5:
                # Ici, la maison est vraiment definitivement trop loin, on ne peut pas la placer
                break
            if distance > self.village.max_radius:
                # Cette fois, la maison est un peu trop loin, mais on peut ressayer de la placer
                continue

            # Convertis les coordonnées polaires en coordonnées cartésiennes
            house_x = int(village_center[0] + distance * math.cos(angle))
            house_y = int(village_center[1] + distance * math.sin(angle))

            # Verifie si la maison chevauche d'autres maisons
            for house in houses:
                if self.is_house_overlapping((house_x, house_y), house, settings.VILLAGES_MIN_GAP_BETWEEN_HOUSES):
                    break
            else:
                # Si la maison ne chevauche pas, on peut definitivement la placer
                self.house_x = house_x
                self.house_y = house_y
                self.dist_from_center = distance
                self.relative_square = self.rectangle((self.house_x, self.house_y, 0))

                return True

        return False

    def categorize_out_of_bounds(self):
        """Verifie à quel chunks appartiennent les blocs de la maison, puis sauvegarde ces infos
        Le but est de trouver quelle est la hauteur maximum de terrain pour la maison, afin de
        remplir de pierre en dessous. Il faut donc que TOUTES les chunks auquelles appartient la maison
        soient génerées avant que la maison puisse être placée"""

        global last_id

        # Definit les chunks dans lesquels se trouve la maison (1, 2 ou 4)
        implicated_chunks = {}
        (x1, y1, _), (x2, y2, _) = self.relative_square
        for x, y in ((x1, y1), (x1, y2), (x2, y1), (x2, y2)):
            chunk = (corresponding_chunk(x), corresponding_chunk(y))
            implicated_chunks[json.dumps(chunk)] = []

        # Ajoute les blocs de la maison dans les chunks correspondantes
        blocs = self.blocs_list
        for x, y, z, i in blocs:
            chunk = (corresponding_chunk(x+self.house_x), corresponding_chunk(y+self.house_y))
            sx, sy = x+self.house_x, y+self.house_y
            implicated_chunks[json.dumps(chunk)].append([sx, sy, z, i])

        # Definit les chunks pour lesquels on doit checker la hauteur maximale du terrain
        gen_top = {}
        for i in implicated_chunks:
            if len(implicated_chunks[i]) != 0:  # si il y a au moins 1 bloc
                gen_top[i] = None

        # Donne un id à la maison
        house_id = last_id
        while os.path.exists(os.path.join(settings.VILLAGES_OOB_HOUSE_PATH, f"{house_id}.json")) or not house_id:
            house_id += 1
        last_id = house_id
        self.house_id = str(house_id)

        # Sauvegarde la data de la maison
        with open(os.path.join(settings.VILLAGES_OOB_HOUSE_PATH, f"{self.house_id}.json"), "w") as fw:
            json.dump(gen_top, fw)

        # Ajoute les bouts de la maison aux fichiers de chunks
        for xy_str in implicated_chunks:

            house_blocs = implicated_chunks[xy_str]
            if len(house_blocs) == 0:
                continue

            # Determine la position que prendra le bout de maison dans la chunk
            (x, y) = json.loads(xy_str)
            max_x = max(house_blocs, key=lambda point: point[0])[0]
            min_x = min(house_blocs, key=lambda point: point[0])[0]
            max_y = max(house_blocs, key=lambda point: point[1])[1]
            min_y = min(house_blocs, key=lambda point: point[1])[1]

            # Load le fichier de chunk
            if os.path.exists(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{x}_{y}.json")):

                with open(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{x}_{y}.json"), "r") as fr:
                    data = json.loads(str(fr.read()))

            else:
                data = {}

            # Ajoute les infos de la maison dans le fichier de chunk
            data[self.house_id] = [[min_x, max_x, min_y, max_y], house_blocs]

            # Sauvegarde le fichier de chunk
            with open(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{x}_{y}.json"), "w") as fw:
                json.dump(data, fw)

        # update les chunks déjà génerées si jamais elles existaient (ce qui n'arrive normalement pas)
        for xy_str in implicated_chunks:
            (x, y) = json.loads(xy_str)
            norm = settings.coords_to_normalized(x, y)
            if os.path.exists(settings.CHUNKS_FORMAT % (*norm,)):
                check_chunk(np.load(settings.CHUNKS_FORMAT % (*norm,)), (x, y))

    def rectangle(self, init_coords=(0, 0, 0)):
        """Retourne le rectangle, ou plutôt le parallelepipede (en 3D), dans lequel se situent les blocs de la maison"""
        fcts = [list(init_coords), list(init_coords)]
        for x, y, z, _ in self.blocs_list:
            for i, item in enumerate((x, y, z)):
                if item + init_coords[i] > fcts[1][i]:
                    fcts[1][i] = item + init_coords[i]
                if item + init_coords[i] < fcts[0][i]:
                    fcts[0][i] = item + init_coords[i]
        return fcts

    def is_house_overlapping(self, house_a_absolute_position, houseB, min_gap):
        """Retourne le rectangle dans lequel se situent les blocs de la maison"""
        def intersect(rectA, rectB):
            """Verifie si deux rectangles 2D rectA et rectB s'intersectent"""
            (x1_1, y1_1), (x2_1, y2_1) = rectA
            (x1_2, y1_2), (x2_2, y2_2) = rectB
            x_overlap = (x1_1 < x2_2 and x2_1 > x1_2) or (x1_2 < x2_1 and x2_2 > x1_1)
            y_overlap = (y1_1 < y2_2 and y2_1 > y1_2) or (y1_2 < y2_1 and y2_2 > y1_1)
            return x_overlap and y_overlap

        house_a = self.relative_position  # position relative des blocs de la maison

        # Determine les coordonnées absolues de la maison, la taille theorique de la maison est augmentée
        # d'un min_gap, pour éviter que les maisons soit collées
        house_a_top_left, house_a_bottom_right = \
            (house_a_absolute_position[0] + house_a[0][0] - min_gap,
             house_a_absolute_position[1] + house_a[0][1] - min_gap), \
            (house_a_absolute_position[0] + house_a[1][0] + min_gap,
             house_a_absolute_position[1] + house_a[1][1] + min_gap)

        house_b_top_left, house_b_bottom_right = houseB

        # Determine si les maisons s'intersectent, ou sont trop proche
        return intersect((house_a_top_left[:2], house_a_bottom_right[:2]),
                         (house_b_top_left[:2], house_b_bottom_right[:2]))

    def load_house(self):
        """Load la maison, depuis le template stocké en local, vers la liste blocs_list"""
        path = os.path.join(settings.VILLAGES_FILE_DIRECTORY, settings.VILLAGES_STRUCT_DIRECTORY,
                            settings.VILLAGES_DIR_TO_GENERATE,
                            f"{self.name}_rotation_[{self.orientation}]{settings.VILLAGES_STRUCT_EXTENSION}")
        data = np.load(path)

        # Convertis l'array 3D en liste de valeurs non nulles associées à un (x, y, z)
        self.blocs_list = []
        for x in range(data.shape[0]):
            for y in range(data.shape[1]):
                for z in range(data.shape[2]):
                    if data[x, y, z] != 0:
                        self.blocs_list.append([x, y, z, data[x, y, z]])



def check_chunk(current_map, top_left_):
    """Verifie si il y a des maisons à cette chunk. Si une maison est terminée, on peut la placer"""
    (x, y) = top_left_

    if os.path.exists(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{x}_{y}.json")):
        # Il y a au moins une maison sur cette chunk
        # Load les données de la chunk
        with open(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{x}_{y}.json"), "r") as fr:
            houses_data = json.loads(fr.read())

        for house_id in houses_data:

            # Load les données de la maison
            with open(os.path.join(settings.VILLAGES_OOB_HOUSE_PATH, f"{house_id}.json"), "r") as fr:
                tops = json.loads(fr.read())

            # Verifie que la chunk fait bien partie de la maison
            if not json.dumps([x, y]) in tops.keys():
                continue

            if not tops[json.dumps([x, y])]:  # Si la maison n'a pas déjà été verifiée pour cette chunk
                # Definit la hauteur du terrain sous la maison
                local_top = get_tops(houses_data[house_id][0], current_map, top_left_)
                tops[json.dumps([x, y])] = local_top

            # Verifie si toutes les chunks de la maison ont été verifiées
            for i in tops.values():
                if not i:
                    break
            else:
                # Genère la maison
                gen_house(tops, house_id)
                continue

            # Si la maison n'est pas genérée, on sauvegarde les informations de la maison
            with open(os.path.join(settings.VILLAGES_OOB_HOUSE_PATH, f"{house_id}.json"), "w") as fw:
                json.dump(tops, fw)


def gen_house(tops, ID):
    """Une fois que l'on sait la hauteur maximale du terrain sous la maison dans toutes les chunks de la maison,
    on peut generer la maison sur ces chunks"""

    # Trouve le point le plus haut sous la maison, qui sera la hauteur finale de la maison
    top = max(list(tops.values()))

    # Supprime le fichier de la maison
    os.remove(os.path.join(settings.VILLAGES_OOB_HOUSE_PATH, f"{ID}.json"))

    for str_chunks in tops:
        (chunk_x, chunk_y) = json.loads(str_chunks)

        # Load les données de la chunk (à laquelle la maison appartient)
        with open(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{chunk_x}_{chunk_y}.json"), "r") as fr:
            data = json.load(fr)
        if ID not in data:
            continue

        # Recupère les blocs de la maison situés dans ce chunk
        blocs = data[ID][1]

        # Marque la maison comme finie dans le chunk, on peut la supprimer
        del data[ID]
        if len(data) > 0:
            # Il reste encore des maisons dans la chunk, la chunk n' donc est pas encore terminée
            with open(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{chunk_x}_{chunk_y}.json"), "w") as fw:
                json.dump(data, fw)
        else:
            # Il ne reste plus de maisons dans la chunk, la chunk est donc terminée
            # On supprime le fichier de chunk
            os.remove(os.path.join(settings.VILLAGES_OOB_CHUNK_PATH, f"chunk_{chunk_x}_{chunk_y}.json"))

            # Fichier de communication avec le data_manager_generation.py, qui indique que toutes les maisons
            # sont placées et que la chunk est terminée et et doit être affichée maintenant
            if os.path.exists(settings.VILLAGE_HOUSE_CHUNK_CHECK_PATH):
                with open(settings.VILLAGE_HOUSE_CHUNK_CHECK_PATH, "r") as fr:
                    completed = json.load(fr)
            else:
                completed = []
            # Ajoute les chunks à l'array des coordonnées des chunks terminés
            completed.append((chunk_x, chunk_y))

            # Sauvegarde, le data_manager_generation s'occupe du reste
            with open(settings.VILLAGE_HOUSE_CHUNK_CHECK_PATH, "w") as fw:
                json.dump(completed, fw)

        norm = settings.coords_to_normalized(chunk_x, chunk_y)

        # Load le terrain à cette chunk
        chunk = np.load(settings.CHUNKS_FORMAT % (*norm,))

        # La hauteur de la maison est 'top', on remplis tout ce qui est dessous par de la pierre
        xy_done = []  # Là ou la pierre a déjà été placée dessous
        for x, y, z, item in blocs:
            sx, sy = x - chunk_x, y - chunk_y
            if (x, y) not in xy_done:
                for sz in range(top, 0, -1):
                    i = chunk[sx, sy, sz]
                    if i in settings.VILLAGES_IGNORED_BLOCS:
                        # On place la pierre dessous
                        chunk[sx, sy, sz] = settings.BLOC_VERS_ID["pierre"]
                    if i in settings.VILLAGES_AUTHORIZED_BLOCS:
                        break
                xy_done.append((x, y))
            # On ajoute le bloc de maison à la chunk
            chunk[sx, sy, z+top+1] = item
        # On sauvegarde la chunk
        np.save(settings.CHUNKS_FORMAT % (*norm,), chunk)


def get_tops_ancien(mins_maxs, current_map, top_left_):
    """Definit le point le plus haut du terrain dans une zone donnée """
    x1, x2, y1, y2 = mins_maxs  # (x1,y1) top_left de la maison, (x2, y2) bottom_right de la maison

    # np.arange est très similaire à "range()", mais plus adapté et efficace pour les arrays numpy
    sx = np.arange(x1 - top_left_[0], x2 - top_left_[0] + 1).reshape(-1, 1)
    sy = np.arange(y1 - top_left_[1], y2 - top_left_[1] + 1).reshape(1, -1)

    # Fais un masque pour les blocs ignorés (air, tronc et feuilles)
    augmented = np.zeros(shape=(16, 16, settings.MAX_HEIGHT))
    augmented[:, :, :-1] = current_map[:, :, 1:]
    mask = np.isin(current_map[sx, sy], settings.VILLAGES_IGNORED_BLOCS)
    #mask2 = np.isin(augmented[sx, sy], [6, 12, 17, 11, 16])
    
    #print(mask.shape, mask2.shape, mask.tolist(), mask2.tolist(), sep="\n")

    #mask *= mask2

    # Trouve l'index du premier bloc qui est un bloc ignoré le long de l'axe z
    indices = np.argmax(mask, axis=2)
    #print(indices)


    # Definit les hauteurs maximales
    tops = indices - 1

    # Hauteur maximum de toutes les hauteurs checkées
    top = int(np.max(tops))

    top = max(settings.WATER_LEVEL, top)

    print("TOP", top)

    return top




def get_tops(mins_maxs, current_map, top_left_):
    """Definit le point le plus haut du terrain dans une zone donnée """
    x1, x2, y1, y2 = mins_maxs  # (x1,y1) top_left de la maison, (x2, y2) bottom_right de la maison

    tops = []
    for x in range(x1 - top_left_[0], x2 - top_left_[0] + 1):
        for y in range(y1 - top_left_[1], y2 - top_left_[1] + 1):
            for z in range(settings.WATER_LEVEL - 5, settings.MAX_HEIGHT):
                if current_map[x, y, z] in settings.VILLAGES_IGNORED_BLOCS:
                    if current_map[x, y, z-1] in settings.VILLAGES_AUTHORIZED_BLOCS:
                        tops.append(z - 1)
                        break 
    try:
        return max(tops)
    except:
        print(range(x1 - top_left_[0], x2 - top_left_[0] + 1), range(y1 - top_left_[1], y2 - top_left_[1] + 1))




def get_tops_2(mins_maxs, current_map, top_left_):
    x1, x2, y1, y2 = mins_maxs  # (x1,y1) top-left of the house, (x2, y2) bottom-right of the house

    # np.arange is similar to "range()", but more suited and efficient for numpy arrays
    sx = np.arange(x1 - top_left_[0], x2 - top_left_[0] + 1).reshape(-1, 1)
    sy = np.arange(y1 - top_left_[1], y2 - top_left_[1] + 1).reshape(1, -1)

    # Mask for ignored blocks (air, trunk, leaves)
    augmented = np.ones(shape=(16, 16, settings.MAX_HEIGHT))
    augmented[:, :, :-1] = current_map[:, :, 1:]
    mask = np.isin(current_map[sx, sy], settings.VILLAGES_IGNORED_BLOCS)
    mask2 = (augmented[sx, sy] in [6, 12, 17, 11, 16])


    # Find the index of the first ignored block along the z-axis
    indices = np.argmax(mask, axis=2)

    # Create a boolean array for valid tops (if indices are within bounds)
    valid_tops = (indices > 0) & (indices < current_map.shape[2])
    
    # Check if the block below the first ignored block is in the below_blocks list
    for i in range(sx.shape[0]):
        for j in range(sy.shape[1]):
            if valid_tops[i, j]:
                below_block = current_map[sx[i, 0], sy[0, j], indices[i, j] - 1]
                if below_block not in [6, 12, 17, 11, 16]:
                    valid_tops[i, j] = False
    
    # Define the tops heights
    tops = np.where(valid_tops, indices - 1, 0)

    # Maximum height of all checked heights
    top = int(np.max(tops))

    return top


def corresponding_chunk(a):
    """Renvoie la chunk à laquelle appartient un bloc"""
    return (a//settings.CHUNK_SIZE)*settings.CHUNK_SIZE
