

class Scene:
    """Une classe qui contient l'ensemble des objets qui vont être dessinés"""
    def __init__(self):
        # Objets génériques sans fonctionnalité particulière.
        # La clef est un index (int) et la valeur est un objet affichable.
        self.generic_objects = {}

        # La clef est un index (int) et la valeur est un 'ChunkBatch'.
        self.chunk_batches = {}

        # prochain indice libre pour chaque catégorie d'objets
        self.next_obj_index = 0
        self.next_chunk_index = 0
        self.next_water_index = 0

        # La clef est un index (int) et la valeur est un 'WaterBatch'.
        self.water_batches = {}

        # Les 'WaterBatch' sont rangés par distance décroissante avec le joueur.
        # Les 'WaterBatch' doivent être dessinés du plus loin au plus proche pour que la transparence
        # fonctionne correctement
        self.sorted_water_batches = []

    def add_object(self, obj):
        """
        :param obj: Un objet générique à dessiner
        :return: l'index qui correspond à l'objet
        """
        index = self.next_obj_index
        self.generic_objects[index] = obj

        self.next_obj_index += 1
        return index

    def add_chunk_batch(self, chunk_batch):
        """
        :param chunk_batch: Un 'ChunkBatch' à dessiner
        :return: l'index qui correspond au 'ChunkBatch'
        """
        index = self.next_chunk_index
        self.chunk_batches[index] = chunk_batch

        self.next_chunk_index += 1
        return index

    def add_water_batch(self, water_batch):
        """
        :param water_batch: Un 'ChunkBatch' à dessiner
        :return: l'index qui correspond au 'WaterBatch'
        """
        index = self.next_water_index
        self.water_batches[index] = water_batch

        self.next_water_index += 1
        return index

    def delete_object(self, index):
        """
        :param index: l'index qui correspond à l'objet à supprimer
        """
        obj = self.generic_objects.pop(index)
        obj.release()

    def delete_chunk_batch(self, index: int):
        """
        :param index: l'index qui correspond au 'ChunkBatch' à supprimer
        """

        chunk_batch = self.chunk_batches.pop(index)
        chunk_batch.release()

    def delete_water_batch(self, index: int):
        """
        :param index: l'index qui correspond au 'WaterBatch' à supprimer
        """

        water_batch = self.water_batches.pop(index)
        self.sorted_water_batches.remove(water_batch)
        water_batch.release()

    def sort_waters(self, player_chunk):
        """Fonction pour ranger les 'WaterBatch' par distance décroissante avec le joueur"""

        def calculate_ditance_squared(water_batch):
            """Fonction qui calcule la distance au carré entre un 'WaterBatch' et le joueur"""
            dx = (water_batch.chunk_coordinates[0] - player_chunk[0])
            dy = (water_batch.chunk_coordinates[1] - player_chunk[1])
            return dx * dx + dy * dy

        self.sorted_water_batches = sorted(self.water_batches.values(), key=calculate_ditance_squared, reverse=True)

    def render(self):
        """Dessine tous les objets sur l'écran."""
        for obj in self.generic_objects.values():
            obj.render()

        for chunk_batch in self.chunk_batches.values():
            chunk_batch.render()

        for delete_water_batch in self.sorted_water_batches:
            delete_water_batch.render()

    def release(self):
        """
        Supprime tous les objets de la scène.
        Réinitailise l'état de la scène
        """
        for obj in self.generic_objects.values():
            obj.release()

        for chunk_batch in self.chunk_batches.values():
            chunk_batch.release()

        for water_batch in self.water_batches.values():
            water_batch.release()

        self.generic_objects.clear()
        self.chunk_batches.clear()
        self.water_batches.clear()

        self.next_obj_index = 0
        self.next_chunk_index = 0
        self.next_water_index = 0
