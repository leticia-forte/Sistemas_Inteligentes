##  RESCUER AGENT
### @Author: Tacla (UTFPR)
### Demo of use of VictimSim
### Not a complete version of DFS; it comes back prematuraly
### to the base when it enters into a dead end position


from vs.abstract_agent import AbstAgent
from vs.constants import VS
from map import Map


## Classe que define o Agente Rescuer com um plano fixo
class Rescuer(AbstAgent):
    def __init__(self, env, config_file):
        """ 
        @param env: a reference to an instance of the environment class
        @param config_file: the absolute path to the agent's config file"""

        super().__init__(env, config_file)

        # Specific initialization for the rescuer
        self.map = Map()            # only SOC_1 has all maps (it is the master)
        self.victims = {}           # list of found victims
        self.plan = []              # a list of planned actions
        self.plan_x = 0             # the x position of the rescuer during the planning phase
        self.plan_y = 0             # the y position of the rescuer during the planning phase
        self.plan_visited = set()   # positions already planned to be visited 
        self.plan_rtime = self.TLIM # the remaing time during the planning phase
        self.plan_walk_time = 0.0   # previewed time to walk during rescue
        self.x = 0                  # the current x position of the rescuer when executing the plan
        self.y = 0                  # the current y position of the rescuer when executing the plan
        self.explorers_remaining = {"EXP_1", "EXP_2", "EXP_3"} # control explorers
        self.rescuers = []          # list of all rescuers
                
        # Starts in IDLE state.
        # It changes to ACTIVE when the map arrives
        self.set_state(VS.IDLE)

    def set_rescuers(self, rescuers_lst):
        """ each rescuer has the reference to the others"""
        self.rescuers = rescuers_lst
        
    def do_rescue(self, map, clusters):
        """ O agente socorrista executa a estratégia de salvamento tendo
            o mapa e os clusters que foram atribuídos a ele.
        """
        # It changes to ACTIVE when the map arrives
        self.set_state(VS.ACTIVE)
        
        print(f"{self.NAME}: socorrista planeja o socorro...")
        print(f"{self.NAME}: que consiste fazer uma lista de ações e...")
        print(f"{self.NAME}: salvá-las em self.plan. No método deliberate,")
        print(f"{self.NAME}: o socorrista executa uma ação do plano por chamada.")
        


        
    def merge_maps(self, exp_name, map, victims):
        """ The explorer named exp_name sends the map containing the walls and
        victims' location. The rescuer becomes ACTIVE. From now,
        the deliberate method is called by the environment"""

        # Merge received map directly into self.map
        # Merge all visited coordinates from this explorer into self.map
        for coord, cell_data in map.map_data.items():  
            # Since each explorer contributes visited cells,
            # simply add coordinates not yet present
            if not self.map.in_map(coord):
                difficulty, victim_seq, actions_res = cell_data
                self.map.add(coord, difficulty, victim_seq, actions_res)
    
        print(f"{self.NAME}: Map received from explorer {exp_name}")

        # Merge found victims
        #print()
        #print(f"{self.NAME} Found victs by {exp_name}: {victims}")
        self.victims.update(victims)
        #print(f"{self.NAME} Updated victs: {self.victims}")
        
        # Mark this explorer as received
        self.explorers_remaining.discard(exp_name)

        if self.explorers_remaining:
            print(f"{self.NAME}: Waiting for remaining explorers... {self.explorers_remaining}")
            return
        
        # print the merged map
        self.map.draw()
        
        # print the found victims by all explorers - you may comment out
        #for seq, data in self.victims.items():
        #    coord, vital_signals = data
        #    x, y = coord
        #    print(f"{self.NAME} Victim {seq} at ({x}, {y}) vs: {vital_signals}")

        ##################
        ### CLUSTERING ###
        ##################
        # O agente socorrista mestre faz o clustering
        clusters = []
        
        #####################
        ### SEND CLUSTERS ###
        #####################
        # Send map and cluster to the other rescuer agents
        for i in range(3):
            self.rescuers[i].do_rescue(self.map, clusters)
            
        
    def deliberate(self) -> bool:
        """ This is the choice of the next action. The simulator calls this
        method at each reasonning cycle if the agent is ACTIVE.
        Must be implemented in every agent
        @return True: there's one or more actions to do
        @return False: there's no more action to do """

        # No more actions to do
        if self.plan == []:  # empty list, no more actions to do
           print(f"{self.NAME} has finished the plan")
           return False

        # Takes the first action of the plan (walk action) and removes it from the plan
        dx, dy, there_is_vict = self.plan.pop(0)
        #print(f"{self.NAME} pop dx: {dx} dy: {dy} vict: {there_is_vict}")

        # Walk - just one step per deliberation
        walked = self.walk(dx, dy)

        # Rescue the victim at the current position
        if walked == VS.EXECUTED:
            self.x += dx
            self.y += dy
            #print(f"{self.NAME} Walk ok - Rescuer at position ({self.x}, {self.y})")
            # check if there is a victim at the current position
            if there_is_vict:
                rescued = self.first_aid() # True when rescued
                if rescued:
                    print(f"{self.NAME} Victim rescued at ({self.x}, {self.y})")
                else:
                    print(f"{self.NAME} Plan fail - victim not found at ({self.x}, {self.x})")
        else:
            print(f"{self.NAME} Plan fail - walk error - agent at ({self.x}, {self.x})")
            
        #input(f"{self.NAME} remaining time: {self.get_rtime()} Tecle enter")

        return True

