##  RESCUER AGENT
### @Author: Tacla (UTFPR)
### Modificado para a Tarefa 5: Trajetória de Socorro (A*), ML e Clustering

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
            print(f"{self.NAME}: Classificador CART treinado e embarcado com sucesso.")
        except Exception as e:
            print(f"{self.NAME}: Erro ao treinar classificador CART. Verifique o caminho. {e}")

    def do_rescue(self, map, cluster_atribuido):
        self.set_state(VS.ACTIVE)
        self.map = map  
        
        print(f"{self.NAME}: Planejando socorro via A*...")

        # =====================================================================
        # --- CÓDIGO DE CLASSIFICAÇÃO INTEGRADO ---
        print(f"{self.NAME}: Classificando a gravidade das vítimas do cluster atribuído...")
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
                except Exception as e:
                    print(f"{self.NAME}: Erro na predição: {e}. Assumindo gravidade 0.")
                    gravidade = 0
            else:
                gravidade = 0 
                
            vitimas_avaliadas.append({
                'coord': victim_coord,
                'gravidade': gravidade,
                'sinais': vital_signals
            })
        # ---------------------------------------------------------------------

        # =====================================================================
        # --- INSIRA AQUI O SEU CÓDIGO DE SEQUENCIAMENTO ---
        # Utilize a lista dicionário 'vitimas_avaliadas' recém-criada (que possui a 'gravidade')
        # para ordenar sua fila.
        
        sequencia_vitimas = [v['coord'] for v in vitimas_avaliadas] # Substitua pela ordenação real
        
        # ---------------------------------------------------------------------

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
                print(f"{self.NAME}: Tempo insuficiente para salvar vítima em {victim_coord}. Retornando à base.")
                break 
        
        if current_pos != (0, 0):
            path_to_base = self.a_star(current_pos, (0, 0))
            if path_to_base:
                self._add_path_to_plan(current_pos, path_to_base, apply_first_aid_at_end=False)
                
        print(f"{self.NAME}: Planejamento finalizado. Ações planejadas: {len(self.plan)}")

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
    
        print(f"{self.NAME}: Map received from explorer {exp_name}")

        self.victims.update(victims)
        self.explorers_remaining.discard(exp_name)

        if self.explorers_remaining:
            print(f"{self.NAME}: Waiting for remaining explorers... {self.explorers_remaining}")
            return
        
        self.map.draw()

        # =====================================================================
        # --- CÓDIGO DE CLUSTERING E ATRIBUIÇÃO AOS SOCORRISTAS ---
        print(f"{self.NAME}: Executando DBSCAN (eps=0.70, min_samples=6)...")
        
        data = []
        seqs = []
        # Extrai features: x_rel, y_rel, tri, gcs (índices 12 e 10 de vital_signals)
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
        
        # Ordena clusters pela média de GCS para criar prioridade
        valid_clusters = [c for c in df_cluster['cluster'].unique() if c != -1]
        cluster_priorities = []
        for c_id in valid_clusters:
            mean_gcs = df_cluster[df_cluster['cluster'] == c_id]['gcs'].mean()
            cluster_priorities.append((c_id, mean_gcs))
            
        # Menor GCS = Maior Prioridade
        cluster_priorities.sort(key=lambda x: x[1]) 
        
        # Atribuição: Round-Robin baseada na prioridade do cluster
        atribuicoes = [[] for _ in range(len(self.rescuers))]
        rescuer_idx = 0
        
        for priority_index, (c_id, mean_gcs) in enumerate(cluster_priorities):
            coords = df_cluster[df_cluster['cluster'] == c_id]['coord'].tolist()
            atribuicoes[rescuer_idx].extend(coords)
            rescuer_idx = (rescuer_idx + 1) % len(self.rescuers)
            
        # Trata as vítimas rotuladas como ruído (-1), distribuindo-as
        noise_coords = df_cluster[df_cluster['cluster'] == -1]['coord'].tolist()
        for coord in noise_coords:
            atribuicoes[rescuer_idx].append(coord)
            rescuer_idx = (rescuer_idx + 1) % len(self.rescuers)
            
        print(f"{self.NAME}: Clustering finalizado. {len(valid_clusters)} clusters válidos encontrados + {len(noise_coords)} ruídos.")
        # ---------------------------------------------------------------------

        #####################
        ### SEND CLUSTERS ###
        #####################
        for i in range(len(self.rescuers)):
            self.rescuers[i].do_rescue(self.map, atribuicoes[i])
            
        
    def deliberate(self) -> bool:
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