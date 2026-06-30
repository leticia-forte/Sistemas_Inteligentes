##  RESCUER AGENT
### @Author: Tacla (UTFPR)
### Demo of use of VictimSim
### Not a complete version of DFS; it comes back prematuraly
### to the base when it enters into a dead end position


from vs.abstract_agent import AbstAgent
from vs.constants import VS
from map import Map
import random
import math


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
            

    def vizinhos_validos(self, pos): #função que retorna os vizinhos válidos e seus custos para se mover, não era necessário, pois o código já tinha isso implementado mas eu não vi

        vizinhos = []
        vetor_custos = []
        direcoes = [ (0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1) ]
        for d in direcoes:
            novo_x = pos[0] + d[0]
            novo_y = pos[1] + d[1]
            if self.map.in_map((novo_x, novo_y)):
                vizinhos.append((novo_x, novo_y))
                difficulty, vic_seq, next_actions_res = self.map.get((novo_x, novo_y)) #não tenho completa certeza disso
            
                if d[0] != 0 and d[1] != 0: # e nem disso pra ser sincero
                    difficulty = difficulty * 1.5

                vetor_custos.append(difficulty)    

        return vizinhos, vetor_custos
    
    def octil_distance(self, start, goal): # a heuristica é a distância octil 
        dx = abs(start[0] - goal[0])
        dy = abs(start[1] - goal[1])
        D = 1          
        D2 = 1.5       
        return D * (dx + dy) + (D2 - 2 * D) * min(dx, dy)

    def aestrela(self, start, goal):    
        vetor_caminho = []
        #print(start)
        heap = [(0, start)]
        vetor_custo_parcial = {start: 0}
        vetor_anteriores = {}

        while heap:
            melhor_i = 0
            for i in range(1, len(heap)):
                if heap[i][0] < heap[melhor_i][0]:
                    melhor_i = i

            custo_atual, atual = heap.pop(melhor_i)
            if  atual == goal:
                vetor_caminho = [atual]
                while atual in vetor_anteriores:
                    atual = vetor_anteriores[atual]
                    vetor_caminho.append(atual)

                vetor_caminho = vetor_caminho[::-1]
                return vetor_custo_parcial[goal], vetor_caminho
            
            vizinhos_validos_lista, vetor_custos = self.vizinhos_validos(atual)
        
                       
            for i in range(len(vizinhos_validos_lista)):
                vizinho = vizinhos_validos_lista[i]
                custo_vizinho = vetor_custos[i]
                custo_real = vetor_custo_parcial[atual] + custo_vizinho
                
            
                if vizinho not in vetor_custo_parcial or custo_real < vetor_custo_parcial[vizinho]:
                    vetor_custo_parcial[vizinho] = custo_real
                    vetor_anteriores[vizinho] = atual
                    custo_atual = custo_real + self.octil_distance(vizinho, goal)
                    heap.append((custo_atual, vizinho))    

        return None, []
    
    def __planner(self, victims_list):
        vetor_caminhos = []
        vetor_custos = []
        i = 0
        for victim in victims_list:
            if i != 0:
                vetor_custos_parcial, vetor_caminhos_parcial = self.aestrela((victims_list[i-1][0]), victim[0])
            else:
                vetor_custos_parcial, vetor_caminhos_parcial = self.aestrela((0, 0), victim[0])
            vetor_caminhos.append(vetor_caminhos_parcial)
            vetor_custos.append(vetor_custos_parcial)
            i = i + 1
        
        vetor_custos_parcial, vetor_caminhos_parcial = self.aestrela(victim[0], (0, 0))
        vetor_caminhos.append(vetor_caminhos_parcial)
        vetor_custos.append(vetor_custos_parcial)
        acumulador = 0
        for custo in vetor_custos:
            acumulador = acumulador + custo

        acumulador = acumulador + (len(victims_list) * self.COST_FIRST_AID)

        self.plan = []

        primeira_pos = True
        posicao_anterior = None
        i = 0
        
        for caminho_parcial in vetor_caminhos:
            for posicao in caminho_parcial:
                if primeira_pos:
                    posicao_anterior = posicao
                    primeira_pos = False
                    continue

                if posicao == caminho_parcial[0]:
                    posicao_anterior = posicao
                    #print(self.plan[i-1])
                    dx, dy, _ = self.plan[i-1]    #A forma pensada para alterar um dado na tupla, que nunca estava salvando aonde tinha sobreviventes
                    self.plan[i-1] = (dx, dy, True)
                    #print(self.plan[i-1])
                    continue
                
                has_victim = False
                dx = posicao[0] - posicao_anterior[0]
                dy = posicao[1] - posicao_anterior[1]
                self.plan.append((dx, dy, has_victim))
                posicao_anterior = posicao
                i = i + 1       

        return acumulador

        pass

    def swap(self, list):
        i = random.randint(0, len(list) - 1)
        j = random.randint(0, len(list) - 1)
        list[i], list[j] = list[j], list[i]
        return list
    
    def simmulated_annealing(self, victims_list):
        # print(victims_list)
        # for v in victims_list:
        #     if len(v) < 4:
        #         print("Vitima:", v, "tamanho:", len(v))
        victims_list.sort(key=lambda v: v[3], reverse=True) #ordena pela sobr
        not_valid = True
        while not_valid:
            current = victims_list.copy()
            best = current
            best_E = self.__planner(best)
            max_iterations = 500

            for i in range(max_iterations):
                T = 100 * 0.99**i #linear: 100 * (max_iterations - i) / max_iterations
                next = current.copy()
                next = self.swap(next)
                current_E = self.__planner( current)
                next_E = self.__planner(next)
                delta = current_E - next_E
                if delta > 0 or random.uniform(0, 1) < math.exp(delta/T):
                    current = next
                if current_E < best_E:
                    best = current
                    best_E = current_E

            if best_E < self.TLIM:
                not_valid = False
            else:
                print(f"{self.NAME} redoing simmulated annealing, best energy {best_E} exceeds time limit {self.TLIM}")
                coeficiente = 1-self.TLIM/best_E 
                for i in range(int(len(victims_list)*coeficiente) + 1):
                    victims_list.pop() #remove a vitima com menor chance de sobrevivencia (a ultima da lista ordenada pela sobr)
                                   #to fazendo isso mais pra suprir aquilo que o Tacla pediu de usar sobr ou tri, mas 
                                   #talvez faria mais sentido tirar a vitima que está mais longe da base
        

        self.__planner(best)
        return best

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

