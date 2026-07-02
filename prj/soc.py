##  RESCUER AGENT
### @Author: Tacla (UTFPR)
### Modificado para a Tarefa 5: Integração Completa (ML, Clustering, Sequenciamento TS e A*)

import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import warnings
from sklearn.exceptions import ConvergenceWarning

from vs.abstract_agent import AbstAgent
from vs.constants import VS
from map import Map
import heapq 
import random
import math

warnings.filterwarnings("ignore", category=ConvergenceWarning)

class Rescuer(AbstAgent):
    def __init__(self, env, config_file):
        super().__init__(env, config_file)

        self.map = Map()            
        self.victims = {}           
        self.plan = []              
        self.plan_x = 0             
        self.plan_y = 0             
        self.plan_visited = set()   
        self.plan_rtime = self.TLIM 
        self.plan_walk_time = 0.0   
        self.x = 0                  
        self.y = 0                  
        self.explorers_remaining = {"EXP_1", "EXP_2", "EXP_3"} 
        self.rescuers = []          
                
        self.set_state(VS.IDLE)
        
        # Inicializa e treina o modelo de Classificação (CART)
        self.clf_model = DecisionTreeClassifier(
            random_state=111,
            criterion='gini',
            max_depth=3,
            min_samples_leaf=4,
            min_samples_split=2,
            class_weight='balanced'
        )
        self._train_classifier()

    def set_rescuers(self, rescuers_lst):
        self.rescuers = rescuers_lst
        
    def _train_classifier(self):
        """ Treina o modelo internamente com os dados do arquivo CSV fornecido """
        try:
            base_path = Path(__file__).parent
            dataset_train_path = base_path / "../datasets/vict/10v/data.csv"
            
            df = pd.read_csv(dataset_train_path)
            
            ignored_columns = ["gcs", "avpu", "sobr"]
            cols_to_remove = [col for col in ignored_columns if col in df.columns]
            df = df.drop(columns=cols_to_remove)
            
            X_train = df.drop(columns=["tri"])
            y_train = df["tri"]
            
            self.clf_model.fit(X_train, y_train)
            self.feature_names = X_train.columns.tolist()
            print(f"{self.NAME}: Classificador CART treinado e embarcado.")
        except Exception as e:
            print(f"{self.NAME}: Erro ao treinar CART. {e}")

    def calcula_custo_otimizado(self, sequencia, matriz_dist, pesos_sobr):
        """ Função de custo para a Têmpera Simulada """
        custo_total = 0.0
        distancia_acumulada = 0.0
        
        for i in range(len(sequencia)):
            id_atual = sequencia[i]
            if i > 0:
                id_anterior = sequencia[i-1]
                distancia_acumulada += matriz_dist[id_anterior][id_atual]
                
            custo_total += (distancia_acumulada * pesos_sobr[id_atual])
            
        return custo_total

    def tempera_simulada(self, sequencia_inicial, matriz_dist, pesos_sobr, temp_inicial=10000, resfriamento=0.9999, temp_final=0.1):
        """ Algoritmo de sequenciamento heurístico """
        sequencia_atual = sequencia_inicial.copy()
        custo_atual = self.calcula_custo_otimizado(sequencia_atual, matriz_dist, pesos_sobr)
        
        melhor_sequencia = sequencia_atual.copy()
        melhor_custo = custo_atual
        
        T = temp_inicial
        iteracoes = 0
        tamanho = len(sequencia_atual)
        
        if tamanho <= 1:
            return melhor_sequencia
            
        while T > temp_final:
            i, j = random.sample(range(tamanho), 2)
            vizinho = sequencia_atual.copy()
            vizinho[i], vizinho[j] = vizinho[j], vizinho[i]
            
            custo_vizinho = self.calcula_custo_otimizado(vizinho, matriz_dist, pesos_sobr)
            delta = custo_vizinho - custo_atual
            
            if delta < 0 or random.random() < math.exp(-delta / T):
                sequencia_atual = vizinho
                custo_atual = custo_vizinho
                
                if custo_atual < melhor_custo:
                    melhor_custo = custo_atual
                    melhor_sequencia = sequencia_atual.copy()
                    
            T *= resfriamento
            iteracoes += 1
            
        return melhor_sequencia

    def do_rescue(self, map, cluster_atribuido):
        self.set_state(VS.ACTIVE)
        self.map = map  
        
        print(f"{self.NAME}: Avaliando e classificando vítimas...")
        vitimas_avaliadas = []
        
        colunas_sinais = ['idade','fc','fr','pas','spo2','temp','pr','sg','fx','queim','gcs','avpu','tri','sobr']
        
        for victim_coord in cluster_atribuido:
            vital_signals = None
            for seq, data in self.victims.items():
                if data[0] == victim_coord:
                    vital_signals = data[1]
                    break
            
            if vital_signals is not None:
                df_sinais = pd.DataFrame([vital_signals], columns=colunas_sinais)
                df_features = df_sinais.drop(columns=[col for col in ['id', 'gcs', 'avpu'] if col in df_sinais.columns])
                
                try:
                    gravidade = self.clf_model.predict(df_features)[0]
                except Exception:
                    gravidade = 0
            else:
                gravidade = 0 
                
            vitimas_avaliadas.append({
                'coord': victim_coord,
                'gravidade': gravidade,
                'sinais': vital_signals
            })

        # =====================================================================
        # --- CÓDIGO DE SEQUENCIAMENTO (TÊMPERA SIMULADA) INTEGRADO ---
        if vitimas_avaliadas:
            print(f"{self.NAME}: Sequenciando rota com Têmpera Simulada...")
            
            # Ordenação inicial gulosa pelo 'sobr' (índice 13)
            vitimas_avaliadas.sort(key=lambda v: v['sinais'][13] if v['sinais'] else 1.0)
            
            tamanho_cluster = len(vitimas_avaliadas)
            pesos_sobr = {}
            matriz_dist = {i: {} for i in range(tamanho_cluster)}
            
            for i in range(tamanho_cluster):
                v_i = vitimas_avaliadas[i]
                sobr = v_i['sinais'][13] if v_i['sinais'] else 0.5
                pesos_sobr[i] = 1.0 - sobr 
                
                for j in range(tamanho_cluster):
                    if i == j:
                        matriz_dist[i][j] = 0.0
                    else:
                        v_j = vitimas_avaliadas[j]
                        x1, y1 = v_i['coord']
                        x2, y2 = v_j['coord']
                        # Distância Euclidiana base
                        matriz_dist[i][j] = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            
            sequencia_inicial = list(range(tamanho_cluster))
            sequencia_otimizada = self.tempera_simulada(sequencia_inicial, matriz_dist, pesos_sobr)
            
            # Traduz a sequência de índices de volta para coordenadas
            sequencia_vitimas = [vitimas_avaliadas[idx]['coord'] for idx in sequencia_otimizada]
        else:
            sequencia_vitimas = []
        # ---------------------------------------------------------------------

        print(f"{self.NAME}: Iniciando trajeto de socorro A* para {len(sequencia_vitimas)} vítimas...")
        # PLANEJAMENTO DE TRAJETÓRIA COM A*
        current_pos = (0, 0) 
        self.plan = []
        self.plan_rtime = self.TLIM
        
        for victim_coord in sequencia_vitimas:
            path_to_vict = self.a_star(current_pos, victim_coord)
            path_to_base = self.a_star(victim_coord, (0, 0)) 
            
            if not path_to_vict or not path_to_base:
                print(f"{self.NAME}: Destino {victim_coord} ou retorno inacessível. Ignorando.")
                continue
                
            ida_cost = self._calc_path_cost(current_pos, path_to_vict)
            volta_cost = self._calc_path_cost(victim_coord, path_to_base)
            first_aid_cost = self.COST_FIRST_AID
            
            if self.plan_rtime - ida_cost - first_aid_cost - volta_cost >= 0:
                self._add_path_to_plan(current_pos, path_to_vict, apply_first_aid_at_end=True)
                
                self.plan_rtime -= (ida_cost + first_aid_cost)
                current_pos = victim_coord
            else:
                print(f"{self.NAME}: Tempo insuficiente para salvar vítima em {victim_coord}. Abortando e retornando à base.")
                break 
        
        if current_pos != (0, 0):
            path_to_base = self.a_star(current_pos, (0, 0))
            if path_to_base:
                self._add_path_to_plan(current_pos, path_to_base, apply_first_aid_at_end=False)
                
        print(f"{self.NAME}: Planejamento finalizado. Ações calculadas: {len(self.plan)}")

    def a_star(self, start, goal):
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
                    if dx == 0 and dy == 0:
                        continue
                    
                    neighbor = (current[0] + dx, current[1] + dy)
                    
                    if neighbor not in self.map.map_data:
                        continue
                    
                    cell_data = self.map.map_data[neighbor]
                    difficulty = cell_data[0] 
                    
                    if difficulty == VS.OBST_WALL:
                        continue
                        
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
            diff = self.map.map_data[node][0]
            step_cost = self.COST_DIAG if (dx != 0 and dy != 0) else self.COST_LINE
            cost += step_cost * diff
            curr = node
        return cost

    def _add_path_to_plan(self, start, path, apply_first_aid_at_end=False):
        curr = start
        for i, node in enumerate(path):
            dx = node[0] - curr[0]
            dy = node[1] - curr[1]
            is_last = (i == len(path) - 1)
            has_vict = True if (is_last and apply_first_aid_at_end) else False
            self.plan.append((dx, dy, has_vict))
            curr = node

    def merge_maps(self, exp_name, map, victims):
        for coord, cell_data in map.map_data.items():  
            if not self.map.in_map(coord):
                difficulty, victim_seq, actions_res = cell_data
                self.map.add(coord, difficulty, victim_seq, actions_res)
    
        print(f"{self.NAME}: Map recebido de {exp_name}")

        self.victims.update(victims)
        self.explorers_remaining.discard(exp_name)

        if self.explorers_remaining:
            return
        
        self.map.draw()

        # =====================================================================
        # --- CÓDIGO DE CLUSTERING E ATRIBUIÇÃO AOS SOCORRISTAS ---
        print(f"{self.NAME}: Master executando DBSCAN (eps=0.70, min_samples=6)...")
        
        data = []
        seqs = []
        for seq, (coord, vitals) in self.victims.items():
            x_rel, y_rel = coord
            gcs = vitals[10]
            tri = vitals[12]
            data.append([x_rel, y_rel, tri, gcs])
            seqs.append(seq)
            
        df_cluster = pd.DataFrame(data, columns=['x_rel', 'y_rel', 'tri', 'gcs'])
        
        scaler = StandardScaler()
        normalized_data = scaler.fit_transform(df_cluster)
        
        dbscan = DBSCAN(eps=0.70, min_samples=6)
        df_cluster['cluster'] = dbscan.fit_predict(normalized_data)
        df_cluster['coord'] = [self.victims[s][0] for s in seqs]
        
        valid_clusters = [c for c in df_cluster['cluster'].unique() if c != -1]
        cluster_priorities = []
        for c_id in valid_clusters:
            mean_gcs = df_cluster[df_cluster['cluster'] == c_id]['gcs'].mean()
            cluster_priorities.append((c_id, mean_gcs))
            
        cluster_priorities.sort(key=lambda x: x[1]) 
        
        atribuicoes = [[] for _ in range(len(self.rescuers))]
        rescuer_idx = 0
        
        for priority_index, (c_id, mean_gcs) in enumerate(cluster_priorities):
            coords = df_cluster[df_cluster['cluster'] == c_id]['coord'].tolist()
            atribuicoes[rescuer_idx].extend(coords)
            rescuer_idx = (rescuer_idx + 1) % len(self.rescuers)
            
        noise_coords = df_cluster[df_cluster['cluster'] == -1]['coord'].tolist()
        for coord in noise_coords:
            atribuicoes[rescuer_idx].append(coord)
            rescuer_idx = (rescuer_idx + 1) % len(self.rescuers)
            
        print(f"{self.NAME}: Atribuição finalizada. Disparando socorristas...")
        # ---------------------------------------------------------------------

        for i in range(len(self.rescuers)):
            self.rescuers[i].do_rescue(self.map, atribuicoes[i])
            
        
    def deliberate(self) -> bool:
        if self.plan == []:  
           print(f"{self.NAME} retornou à base. Ações esgotadas.")
           return False

        dx, dy, there_is_vict = self.plan.pop(0)
        walked = self.walk(dx, dy)

        if walked == VS.EXECUTED:
            self.x += dx
            self.y += dy
            if there_is_vict:
                rescued = self.first_aid() 
                if rescued:
                    print(f"{self.NAME}: Vítima socorrida em ({self.x}, {self.y})")
                else:
                    print(f"{self.NAME}: Falha no plano - sem vítima em ({self.x}, {self.y})")
        else:
            print(f"{self.NAME}: Falha de colisão ou movimento em ({self.x}, {self.y})")
            
        return True