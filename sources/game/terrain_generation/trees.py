import random
import game.terrain_generation.settings as settings
import numpy as np


def generate_tree(is_sand):
    """Load l'arbre, en fonction de si c'est sur du sable ou non"""
    if is_sand:
        # Palmier
        # Choisis la hauteur du palmier
        height = random.randint(1, 3)

        # Choisis l'orientation (pour l'instant inutile car les palmiers sont symetriques)
        orientation = random.randint(0, 3)
        path = settings.palmiers_path % (height, orientation)

        # Load le template
        tree = np.load(path)
        width, height = tree.shape[:2]
        size = max(width, height)
        center = (size/2).__floor__()

        # Convertis sur le bon format
        t2 = []
        for row in tree:
            for item in row:
                t2.append(item)

        return t2, center, size

    else:
        # Arbre normal
        return [[0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0],
                [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 4, 0], [0, 0, 0, 4, 4, 4, 4],
                [0, 0, 0, 4, 4, 4, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 4, 4],
                [3, 3, 3, 3, 3, 3, 4], [0, 0, 0, 4, 4, 4, 4], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0],
                [0, 0, 0, 4, 4, 4, 0], [0, 0, 0, 4, 4, 4, 4], [0, 0, 0, 4, 4, 4, 0], [0, 0, 0, 4, 4, 0, 0],
                [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0], [0, 0, 0, 4, 4, 0, 0],
                [0, 0, 0, 4, 4, 0, 0]], 2, 5
