import os
import json
import shutil


class RebootManager:
    @staticmethod
    def erase_worlds():
        """Supprime tous les mondes créés"""
        # Load les données de tous les mondes
        with open("worlds.json", "r") as fr:
            data = json.load(fr)

        # Pour chaque monde, supprime le dossier du monde (et tout son contenu)
        for i in data:
            path = i
            if os.path.exists(path):
                shutil.rmtree(path)

        # Supprime les données des mondes, et sauvegarde
        with open("worlds.json", "w") as fw:
            json.dump({}, fw)


if __name__ == "__main__":
    # Instancie la classe de reboot (pour la suppression des mondes)
    reboot_manager = RebootManager()

    # Demande une confirmation de suppression des mondes
    verif = input("Etes vous sûr de vouloir supprimer l'entiereté de vos mondes ? (o/n) ")
    if verif == "o" or verif == "O" or verif == "oui":
        # La suppression est confirmée, on va supprimer tous les mondes
        reboot_manager.erase_worlds()
