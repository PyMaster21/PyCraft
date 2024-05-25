import random
import numpy as np

import game.terrain_generation.settings as settings
from game.terrain_generation.perlin_noise import PerlinNoise


class FloatingIsland:

    def __init__(self, seed, current_map, top_left, **perlin_noises):
        """Classe responsable des iles flottantes présentes dans les airs"""
        self.current_map = current_map
        self.top_left = top_left
        self.seeds = settings.setSeeds(seed, settings.FLOATING_ISLAND_LAYERS)

        # utilise des perlin noises déjà génerés pour le terrain pour gagner du temps
        self.perlin_noises = perlin_noises

        # Les îles flottantes sont génerées sur plusieurs couches afin d'avoir une diversité aussi en z
        heights = [random.randint(*settings.FLOATING_ISLAND_RANDOM_HEIGHTS)]
        for i in range(settings.FLOATING_ISLAND_LAYERS - 1):
            heights.append(heights[i] + random.randint(*settings.FLOATING_ISLAND_RANDOM_HEIGHTS))
        for i, height in enumerate(heights):
            # Genere la couche
            self.generate_layer(self.seeds[i], height)

    def get_map(self):
        return self.current_map

    def generate_layer(self, seed, height_shift):
        """Genère une couche d'ile flottante à une hauteur donnée"""

        # Calcule la hauteur totale de l'île
        absolute_height = settings.FLOATING_ISLAND_BASE_HEIGHT + height_shift

        x_range, y_range = self.current_map.shape[0:2]
        seeds = settings.setSeeds(seed, 10, 9)

        # Responsable de la dispersion et la disposition des iles flottante (en x,y)
        base_perlin = PerlinNoise(seeds[9], *settings.FLOATING_ISLAND_PERLIN_NOISE_INFO["main"])
        base_perlin.extend(self.top_left, (self.top_left[0]+x_range, self.top_left[1]+y_range))
        base = base_perlin.get_pixels()

        # Responsable des variations de base des îles flottantes (en x,y mais aussi en z)
        base_variation_perlin = PerlinNoise(seeds[8], *settings.FLOATING_ISLAND_PERLIN_NOISE_INFO["main_variation"])
        base_variation_perlin.extend(self.top_left, (self.top_left[0]+x_range, self.top_left[1]+y_range))
        base_variation = base_variation_perlin.get_pixels()
        # Responsable des petites variations dans ce qui est sous l'île flottante (en z)
        small_variation_perlin = PerlinNoise(seeds[9], *settings.FLOATING_ISLAND_PERLIN_NOISE_INFO["small_variation"])
        small_variation_perlin.extend(self.top_left, (self.top_left[0]+x_range, self.top_left[1]+y_range))
        small_variation = small_variation_perlin.get_pixels()

        # Responsable des toutes petites variations sous l'île flottante, de manière aléatoire
        blocs_variations = (np.random.randint(0, 100*10, size=(x_range, y_range))/10) ** 5 / 90**5

        for x in range(x_range):
            for y in range(y_range):
                sx = x + self.top_left[0]
                sy = y + self.top_left[1]

                # Determine à quel point il y a une îles flottante
                value = ((-(self.perlin_noises["terrain"][sx, sy]) + base[sx, sy]*3 + base_variation[sx, sy]*2)/6)**2
                if settings.FLOATING_ISLAND_THRESHOLD < value < 1:

                    # Il y a une île flottante à cette coordonée x,y
                    h = -(self.perlin_noises["flat"][sx, sy]) * \
                        self.perlin_noises["water"][sx, sy] * \
                        base[sx, sy] \
                        + base_variation[sx, sy]*3

                    # Determine la hauteur de l'île flottante
                    height = (h+1.5)*(settings.FLOATING_ISLAND_HEIGHT_GAP/2)*3
                    island_gen = (value-settings.FLOATING_ISLAND_THRESHOLD) * settings.FLOATING_ISLAND_HEIGHT_GAP
                    total_height = int((island_gen + height)/2)

                    # Calcule tout ce qui est sous l'île flottante
                    underisland = int(((((self.perlin_noises["terrain"][sx, sy]*0.5) + base[sx, sy]*2
                                         + base_variation[sx, sy]*5) + 1) *
                                       settings.FLOATING_ISLAND_ISLAND_STRETCH * island_gen)
                                      + int(small_variation[sx, sy] * 7000 * (island_gen+2)/3)
                                      + (int(blocs_variations[x, y])*3))

                    # met au maximum 3 blocs d'herbe
                    blocs = {"herbe": min(3, underisland), "pierre": 0}

                    blocs["pierre"] = underisland - blocs["herbe"]

                    z = 0
                    for i in range(blocs["herbe"]):
                        # place l'herbe
                        self.current_map[x, y, absolute_height + total_height - z - i] = settings.BLOC_VERS_ID["herbe"]

                    z += blocs["herbe"]

                    for i in range(blocs["pierre"]):
                        # place la pierre
                        self.current_map[x, y, absolute_height + total_height - z - i] = settings.BLOC_VERS_ID["pierre"]
