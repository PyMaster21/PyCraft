import game.terrain_generation.settings as settings
import random
import math
import numpy as np
import json
import os


last_id = 0


class Volcano:

    def __init__(self, coords, seed, player_pos):
        """Classe qui va génerer le volcan et sauvegarder ses données
        Le volcan sera ainsi géneré seulement sur la chunk quand une chunk du volcan est checkée (check_chunk)"""

        random.seed(seed)

        # Determine à quel point le volcan sera pentu
        self.decreasing_factor = random.randint(*settings.VOLCANO_DECREASING_FACTOR)

        # Determine la hauteur approximative du volcan
        self.height = random.randint(*settings.VOLCANO_HEIGHT)  # random.randint(60, 120)
        self.center = coords
        self.d2 = self.decreasing_factor / self.height
        self.volcano_id = ""

        # Determine la hauteur max du volcan et le rayon auquel cette hauteur est atteinte

        self.max_radius, self.max_height_volc = self.compute_max()

        # Calcule la distance qui sépare le centre du volcan theorique et le player
        dist_from_player = ((self.center[0]-player_pos[0])**2+(self.center[1]-player_pos[1])**2)**(1/2)
        if dist_from_player < (self.max_radius*2 + settings.preferences.RENDER_DISTANCE * settings.CHUNK_SIZE):
            # Le volcan est trop proche du joueur pour être géneré en sécurité, on renonce à génerer
            import winsound
            winsound.Beep(1000, 500 )
            pass
        else:
            # Le volcan est assez loin pour être géneré sans bugs theoriques
            self.define_lava_chunks()
            print(f"Volcano {self.volcano_id} placed at {self.center}")

    def define_lava_chunks(self):
        """Definit les chunks sujettes à un ajout de lave, puis sauvegarde toutes les informations du volcan"""
        global last_id

        # Definit les chunks qui sont sur le rayon du volcan, pour ainsi savoir quelle est la hauteur minimum
        # de ce rayon (qui dépend du terrain pas encore géneré).
        # On va donc devoir checké la hauteur minimum pour chacun des points du rayon, pour savoir cette hauteur minimum
        # Quand on sait ça, on génere la lave à l'interieur jusqu'à cette hauteur, pour qu'elle ne dépasse pas du volcan

        implicated_chunks = {}

        for theta in range(0, 360, settings.VOLCANO_CHECK_THETA_STEP):
            # convertis des coordonnées polaires en coordonnées cartésiennes (x,y)
            x, y = math.cos(theta) * self.max_radius + self.center[0], math.sin(theta) * self.max_radius + self.center[
                1]

            # donne la chunk correspondante
            chunk = (int(corresponding_chunk(x)), int(corresponding_chunk(y)))
            if implicated_chunks.get(json.dumps(chunk)):
                # si la chunk existe déjàdans les implicated_chunks, on ajoute les coordonnées à check
                implicated_chunks[json.dumps(chunk)].append((x, y))
            else:
                # si elle n'existe pas, on crée la clé
                implicated_chunks[json.dumps(chunk)] = [(x, y)]

        # On va maintenant regarder quelles chunks sont à l'intérieur de ce rayon (où il y aura la lave)
        inner_chunks = set()
        for radius in range(4):
            for theta in range(0, 360, settings.VOLCANO_CHECK_THETA_STEP):
                # convertis des coordonnées polaires en coordonnées cartésiennes (x,y)
                x, y = math.cos(theta) * self.max_radius * (radius/4) + self.center[0], \
                    math.sin(theta) * self.max_radius * (radius/4) + self.center[1]

                chunk = (int(corresponding_chunk(x)), int(corresponding_chunk(y)))
                if implicated_chunks.get(json.dumps(chunk)):
                    # si la chunk est déjà dans implicated_chunks on ne fait rien, elle est déjà prise en compte
                    pass
                else:
                    # Si elle ne l'est pas, on ajoute la chunk aux inner chunks, et aux implicated_chunks,
                    # mais sans aucune coordonnée à checker
                    inner_chunks.add((int(x//16), int(y//16)))
                    implicated_chunks[json.dumps(chunk)] = []

        volcano_id = last_id
        # determine l'ID propre du volcan
        while os.path.exists(os.path.join(settings.OOB_VOLCANOS_PATH, f"{volcano_id}")) or not volcano_id:
            volcano_id += 1

        self.volcano_id = str(volcano_id)

        # va sauvegarder toutes les chunks impliquées
        for xy_str in implicated_chunks:
            (x, y) = json.loads(xy_str)
            x, y = int(x), int(y)
            chunk_pos_to_check = implicated_chunks[xy_str]
            data = {}
            if os.path.exists(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH, f"chunk_{x}_{y}.json")):
                # si jamais il y a un autre volcan sur cette chunk
                with open(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH, f"chunk_{x}_{y}.json"), "r") as fr:
                    data = json.load(fr)

            data[self.volcano_id] = chunk_pos_to_check

            # sauvegarde la chunk impliquée
            with open(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH, f"chunk_{x}_{y}.json"), "w") as fw:
                json.dump(data, fw)
        chunks_to_check = {}
        for key in implicated_chunks:
            if implicated_chunks[key] != []:
                # n'ajoute que les chunks qui sont sur le rayon et où il y a un check à faire
                chunks_to_check[key] = False

        data = [chunks_to_check, self.center, self.max_height_volc, self.d2, self.height,
                self.decreasing_factor, self.max_radius, list(inner_chunks)]

        # sauvegarde toutes les données du volcan
        with open(os.path.join(settings.OOB_VOLCANOS_PATH, self.volcano_id), "w") as fw:
            json.dump(data, fw)

        # update les chunks déjà génerées si jamais elles existaient (ce qui n'arrive normalement pas)
        center_chunk = settings.coords_to_normalized(corresponding_chunk(self.center[0]),
                                                     corresponding_chunk(self.center[1]))
        for x in range(center_chunk[0] - settings.VOLCANO_VERIFICATION_SIZE,
                       center_chunk[0] + settings.VOLCANO_VERIFICATION_SIZE):
            for y in range(center_chunk[1] - settings.VOLCANO_VERIFICATION_SIZE,
                           center_chunk[1] + settings.VOLCANO_VERIFICATION_SIZE):

                if os.path.exists(settings.CHUNKS_FORMAT % (x, y)):
                    old = np.load(settings.CHUNKS_FORMAT % (x, y))
                    new = check_chunk(old, settings.normalized_to_coords(x, y))
                    np.save(settings.CHUNKS_FORMAT % (x, y), new)

    @staticmethod
    def shape_sigmoid_1(x, d2, h):
        """Premier facteur du sigmoid complet"""
        if x > 500:
            # empêche les valeurs trop grandes
            return 0
        v = (h - 40) / (1 + 2 ** (d2 * x - 6))
        if v <= 0:
            return 0
        return v

    @staticmethod
    def shape_sigmoid_2(x, d2):
        """Deuxième facteur du sigmoid complet"""
        v = 1.5 / (1 + (2 ** (-2 * d2 * x - 2)))  # 0.5/(1+(2**(-d2*x-2)))
        if v <= 0:
            return 0
        return v

    @staticmethod
    def complete_shape_sigmoid(x, d2, h, d):
        """Sigmoide complet qui trace la forme du volcan (en coupe 2D), utilisé soit par
        complete_shape_sigmoid_nonstatic, soit directement, depuis l'exterieur de la classe"""
        return 1 * (Volcano.shape_sigmoid_1(x - 40 + d, d2, h) * (Volcano.shape_sigmoid_2(x - 40 + d, d2) + 1))

    def compute_max(self):
        """Calcule le maximum de la fonction
        """
        step = 0.1  # Distance entre deux calculs de hauteur, + il est petit, + il y a de précision

        # Max initiaux à 0
        max_of_the_funct = 0
        max_index = 0
        for i in range(0, int(100 / step), 1):
            a = i * step
            volcano_height = self.complete_shape_sigmoid(a, self.d2, self.height, self.decreasing_factor)
            if volcano_height > max_of_the_funct:
                # Si on trouve un max plus élevé, on met à jour le max
                max_of_the_funct = volcano_height
                max_index = a

        return max_index, max_of_the_funct


def corresponding_chunk(a):
    """Renvoie la chunk à laquelle appartient un bloc"""
    return (a // settings.CHUNK_SIZE) * settings.CHUNK_SIZE


def check_chunk(current_map, top_left_):
    """Verifie si il y a de la lave à cette chunk et regarde si elle est sous l'influence d'un volcan,
    au quel cas il sera ajouté"""
    (x, y) = top_left_

    if os.path.exists(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH, f"chunk_{x}_{y}.json")):
        # Calcule les hauteur minimum des coordonnées à verifier pour cette chunk
        find_lava_height(top_left_)

    # Liste tous les volcans existants
    for ID in os.listdir(settings.OOB_VOLCANOS_PATH):
        if "_" in ID:
            continue

        # Check si la chunk est sous l'influence du volcan
        current_map = check_volcano_nearby(top_left_, ID, current_map)

    return current_map


def find_lava_height(top_left_):
    """Calcule les hauteur minimum des coordonnées à verifier
    (qui sont celles qui sont sur le cercle formé par le haut du volcan)"""

    (x, y) = top_left_
    norm = settings.coords_to_normalized(*top_left_)  # coordonnées normalisées

    # load les hauteurs de terrain, sauvegardées dans generation.py
    chunk_heights = np.load(settings.HEIGHTS_FORMAT % (*norm,))

    with open(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH, f"chunk_{x}_{y}.json"), "r") as fr:
        data = json.load(fr)
    # On check tous les volcans nécessaires
    for ID in data:

        coords_to_check = data[ID]

        # Load les données du volcan
        with open(os.path.join(settings.OOB_VOLCANOS_PATH, ID), "r") as fr:
            min_heights, center, max_height_volc, d2, h, d, max_radius, inner_chunks = json.load(fr)

        # Si il y a au moins une coordonnée à checker, c'est à dire si cette chunk est située sur le rayon
        if not coords_to_check == [] and json.dumps(top_left_) in min_heights.keys():
            if not min_heights[json.dumps(top_left_)]:  # si la chunk n'as pas déjà été checkée

                heights = []
                for (x, y) in coords_to_check:
                    # ajoute aux hauteurs le nombre de blocs de pierre à ces coordonnées
                    heights.append(chunk_heights[int(x) % settings.CHUNK_SIZE, int(y) % settings.CHUNK_SIZE, 0])

                # regarde la hauteur minimale sur les coordonnées à checker
                min_height = min(heights)
                min_heights[json.dumps(top_left_)] = min_height

                # sauvegarde le résultat de ce check
                with open(os.path.join(settings.OOB_VOLCANOS_PATH, ID), "w") as fw:
                    json.dump((min_heights, center, max_height_volc, d2, h, d, max_radius, inner_chunks), fw)

        # verifie si toutes les chunks ont été verifiées
        for i in min_heights:
            if not min_heights[i]:
                break
        else:
            # determine le minimum de toutes les hauteurs de terrain au niveau du cercle du haut du volcan
            min_to_rule_them_all = min(min_heights.values())

            # determine la hauteur de la lave
            lava_height = max_height_volc + min_to_rule_them_all - settings.VOLCANO_SAFETY_THRESHOLD

            # Place la lave dans le volcan
            """norm = settings.coords_to_normalized(*top_left_)  # normalise les coordonnées
            chunk_map = np.load(settings.HEIGHTS_FORMAT % (*norm,))
            check_volcano_nearby(top_left_, ID, chunk_map)"""

            place_lava(ID, lava_height, min_heights, inner_chunks)
            print(f"Lava placed for volcano {ID}")


def check_volcano_nearby(top_left_, ID, current_map):
    """Verifie pour ce volcan si il influence la chunk, si oui, on place les blocs en conséquence"""
    with open(os.path.join(settings.OOB_VOLCANOS_PATH, ID), "r") as fr:
        init_volcano_data = json.load(fr)
        volcano_data = init_volcano_data
        min_heights, center, max_height_volc, d2, h, d, max_radius, chunks = volcano_data

    center_x, center_y = top_left_[0] + settings.CHUNK_SIZE / 2, top_left_[1] + settings.CHUNK_SIZE / 2

    # Fais une première verification de si le volcan est assez proche
    squared_dist_from_center = ((center_x - center[0]) ** 2 + (center_y - center[1]) ** 2)
    if squared_dist_from_center > (max_radius * 10) ** 2:
        # Le volcan est très loin de la chunk, il n'y a pas besoin de verifier
        return current_map
    dist_from_center = squared_dist_from_center ** (1 / 2)

    # On calcule la hauteur qu'aurait le volcan à cette chunk si on prenait le centre de la chunk
    mean_bloc_height = Volcano.complete_shape_sigmoid(dist_from_center, d2, h, d)

    if mean_bloc_height > 0.2:  # Si la hauteur est serait suffisante

        norm = settings.coords_to_normalized(*top_left_)  # normalise les coordonnées
        chunk_heights = np.load(settings.HEIGHTS_FORMAT % (*norm,))  # load les hauteurs de bloc
        for x in range(settings.CHUNK_SIZE):
            for y in range(settings.CHUNK_SIZE):

                sx, sy = x + top_left_[0], y + top_left_[1]

                dist_from_center = ((sx - center[0]) ** 2 + (sy - center[1]) ** 2) ** 0.5

                # Calcule la hauteur du volcan à ce point
                bloc_height = Volcano.complete_shape_sigmoid(dist_from_center, d2, h, d)

                if bloc_height >= 2:  # Si la hauteur est suffisante
                    bloc_height = int(bloc_height + chunk_heights[x, y, 0] - 1)  # hauteur totale du volcan à ce point
                    if int(chunk_heights[x, y, 0]) < settings.WATER_LEVEL:
                        if bloc_height <= settings.WATER_LEVEL:

                            current_map[x, y, int(chunk_heights[x, y, 0]):(bloc_height+1)] = 1

                        else:
                            current_map[x, y, int(chunk_heights[x, y, 0]):int(settings.WATER_LEVEL)] = 1
                            current_map[x, y, settings.WATER_LEVEL:int(bloc_height+1)] = 17
                    else:
                        current_map[x, y, int(chunk_heights[x, y, 0]):bloc_height+1] = 17

                    chunk_heights[x, y, 2] = bloc_height  # update la hauteur totale du terrain

                if dist_from_center < max_radius:  # il y aura de la lave à ces coordonnées
                    # sauvegarde le fait qu'il y ait de la lave à ces coordonnées
                    chunk_heights[x, y, 3] = True

                    if norm not in volcano_data[7]:
                        volcano_data[7].append(norm)

        with open(os.path.join(settings.OOB_VOLCANOS_PATH, ID), "w") as fw:
            json.dump(volcano_data, fw)

        # sauvegarde les hauteurs mises à jour
        np.save(settings.HEIGHTS_FORMAT % (*norm,), chunk_heights)

    return current_map


lava_placed = []  # liste qui stocke les volcans pour lesquels la lave est déjà placée, pour éviter de la re-placer


def place_lava(ID, lava_height, radius_chunks, inner_chunks):
    """Place la lave du volca"""
    global lava_placed
    if ID in lava_placed:
        return

    lava_placed.append(ID)

    # ajoute les chunks interieures aux chunks qui ont de la lave
    chunks_with_lava = inner_chunks

    # ajoute les chunks du rayon aux chunks qui ont de la lave
    for i in radius_chunks:
        chunk_coords = json.loads(i)
        norm = settings.coords_to_normalized(*chunk_coords)
        if norm not in chunks_with_lava:
            chunks_with_lava.append(norm)

    # supprime les doublons
    chunks_with_lava = list(set(map(tuple, inner_chunks)))

    # Fichier de communication avec le data_manager_generation.py, qui indique que la lave a été placée
    # et que ces chunks sont terminés et doivent être affichés maintenant
    if os.path.exists(settings.VOLCANO_LAVA_CHECK_PATH):
        with open(settings.VOLCANO_LAVA_CHECK_PATH, "r") as fr:
            coords_array = json.load(fr)
    else:
        coords_array = []

    for chunk_coords_str in chunks_with_lava:

        norm = chunk_coords_str

        chunk_coords = int(norm[0] * settings.CHUNK_SIZE), int(norm[1] * settings.CHUNK_SIZE)

        # verifie si le fichier de chunk existe (normalement il existe toujours)
        if not os.path.exists(settings.CHUNKS_FORMAT % (*norm,)):
            continue
        terrain = np.load(settings.CHUNKS_FORMAT % (*norm,))
        heights = np.load(settings.HEIGHTS_FORMAT % (*norm,))  # load les hauteurs de terrain
        for x in range(settings.CHUNK_SIZE):
            for y in range(settings.CHUNK_SIZE):
                if heights[x, y, 3]:  # si il y a de la lave à ce bloc
                    height = heights[x, y, 2]  # hauteur totale = hauteur du basalte

                    # Remplis la colonne de lave, depuis le basalte jusqu'à la hauteur max de la lave
                    terrain[x, y, int(height):int(lava_height)] = settings.BLOC_VERS_ID["lave"]

        # Sauvegarde la chunk modifiée
        np.save(settings.CHUNKS_FORMAT % (*norm,), terrain)

        if os.path.exists(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH,
                                       f"chunk_{chunk_coords[0]}_{chunk_coords[1]}.json")):

            # On load la data du volcan
            with open(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH,
                                   f"chunk_{chunk_coords[0]}_{chunk_coords[1]}.json"), "r") as fr:
                data = json.load(fr)

            if ID in data:
                del data[ID]
            if len(data) > 0:
                # Si il y a encore des volcans, la chunk n'est pas encore terminée
                with open(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH,
                                       f"chunk_{chunk_coords[0]}_{chunk_coords[1]}.json"), "w") as fw:
                    json.dump(data, fw)
            else:
                # Il n'y a plus de volcan dans cette chunk, elle est terminée
                # Supprime la chunk superflue
                os.remove(os.path.join(settings.OOB_VOLCANOS_CHUNK_PATH,
                                       f"chunk_{chunk_coords[0]}_{chunk_coords[1]}.json"))

                # Ajoute les chunks à l'array des coordonnées des chunks terminés
                coords_array.append(norm)

    # Sauvegarde
    with open(settings.VOLCANO_LAVA_CHECK_PATH, "w") as fw:
        json.dump(coords_array, fw)
