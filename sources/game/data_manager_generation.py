"""
Ceci est un module en deux fichiers qui permettra de stocker des chunks et de gérér ceux qui doivent être générés.
Il y a deux côtés:
    data manager world
        Ce module va stocker les chunks générés, en cours de génération, non générés, modifiés etc.
        Il va également demander à générer certains chunks auu data manager generation
    data manager generation
        Ce module va recevoir les messages de data manager generation, les trier en ordre de priorité et va
        générer les chunks.
        Il va ensuite envoyer un message de confirmation au data manager world
Les deux côtés communiquent avec une multiprocessing.Pipe instantiée chez le data manager world
"""

import game.settings as settings
import game.terrain_generation.main as chunk_generation
import game.terrain_generation.structures as structures

import os
import json
import time

# Path des fichiers de structure
VOLCANO_LAVA_CHECK_PATH = f"{settings.WORLD_ID}/_outofbounds/volcanos/lava.json"
VILLAGE_HOUSE_CHUNK_CHECK_PATH = f"{settings.WORLD_ID}/_outofbounds/villages/houses_finished.json"
oob_volcanos_chunk_path = f"{settings.WORLD_ID}/_outofbounds/volcanos"
oob_house_path = f"{settings.WORLD_ID}/_outofbounds/villages"
oob_chunk_path = f"{settings.WORLD_ID}/_outofbounds/villages"

# ---------------------------------- VARIABLES DE GENERATION ----------------------------------

queue = []  # la queue des chunks à être générés
# pareil que la queue standard mais les éléments ici ont la priorité sur les éléments dans la queue
priority_queue = []

# ---------------------------------- TOUT  BUSINESS DE QUEUE ----------------------------------


def read_messages(connection):
    """
    Cette fonction va lire tous les nouveaux messages arrivés dans la pipe depuis le datamanager world,
    et les traîter afin de les ajouter aux queues
    :param connection: la connection entre les datamanagers
    """
    global queue, priority_queue
    while connection.poll():  # Tant qu'il y a des messages on va les lire
        message = connection.recv()  # On récupère le message
        if message[0] == 1:  # Un seul chunk a été envoyé
            # Le composant du message, le message[1] correspond au type de génération, et message[2] au chunk
            to_add = (message[1], message[2])
            if message[2] == 2 or message[2] == 3:  # Cette chunk a la priorité
                if to_add in priority_queue:  # si la chunk est déjà dans la queue on la remonte au début
                    priority_queue.remove(to_add)
                priority_queue.append(to_add)
            else:  # Cette chunk est une chunk démandée de façon standard
                if to_add in queue:  # si la chunk est déjà dans la queue on remonte la chunk à la fin de la queue
                    queue.remove(to_add)
                queue.append(to_add)
        elif message[0] == 2:  # On a envoyé un batch
            # On enlève l'élement nous disant que c'est un batch pour ne plus qu'avoir un tuple de tuples
            message.remove(2)
            for chunk in message:  # On itère à travers les chunks
                if chunk[1] == 2 or chunk[1] == 3:  # Priorité
                    if chunk in priority_queue:  # si la chunk est déjà dans la queue on la remonte au début
                        priority_queue.remove(chunk)
                    priority_queue.append(chunk)
                else:
                    if chunk in queue:  # si la chunk est déjà dans la queue on remonte la chunk à la fin de la queue
                        queue.remove(chunk)
                    queue.append(chunk)  # Adding the new chunk
        elif message[0] == 3:  # On a demandé un chunk scan

            overchunk = message[1][0]  # l'overchunk actuel
            player_pos = message[1][1]  # La position du joueur
            structures.pregenerate(overchunk[0], overchunk[1],
                                   settings.setSeeds(settings.SEED, 2),
                                   player_pos)  # On effectue le structure scan
            # On envoie le message de confirmation
            connection.send((message[1][0], 4))
    len_queue = len(queue)
    if len_queue > settings.MAX_QUEUE:  # si la longueur de la queue est trop grande, on enlève les vieux éléments
        connection.send((queue[0][0], 0))
        queue = queue[len_queue:]


def generation(connection):
    """
    La fonction qui appelle la génération
    :param connection: la connection entre les deux data_manager
    """
    global queue, priority_queue
    time.sleep(1)  # Limite les broken pipe error
    try:
        read_messages(connection)
    # Cette erreur est une erreur système contre laquelle nous ne pouvons rien faire,
    # mais elle n'arrive qu'en début de jeu
    except BrokenPipeError:
        raise Exception("DUDE THIS IS ANNOYING")

    while 1:  # Plus rapide que while True
        read_messages(connection)  # on lit les messages de la connection
        if priority_queue:  # On lit de la priority queue en priorité
            # On récupère le chunk à générer
            generating = priority_queue.pop(-1)
        elif queue:  # si la priority queue est vide on peut prendre la queue standard
            generating = queue.pop(-1)  # On récupère le chunk à générér
        else:
            continue  # On passe
        # On a juste demandé les renderables (message 1 ou 3)
        # qui correspondent aux renderables avec (1) et sans priorité (3) et donc reste 1 sous mod 2
        if generating[1] & 2 == 1:
            renderables = chunk_generation.get_renderables_norm(
                *generating[0])  # On demande les renderables
            if renderables:
                # On envoie le message de confirmation, on a les renderables (3)
                connection.send((generating[0], 3))
            else:
                # On envoie le message de confirmation, on n'a rien pu générere (0)
                connection.send((generating[0], 0))
        else:  # Génération normale
            chunk_generation.generate_chunk_norm(
                [generating[0]])  # On génère la chunk
            if not has_structures(generating[0]):  # Il n'y a pas de structure
                renderables = chunk_generation.get_renderables_norm(
                    *generating[0])  # On demande les structures
                if renderables:
                    # On envoie le message de confirmation, tout a pu être généré (2)
                    connection.send((generating[0], 2))
                else:
                    # On envoie le messaage de confirmation, que la chuunk a pu être générée (1)
                    connection.send((generating[0], 1))
            else:
                # La chunk a une structure donc on demande au datamanager world d'attendre (5)
                connection.send((generating[0], 5))

        check_structures_done(connection)


def check_structures_done(connection):
    """
    Vérifie quelles chunks ont fini de placer leurs structures(volcan ou village) grâce au fichiers de communication
    des villages et des volcans. Cette fonction va générer les chunks à structures pour lesquelles nous avions
    renvoyé 5 au data manager world
    :param connection: la connection au datamanager world via la pipe
    """
    if os.path.exists(VILLAGE_HOUSE_CHUNK_CHECK_PATH):  # Regarde si le fichier de communication existe
        with open(VILLAGE_HOUSE_CHUNK_CHECK_PATH, "r") as fr:
            # Chunks ayant fini de générer leurs villages
            completed = json.load(fr)
        for coords in completed:
            norm = coords[0] // settings.CHUNK_SIZE, coords[1] // settings.CHUNK_SIZE
            # Si il n'y a pas aussi un volcan sur cette chunk
            if not has_structures(norm, structures_to_check="volcanos"):
                renderables = chunk_generation.get_renderables_norm(
                    *norm)  # obtient les renderables
                if renderables:  # Les renderables ont-ils été obtenus?
                    connection.send((norm, 2))  # Envoie la confirmation
                else:
                    connection.send((norm, 1))
                completed.remove(coords)
        if len(completed) > 0:  # Si il reste des chunks complétés mais pas enregistrés comme tels
            with open(VILLAGE_HOUSE_CHUNK_CHECK_PATH, "w") as fw:  # Sauvegarde pour qu'ils le soient
                json.dump(completed, fw)
        else:
            os.remove(VILLAGE_HOUSE_CHUNK_CHECK_PATH)

    if os.path.exists(VOLCANO_LAVA_CHECK_PATH):  # Si il reste des chunks avec volcan
        # On récupère les chunks ayant complété leur volcan complètement
        with open(VOLCANO_LAVA_CHECK_PATH, "r") as fr:
            completed = json.load(fr)
        # On ôte les duplicats de là
        completed = list(set(map(tuple, completed)))
        for coords in completed:
            # Si il y a un village sur la chunk avec un volcan
            if not has_structures(coords, structures_to_check="villages"):
                renderables = chunk_generation.get_renderables_norm(
                    *coords)  # On récupère les renderables
                if renderables:
                    # On envoie confirmation de génération
                    connection.send((coords, 2))
                else:
                    # On envoie la confirmation mais pas pour les renderables
                    connection.send((coords, 1))
                completed.remove(coords)
        if len(completed) > 0:  # Si il reste des chunks complétés mais pas enregistrés comme tels
            with open(VOLCANO_LAVA_CHECK_PATH, "w") as fw:  # Sauvegarde pour qu'ils le soient
                json.dump(completed, fw)
        else:
            os.remove(VOLCANO_LAVA_CHECK_PATH)


def has_structures(chunk, structures_to_check=("volcanos", "villages")):
    """
    Dit si il y a une structure dans la chunk
    :param chunk: le tuple (chunk_x, chunk_y)
    :param structures_to_check: le tuple (struct1,struct2...) des structures pour lesquelles vérifier 
    """

    # On récupère les coordonnées absolues et on int pour quand on formatera des strings
    x, y = int(chunk[0]*settings.CHUNK_SIZE), int(chunk[1] *
                                                  settings.CHUNK_SIZE)

    if "volcanos" in structures_to_check:
        # La structure existe-t-elle?
        if os.path.exists(os.path.join(oob_volcanos_chunk_path, f"chunk_{x}_{y}.json")):
            return True
    if "villages" in structures_to_check:  # La structure existe-t-elle?
        if os.path.exists(os.path.join(oob_chunk_path, f"chunk_{x}_{y}.json")):
            return True
    return False
