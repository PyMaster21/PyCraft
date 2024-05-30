from game.terrain_generation.perlin_noise import PerlinNoise
import game.terrain_generation.settings as settings


shift_table = [
    [[None],None],
    [[0], 0],
    [[-15, 15], 1],
    [[-20, 0, 20], 2],
    [[-20, -5, 10, 25], 3],
    [[-20, -8, 4, 16, 24], 4],
    [[-22, -12, -2, 8, 18, 28], 5],
    [[-24, -16, -8, 0, 8, 16, 24], 6],
    [[-24, -17, -10, -3, 4,11, 18, 25], 7]

]

class Cave:

    def __init__(self, top_left, bottom_right, seed):
        """Met les grottes du jeu"""
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.number_of_cursors_pairs = settings.NUMBER_OF_CURSOR_PAIRS
        self.cursors = []
        self.seeds = settings.setSeeds(seed, self.number_of_cursors_pairs * 2)

        self.generate_perlin_noises()

    def generate_perlin_noises(self):
        """Genere les perlin noises responsables de la hauteur des curseurs"""
        for i in range(self.number_of_cursors_pairs):
            pair = []
            for j in range(2):
                cursor = PerlinNoise(self.seeds[i*2+j], 120, 0, 0.6, [3, 5])
                cursor.extend(self.top_left, self.bottom_right)
                pair.append(cursor.get_pixels())
                #print(pair[-1])
            self.cursors.append(pair)


    def place(self, array):
        #print(self.cursors)
        #print("MIN : ", min(min(list(self.cursors[0][0].values())), min(list(self.cursors[0][1].values()))), 
        #    "MAX : ", max(max(list(self.cursors[0][0].values())), max(list(self.cursors[0][1].values()))))
        new_array = array.copy()
        for x in range(array.shape[0]):
            for y in range(array.shape[1]):
                for cursor_id, (cursorA, cursorB) in enumerate(self.cursors):

                    z_start = cursorA.get((x+self.top_left[0], y+self.top_left[1]))
                    z_end = cursorB.get((x+self.top_left[0], y+self.top_left[1]))
                    #print(self.convert(z_start), self.convert(z_end))
                    if z_start is not None and z_end is not None and z_start < z_end:
                        z1 = self.convert(z_start) + int((shift_table[self.number_of_cursors_pairs][0][cursor_id]) * 0.3)
                        z2 = self.convert(z_end) + int((shift_table[self.number_of_cursors_pairs][0][cursor_id])* 0.3)
                        z2 -= shift_table[self.number_of_cursors_pairs][1]
                        #   print(f"from {z1} to {z2}")
                        if z1 < 20 and z2 >= 20:
                            for z in range(z1, 20):
                                if self.is_authorized(array[x, y, z]):
                                    new_array[x, y, z] = 11

                        for z in range(max(z1, 20), z2+1):

                            if self.is_authorized(array[x, y, z]):
                                
                                new_array[x, y, z] = 0

        return new_array
    
    @staticmethod
    def is_authorized(block):
        if block in [1, 7, 8, -1, 17, 2, 3, 4, 6, 12, 13, 14, 14.1, 14.2, 16, 17, 21]:
            return True
        return False

    @staticmethod
    def convert(value):
        return int((value + 0.5) * settings.WATER_LEVEL * 1.5) - 10