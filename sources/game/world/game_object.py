"""
Ceci est le fichier qui contient la base pour tout objet dans la scène, le game_object
"""
import numpy as np
import math

# -------------------------------------------------------------------- #
#                           Basic Gameobjects


class GameObject:
    def __init__(self, position, direction=(0, 1, 0), following_position=None, tag=None):
        """
        Un objet du jeu
        :param position: la position de l'objet (x,y,z)
        :param direction: la direction dans laquelle l'objet regarde, un vecteur
        :param following_position: un objet que l'objet serait en train de suivre
        :param tag: le tag de l'objet, qui ne change absolument rien pour cette classe,
                    il peut cependant être utile pour avoir un identifiant lors de développement ultérieur
        """

        self.following_position = following_position
        self.tag = tag
        self.position = position
        self.direction = direction
        self._angles_updated = False
        self._updateAngles()

    # Quand on suit un objet, la position se comporte différemment
    @property
    def position(self):
        if self.following_position is not None:
            return self._position+self.following_position.position
        else:
            return self._position

    @position.setter
    def position(self, value):
        self._position = np.array(value, dtype=np.float32)

    # La direction est stockée à la fois comme vecteur et comme angles alpha beta (voir la doc),
    # il faut donc les mettre en relation
    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        self._direction = np.array(value, dtype=np.float32)
        self._angles_updated = False

    @property
    def angles(self):
        if not self._angles_updated:
            self._updateAngles()
        return self._angles

    def _updateAngles(self):
        """
        Met à jour les angles après un changement de direction
        """
        # La conversion direction-angle et inversément est décrite dans la doc
        direction = self.direction
        radius = math.sqrt(
            direction[0]*direction[0]+direction[1]*direction[1]+direction[2]*direction[2])  # x**2 est plus lent que x*x
        sin_beta = direction[2]/radius
        beta = math.asin(sin_beta)
        cos_beta = math.cos(beta)
        cos_alpha = direction[1]/(radius*cos_beta+0.00001)
        sin_alpha = -direction[0]/(radius*cos_beta+0.00001)
        alpha = math.acos(cos_alpha)  # The little + is to avoid /0
        self._angles = [alpha, beta, radius,
                        cos_alpha, sin_alpha, cos_beta, sin_beta]
        self._angles_updated = True

    def turn(self, alpha_turn, beta_turn=0):
        """
        Ajoute des valeurs aux angles de l'objet, effectivement le tournant, met aussi à jour la direction
        (voir la doc pour les calculs)
        :param alpha_turn: la quantité en radians par laquelle tourner l'angle alpha
        :param beta_turn: la quantité en radians par laquelle tourner l'angle beta
        """
        alpha = alpha_turn+self.angles[0]
        cos_alpha = math.cos(alpha)
        sin_alpha = math.sin(alpha)
        beta = beta_turn + self.angles[1]
        cos_beta = math.cos(beta)
        sin_beta = math.sin(beta)
        radius = self.angles[2]
        self._angles = [alpha, beta, radius,
                        cos_alpha, sin_alpha, cos_beta, sin_beta]
        self._direction = np.array([-radius * sin_alpha * cos_beta, radius * cos_alpha * cos_beta, radius * sin_beta],
                                   dtype=np.float32)
        self._angles_updated = True

    def move(self, movement, relative=True):
        """
        Bouge l'objet par le vecteur mouvement
        :param movement: le vecteur mouvement
        :param relative: si le mouvement est relatif à la direction, sachant que ça ne vaut pas pour l'axe z
        """
        if not relative:
            self.position += np.array(movement, dtype=np.float32)
        else:
            angles = self.angles
            
            self.position += np.array([self.angles[3]*movement[0] - self.angles[4]*movement[1],
                                       self.angles[3]*movement[1] + self.angles[4]*movement[0],
                                       movement[2]], dtype=np.float32)
