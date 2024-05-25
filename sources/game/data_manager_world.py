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
# Utilisé pour la création du nouveau process
import game.data_manager_generation as data_manager_generation

from multiprocessing import Process, Pipe
import numpy as np
import os

# Les paths des fichiers de structures
oob_volcanos_chunk_path = f"{settings.WORLD_ID}/_outofbounds/volcanos"
oob_chunk_path = f"{settings.WORLD_ID}/_outofbounds/villages"


def has_structures(chunk):
    """
    fonction qui détermine si une chunk a des structures non terminées ou pas
    :param chunk: le tuple (chunk_x, chunk_y)
    :return: un bool
    """
    x, y = int(chunk[0]*settings.CHUNK_SIZE), int(chunk[1]*settings.CHUNK_SIZE)
    if os.path.exists(os.path.join(oob_volcanos_chunk_path, f"chunk_{x}_{y}.json")):
        return True
    if os.path.exists(os.path.join(oob_chunk_path, f"chunk_{x}_{y}.json")):
        return True
    return False


# ---------------------------------- VARIABLES DE GÉNÉRATION----------------------------------

generated_chunks = set()  # tous les chunks ayant été générés
# tous les chunks ayant été générés, avec renderables
generated_with_renderables = set()

# On récupère tous les chunks ayant été générés avec/sans renderables
# et on met à jour les variables generated_chunks et generated_with_renderables
# Utilisé lors du load de monde, pour ne pas regénérer des chunks
for file in os.listdir(settings.WORLD_ID):  # On itère sur les fichiers
    file = file.replace(".npy", "")  # On enlève l'extension
    # Le fichier de la chunk existe (format "chunk_{chunk_x}_{chunk_y}")
    if "chunks" in file and "renderables" not in file:
        # On split selon le _ pour obtenir _="chunk" , x_chunk = chunk_x et y_chunk = chunk_y,
        # voir le format à la ligne d'au dessus
        _, x_chunk, y_chunk = file.split("_")
        # On récupère le nombre à partir du str
        x_chunk, y_chunk = int(x_chunk), int(y_chunk)
        # Si il y a des structures non générées on ne peut pas encore dire que cette chunk est terminée
        if not has_structures((x_chunk, y_chunk)):
            generated_chunks.add((x_chunk, y_chunk))
    # le fichier est un fichier de format "chunk_renderables_{chunk_x}_{chunk_y}"
    if "renderables" in file:
        # On split afin de récupérér les coordonnées chunk, voir le format au dessus
        _, _, x_renderable, y_renderable = file.split("_")
        x_renderable, y_renderable = int(x_renderable), int(
            y_renderable)  # On récupère le int à partir du str
        # La chunk est générée (alphabétiquement elles passent avant les renderables donc il n'y a pas de souci)
        if (x_renderable, y_renderable) in generated_chunks:
            # On ajoute la chunk aux renderables
            generated_with_renderables.add((x_renderable, y_renderable))
            # Si il n'y a pas de structure non terminée on peut également dire que la chunk est générée
            # (cas de la lave de certains volcans)
            if not has_structures((x_renderable, y_renderable)):
                # On joute aux generated
                generated_chunks.add((x_renderable, y_renderable))


# ---------------------------------- FONCTIONS POUR RÉCUPÉRER LES CHUNKS ----------------------------------


# Les chunks stockées dans le data manager, pour la physique entre autres
loaded_chunks = []
loaded_renderables = []  # Les chunks affichéés à l'écran
# Ces deux variables sont des liste car on enlève les chunks les plus vieilles quand les listes deviennent trop grandes

# Le dictionnaire d'éléments ((chunk_x,chunk_y), np.ndarray (la chunk))
loaded_chunks_dict = {}
# Le dictionnaire d'éléments ((chunk_x,chunk_y), np.ndarray (les renderables))
loaded_renderables_dict = {}

called_structure_overchunks = set()  # Les structures scans déjà demandés

# Chunks avec structures qui ont donc un fonctionnement particulier
chunks_with_structures = set()

changed_chunks = set()  # Les chunks qui ont été changés (plaçage/cassage de bloc)

# Chunks qui n'ont pas pu être générés donc inutile de les redemander avant d'avoir pu générer d'autres chunks
not_generable_yet = set()
# Les derniers chunks envoyés à la queue le chunk (1,1) est déjà généré donc ne sera jamais demandé.
# Il agit tel un None ici
last_sent = [(1, 1) for i in range(settings.LAST_SENT_LENGTH)]

# ---------------------------------- CREATION DU PROCESS ----------------------------------
# On crée une pipe, soit unn moyen de communication entre deux process
connection_world, connection_generation = Pipe(duplex=True)
process = Process(target=data_manager_generation.generation, args=(
    connection_generation,))  # On instantie le second process
process.start()  # On le démarre


# ---------------------------------- TOUT BUSINESS DE QUEUE ----------------------------------

def send_to_queue(chunk, message_type=0):
    """
    Envoie la chunk à la queue dans le process de génération (data manager génération)
    :param chunk: le tuple (chunk_x, chunk_y)
    :param message_type: le type de génération:
                            0: génération normale
                            1: juste les renderables
                            2: génération normale TOP PRIORITY
                            3: juste les renderables TOP PRIORITY
    """
    global connection_world

    # La chunk est potentiellement générable et non générée
    if chunk not in not_generable_yet and chunk not in last_sent and chunk not in chunks_with_structures:
        if message_type == 0 or message_type == 2:  # Génération normale
            if chunk not in generated_chunks:
                last_sent.append(chunk)  # On vient de l'envoyer
                last_sent.pop(0)  # On enlève un élément de last_sent
                # On envoie le message à la connection
                connection_world.send([1, chunk, message_type])
        # la génération de chunks renderables a la condition d'avoir tous ses
        # chunks voisins de générés pour pouvoir être effectuée
        elif (chunk not in generated_with_renderables) and renderability(chunk):
            last_sent.append(chunk)  # On vient de l'envoyer
            last_sent.pop(0)  # On enlève un élément de last_sent
            # On envoie le message à la connection
            connection_world.send([1, chunk, message_type])


def send_batch(batch):
    """
    Envoie le batch de chunks au process de génération
    Ceci est utile car send_batch(batch) est nettement plus rapide que
    for chunk in batch:
        send_to_queue(chunk)
    de par le fait que ce qui prend du temps est surtout l'ouverture de la pipe, et moins le transfert
    :param batch: le tuple de tuples (((chunk_x, chunk_y), message_type), ((chunk_x, chunk_y), message_type)...)
    avec message_type : le type de génération:
                            0: génération normale
                            1: juste les renderables
                            2: génération normale TOP PRIORITY
                            3: juste les renderables TOP PRIORITY
    """
    global connection_world
    # message[0] est utilisé pour savoir quel type d'envoi c'est. Ici, c'est un batch send
    new_batch = [2]

    for chunk in batch:
        # Selon ces conditions la chunk ne devrait pas être envoyée
        if chunk[0] not in not_generable_yet and chunk[0] not in last_sent:
            if chunk[1] == 0 or chunk[1] == 2:  # génération normale
                if chunk[0] not in generated_chunks:  # On ne l'a pas déjà généré
                    last_sent.append(chunk[0])
                    last_sent.pop(0)
                    # On ajoute la chunk au batch à envoyer
                    new_batch.append(chunk)
            # les conditions pour les renderables sont différentes
            elif (chunk[0] not in generated_with_renderables) and renderability(chunk[0]):
                last_sent.append(chunk[0])
                last_sent.pop(0)
                # On ajoute la chunk au batch à envoyer
                new_batch.append(chunk)
    # On envoie le batch au process de génération
    connection_world.send(new_batch)


def send_structure_scan(chunk_scan, player_pos):
    """
    Demande au data manager generation d'effectuer un scan de structures sur une grande aire
    Ceci est nécessaire pour pouvoir savoir quels chunks ont des structures
    avant d'arriver en gendistance du centre de celle-ci
    :param chunk_scan: la paire de tuples d'overchunks ((x,y),(x2,y2))
    :param player_pos: la position du joueur, en coordonnées standard
    """
    global connection_world, called_structure_overchunks
    if chunk_scan not in called_structure_overchunks:  # Le chunk scan n'a pas déjà été effectué
        # On envoie le scan
        connection_world.send((3, (chunk_scan, player_pos)))


def read_messages():
    """
    Une fonction qui va vérifier tous les nouveaux messages dans la pipe depuis le data_manager_generation 
    """
    while connection_world.poll():  # Il y a des messages
        message = connection_world.recv()  # On les récupère
        handle_message(message)  # On les traîte


def handle_message(message):
    """
    Ceci est une fonction faite pour traîter les messages reçus depuis le data_manager_generation via la pipe
    Cette fonction va essentiellement alors mettre à jour des variables de ce côté
    :param message: the message depuis le data manager generation via le pipe: ((chunk_x,chunk_y), generation_id) 
            generation_id: 
                0 : rien
                1 : généré sans renderables
                2 : généré avec renderables
                3 : juste des renderables
                4 : structure scan complet
                5 : chunk avec structures (qui sera renvoyé quand terminé - en théorie)
    """
    chunk = message[0]
    if chunk in last_sent:  # On sort la chunk des dernières chunks envoyées
        last_sent.remove(chunk)
        last_sent.append((1, 1))
    match message[1]:  # Le type de message
        case 0:  # la chunk n'est pas générable comme c'est maintenant
            not_generable_yet.add(chunk)
        case 1:
            generated_chunks.add(chunk)
            not_generable_yet.clear()  # Elle pourraient maintenant être générables
            if chunk in chunks_with_structures:  # Était-ce une chunk avec structures?
                chunks_with_structures.remove(chunk)  # On peut donc l'enlever

            if chunk in loaded_chunks:  # On a réenvoyé la chunk
                # On peut alors l'enlever des listes puisque les get_chunk et get_renderables vont alors la rechercher
                loaded_chunks.remove(chunk)
                loaded_chunks_dict.pop(chunk)
        case 2:
            generated_chunks.add(chunk)
            generated_with_renderables.add(chunk)
            not_generable_yet.clear()  # Elle pourraient maintenant être générables
            if chunk in chunks_with_structures:  # Était-ce une chunk avec structures?
                chunks_with_structures.remove(chunk)  # On peut donc l'enlever

            if chunk in loaded_renderables:  # Réenvoi de chunk
                # On peut alors l'enlever des listes puisque les get_chunk et get_renderables vont alors la rechercher
                loaded_renderables.remove(chunk)
                loaded_renderables_dict.pop(chunk)
            if chunk in loaded_chunks:
                # On peut alors l'enlever des listes puisque les get_chunk et get_renderables vont alors la rechercher
                loaded_chunks.remove(chunk)
                loaded_chunks_dict.pop(chunk)
        case 3:
            generated_with_renderables.add(chunk)
            if chunk in chunks_with_structures:  # Était-ce une chunk avec structures?
                chunks_with_structures.remove(chunk)  # On peut donc l'enlever

            if chunk in loaded_renderables:  # réenvoi de chunk
                # On peut alors l'enlever des listes puisque les get_chunk et get_renderables vont alors la rechercher
                loaded_renderables.remove(chunk)
                loaded_renderables_dict.pop(chunk)
            if chunk in loaded_chunks:
                # On peut alors l'enlever des listes puisque les get_chunk et get_renderables vont alors la rechercher
                loaded_chunks.remove(chunk)
                loaded_chunks_dict.pop(chunk)
        case 4:
            called_structure_overchunks.add(chunk)
        case 5:
            chunks_with_structures.add(chunk)  # Cette chunk a une structure


def renderability(chunk):
    """
    Si la chunk est renderables étant donné les circonstances actuelles de chunks
    (tous ses voisins doivent être générés)
    :param chunk: le tuple (chunk_x, chunk_y)
    """
    to_check = ((chunk[0]-1, chunk[1]),  # Toutes les chunks à check pour déterminer si la chunk est renderable ou non
                (chunk[0]+1, chunk[1]),
                (chunk[0], chunk[1]-1),
                (chunk[0], chunk[1]+1),
                (chunk[0], chunk[1]))

    for chunk_check in to_check:
        if chunk_check not in generated_chunks:  # Si une des chunks n'est pas encore générée
            return False                         # il est impossible que *la* chunk puisse avoir des renderables
    return True


# ---------------------------------- MANAGEMENT DE DONNÉES----------------------------------

def get_renderables(chunk, generate=False, read=False):
    """
    Permet de chercher les renderables de chunks, sans avoir à les re-chercher à chaque fois, si c'est une chunk active
    :param chunk: le tuple (chunk-x,chunk-y)
    :param generate: si le code doit demander à générer la chunk en cas d'abscence de celle-ci
    :param read: si le code doit lire les messages du data manager avant de s'éxécuter
                 (attention, connection.poll et connection.recv sont des fonctions fort chronophages)
    """
    global loaded_renderables, loaded_renderables_dict, generated_with_renderables
    if read:  # connection.poll et connection.recv sont très chronophages
        read_messages()  # On lit les nouveaux messages potentiellement reçus du data manager
    if chunk in loaded_renderables:  # La chunk est déjà stockée
        # Donc on peut la renvoyer à partir du dict
        return loaded_renderables_dict[chunk]
    elif chunk in generated_with_renderables:  # La chunk n'est pas stockée mais elle a été générée
        try:
            chunk_load = np.load(settings.RENDERABLES_FORMAT %
                                 chunk)  # On load le np.array
        # Un autre programme est en train de le lire (ceci n'est pas censé se passer,
        # mais le try except ne coûte presque rien en plus, tant que le except n'est pas trigger)
        except Exception:
            return False
        # On met à jour les variables
        loaded_renderables_dict[chunk] = chunk_load
        loaded_renderables.append(chunk)
        # Les listes ont atteint leur limite (on limite la ram utilisée)
        if len(loaded_renderables) > settings.MAX_RENDERABLES_STORED:
            chunk_pop = loaded_renderables[0]
            if chunk_pop in changed_chunks:  # On sauvegarde la chunk si cela est nécéssaire
                save_chunk(chunk_pop)
            # Ceci permet d'enlever la plus vielle chunk de la liste et du dict
            loaded_renderables_dict.pop(loaded_renderables.pop(0))
        return chunk_load
    else:  # La chunk n'a pas encore été générée ou n'est pas engregistrée comme telle
        if generate:  # On a le droit de générer la chunk
            if chunk in generated_chunks:  # La chunk est générée, mais il manque les renderables
                send_to_queue(chunk, 3)  # On ne demande que les renderables
            else:  # Il manque tout
                send_to_queue(chunk, 2)  # On demande donc tout
    return False  # Si rien d'autre a été return avant, on return False


def get_chunk(chunk, read=False):
    """
    Permet de recupérer une chunks, sans avoir à les re-chercher à chaque fois, si c'est une chunk "active"
    :param chunk: le tuple (chunk-x,chunk-y)
    :param read: si le code doit lire les messages du data manager avant de s'éxécuter
    (attention, connection.poll et connection.recv sont des fonctions fort chronophages)
    """
    global loaded_chunks, loaded_chunks_dict, generated_chunks
    if read:  # connection.poll et connection.recv sont très chronophages
        read_messages()  # On lit les nouveaux messages potentiellement reçus du data manager
    if chunk in loaded_chunks:  # La chunk est déjà stockée
        return loaded_chunks_dict[chunk]  # On peut donc la chercher
    elif chunk in generated_chunks:  # La chunk n'est pas stockée mais elle est générée
        chunk_load = np.load(settings.CHUNKS_FORMAT %
                             chunk)  # On cherche la chunk
        loaded_chunks_dict[chunk] = chunk_load  # On met à jour des variables
        loaded_chunks.append(chunk)
        # Si la liste est trop longue on la limite (on limite la ram utilisée)
        if len(loaded_chunks) > settings.MAX_CHUNKS_STORED:
            chunk_pop = loaded_chunks[0]
            if chunk_pop in changed_chunks:  # On sauvegarde la chunk si cela est nécéssaire
                save_chunk(chunk_pop)
            # Ceci permet d'enlever la plus vielle chunk de la liste et du dict
            loaded_chunks_dict.pop(loaded_chunks.pop(0))
        return chunk_load
    return False


# ---------------------------------- DATA MODIFICATION----------------------------------

def change_in_renderables(chunk_x, chunk_y, new_renderables=None, block=None):
    """
    Fonction appellée lors d'un changement dans les renderables (plaçage/cassage).
    Elle va alors mettre à jour ceux-ci dans les variables du data_manager
    Il y a deux choix: donner un nouvel array ou un block à ajouter à l'actuelle
    :param chunk_x: coordonnée x de la chunk
    :param chunk_y: coordonnée y de la chunk
    :param new_renderables: version mise à jour des renderables, donnée par fast_renderables
    :param block: le bloc à ajouter, si la fonction est utilisée dans son second cas d'utilisation
    """
    global loaded_renderables_dict, changed_chunks
    if new_renderables is not None:  # Le premmier cas d'utilisation est choisi
        # On s'assure bien du fait que les renderables existaient déjà
        chunk_fetch = get_renderables((chunk_x, chunk_y))
        if isinstance(chunk_fetch, np.ndarray):  # Voir la ligne d'au dessus
            # On change les renderables
            loaded_renderables_dict[chunk_x, chunk_y] = new_renderables
            # Le chunk est maintenant changé
            changed_chunks.add((chunk_x, chunk_y))
    elif block is not None:  # Le second cas d'uutilisation est choisi
        # On s'assure bien du fait que les renderables existent
        chunk_fetch = get_renderables((chunk_x, chunk_y))
        if isinstance(chunk_fetch, np.ndarray):  # Voir la ligne d'au dessus
            if block[3] != 0:  # Ce n'est pas de l'air
                loaded_renderables_dict[chunk_x, chunk_y] = np.resize(loaded_renderables_dict[chunk_x, chunk_y], (len(
                    loaded_renderables_dict[chunk_x, chunk_y])+1, 4))  # On doit resize l'array pour ajouter un élément
                # On ajoute le bloc
                loaded_renderables_dict[chunk_x, chunk_y][-1] = np.array(block)
                # le wchunk est maintenant changé
                changed_chunks.add((chunk_x, chunk_y))


def change_in_chunks(chunk_x, chunk_y, bloc_pos, bloc_value=0):
    """
    Fonction appellée quand il y a un changement physique dans une chunk (cassage/plaçage)
    Elle va modifier la chunk stockée dans le data_manager
    À appeler avant l'appel de fast_renderables
    :param chunk_x: coordonnée x de la chunk
    :param chunk_y: coordonnée y de la chunk
    :param bloc_pos: position du bloc relative à sa chunk
    :param bloc_value: type de bloc (uniquement lors de plaçage, default=0=air)
    """
    global loaded_chunks_dict, loaded_renderables_dict, changed_chunks
    chunk_fetch = get_chunk((chunk_x, chunk_y))  # On récupère la chunk
    if isinstance(chunk_fetch, np.ndarray):
        # On met à jour des variables
        loaded_chunks_dict[chunk_x, chunk_y][bloc_pos] = bloc_value
        # On stocke le fait que la chunk soit mise à jour
        changed_chunks.add((chunk_x, chunk_y))


def save_chunk(chunk):
    """
    Sauvegarde la chunk en dur en remplaçant celle déjà existante par le array localement stocké.
    Ceci est fait afin de sauvegarder tout changement tel un cassage ou un plaçage de bloc
    :param chunk: le tuple (chunk_x, chunk_y)
    """
    chunk_fetch = get_chunk(chunk)  # On récupère la chunk
    if isinstance(chunk_fetch, np.ndarray):  # La chunk est bonne
        np.save(settings.CHUNKS_FORMAT %
                chunk, chunk_fetch)  # On sauvegarde la chunk
        changed_chunks.remove(chunk)  # Tout est bon
    renderable_fetch = get_renderables(chunk)  # On récupère les renderables
    if isinstance(renderable_fetch, np.ndarray):  # Les renderables sont bons
        np.save(settings.RENDERABLES_FORMAT % chunk, renderable_fetch)
