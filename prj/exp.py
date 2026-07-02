# EXPLORER AGENT
# Modificado para implementar estratégia Frontier-Based Exploration com A*
# 1. Varredura de Perímetro, Atração de Cluster e Viés de Setor
# 2. A* para pular becos sem saída (Backtracking Inteligente)
# 3. A* dinâmico para Retorno à Base (Otimização Máxima de Bateria)

from vs.abstract_agent import AbstAgent
from vs.constants import VS
from map import Map
import heapq
import math

class Explorer(AbstAgent):
    def __init__(self, env, config_file, resc):
        super().__init__(env, config_file)
        self.set_state(VS.ACTIVE)
        self.resc = resc           
        self.x = 0                 
        self.y = 0                 
        self.map = Map()           
        self.victims = {}          

        self.visited = set()
        self.visited.add((self.x, self.y))

        self.last_victim_pos = None
        self.last_dx = 0
        self.last_dy = 0

        self.map.add((self.x, self.y), 1, VS.NO_VICTIM, self.check_walls_and_lim())
        
        # --- NOVAS ESTRUTURAS DE INTELIGÊNCIA ---
        self.frontiers = set()       # Guarda nós adjacentes livres que não foram visitados
        self.plan = []               # Guarda a rota do A* sendo percorrida no momento
        self.returning_to_base = False 

    def get_unvisited_neighbors(self):
        """ Identifica posições vizinhas livres e as ordena baseando-se em heurísticas """
        obstacles = self.check_walls_and_lim()
        unvisited = []
        
        for direction in range(8):
            if obstacles[direction] == VS.CLEAR:
                dx, dy = Explorer.AC_INCR[direction]
                if (self.x + dx, self.y + dy) not in self.visited:
                    unvisited.append((dx, dy))
                    # Sempre que enxergamos um caminho livre, registramos como fronteira!
                    self.frontiers.add((self.x + dx, self.y + dy))
                    
        if unvisited:
            agent_id = 1
            if "_" in self.NAME:
                try:
                    agent_id = int(self.NAME.split("_")[1])
                except ValueError:
                    pass

            def heuristic_score(move):
                mdx, mdy = move
                nx, ny = self.x + mdx, self.y + mdy
                score = 0
                
                # Perímetro de vítima
                is_adjacent_to_victim = False
                for (vx, vy), _ in self.victims.values():
                    if abs(nx - vx) <= 1 and abs(ny - vy) <= 1:
                        is_adjacent_to_victim = True
                        break
                if is_adjacent_to_victim:
                    score -= 1000  
                
                # Atração de Cluster 
                if self.last_victim_pos is not None:
                    vx, vy = self.last_victim_pos
                    dist_sq = (nx - vx)**2 + (ny - vy)**2
                    if dist_sq <= 16: 
                        score += dist_sq 
                    else:
                        self.last_victim_pos = None 
                
                # Inércia Direcional 
                if mdx == self.last_dx and mdy == self.last_dy:
                    score -= 20
                    
                # Eficiência Ortogonal
                if mdx == 0 or mdy == 0:
                    score -= 5
                    
                # Viés de Setor Espacial
                if agent_id == 1: score += (mdx + mdy)       
                elif agent_id == 2: score += (-mdx + mdy)      
                else: score += (-mdy)            
                    
                return score

            unvisited.sort(key=heuristic_score)
            
        return unvisited

    def a_star(self, start, goal):
        """ A* que cruza apenas células já exploradas pelo robô para pular caminhos """
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}

        def h(pos):
            dx = abs(pos[0] - goal[0])
            dy = abs(pos[1] - goal[1])
            return self.COST_LINE * (dx + dy) + (self.COST_DIAG - 2 * self.COST_LINE) * min(dx, dy)

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    neighbor = (current[0] + dx, current[1] + dy)

                    # A* só pode andar por onde o agente já passou, a menos que seja o próprio destino (fronteira)
                    if neighbor not in self.visited and neighbor != goal:
                        continue

                    if neighbor in self.map.map_data:
                        difficulty = self.map.map_data[neighbor][0]
                        if difficulty == VS.OBST_WALL:
                            continue
                    else:
                        difficulty = 1.0 # Nó destino inexplorado ganha custo base

                    step_cost = (self.COST_DIAG if dx != 0 and dy != 0 else self.COST_LINE) * difficulty
                    tentative_g_score = g_score[current] + step_cost

                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score = tentative_g_score + h(neighbor)
                        heapq.heappush(open_set, (f_score, neighbor))
        return None

    def _calc_path_cost(self, start, path):
        cost = 0.0
        curr = start
        for node in path:
            dx = node[0] - curr[0]
            dy = node[1] - curr[1]
            if node in self.map.map_data:
                diff = self.map.map_data[node][0]
            else:
                diff = 1.0
            step_cost = self.COST_DIAG if (dx != 0 and dy != 0) else self.COST_LINE
            cost += step_cost * diff
            curr = node
        return cost

    def _process_execution(self, rtime_bef, dx, dy):
        """ Função utilitária para atualizar os mapas quando o robô anda com sucesso """
        rtime_aft = self.get_rtime()
        self.x += dx
        self.y += dy          
        self.visited.add((self.x, self.y))
        self.last_dx, self.last_dy = dx, dy

        seq = self.check_for_victim()
        if seq != VS.NO_VICTIM:
            vs = self.read_vital_signals()
            self.victims[seq] = ((self.x, self.y), vs)
            self.last_victim_pos = (self.x, self.y)
        
        difficulty = (rtime_bef - rtime_aft)
        if dx == 0 or dy == 0:
            difficulty = difficulty / self.COST_LINE
        else:
            difficulty = difficulty / self.COST_DIAG

        self.map.add((self.x, self.y), difficulty, seq, self.check_walls_and_lim())
        
    def deliberate(self) -> bool:
        # 1. Se estiver voltando para a base para encerrar o ciclo
        if self.returning_to_base:
            if not self.plan:
                # Chegou na base! Encerra exploração.
                print(f"{self.NAME}: Exploracao finalizada. Invocando Master. Sobrou {self.get_rtime():.1f} TLIM")
                self.resc.merge_maps(self.NAME, self.map, self.victims)
                return False
                
            dx, dy = self.plan.pop(0)
            self.walk(dx, dy)
            self.x += dx
            self.y += dy
            return True

        # 2. Condição Segura de Retorno (A*)
        # Para não gastar CPU calculando A* a cada frame, só avalia se estiver fisicamente distante
        dist_to_base = math.hypot(self.x, self.y)
        estimated_cost = dist_to_base * self.COST_DIAG * 2.5 
        
        if self.get_rtime() < estimated_cost + 100.0:
            path_to_base = self.a_star((self.x, self.y), (0,0))
            cost_to_base = self._calc_path_cost((self.x, self.y), path_to_base) if path_to_base else 0.0
            
            # Deixa uma margem de segurança de 25 de TLIM (caso ache vítimas no caminho)
            if self.get_rtime() <= cost_to_base + 25.0:
                self.returning_to_base = True
                if path_to_base:
                    curr = (self.x, self.y)
                    for node in path_to_base:
                        self.plan.append((node[0]-curr[0], node[1]-curr[1]))
                        curr = node
                return True

        # 3. Remove Fronteiras que já foram esbarradas ou visitadas
        self.frontiers = {f for f in self.frontiers if f not in self.visited}

        # 4. Executa plano de deslocamento em andamento (Pulo Inteligente A*)
        if self.plan:
            dx, dy = self.plan.pop(0)
            rtime_bef = self.get_rtime()
            result = self.walk(dx, dy)
            
            if result == VS.BUMPED:
                self.plan = [] # Encontrou obstáculo surpresa? Cancela o A* e recalcula
                self.map.add((self.x + dx, self.y + dy), VS.OBST_WALL, VS.NO_VICTIM, self.check_walls_and_lim())
                self.visited.add((self.x + dx, self.y + dy))
            elif result == VS.EXECUTED:
                self._process_execution(rtime_bef, dx, dy)
            return True

        # 5. Modo de Exploração Gulosa
        unvisited_moves = self.get_unvisited_neighbors()
        
        if unvisited_moves:
            dx, dy = unvisited_moves[0]
            rtime_bef = self.get_rtime()
            result = self.walk(dx, dy)
            
            if result == VS.BUMPED:
                self.map.add((self.x + dx, self.y + dy), VS.OBST_WALL, VS.NO_VICTIM, self.check_walls_and_lim())
                self.visited.add((self.x + dx, self.y + dy))
            elif result == VS.EXECUTED:
                self._process_execution(rtime_bef, dx, dy)
            return True
            
        # 6. Ficou preso! Usa A* para pular para a fronteira (esquina) inexplorada mais próxima
        if not self.frontiers:
            # Não sobrou mapa! Retorna à base.
            self.returning_to_base = True 
            return True
            
        # Ordena rápido por linha reta para economizar CPU e evitar rodar A* em dezenas de fronteiras
        sorted_frontiers = sorted(list(self.frontiers), key=lambda f: math.hypot(self.x - f[0], self.y - f[1]))
        
        for frontier in sorted_frontiers:
            path = self.a_star((self.x, self.y), frontier)
            if path:
                curr = (self.x, self.y)
                for node in path:
                    self.plan.append((node[0]-curr[0], node[1]-curr[1]))
                    curr = node
                break
        
        if not self.plan:
            self.frontiers.clear() # Se não há caminho para a fronteira, zera para não bugar
            
        return True