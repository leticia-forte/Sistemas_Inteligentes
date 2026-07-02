##  RESCUER AGENT
### @Author: Tacla (UTFPR)
### Modificado para a Tarefa 5: Trajetória de Socorro (A*)

from vs.abstract_agent import AbstAgent
from vs.constants import VS
from map import Map
import heapq # Necessário para o algoritmo A*

## Classe que define o Agente Rescuer com planejamento A*
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
        self.set_state(VS.IDLE)

    def set_rescuers(self, rescuers_lst):
        """ each rescuer has the reference to the others"""
        self.rescuers = rescuers_lst
        
    def do_rescue(self, map, cluster_atribuido):
        """ O agente socorrista planeja o salvamento usando A* para o cluster atribuído. """
        self.set_state(VS.ACTIVE)
        self.map = map  # Recebe o mapa mesclado do master
        
        print(f"{self.NAME}: Planejando socorro via A*...")

        # =====================================================================
        # --- INSIRA AQUI O SEU CÓDIGO DE CLASSIFICAÇÃO E REGRESSÃO ---
        # Exemplo: avaliar sinais vitais das vítimas recebidas em 'cluster_atribuido'
        # e prever a gravidade.
        
        
        # ---------------------------------------------------------------------

        # =====================================================================
        # --- INSIRA AQUI O SEU CÓDIGO DE SEQUENCIAMENTO ---
        # Exemplo: ordernar as vítimas do 'cluster_atribuido' baseado na
        # gravidade ou distância.
        sequencia_vitimas = cluster_atribuido # Substitua por sua lista ordenada
        
        # ---------------------------------------------------------------------

        # PLANEJAMENTO DE TRAJETÓRIA COM A*
        current_pos = (0, 0) # Inicia na base
        self.plan = []
        self.plan_rtime = self.TLIM
        
        for victim_coord in sequencia_vitimas:
            # Busca caminho até a vítima
            path_to_vict = self.a_star(current_pos, victim_coord)
            
            # Busca caminho da vítima de volta pra base (garantia de sobrevivência)
            path_to_base = self.a_star(victim_coord, (0, 0)) 
            
            if not path_to_vict or not path_to_base:
                print(f"{self.NAME}: Destino {victim_coord} ou retorno inacessível. Ignorando.")
                continue
                
            ida_cost = self._calc_path_cost(current_pos, path_to_vict)
            volta_cost = self._calc_path_cost(victim_coord, path_to_base)
            first_aid_cost = self.COST_FIRST_AID
            
            # Verifica se o agente tem tempo para ir, realizar os primeiros socorros e voltar para a base
            if self.plan_rtime - ida_cost - first_aid_cost - volta_cost >= 0:
                # Adiciona o trajeto da vítima ao plano e aplica o kit de socorro no último passo
                self._add_path_to_plan(current_pos, path_to_vict, apply_first_aid_at_end=True)
                
                # Atualiza tempo restante e posição atual virtual
                self.plan_rtime -= (ida_cost + first_aid_cost)
                current_pos = victim_coord
            else:
                print(f"{self.NAME}: Tempo insuficiente para salvar vítima em {victim_coord}. Retornando à base.")
                break # Para de tentar salvar e vai para a rotina de voltar à base
        
        # Fim do sequenciamento, deve retornar à base
        if current_pos != (0, 0):
            path_to_base = self.a_star(current_pos, (0, 0))
            if path_to_base:
                self._add_path_to_plan(current_pos, path_to_base, apply_first_aid_at_end=False)
                
        print(f"{self.NAME}: Planejamento finalizado. Ações planejadas: {len(self.plan)}")

    def a_star(self, start, goal):
        """ Algoritmo A* para encontrar o menor custo do ponto 'start' ao 'goal'. """
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        
        # Função Heurística (Distância Diagonal - Admissível e Consistente para grids 8-way)
        def h(pos):
            dx = abs(pos[0] - goal[0])
            dy = abs(pos[1] - goal[1])
            # Utiliza COST_LINE e COST_DIAG para manter consistência com o custo do cenário
            return self.COST_LINE * (dx + dy) + (self.COST_DIAG - 2 * self.COST_LINE) * min(dx, dy)
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path # Retorna lista de coordenadas excluindo o 'start'
            
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    neighbor = (current[0] + dx, current[1] + dy)
                    
                    # Checa se o vizinho existe no mapa que foi explorado
                    if neighbor not in self.map.map_data:
                        continue
                    
                    cell_data = self.map.map_data[neighbor]
                    difficulty = cell_data[0] # índice 0 contém a dificuldade da célula
                    
                    if difficulty == VS.OBST_WALL:
                        continue
                        
                    step_cost = (self.COST_DIAG if dx != 0 and dy != 0 else self.COST_LINE) * difficulty
                    tentative_g_score = g_score[current] + step_cost
                    
                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score = tentative_g_score + h(neighbor)
                        heapq.heappush(open_set, (f_score, neighbor))
                        
        return None # Caminho não encontrado

    def _calc_path_cost(self, start, path):
        """ Calcula o custo de tempo de um caminho planejado """
        cost = 0.0
        curr = start
        for node in path:
            dx = node[0] - curr[0]
            dy = node[1] - curr[1]
            diff = self.map.map_data[node][0]
            step_cost = self.COST_DIAG if (dx != 0 and dy != 0) else self.COST_LINE
            cost += step_cost * diff
            curr = node
        return cost

    def _add_path_to_plan(self, start, path, apply_first_aid_at_end=False):
        """ Converte lista de coordenadas em ações (dx, dy, has_victim) e adiciona ao self.plan """
        curr = start
        for i, node in enumerate(path):
            dx = node[0] - curr[0]
            dy = node[1] - curr[1]
            is_last = (i == len(path) - 1)
            has_vict = True if (is_last and apply_first_aid_at_end) else False
            self.plan.append((dx, dy, has_vict))
            curr = node

    def merge_maps(self, exp_name, map, victims):
        """ O mestre SOC_1 recebe o mapa dos exploradores, mescla, e quando completo
            divide o trabalho para todos os socorristas. """

        for coord, cell_data in map.map_data.items():  
            if not self.map.in_map(coord):
                difficulty, victim_seq, actions_res = cell_data
                self.map.add(coord, difficulty, victim_seq, actions_res)
    
        print(f"{self.NAME}: Map received from explorer {exp_name}")

        self.victims.update(victims)
        self.explorers_remaining.discard(exp_name)

        if self.explorers_remaining:
            print(f"{self.NAME}: Waiting for remaining explorers... {self.explorers_remaining}")
            return
        
        self.map.draw()

        # =====================================================================
        # --- INSIRA AQUI O SEU CÓDIGO DE CLUSTERING ---
        # Exemplo: clusters = seu_algoritmo_de_clustering(self.victims)
        clusters = [] # Temporário
        
        # ---------------------------------------------------------------------

        # =====================================================================
        # --- INSIRA AQUI O SEU CÓDIGO DE ATRIBUIÇÃO AOS SOCORRISTAS ---
        # Exemplo: atribuicoes = seu_algoritmo_de_atribuicao(clusters, len(self.rescuers))
        atribuicoes = [[], [], []] # Temporário (esperando 3 socorristas)
        
        # ---------------------------------------------------------------------

        #####################
        ### SEND CLUSTERS ###
        #####################
        for i in range(len(self.rescuers)):
            self.rescuers[i].do_rescue(self.map, atribuicoes[i])
            
        
    def deliberate(self) -> bool:
        """ Executa o plano ação por ação """

        if self.plan == []:  
           print(f"{self.NAME} has finished the plan")
           return False

        dx, dy, there_is_vict = self.plan.pop(0)

        walked = self.walk(dx, dy)

        if walked == VS.EXECUTED:
            self.x += dx
            self.y += dy
            if there_is_vict:
                rescued = self.first_aid() 
                if rescued:
                    print(f"{self.NAME} Victim rescued at ({self.x}, {self.y})")
                else:
                    print(f"{self.NAME} Plan fail - victim not found at ({self.x}, {self.y})")
        else:
            print(f"{self.NAME} Plan fail - walk error - agent at ({self.x}, {self.y})")
            
        return True