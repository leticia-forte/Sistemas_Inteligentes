# EXPLORER AGENT
# Modificado para implementar estratégia Online DFS com heurísticas unificadas:
# 1. Varredura de Perímetro (Adjacência a vítimas)
# 2. Atração de Cluster
# 3. Inércia Direcional
# 4. Viés de Setor

from vs.abstract_agent import AbstAgent
from vs.constants import VS
from map import Map

class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if not self.is_empty():
            return self.items.pop()

    def is_empty(self):
        return len(self.items) == 0

class Explorer(AbstAgent):
    def __init__(self, env, config_file, resc):
        """ Construtor do agente explorador
        @param env: a reference to the environment 
        @param config_file: the absolute path to the explorer's config file
        @param resc: a reference to the rescuer agent to invoke when exploration finishes
        """

        super().__init__(env, config_file)
        self.walk_stack = Stack()  # a stack to store the movements
        self.set_state(VS.ACTIVE)  # explorer is active since the begin
        self.resc = resc           # reference to the rescuer agent
        self.x = 0                 # current x position relative to the origin 0
        self.y = 0                 # current y position relative to the origin 0
        self.map = Map()           # create a map for representing the environment
        self.victims = {}          # a dictionary of found victims: (seq): ((x,y), [<vs>])
                                   # the key is a seq number of the victim,(x,y) the position, <vs> the list of vital signals

        # Conjunto para rastrear os nós já visitados
        self.visited = set()
        self.visited.add((self.x, self.y))

        # Variável para rastrear a posição da última vítima (Atração de Cluster)
        self.last_victim_pos = None

        # put the current position - the base - in the map
        self.map.add((self.x, self.y), 1, VS.NO_VICTIM, self.check_walls_and_lim())
        
        # Cost to move diagonally, read vital signs, and return,
        # assuming the maximum difficulty is 3.    
        self.one_more_step = self.COST_DIAG*2*3 + self.COST_READ

    def get_unvisited_neighbors(self):
        """ 
        Identifica posições vizinhas livres e as ordena baseando-se em um
        sistema de pontuação unificado (menor pontuação = maior prioridade).
        """
        obstacles = self.check_walls_and_lim()
        unvisited = []
        
        for direction in range(8):
            if obstacles[direction] == VS.CLEAR:
                dx, dy = Explorer.AC_INCR[direction]
                if (self.x + dx, self.y + dy) not in self.visited:
                    unvisited.append((dx, dy))
                    
        if unvisited:
            # Extrai o ID do agente para o viés de setor
            agent_id = 1
            if "_" in self.NAME:
                try:
                    agent_id = int(self.NAME.split("_")[1])
                except ValueError:
                    pass
            
            # Extrai o último movimento para manter a Inércia Direcional
            last_dx, last_dy = 0, 0
            if not self.walk_stack.is_empty():
                last_dx, last_dy = self.walk_stack.items[-1]

            def heuristic_score(move):
                mdx, mdy = move
                nx, ny = self.x + mdx, self.y + mdy
                score = 0
                
                # --- 1. PRIORIDADE MÁXIMA: PERÍMETRO DE VÍTIMA ---
                # Se a célula alvo encosta em QUALQUER vítima já achada, explora na hora.
                is_adjacent_to_victim = False
                for (vx, vy), _ in self.victims.values():
                    if abs(nx - vx) <= 1 and abs(ny - vy) <= 1:
                        is_adjacent_to_victim = True
                        break
                
                if is_adjacent_to_victim:
                    score -= 1000  # Força o agente a "limpar" o 3x3 ao redor da vítima
                
                # --- 2. ATRAÇÃO DE CLUSTER (Área próxima à última vítima) ---
                if self.last_victim_pos is not None:
                    vx, vy = self.last_victim_pos
                    dist_sq = (nx - vx)**2 + (ny - vy)**2
                    
                    if dist_sq <= 16: # Raio de 4 células
                        score += dist_sq # Células mais próximas recebem score menor
                    else:
                        self.last_victim_pos = None # Esquece se afastar demais
                
                # --- 3. INÉRCIA DIRECIONAL (Evita zigue-zague) ---
                if mdx == last_dx and mdy == last_dy:
                    score -= 20
                    
                # --- 4. EFICIÊNCIA ORTOGONAL ---
                if mdx == 0 or mdy == 0:
                    score -= 5
                    
                # --- 5. VIÉS DE SETOR (Espalhamento inicial pelo mapa) ---
                if agent_id == 1:
                    score += (mdx + mdy)       # Noroeste
                elif agent_id == 2:
                    score += (-mdx + mdy)      # Nordeste
                else:
                    score += (-mdy)            # Sul
                    
                return score

            # Ordena do menor score (mais desejado) para o maior (menos desejado)
            unvisited.sort(key=heuristic_score)
            
        return unvisited
        
    def explore(self):
        unvisited_moves = self.get_unvisited_neighbors()

        # FASE DE EXPANSÃO (DFS)
        if unvisited_moves:
            dx, dy = unvisited_moves[0]

            rtime_bef = self.get_rtime()
            result = self.walk(dx, dy)
            rtime_aft = self.get_rtime()

            if result == VS.BUMPED:
                self.map.add((self.x + dx, self.y + dy), VS.OBST_WALL, VS.NO_VICTIM, self.check_walls_and_lim())
                self.visited.add((self.x + dx, self.y + dy))

            if result == VS.EXECUTED:
                self.walk_stack.push((dx, dy))

                self.x += dx
                self.y += dy          
                self.visited.add((self.x, self.y))

                # Verificação de Vítimas
                seq = self.check_for_victim()
                if seq != VS.NO_VICTIM:
                    vs = self.read_vital_signals()
                    self.victims[seq] = ((self.x, self.y), vs)
                    
                    # Salva a posição da vítima para aplicar a Atração de Cluster
                    self.last_victim_pos = (self.x, self.y)
                
                difficulty = (rtime_bef - rtime_aft)
                if dx == 0 or dy == 0:
                    difficulty = difficulty / self.COST_LINE
                else:
                    difficulty = difficulty / self.COST_DIAG

                self.map.add((self.x, self.y), difficulty, seq, self.check_walls_and_lim())
        
        # FASE DE BACKTRACKING (DFS - Retorno)
        else:
            if not self.walk_stack.is_empty():
                dx, dy = self.walk_stack.pop()
                
                bdx = dx * -1
                bdy = dy * -1
                
                result = self.walk(bdx, bdy)
                
                if result == VS.EXECUTED:
                    self.x += bdx
                    self.y += bdy

        return

    def come_back(self):
        dx, dy = self.walk_stack.pop()
        dx = dx * -1
        dy = dy * -1

        result = self.walk(dx, dy)
        if result == VS.BUMPED:
            # print(f"{self.NAME}: when coming back bumped at ({self.x+dx}, {self.y+dy}) , rtime: {self.get_rtime()}")
            return
            
        if result == VS.EXECUTED:
            self.x += dx
            self.y += dy
        
    def deliberate(self) -> bool:
        if self.walk_stack.is_empty() and not self.get_unvisited_neighbors():
            # print(f"{self.NAME}: rtime {self.get_rtime()}, FULL EXPLORATION, invoking the MASTER rescuer")
            self.resc.merge_maps(self.NAME, self.map, self.victims)
            return False

        consumed_time = self.TLIM - self.get_rtime()
        
        if (consumed_time + self.one_more_step) < self.get_rtime():
            self.explore()
            return True

        if self.walk_stack.is_empty():
            # print(f"{self.NAME}: rtime {self.get_rtime()}, invoking the MASTER rescuer")
            self.resc.merge_maps(self.NAME, self.map, self.victims)
            return False

        self.come_back()
        return True