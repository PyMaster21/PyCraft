"""
EDITO :
"renderables" est un mot que nous avons "inventé" qui vient de l'anglais 'render',
et qui signifie "les blocs pouvant être affichés à l'écran".
En effet, par souci d'optimisation, nous n' allons pas envoyer TOUS les blocs du jeu à être affichés, ce serait inutile,
puisque on ne va par exemple dans tous les cas ne jamais voir un bloc en profondeur.
Les renderables sont donc tous les blocs qui sont adjacent à un bloc d'air (c'est un peu plus compliqué pour l'eau),
et qui seront potentiellement vus par le joueur.
"""


import os

import game.terrain_generation.settings as settings
import numpy as np


def load_border_chunks(top_left):
    """Load les chunks qui sont en adjacents à la chunk principale pour pouvoir bien génerer les renderables"""
    border_chunks_coords = {}

    # Definis les chunks à check
    to_check = (("left", (-1, 0)),
                ("right", (1, 0)),
                ("top", (0, -1)),
                ("bottom", (0, 1)))

    is_missing = False
    for pos, (bx1, by1) in to_check:

        temp_coords = (top_left[0] + settings.CHUNK_SIZE * bx1, top_left[1] + settings.CHUNK_SIZE * by1)
        
        norm = settings.coords_to_normalized(*temp_coords)
        if os.path.exists(f"{settings.CHUNKS_FORMAT % (*norm,)}"):
            # load le chunk adjacents
            border_chunks_coords[pos] = np.load(
                f"{settings.CHUNKS_FORMAT % (*norm,)}")
        else:
            # Si un chunk adjacent n'existe pas, il est impossible de génerer les renderables
            is_missing = True
            break

    if is_missing:
        return False
    return border_chunks_coords


def load_in_extended_chunk(extended_chunk, border_chunks_coords):
    """Load les bordures des chunks adjacents dans un grand array principal étendu"""

    # Extrait les bonnes bordures des chunks adjacents
    left_boundary = border_chunks_coords["left"][-1, :, :]
    right_boundary = border_chunks_coords["right"][0, :, :]
    top_boundary = border_chunks_coords["top"][:, -1, :]
    bottom_boundary = border_chunks_coords["bottom"][:, 0, :]

    # Ajoute les bordures au chunk principal
    extended_chunk[0, 1:-1, 1:-1] = left_boundary
    extended_chunk[-1, 1:-1, 1:-1] = right_boundary
    extended_chunk[1:-1, 0, 1:-1] = top_boundary
    extended_chunk[1:-1, -1, 1:-1] = bottom_boundary

    # Ajoute un layer de pierre (au dessus et en dessous) temporairement,
    # pour bien génerer les renderables aux extremités z du monde
    extended_chunk[:, :, 0] = 17
    extended_chunk[:, :, -1] = 17

    return extended_chunk


def find_renderables(chunk_array):
    """Algorithme principal d'obtention des renderables dans un array étendu"""

    # Crées des masques, c'est à dire un array où les cellules qui satisfont la condition ont un 1, les autres 0.
    non_zero_mask = chunk_array != 0
    is_water_mask = chunk_array == 5
    is_not_water_mask = chunk_array != 5

    adjacent_product = chunk_array[:-2, 1:-1, 1:-1] * chunk_array[1:-1, :-2, 1:-1] * chunk_array[1:-1, 1:-1, :-2] * \
        chunk_array[2:, 1:-1, 1:-1] * chunk_array[1:-1, 2:, 1:-1] * chunk_array[1:-1, 1:-1, 2:]

    # pour les blocs non-eau, si le modulo 5 est 0, soit :
    # - la multiplication des blocs est égale à 0, il y a un bloc d'air, le bloc est donc renderable
    # - la multiplication est un muliple de 5, ce qui veut dire qu'il y a un bloc d'eau à côté, le bloc doit donc
    # être renderable car les blocs d'eau ont un filtre bleu transparents
    land_mask = (adjacent_product % 5 == 0) & non_zero_mask[1:-1, 1:-1, 1:-1] & is_not_water_mask[1:-1, 1:-1, 1:-1]

    # pour les blocs d'eau, si la multiplication est différente à 5^6 = 15625, cela veut dire que le bloc d'eau
    # n'est pas entouré QUE d'eau, il va donc être renderable pour faire le filtre bleu transparent
    water_mask = (adjacent_product != 15625) & non_zero_mask[1:-1, 1:-1, 1:-1] & is_water_mask[1:-1, 1:-1, 1:-1]

    # Combine les deux masques
    rd = land_mask | water_mask

    # Obtient les indexes des renderables
    renderable_coords = np.argwhere(rd)

    # Obtient les valeurs des renderables, en prenant seulement la chunk au centre,
    # et en supprimant les bordures précedemment ajoutées
    renderable_values = chunk_array[1:-1, 1:-1, 1:-1][rd]
    renderable_coords_and_values = list(zip(*renderable_coords.T, renderable_values))
    return renderable_coords_and_values


def save(renderables, coords, path):
    """Sauvegarde les renderables pour 1 chunk"""
    norm = settings.coords_to_normalized(*coords)
    np.save(f"{path % (*norm,)}", renderables)
        
