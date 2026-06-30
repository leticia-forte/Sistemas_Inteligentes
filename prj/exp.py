# EXPLORER AGENT
# @Author: Tacla, UTFPR
#
### It walks randomly in the environment looking for victims. When half of the
### exploration has gone, the explorer goes back to the base.


import random
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
        """ Construtor do agente random on-line
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

        # put the current position - the base - in the map
        self.map.add((self.x, self.y), 1, VS.NO_VICTIM, self.check_walls_and_lim())
        
        # Cost to move diagonally, read vital signs, and return,
        # assuming the maximum difficulty is 3.    
        self.one_more_step = self.COST_DIAG*2*3 + self.COST_READ

    def get_next_position(self):
        """ Randomically, gets the next position that can be explored (no wall and inside the grid)
            There must be at least one CLEAR position in the neighborhood, otherwise it loops forever.
        """
        # Check the neighborhood walls and grid limits
        obstacles = self.check_walls_and_lim()
    
        # Loop until a CLEAR position is found
        while True:
            # Get a random direction
            direction = random.randint(0, 7)
            # Check if the corresponding position in walls_and_lim is CLEAR
            if obstacles[direction] == VS.CLEAR:
                return Explorer.AC_INCR[direction]
        
    def explore(self):
        # get an random increment for x and y       
        dx, dy = self.get_next_position()

        # Moves the explorer agent to another position
        rtime_bef = self.get_rtime()   ## get remaining batt time before the move
        result = self.walk(dx, dy)
        rtime_aft = self.get_rtime()   ## get remaining batt time after the move

        # Test the result of the walk action
        # It should never bump, since get_next_position always returns a valid position...
        # but for safety, let's test it anyway
        if result == VS.BUMPED:
            # update the map with the wall
            self.map.add((self.x + dx, self.y + dy), VS.OBST_WALL, VS.NO_VICTIM, self.check_walls_and_lim())
            #print(f"{self.NAME}: Wall or grid limit reached at ({self.x + dx}, {self.y + dy})")

        if result == VS.EXECUTED:
            # puts the visited position in a stack. When the batt is low, 
            # the explorer unstack each visited position to come back to the base
            self.walk_stack.push((dx, dy))

            # update the agent's position relative to the origin of 
            # the coordinate system used by the agents
            self.x += dx
            self.y += dy          

            # Check for victims
            seq = self.check_for_victim()
            if seq != VS.NO_VICTIM:
                vs = self.read_vital_signals()
                self.victims[seq] = ((self.x, self.y), vs)
                #print(f"{self.NAME} Victim found at ({self.x}, {self.y}), rtime: {self.get_rtime()}")
                #print(f"{self.NAME} Seq: {seq} Vital signals: {vs}")
            
            # Calculates the difficulty of the visited cell
            difficulty = (rtime_bef - rtime_aft)
            if dx == 0 or dy == 0:
                difficulty = difficulty / self.COST_LINE
            else:
                difficulty = difficulty / self.COST_DIAG

            # Update the map with the new cell
            self.map.add((self.x, self.y), difficulty, seq, self.check_walls_and_lim())
            #print(f"{self.NAME}:at ({self.x}, {self.y}), diffic: {difficulty:.2f} vict: {seq} rtime: {self.get_rtime()}")

        return

    def come_back(self):
        """ Procedure to return to the base: pops the walk_stack to follow
        the exploration path in the opposite direction """
  
        dx, dy = self.walk_stack.pop()
        dx = dx * -1
        dy = dy * -1

        result = self.walk(dx, dy)
        # Walk resulted in bumping into a wall or end of grid
        if result == VS.BUMPED:
            print(f"{self.NAME}: when coming back bumped at ({self.x+dx}, {self.y+dy}) , rtime: {self.get_rtime()}")
            return
            
        # Walk succeded
        if result == VS.EXECUTED:
            # update the agent's position relative to the origin
            self.x += dx
            self.y += dy
            #print(f"{self.NAME}: coming back at ({self.x}, {self.y}), rtime: {self.get_rtime()}")
        
    def deliberate(self) -> bool:
        """  The simulator calls this method at each cycle. 
        Must be implemented in every agent. The agent chooses the next action.
        """

        consumed_time = self.TLIM - self.get_rtime()
        
        # check if it is time to come back to the base      
        if (consumed_time + self.one_more_step) < self.get_rtime():
            # continue to explore
            self.explore()
            return True

        # Returning to the base terminates when there are no more moves to pop from the stack
        if self.walk_stack.is_empty():
            # time to wake up the rescuer
            # pass the walls and the victims (here, they're empty)
            print(f"{self.NAME}: rtime {self.get_rtime()}, invoking the MASTER rescuer")
            self.resc.merge_maps(self.NAME, self.map, self.victims)
            return False

        # move to the base
        self.come_back()
        return True



##################################################################################################
##################################################################################################
##################################################################################################
##################################################################################################
################### FEITO PELO GEMINI, NAO ACHO QUE FUNCIONOU NAO ######################
##################################################################################################
##################################################################################################
##################################################################################################
import math
import random
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
        """ Construtor do agente random on-line """
        super().__init__(env, config_file)
        self.walk_stack = Stack()  # Pilha fornecida para armazenar os passos de volta
        self.set_state(VS.ACTIVE)  
        self.resc = resc           
        self.x = 0                 # Posição x relativa
        self.y = 0                 # Posição y relativa
        
        # --- ESTRUTURAS DO ONLINE DFS ---
        self.untried = {}          # untried[s] = [ações...]
        self.unbacktracked = {}    # caminhos de volta do DFS
        self.result = {}           # result[(s, a)] = s'
        self.previous_s = None
        self.previous_a = None
        
        # Instância de Map() já definida no seu esqueleto para salvar o mapa
        self.map = Map() 

    def get_agent_angle_range(self):
        """ Divide 360° em 3 fatias de 120° com base no número contido no NAME do agente """
        if "1" in self.NAME:   # EXP_1: Topo / Nordeste
            return -60, 60
        elif "2" in self.NAME: # EXP_2: Sul / Sudeste
            return 60, 180
        else:                  # EXP_3: Oeste / Noroeste
            return -180, -60

    def is_in_my_zone(self, x, y):
        """ Verifica se o ponto (x, y) está dentro do cone de 120 graus do agente """
        if x == 0 and y == 0:
            return True # A base (0,0) é neutra
        
        # Calcula o ângulo em radianos e converte para graus
        angulo_rad = math.atan2(y, x)
        angulo_graus = math.degrees(angulo_rad)
        
        min_ang, max_ang = self.get_agent_angle_range()
        return min_ang <= angulo_graus <= max_ang

    def get_ordered_actions(self, s):
        """ Usa self.AC_INCR do abstract_agent para obter as direções e as ordena 
            priorizando as que mantêm o agente em sua fatia de 120 graus """
        x, y = s
        actions_in_zone = []
        actions_out_zone = []
        
        # self.AC_INCR contém o dicionário com as 8 direções de movimento (0 a 7)
        for action, (dx, dy) in self.AC_INCR.items():
            next_x = x + dx
            next_y = y + dy
            
            if self.is_in_my_zone(next_x, next_y):
                actions_in_zone.append(action)
            else:
                actions_out_zone.append(action)
                
        # Embaralha listas internas para evitar loops determinísticos em obstáculos
        random.shuffle(actions_in_zone)
        random.shuffle(actions_out_zone)
        
        # Retorna primeiro as ações de dentro da zona e depois as de fora (como escape)
        return actions_in_zone + actions_out_zone

    def explore(self):
        """ Lógica do ONLINE-DFS-AGENT usando as funções do simulador """
        s_prime = (self.x, self.y)
        
        # Inicializa o estado se ele for novo
        if s_prime not in self.untried:
            self.untried[s_prime] = self.get_ordered_actions(s_prime)
            self.unbacktracked[s_prime] = []

        # Se veio de um movimento anterior bem-sucedido, atualiza a tabela de transição
        if self.previous_s is not None and self.previous_a is not None:
            self.result[(self.previous_s, self.previous_a)] = s_prime
            if self.previous_s not in self.unbacktracked[s_prime]:
                self.unbacktracked[s_prime].append(self.previous_s)

        # Escolha da ação conforme o Online DFS
        if not self.untried[s_prime]: 
            if not self.unbacktracked[s_prime]:
                # Se não há para onde voltar no DFS, o leque local foi todo explorado
                return
            else:
                # Backtrack: Encontra qual ação levou ao estado anterior gravado
                target_s = self.unbacktracked[s_prime].pop()
                action = None
                for act, next_s in self.result.items():
                    if act[0] == s_prime and next_s == target_s:
                        action = act[1]
                        break
                if action is None:
                    return
        else:
            action = self.untried[s_prime].pop(0)

        # Traduz a ação numérica usando AC_INCR herdado do abstract_agent
        dx, dy = self.AC_INCR[action]
        
        # Executa a função nativa de movimento
        result_move = self.walk(dx, dy)
        
        if result_move == VS.EXECUTED:
            # Atualiza o estado interno
            self.previous_s = s_prime
            self.previous_a = action
            self.x += dx
            self.y += dy
            
            # Alimenta a pilha nativa do esqueleto para que ele saiba voltar à base
            # O retorno precisa de coordenadas inversas para desfazer o passo (-dx, -dy)
            self.walk_stack.push((-dx, -dy))
            
            # FUNÇÃO NATIVA: Verifica se há vítima na nova célula
            seq_vitima = self.check_for_victim()
            if seq_vitima != VS.NO_VICTIM:
                # Salva a vítima encontrada no objeto de mapa local
                self.map.add_victim(self.x, self.y, seq_vitima)
                
        elif result_move == VS.BUMPED:
            # Encontrou uma parede: salva no objeto Map
            self.map.add_wall(self.x + dx, self.y + dy)
            # Para o Online DFS, a ação que bateu resulta em continuar no mesmo lugar
            self.result[(s_prime, action)] = s_prime

    def deliberate(self) -> bool:
        """ Método acionado a cada ciclo pelo simulador """
        consumed_time = self.TLIM - self.get_rtime()
        
        # VERIFICAÇÃO DE TEMPO SEGURO:
        # Se o tempo decorrido + margem de erro for menor que o tempo restante na bateria, 
        # significa que ainda há tempo suficiente para se distanciar da base explorando.
        if (consumed_time + self.one_more_step) < self.get_rtime():
            self.explore()
            return True

        # --- SE O TEMPO ESGOTAR: ENTRA NO MODO DE RETORNO À BASE ---
        if self.walk_stack.is_empty():
            # Chegou de volta à base! Salva o mapa final e aciona o Socorrista Mestre
            print(f"{self.NAME}: rtime {self.get_rtime()}, enviando dados ao SOCORRISTA MESTRE")
            self.resc.go_save_victims(self.map)
            return False

        # Desempilha o passo de volta e executa o movimento inverso em direção à base
        dx, dy = self.walk_stack.pop()
        result = self.walk(dx, dy)
        
        if result == VS.BUMPED:
            print(f"{self.NAME}: erro ao voltar, bateu em ({self.x+dx}, {self.y+dy})")
            return False
            
        if result == VS.EXECUTED:
            self.x += dx
            self.y += dy
            
        return True