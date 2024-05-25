"""
Ceci est le fichier qui contient les classes joueur et caméra, utilisées dans le world_manager
Elles sont basées sur la classe GameObject définie dans objects
"""
import game.settings as settings
from game.world.game_object import GameObject
import game.data_manager_world as data_manager
import game.preferences as preferences

import numpy as np
import math

# -------------------------------------------------------------------- #
#                               Classe du joueur


class Player(GameObject):
    def __init__(self, position, direction=[0, 1, 0], following_position=None, tag=None):
        """
        Le joueur
        :param position: un tuple de la position du joueur (x, y, z)
        :param direction: la direction in which the player is pointing, a vector (x, y, z)
        :param following_position: La position d'un objet que le joueur suit (optionnel),
                                   instance de ou de sous classe de objects.GameObject
        :param tag: le tag du joueur, simplement comme un identifiant, ne change rien de ce côté
        """
        super().__init__(position, direction, following_position, tag)
        # Initialisation des variables
        self.can_jump = True
        self.in_water = False
        self.speed_y = 0

    # On overwrite les propriétés de position pour incorporer le self.chunk, très utilisé dans le world_manager,
    # mais on n'en a pas trop besoin pour les autres objets, donc on ne l'implémente qu'ici
    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = np.array(value, dtype=np.float32)
        self.chunk = (self._position[0]//settings.CHUNK_SIZE,
                      self._position[1]//settings.CHUNK_SIZE)

    def simulatePhysics(self, term_velocity=-0.9, deltatime=0, gravity=True):
        """
        Simule la physique du joueur
        :param term_velocity: si la vélocité terminale est incorporée dans le jeu, laissez à False pour aucune,
                              à vos risques et périls
        :param deltatime: le temps élapsé depuis le dernier frame
        :param gravity: si la physique doit être simulée mais sans gravité (utilisé pour voler)
        """
        self.in_water = False  # Ceci sera changé si il s'avère que oui
        self.can_jump = False  # de même ici

        # On arrondit la position du joueur
        object_x = int(self.position[0]//1)
        object_y = int(self.position[1]//1)
        object_z = int(self.position[2]//1)

        # Mise en place de la gravité
        if gravity:
            # le z en dessous duquel la gravité est normale
            lower_threshold = settings.GRAVITY_THRESHOLD[0]
            # Le z au dessus duquel la gravité est 0 ou positive
            upper_threshold = settings.GRAVITY_THRESHOLD[1]
            # La gravité est normale en dessous du lower_threshold
            if not preferences.DYNAMIC_GRAVITY or object_z <= lower_threshold:
                self.speed_y -= settings.GRAVITY * deltatime  # gravité
            else:
                gravity = (upper_threshold - object_z + lower_threshold) / \
                    (upper_threshold-lower_threshold) * \
                    settings.GRAVITY  # gravité dynamique
                self.speed_y -= gravity * deltatime  # ajout de la gravité
            # Mise en place de vélocité terminale
            if term_velocity:
                if self.speed_y < term_velocity:
                    self.speed_y = term_velocity
            # On a un facteur de 1/30 pour avoir des constantes plus cohérentes
            change_by = self.speed_y * deltatime * 1/30
            if change_by < -0.9:
                self.position[2] -= 0.9  # On cap le mouvement
            else:
                self.position[2] += change_by

        if self.position[2] < 0:  # On ne va pas non plus tomber dans l'abysse du monde
            self.speed_y = 0
            self.position[2] = 0
        elif self.position[2] > 1000 and preferences.DYNAMIC_GRAVITY:  # Ni dans l'éternel abîme qu'est le ciel
            self.speed_y = 0
            self.position[2] = 1000

        # toutes les positions des blocs avec lesquels une collision peut avoir lieu
        ground = [[object_x-i, object_y-j, object_z-2]
                  for i in range(-1, 2) for j in range(-1, 2)]  # Les blocs du sol
        ceiling = [[object_x-i, object_y-j, object_z+k]
                   for i in range(-1, 2) for j in range(-1, 2) for k in [1]]  # Les blocs au dessus du joueur

        side_left = ((object_x-1, object_y, object_z),
                     (object_x-1, object_y, object_z-1))  # Les blocs à gauche du joueur
        side_right = ((object_x+1, object_y, object_z),  # Les blocs à droite du joueur
                      (object_x+1, object_y, object_z-1))
        side_up = ((object_x, object_y+1, object_z),  # Les blocs devant le joueur
                   (object_x, object_y+1, object_z-1))
        side_down = ((object_x, object_y-1, object_z),  # Les blocs derrière le joueur
                     (object_x, object_y-1, object_z-1))

        diag_left_front = ((object_x-1, object_y+1, object_z),  # La diagonale à gauche et devant le joueur
                           (object_x-1, object_y+1, object_z-1))
        diag_front_right = ((object_x+1, object_y+1, object_z),  # La diagonale devant et à droite le joueur
                            (object_x+1, object_y+1, object_z-1))
        diag_right_back = ((object_x+1, object_y-1, object_z),  # La diagonale à droite et derrière le joueur
                           (object_x+1, object_y-1, object_z-1))
        diag_back_left = ((object_x-1, object_y-1, object_z),  # La diagonale derrière et à gauche le joueur
                          (object_x-1, object_y-1, object_z-1))

        in_player = ((object_x, object_y, object_z-1),  # Les blocs dans le joueur
                     (object_x, object_y, object_z))
        collision_checks = (side_left, side_up, side_right,
                            side_down, ground, ceiling, 
                            diag_left_front, diag_front_right, 
                            diag_right_back, diag_back_left,
                            in_player)

        # On énumère pour savoir quel type de collision arrive
        for collision_type, collision in enumerate(collision_checks):
            for block in collision:
                # On est en dehors du monde matériel
                # et nous ne pouvons donc pas avoir de collision avec un bloc non existant
                if block[2] >= settings.WORLD_HEIGHT or block[2] < 0:
                    continue
                # La chunk du bloc ainsi que la position de ce dernier dans cette première
                block_chunk = (
                    int(block[0]//settings.CHUNK_SIZE), int(block[1]//settings.CHUNK_SIZE))
                block_pos_relative = [int(block[0] % settings.CHUNK_SIZE), int(
                    block[1] % settings.CHUNK_SIZE), block[2]]

                # On cherche la chunk chez le data manager
                chunk_fetch = data_manager.get_chunk(block_chunk,)
                # On regarde si la chunk a bien pu être cherchée
                if isinstance(chunk_fetch, np.ndarray):
                    # Le type du bloc
                    block_type = chunk_fetch[block_pos_relative[0],
                                             block_pos_relative[1], block_pos_relative[2]]
                    match block_type:  # Différentes méchaniques pour différents types de blocs
                        case 0:  # On a de l'air
                            pass
                        case 5:  # de l'eau
                            if collision_type == 10:  # Le joueur est bien *dans* de l'eau
                                self.speed_y *= 0.5  # L'eau réduit toute vitesse progressivement
                                self.in_water = True
                        case other:  # Autre bloc
                            # On prépare la hitbox du cube
                            cube_hitbox = [[block[0],
                                            block[1],
                                            block[2]],
                                           [block[0]+settings.CUBE_SIDELENGTH,
                                            block[1]+settings.CUBE_SIDELENGTH,
                                            block[2]+settings.CUBE_SIDELENGTH]]

                            match collision_type:
                                case 4:  # Si on touche le sol, il faut monter
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 0):
                                        self.can_jump = True
                                        # Afin de ne pas coller à la surface
                                        # et de donc pouvoir placer des blocs en dessous de nous on fait + 0.001
                                        if block_type == 11:
                                            self.speed_y = 0.8
                                        else:
                                            self.speed_y = 0
                                        self.position[2] = cube_hitbox[1][2] - \
                                            settings.PLAYER_HITBOX_OFFSETS[2][0] + 0.001
                                case 5:  # Si on collisionne avec le plafond il faut descendre
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 1):
                                        # On vérifie que nous soyons bien en train de toucher le plafond,
                                        # puisque nous montons
                                        if self.speed_y > 0:
                                            # On se décale
                                            self.position[2] = cube_hitbox[0][2] - \
                                                settings.PLAYER_HITBOX_OFFSETS[2][1]
                                            self.speed_y = -0.1  # Maintenant il faut redescendre
                                # Le bloc que nous toucherions est à notre gauche (-x)
                                case 0:
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 2):
                                        # On se décale
                                        self.position[0] = cube_hitbox[1][0] + \
                                            settings.PLAYER_HITBOX_OFFSETS[0] + \
                                            0.001  # le + 0.001 est pour éviter de coller au mur
                                # Le bloc que nous toucherions est devant nous (+y)
                                case 1:
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 3):
                                        # On se décale
                                        self.position[1] = cube_hitbox[0][1] - \
                                            settings.PLAYER_HITBOX_OFFSETS[1] - \
                                            0.001  # le + 0.001 est pour éviter de coller au mur
                                # Le bloc que nous toucherions est à notre droite (+x)
                                case 2:
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 4):
                                        # On se décale
                                        self.position[0] = cube_hitbox[0][0] - \
                                            settings.PLAYER_HITBOX_OFFSETS[0] - \
                                            0.001  # le + 0.001 est pour éviter de coller au mur
                                # Le bloc que nous toucherions est derrière nous (-y)
                                case 3:
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 5):
                                        # On se décale
                                        self.position[1] = cube_hitbox[1][1] + \
                                            settings.PLAYER_HITBOX_OFFSETS[1] + \
                                            0.001  # le + 0.001 est pour éviter de coller au mur
                                case 6:  # Le bloc est devant et à notre gauche
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 6):
                                        # Pour savoir de quel côté on se décale on regarde quelle dimension 
                                        # est la plus proche d'une bordure de chunk
                                        border_x = self.position[0] % 1  # La distance à une bordure dans les x
                                        if max(border_x, 1-self.position[1] % 1) == border_x:
                                            self.position[0] = cube_hitbox[1][0] + \
                                                settings.PLAYER_HITBOX_OFFSETS[0] + \
                                                0.001  # le + 0.001 est pour éviter de coller au mur
                                        else:
                                            self.position[1] = cube_hitbox[0][1] - \
                                                settings.PLAYER_HITBOX_OFFSETS[1] - \
                                                0.001
                                case 7:  # Le bloc est devant et à notre droite
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 7):
                                        # Pour savoir de quel côté on se décale on regarde quelle dimension 
                                        # est la plus proche d'une bordure de chunk
                                        border_x = 1-self.position[0] % 1  # La distance à une bordure dans les x
                                        if max(border_x, 1-self.position[1] % 1) == border_x:
                                            self.position[0] = cube_hitbox[0][0] - \
                                                settings.PLAYER_HITBOX_OFFSETS[0] - \
                                                0.001  # le + 0.001 est pour éviter de coller au mur
                                        else:
                                            self.position[1] = cube_hitbox[0][1] - \
                                                settings.PLAYER_HITBOX_OFFSETS[1] - \
                                                0.001
                                case 8:  # Le bloc est derrière et à notre droite
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 8):
                                        # Pour savoir de quel côté on se décale on regarde quelle dimension 
                                        # est la plus proche d'une bordure de chunk
                                        border_x = 1-self.position[0] % 1  # La distance à une bordure dans les x
                                        if max(border_x, self.position[1] % 1) == border_x:
                                            self.position[0] = cube_hitbox[0][0] - \
                                                settings.PLAYER_HITBOX_OFFSETS[0] - \
                                                0.001  # le + 0.001 est pour éviter de coller au mur
                                        else:
                                            self.position[1] = cube_hitbox[1][1] + \
                                                settings.PLAYER_HITBOX_OFFSETS[1] + \
                                                0.001
                                case 9:  # Le bloc est derrière et à notre gauche
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 9):
                                        # Pour savoir de quel côté on se décale on regarde quelle dimension 
                                        # est la plus proche d'une bordure de chunk
                                        border_x = self.position[0] % 1  # La distance à une bordure dans les x
                                        if max(border_x, self.position[1] % 1) == border_x:
                                            self.position[0] = cube_hitbox[1][0] + \
                                                settings.PLAYER_HITBOX_OFFSETS[0] + \
                                                0.001  # le + 0.001 est pour éviter de coller au mur
                                        else:
                                            self.position[1] = cube_hitbox[1][1] + \
                                                settings.PLAYER_HITBOX_OFFSETS[1] + \
                                                0.001
                                           
                                case 10:  # Nous serions *dans* le sol
                                    if self.colliding(cube_hitbox[0], cube_hitbox[1], 6):
                                        self.can_jump = True  # Nous pouvons maintenant sauter
                                        # On se décale
                                        self.position[2] = cube_hitbox[1][2] - \
                                            settings.PLAYER_HITBOX_OFFSETS[2][0]
                                        self.speed_y = 0  # On reset la vitesse

    def colliding(self, coordinates_1, coordinates_2, check_type=10):
        """
        Vérifie si self collisionne avec le cube de sommets définis
        :param coordinates_1: un des coins diagonalement opposés formant la hitbox du cube
        :param coordinates_2: l'autre coin diagonalement opposés formant la hitbox du cube
        :param check_type: Le type de check de collision à faire 
                           (il y en a beaucoup donc allez voir la doc)
        :return bool: True si le joueur est en collision, False sinon
        """

        x, y, z = self.position

        # On crée la hitbox du joueur
        x_off, y_off, z_off = settings.PLAYER_HITBOX_OFFSETS
        # On regarde quel type de check de collision nous allons effectuer (voir la doc)
        match check_type:
            case 0:  # Check de sol
                hitbox = ((x-x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y+y_off, z+z_off[0]+0.9),
                          (x-x_off, y+y_off, z+z_off[0]+0.9))
            case 1:  # Check de "plafond"
                hitbox = ((x-x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y+y_off, z+z_off[0]+0.9),
                          (x-x_off, y+y_off, z+z_off[0]+0.9))
            case 2:  # Check de côté gauche
                hitbox = ((x-x_off, y-y_off, z+z_off[0]),
                          (x-x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y-y_off, z+z_off[1]),
                          (x-x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y-y_off, z+z_off[0]+0.9),
                          (x-x_off, y+y_off, z+z_off[0]+0.9))
            case 3:  # Check de côté devant
                hitbox = ((x+x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y+y_off, z+z_off[0]),
                          (x+x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y+y_off, z+z_off[1]),
                          (x+x_off, y+y_off, z+z_off[0]+0.9),
                          (x-x_off, y+y_off, z+z_off[0]+0.9))
            case 4:  # Check de côté droit
                hitbox = ((x+x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y+y_off, z+z_off[0]),
                          (x+x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y+y_off, z+z_off[1]),
                          (x+x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y+y_off, z+z_off[0]+0.9))
            
            case 5:  # Check de côté derrière
                hitbox = ((x-x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y-y_off, z+z_off[0]),
                          (x-x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y-y_off, z+z_off[1]),
                          (x-x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y-y_off, z+z_off[0]+0.9))
            case 6:  # Check de diagonale gauche-devant
                hitbox = ((x-x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y+y_off, z+z_off[0]+0.9))
            case 7:  # Check de diagonale devant-droite
                hitbox = ((x+x_off, y+y_off, z+z_off[0]),
                          (x+x_off, y+y_off, z+z_off[1]),
                          (x+x_off, y+y_off, z+z_off[0]+0.9))
            case 8:  # Check de diagonale droite-derrière
                hitbox = ((x+x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y-y_off, z+z_off[0]+0.9))
            case 9:  # Check de diagonale derrière-gauche
                hitbox = ((x-x_off, y-y_off, z+z_off[0]),
                          (x-x_off, y-y_off, z+z_off[1]),
                          (x-x_off, y-y_off, z+z_off[0]+0.9))
            case 10:  # Toute la hitbox
                hitbox = ((x-x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y-y_off, z+z_off[0]),
                          (x+x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y+y_off, z+z_off[0]),
                          (x-x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y-y_off, z+z_off[1]),
                          (x+x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y+y_off, z+z_off[1]),
                          (x-x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y-y_off, z+z_off[0]+0.9),
                          (x+x_off, y+y_off, z+z_off[0]+0.9),
                          (x-x_off, y+y_off, z+z_off[0]+0.9))
        # On itère sur tous les points de la hitbox
        for point in hitbox:
            # si le point est dans le parrallélépipède de la hitbox du cube dans les x, y et z
            colliding = [coordinates_1[i] < point[i] < coordinates_2[i] for i in range(3)]

            if False not in colliding:
                # Si il n'y a pas au moins une dimension dans laquelle le point ne fait pas de collision
                return True  # collision
        return False

    def look_at_block(self, max_reach=5):
        """
        Fonction utilisée pour regarder des blocs. 
        On va essentiellement projeter une ligne depuis la tête du joueur
        dans la direction dans laquelle celui-ci regarde
        et voir si et quand cette ligne traverse un bloc. Voir l'algorithme dans la doc
        :param max_reach: la distance maximum à laquelle le joueur va regarder
        """

        t = 0  # la distance déjà parcourue le long de la ligne de vue
        # La distance à parcourir le long de la ligne pour avoir traversé un mètre dans un des axes
        # On évite /0, cette addition évite du branching additionnel, et est négligeable pour le résultat
        delta_x = abs(1/(self.direction[0]+0.00001))
        delta_y = abs(1/(self.direction[1]+0.00001))
        delta_z = abs(1/(self.direction[2]+0.00001))
        # On récupère la distance requise pour traverser une bordure dans tous les axes
        if self.direction[0] > 0:
            cross_x = delta_x*(1-self.position[0] % 1)
            sign_x = 1
        else:
            cross_x = delta_x*(self.position[0] % 1)
            sign_x = -1

        if self.direction[1] > 0:
            cross_y = delta_y*(1-self.position[1] % 1)
            sign_y = 1
        else:
            cross_y = delta_y*(self.position[1] % 1)
            sign_y = -1

        if self.direction[2] > 0:
            cross_z = delta_z*(1-self.position[2] % 1)
            sign_z = 1
        else:
            cross_z = delta_z*(self.position[2] % 1)
            sign_z = -1

        # l'algorithme, VOIR LA DOC
        current_block = [int(self.position[0]//1),
                         int(self.position[1]//1), int(self.position[2]//1)]
        last_crossed = 0  # 0 correrspond à rien, 1 ou -1 à + ou - x, et ainsi de suite pour y and z
        while t <= max_reach:
            minimum = min((cross_x, cross_y, cross_z))
            if minimum == cross_x:
                t += cross_x
                cross_y -= cross_x
                cross_z -= cross_x
                cross_x = delta_x
                current_block[0] += sign_x
                last_crossed = 1*sign_x
            elif minimum == cross_y:
                t += cross_y
                cross_x -= cross_y
                cross_z -= cross_y
                cross_y = delta_y
                current_block[1] += sign_y
                last_crossed = 2*sign_y
            else:
                t += cross_z
                cross_x -= cross_z
                cross_y -= cross_z
                cross_z = delta_z
                current_block[2] += sign_z
                last_crossed = 3*sign_z
            # On récupère le bloc
            if 0 < current_block[2] < settings.WORLD_HEIGHT:  # Le bloc peut exister
                block_chunk = (current_block[0]//16, current_block[1]//16)
                block_chunk_fetch = data_manager.get_chunk(block_chunk)
                if isinstance(block_chunk_fetch, np.ndarray):  # Le chunk a pu être cherché
                    block_relative = (
                        current_block[0] % 16, current_block[1] % 16, current_block[2])
                    block_type = block_chunk_fetch[block_relative]
                    if block_type != 0:
                        return block_chunk, block_relative, block_type, last_crossed


class Camera(GameObject):
    def __init__(self, position, direction=[0, 1, 0], fov=70, aspect_ratio=1.2,
                 clip=(0.1, 100), following_position=None, tag=None):
        """
        Une caméra, à être utilisée avec un joueur
        :param position: position de la caméra (x,y,z)
        :param direction: la direction de la caméra vecteur
        :param fov: le fov en largeur (en degrees)
        :param aspect_ratio: the width/height screen ratio
        :param clip: tuple avec les distances clip near et far (near,far)
        :param following_position: un objet duquel la position sera suivie par la caméra (généralement un joueur)
                                   attention, la position sera alors relative
        :param tag: Le tag de la caméra, ne changera rien au jeu (pouvait être utile pour développement ultérieur)
        """
        super().__init__(position, direction, following_position, tag)
        self.computed_projection_matrix = False
        self._computed_alpha = False
        self._computed_beta = False
        # on prend son inverse parce que c'est ce que l'on utilise
        self.inverse_aspect_ratio = 1/aspect_ratio
        self.clip = clip
        # On veut des radians mais des degrés sont plus parlants
        self.fov = math.radians(fov)

    # Si le fov venait à être modifié, la matrice de projection ne serait plus d'actualité
    @property
    def fov(self):
        """
        La mesure de l'angle en radians mesurant le champ de vision dans la largeur (voir la doc) 
        """
        return self._fov

    @fov.setter
    def fov(self, value):
        self._fov = value
        self.computed_projection_matrix = False
    # Même chose qu'avec le fov

    @property
    def inverse_aspect_ratio(self):
        """
        On utilise plus le inverse aspect ratio que le aspect ratio
        """
        return self._inverse_aspect_ratio

    @inverse_aspect_ratio.setter
    def inverse_aspect_ratio(self, value):
        self._inverse_aspect_ratio = value
        self.computed_projection_matrix = False
    # La matrice de projection doit être mise à jour si elle ne l'est plus

    @property
    def projectionMatrix(self):
        """
        La matrice de projection utilisée dans les shaders
        """
        if self.computed_projection_matrix is False:
            self._computeProjMatrix()
        return self._projection_matrix

    def _computeProjMatrix(self):
        """
        Permet de calculer la matrice de projection, voir la doc
        """
        near = self.clip[0]
        far = self.clip[1]
        width = 2*math.tan(self.fov/2)*near
        height = self.inverse_aspect_ratio*width
        self._projection_matrix = np.array([
            [near/width, 0, 0, 0],
            [0, 0, (far+near)/(far-near), 1],
            [0, near/height, 0, 0],
            [0, 0, -2*far*near/(far-near), 0]], dtype=np.float32)
        self.computed_projection_matrix = True

    @property
    def alpha_matrix(self):
        """
        La matrice de rotation de l'angle alpha, utilisée dans les shaders 
        """
        self._computeAlphaMatrix()
        return self._alpha_matrix

    def _computeAlphaMatrix(self):
        """
        Calcule la matrice de rotation de l'angle alpha, voir la doc
        """
        cos_alpha = self.angles[3]
        # Because the rotation is to be done anticlockwise, not clockwise and sin(-x) = -sin(x)
        sin_alpha = -self.angles[4]
        self._alpha_matrix = np.array([[cos_alpha, sin_alpha, 0],
                                      [-sin_alpha, cos_alpha, 0],
                                      [0, 0, 1]], dtype=np.float32)

    @property
    def beta_matrix(self):
        """
        La matrice de rotation de l'angle alpha, utilisée dans les shaders 
        """
        self._computeBetaMatrix()
        return self._beta_matrix

    def _computeBetaMatrix(self):
        """
        Calcule la matrice de rotation de l'angle alpha, voir la doc
        """
        cos_beta = self.angles[5]
        sin_beta = self.angles[6]
        self._beta_matrix = np.array([[1, 0, 0],
                                      [0, cos_beta, -sin_beta],
                                      [0, sin_beta, cos_beta]], dtype=np.float32)
