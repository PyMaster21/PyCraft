import math
import random
import time


COORD_SHIFT = 10000


class PerlinNoise:
    def __init__(self, SEED, noise_scale, octaves, noise_persistence, artifical_frequencies=None):
        self.st = time.time_ns()
        self.seed = SEED
        self.scale = noise_scale
        if isinstance(octaves, int):
            self.octaves_list = range(octaves)
        else:
            self.octaves_list = octaves
        self.persistence = noise_persistence
        self.artifical_frequencies = artifical_frequencies
        self.width = None
        self.height = None
        self.global_pixels = {}
        self.global_top_left = None
        self.global_bottom_right = None
        self.permutation = []

    def extend(self, top_left, bottom_right):
        """Appelle la generation de perlin noise du top_left jusqu'au bottom_right, ajoute la zone au
        perlin noise déjà géneré si un perlin noise a déjà été généré"""
        pixels = self.generate_noise(top_left, bottom_right)
        self.global_pixels.update(pixels)

    def get_pixels(self):
        """Renvoie tous les pixels (et leur valeur) générés avec extend()"""
        return self.global_pixels

    def generate_noise(self, top_left, bottom_right):
        """Genere le Perlin Noise entre le top_left et le bottom_right"""
        self.generate_permutation_grid()
        pixels = {}

        x_pixels, y_pixels = self.define_pixels_to_generate(top_left, bottom_right)
        for y_pixel in y_pixels:
            for x_pixel in x_pixels:
                value = 0
                if self.artifical_frequencies:
                    for i in self.artifical_frequencies:
                        value += self.pixelwise_generation(x_pixel, y_pixel, i, self.persistence ** i)

                for octave in self.octaves_list:
                    value += self.pixelwise_generation(x_pixel, y_pixel, 2 ** octave, self.persistence ** octave)

                pixels[(x_pixel - COORD_SHIFT, y_pixel - COORD_SHIFT)] = value

        return pixels

    def define_pixels_to_generate(self, top_left, bottom_right):
        """Definit les valeurs à génerer"""
        self.global_top_left = list(top_left)
        self.global_bottom_right = list(bottom_right)

        x_range = bottom_right[0] - top_left[0]
        y_range = bottom_right[1] - top_left[1]
        x_pixels = [top_left[0] + i + COORD_SHIFT for i in range(x_range)]
        y_pixels = [top_left[1] + i + COORD_SHIFT for i in range(y_range)]
        self.width = abs(bottom_right[0] - top_left[0])
        self.height = abs(bottom_right[1] - top_left[1])
        return x_pixels, y_pixels

    def pixelwise_generation(self, x_pixel, y_pixel, frequency, weight):
        """Retravaille les coordonnées données en fonction des paramètres du Perlin Noise"""
        x_coord = x_pixel / self.scale * frequency
        y_coord = y_pixel / self.scale * frequency

        return self.pixelwise_perlin(x_coord, y_coord) * weight

    def pixelwise_perlin(self, x, y):
        """Genere le perlin noise pour 1 pixel"""
        x_cell_position = math.floor(x) & 255
        y_cell_position = math.floor(y) & 255
        x_incell_position = x - math.floor(x)
        y_incell_position = y - math.floor(y)
        x_fading = self.fade(x_incell_position)
        y_fading = self.fade(y_incell_position)

        left_index = self.permutation[x_cell_position] + y_cell_position
        left_top_gradient_index = self.permutation[left_index]
        left_bottom_gradient_index = self.permutation[left_index + 1]

        right_index = self.permutation[x_cell_position + 1] + y_cell_position
        right_top_gradient_index = self.permutation[right_index]
        right_bottom_gradient_index = self.permutation[right_index + 1]

        horizontal_blends = [

            # Lerp des gradients du haut
            self.lerp(x_fading,
                      self.gradient(left_top_gradient_index, x_incell_position, y_incell_position),
                      self.gradient(right_top_gradient_index, x_incell_position - 1, y_incell_position)),

            # Lerp des gradients du bas
            self.lerp(x_fading,
                      self.gradient(left_bottom_gradient_index, x_incell_position, y_incell_position - 1),
                      self.gradient(right_bottom_gradient_index, x_incell_position - 1, y_incell_position - 1))

        ]

        vertical_blends = self.lerp(y_fading, *horizontal_blends)
        return vertical_blends

    @staticmethod
    def fade(t):
        """Optimisation de la fonction 6t^5-15t^4+10t^3, qui procède à un lissage de la valeur avec 0<=t<=1"""
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def lerp(t, a, b):
        """Interpolation linéaire entre deux valeurs, avec 0<=t<=1,
        pour t=0, la fonction retourne a, pour t=1, elle retourne b"""
        return a + t * (b - a)

    @staticmethod
    def gradient(angle_value_hash, x, y):
        """
        L'angle_value_hash est une valeur issue de self.permutations, comprise entre 0 et 255 inclus.
        Calcule le gradient pour un hash d'angle donné à un point donné
        """

        """match angle_value_hash & 15:
            case 0: return x + y
            case 1: return -x + y
            case 2: return x - y
            case 3: return -x -y
            case 4: return x
            case 5: return -x
            case 6: return x
            case 7: return -x
            case 8: return y
            case 9: return -y
            case 10: return y
            case 11: return -y
            case 12: return y + x
            case 13: return -y
            case 14: return y - x
            case 15: return -y
            case other: return 0"""
        h = angle_value_hash & 15  # equivalent de % 16
        if h < 8:  # 50% chances
            u = x
        else:  # 50% chances
            u = y

        if h < 4:  # 25% de chances
            v = y
        elif h == 9 or h == 10:  # 13% de chances
            v = x
        else:  # 62% de chances
            v = 0

        if (h % 2) == 0:  # 50% de chances
            temp = u + v
        else:  # 50% de chances
            temp = - (u + v)

        return temp

    def generate_permutation_grid(self):
        """Initie la grille de permutation, responsable de l'aléatoire dans le Perlin Noise,
        et controllé par une SEED spécifique"""
        if self.seed is not None:
            random.seed(self.seed)
        self.permutation = [151, 160, 137, 91, 90, 15, 131, 13, 201, 95, 96, 53, 194, 233, 7, 225,
                            140, 36, 103, 30, 69, 142, 8, 99, 37, 240, 21, 10, 23, 190, 6, 148,
                            247, 120, 234, 75, 0, 26, 197, 62, 94, 252, 219, 203, 117, 35, 11, 32,
                            57, 177, 33, 88, 237, 149, 56, 87, 174, 20, 125, 136, 171, 168, 68, 175,
                            74, 165, 71, 134, 139, 48, 27, 166, 77, 146, 158, 231, 83, 111, 229, 122,
                            60, 211, 133, 230, 220, 105, 92, 41, 55, 46, 245, 40, 244, 102, 143, 54,
                            65, 25, 63, 161, 1, 216, 80, 73, 209, 76, 132, 187, 208, 89, 18, 169,
                            200, 196, 135, 130, 116, 188, 159, 86, 164, 100, 109, 198, 173, 186, 3, 64,
                            52, 217, 226, 250, 124, 123, 5, 202, 38, 147, 118, 126, 255, 82, 85, 212,
                            207, 206, 59, 227, 47, 16, 58, 17, 182, 189, 28, 42, 223, 183, 170, 213,
                            119, 248, 152, 2, 44, 154, 163, 70, 221, 153, 101, 155, 167, 43, 172, 9,
                            129, 22, 39, 253, 19, 98, 108, 110, 79, 113, 224, 232, 178, 185, 112, 104,
                            218, 246, 97, 228, 251, 34, 242, 193, 238, 210, 144, 12, 191, 179, 162, 241,
                            81, 51, 145, 235, 249, 14, 239, 107, 49, 192, 214, 31, 181, 199, 106, 157,
                            184, 84, 204, 176, 115, 121, 50, 45, 127, 4, 150, 254, 138, 236, 205, 93,
                            222, 114, 67, 29, 24, 72, 243, 141, 128, 195, 78, 66, 215, 61, 156, 180]
        self.permutation += self.permutation
        random.shuffle(self.permutation)


def is_in_rectangle(x, y, top_left, bottom_right):
    """Check si un point est dans un rectangle formé par top_left bottom_right"""
    if top_left[0] <= x <= bottom_right[0]:
        if top_left[1] <= y <= bottom_right[1]:
            return True
    return False
