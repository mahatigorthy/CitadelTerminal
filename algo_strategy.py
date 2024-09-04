import gamelib
import random
import math
import warnings
from sys import maxsize
import json

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, PREV_HEALTH, DEFENDED_TURNS, ATTACKED_SIDE
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        PREV_HEALTH = 100
        DEFENDED_TURNS = 0
        ATTACKED_SIDE = {"left": 0, "right": 0}
        self.start_d = [[[4, 12], [23, 12], [9, 12], [18, 12]], [[4, 13], [23, 13], [9, 13], [18, 13]]]
        self.base_d = [[[3, 12], [24, 12], [4, 12], [23, 12], [9, 12], [10, 12], [18, 12], [17, 12], [25, 12], [2, 12], [13, 9]], 
                       [[0, 13], [27, 13]]]
        for t in self.base_d[0]:
            self.base_d[1].append([t[0], t[1] + 1])
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  # Comment or remove this line to enable warnings.
        
        if game_state.turn_number == 0: 
            game_state.attempt_spawn(TURRET, self.start_d[0])
            game_state.attempt_upgrade(self.start_d[0])
            game_state.attempt_spawn(WALL, self.start_d[1])

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def starter_strategy(self, game_state):
        global PREV_HEALTH, DEFENDED_TURNS

        if game_state.turn_number > 2:
            game_state.attempt_spawn(SUPPORT, [13, 6])
            game_state.attempt_upgrade([13, 6])

        self.update_attacked_side()
        
        if PREV_HEALTH > game_state.my_health and self.check_base_defense(game_state):
            self.build_reactive_defense(game_state)
            self.build_defences(game_state)
        else:
            self.build_defences(game_state)
            self.build_reactive_defense(game_state)
            
        if PREV_HEALTH == game_state.my_health:
            DEFENDED_TURNS += 1
        else:
            DEFENDED_TURNS = 0 

        if DEFENDED_TURNS > 3:
            self.send_scouts(game_state, 20)
        else: 
            self.send_scouts(game_state, 8)
        
        PREV_HEALTH = game_state.my_health
        gamelib.debug_write("end of turn (health): {}".format(PREV_HEALTH))
        gamelib.debug_write("end of turn (defended): {}".format(DEFENDED_TURNS))

    def update_attacked_side(self):
        for location in self.scored_on_locations:
            if location[0] < 14:
                ATTACKED_SIDE["left"] += 1
            else:
                ATTACKED_SIDE["right"] += 1
    
    def send_scouts(self, game_state, min_score):
        if game_state.get_resource(MP, 0) > min_score:
            scout_spawn_location_options = []
            for i in range(11):
                scout_spawn_location_options.append([3 + i, 10 - i])
                scout_spawn_location_options.append([24 - i, 10 - i])
            gamelib.util.debug_write(scout_spawn_location_options)
            best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
            game_state.attempt_spawn(SCOUT, best_location, 1000)

    def build_defences(self, game_state):
        if game_state.turn_number > 0: 
            if game_state.turn_number > 4:
                priority_side = "left" if ATTACKED_SIDE["left"] > ATTACKED_SIDE["right"] else "right"
                low_priority_side = "right" if priority_side == "left" else "left"

                self.rebuild_defense(game_state, priority_side)
                self.rebuild_defense(game_state, low_priority_side)

                game_state.attempt_spawn(SUPPORT, [13, 6])
            elif game_state.turn_number > 2:
                for location in self.base_d[0]:
                    if not game_state.contains_stationary_unit(location):
                        game_state.attempt_spawn(TURRET, location)
                        game_state.attempt_upgrade(location)
                        game_state.attempt_spawn(WALL, [location[0], location[1] + 1])

                for location in self.base_d[1]:
                    if not game_state.contains_stationary_unit(location):
                        game_state.attempt_spawn(WALL, location)
                        game_state.attempt_upgrade(location)

    def rebuild_defense(self, game_state, side):
        turret_locations = [loc for loc in self.base_d[0] if (loc[0] < 14 if side == "left" else loc[0] >= 14)]
        wall_locations = [loc for loc in self.base_d[1] if (loc[0] < 14 if side == "left" else loc[0] >= 14)]

        for location in turret_locations:
            if not game_state.contains_stationary_unit(location):
                game_state.attempt_spawn(TURRET, location)
                game_state.attempt_upgrade(location)
                game_state.attempt_spawn(WALL, [location[0], location[1] + 1])

        for location in wall_locations:
            if not game_state.contains_stationary_unit(location):
                game_state.attempt_spawn(WALL, location)
                game_state.attempt_upgrade(location)
                    
    def check_base_defense(self, game_state):
        if game_state.turn_number > 0: 
            for location in self.base_d[0]:
                if not game_state.contains_stationary_unit(location):
                    return False
        return True
    
    def build_reactive_defense(self, game_state):
        for location in self.scored_on_locations:
            build_location = [location[0], location[1] + 1]
            game_state.attempt_spawn(TURRET, build_location)

        for location in self.base_d[0]:
            if game_state.contains_stationary_unit(location) and not game_state.contains_stationary_unit([location[0], location[1] + 1]):
                game_state.attempt_spawn(WALL, [location[0], location[1] + 1])
                game_state.attempt_upgrade([location[0], location[1] + 1])

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
