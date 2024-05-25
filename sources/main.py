"""
PyCraft - Projet dans le cadre du trophée NSI
"""

if __name__ == "__main__":
    # importe les paramètres
    import game.settings as settings

    # recupère et applique les préferences de preferences.txt
    import game.preferences as preferences
    preferences.setup_preferences()

    # importe la classe Game, responsable de l'initialisation du monde
    # et de la créatitno d'un contexte de jeu
    from game.game_manager import Game

    active_game = Game()

    # intialise le jeu avec des "input()"
    active_game.starting_input()


    # crée la classe du monde par défaut
    import game.world.world_manager as world_manager
    world = world_manager.World()

    # Donne l'instance 'world' à la classe de contexte 'game'
    active_game.bind_context_to_world(world)

    # recupère les paramètres du monde chargé
    active_game.load_parameters()

    # rentre dans le contexte du jeu (dans lequel est executée la loop principale)
    # appelle la fonction __enter__() de game  
    with active_game: 
        # lance le jeu dans le contexte
        world.run(settings.MAXFPS)

    # en cas d'erreur/Ctrl-C dans le jeu, on sort du contexte de jeu 
    # et on appelle __exit__() de game, qui va sauvegarder.
