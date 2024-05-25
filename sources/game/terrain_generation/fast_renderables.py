import numpy as np
import game.terrain_generation.settings as settings
import math
import game.data_manager_world as data_manager

power_of_two = int(math.log2(settings.CHUNK_SIZE))


def cassage(coords, chunk_coords):
    """Determine les changes dans les renderables qu'impactent ce cassage de bloc"""
    changes = set(add_renderables(*coords, *chunk_coords))  # evite les duplicats
    return changes


def add_renderables(x, y, z, chunk_x, chunk_y):
    """Determine les nouveaux renderables après une suppression de bloc en x, y, z"""
    changes = []
    # Supprime des renderables le bloc cassé
    changes = update_renderable_bloc((0, 0), (x, y, z), chunk_x, chunk_y, changes, delete=True)

    # Verfie les blocs au dessus et en dessous sur l'axe Z
    changes = update_renderable_bloc((0, 0), (x, y, z+1), chunk_x, chunk_y, changes)
    changes = update_renderable_bloc((0, 0), (x, y, z-1), chunk_x, chunk_y, changes)

    # RQ: Tous les appelations "dessus dessous haut bas" sont les appellations pour l'axe Y, en 2D
    if x == 0:
        # Si on est tout à gauche de la chunk
        # Update le bloc le plus à droite de la chunk adjacente à gauche (donc à gauche du bloc cassé)
        changes = update_renderable_bloc((-1, 0), (settings.CHUNK_SIZE-1, y, z), chunk_x, chunk_y, changes)
        # Update le bloc à droite du bloc cassé
        changes = update_renderable_bloc((0, 0), (x + 1, y, z), chunk_x, chunk_y, changes)
    elif x == settings.CHUNK_SIZE - 1:
        # Si on est tout à droite de la chunk
        # Update le bloc le plus à gauche de la chunk adjacente à droite (donc à droite du bloc cassé)
        changes = update_renderable_bloc((+1, 0), (0, y, z), chunk_x, chunk_y, changes)
        # Update le bloc à gauche du bloc cassé
        changes = update_renderable_bloc((0, 0), (x - 1, y, z), chunk_x, chunk_y, changes)
    else:
        # Update le bloc à droite du bloc cassé
        changes = update_renderable_bloc((0, 0), (x + 1, y, z), chunk_x, chunk_y, changes)
        # Update le bloc à gauche du bloc cassé
        changes = update_renderable_bloc((0, 0), (x - 1, y, z), chunk_x, chunk_y, changes)

    if y == 0:
        # Si on est tout en haut de la chunk
        # Update le bloc le plus en bas de la chunk adjacente en haut (donc au dessus du bloc cassé)
        changes = update_renderable_bloc((0, -1), (x, settings.CHUNK_SIZE-1, z), chunk_x, chunk_y, changes)
        # Update le bloc au dessous du bloc cassé
        changes = update_renderable_bloc((0, 0), (x, y + 1, z), chunk_x, chunk_y, changes)
    elif y == settings.CHUNK_SIZE - 1:
        # Si on est tout en bas de la chunk
        # Update le bloc le plus en haut de la chunk adjacente en bas (donc au dessous du bloc cassé)
        changes = update_renderable_bloc((0, +1), (x, 0, z), chunk_x, chunk_y, changes)
        # Update le bloc au dessus du bloc cassé
        changes = update_renderable_bloc((0, 0), (x, y - 1, z), chunk_x, chunk_y, changes)
    else:
        # Update le bloc au dessus du bloc cassé
        changes = update_renderable_bloc((0, 0), (x, y + 1, z), chunk_x, chunk_y, changes)
        # Update le bloc au dessous du bloc cassé
        changes = update_renderable_bloc((0, 0), (x, y - 1, z), chunk_x, chunk_y, changes)

    return changes


def update_renderable_bloc(shift, position, chunk_x, chunk_y, changes, delete=False):
    """Ajoute (ou supprime si delete est True) le bloc aux renderables s'il ne l'est pas déjà"""
    renderables = data_manager.get_renderables((chunk_x + shift[0], chunk_y + shift[1]))
    if not isinstance(renderables, np.ndarray):
        # Si les blocs renderables ne sont pas encore generés
        return changes

    init_renderables = renderables.copy()

    # Obtiens les blocs de la chunk correspondante
    chunk = data_manager.get_chunk((chunk_x + shift[0], chunk_y + shift[1]))
    x, y, z = position

    # nouveau bloc à être ajouté
    new_bloc = chunk[x & 15, y & 15, z]  # &15 = %16

    # check si il y a déjà un bloc renderable à ces coordonnées dans la liste
    indexes = np.argwhere(np.all(renderables[:, :3] == (x, y, z), axis=1))

    if len(indexes) == 0:
        # Si il n'y en a pas déjà
        if not delete:
            if new_bloc != 0:
                # Ajoute le bloc à la fin des renderables
                renderables = np.resize(renderables, (renderables.shape[0]+1, renderables.shape[1]))
                renderables[renderables.shape[0]-1] = [x, y, z, new_bloc]

    else:
        # Supprime les renderables déjà existants à ces coordonnées
        for i in indexes:
            renderables[i] = [x, y, z, 0]
        if not delete:
            if new_bloc != 0:
                # Ajoute le bloc à la fin des renderables
                renderables = np.resize(renderables, (renderables.shape[0]+1, renderables.shape[1]))
                renderables[renderables.shape[0]-1] = [x, y, z, new_bloc]

    # "if not np.all(renderables == init_renderables)" ne marche pas avec les versions récentes de numpy
    # on verifie donc avec une comparaison de sets
    set_a = set(map(tuple, renderables))
    set_b = set(map(tuple, init_renderables))
    if set_a != set_b:

        # Si il y a eu un changement dans les renderables
        data_manager.change_in_renderables(chunk_x + shift[0], chunk_y + shift[1], renderables)
        changes.append(handle_new_renderable(not delete, chunk_x + shift[0], chunk_y + shift[1], position, new_bloc))

    return changes


def handle_new_renderable(is_added, chunk_x, chunk_y, bloc_pos, bloc_value=0):
    """Fonction appelée pour savoir quoi faire avec un nouveau bloc renderable,
    et le format de ce qui sera ajouté à changes"""
    if not is_added:
        bloc_value = 0
    return (chunk_x, chunk_y), bloc_pos, bloc_value  # ajouté à changes


def convert_to_chunk(x, y):
    """Convertis des coordonnées relatives en coordonnées normalisées"""
    return x >> power_of_two, y >> power_of_two  # bitwise right shift, équivalent de x // 16
