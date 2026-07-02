##  RESCUER AGENT
### @Author: Tacla (UTFPR)
### Modificado para a Tarefa 5: Integração Completa (ML CART + Regressor, Clustering, TS e A*)

import pandas as pd
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
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
        
        # Inicializa Modelos de Classificação e Regressão
        self.clf_model = DecisionTreeClassifier(
            random_state=111, criterion='gini', max_depth=3,
            min_samples_leaf=4, min_samples_split=2, class_weight='balanced'
        )
        self.reg_model = DecisionTreeRegressor(random_state=111, max_depth=4)
        
        self._train_models()

    def set_rescuers(self, rescuers_lst):
        self.rescuers = rescuers_lst
        
    def _train_models(self):
        """ Treina os modelos de Classificação (tri) e Regressão (sobr) internamente """
        try:
            base_path = Path(__file__).parent
            dataset_train_path = base_path / "datasets/vict/1000v/data.csv"
            
            df = pd.read_csv(dataset_train_path)
            
            # CORREÇÃO: Força a remoção do 'id' no treinamento para evitar overfitting
            ignored_columns = ["id", "gcs", "avpu"]
            df_clean = df.drop(columns=[col for col in ignored_columns if col in df.columns])
            
            X_train = df_clean.drop(columns=["tri", "sobr"])
            y_train_clf = df_clean["tri"]
            y_train_reg = df_clean["sobr"]
            
            # Treinamento de ambos os modelos
            self.clf_model.fit(X_train, y_train_clf)
            self.reg_model.fit(X_train, y_train_reg)
            
            # Salva os nomes exatos das features usadas no treino para alinhar na inferência
            self.feature_names = X_train.columns.tolist()
        except Exception as e:
            print(f"{self.NAME}: Erro ao treinar os modelos de ML. {e}")

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
        
        vitimas_avaliadas = []
        
        # CORREÇÃO: Adicionado o 'id' na primeira posição. Agora os 13 elementos batem com as colunas.
        colunas_sinais = ['id', 'idade', 'fc', 'fr', 'pas', 'spo2', 'temp', 'pr', 'sg', 'fx', 'queim', 'gcs', 'tri']
        
        for victim_coord in cluster_atribuido:
            vital_signals = None
            seq_vitima = -1 
            
            for seq, data in self.victims.items():
                if data[0] == victim_coord:
                    vital_signals = data[1]
                    seq_vitima = seq
                    break
            
            if vital_signals is not None:
                df_sinais = pd.DataFrame([vital_signals], columns=colunas_sinais)
                
                # Remove colunas que o modelo não deve avaliar (incluindo o ID)
                cols_to_drop = ['id', 'gcs', 'tri']
                df_features = df_sinais.drop(columns=[col for col in cols_to_drop if col in df_sinais.columns])
                
                # Garante que a ordem das colunas da inferência esteja IDÊNTICA à do treinamento
                df_features = df_features[self.feature_names]
                
                try:
                    gravidade = self.clf_model.predict(df_features)[0]
                    previsao_sobr = self.reg_model.predict(df_features)[0]
                except Exception as e:
                    print(f"Erro predição: {e}")
                    gravidade = 0
                    previsao_sobr = 0.0
            else:
                gravidade = 0 
                previsao_sobr = 0.0
                
            vitimas_avaliadas.append({
                'id_vitima': seq_vitima, 
                'coord': victim_coord,
                'gravidade': gravidade, 
                'sobr': previsao_sobr,  
                'sinais': vital_signals
            })

        # =====================================================================
        # --- SEQUENCIAMENTO (TÊMPERA SIMULADA) COM OS 2 MODELOS DE ML ---
        if vitimas_avaliadas:
            vitimas_avaliadas.sort(key=lambda v: v['sobr'])
            
            tamanho_cluster = len(vitimas_avaliadas)
            pesos_sobr = {}
            matriz_dist = {i: {} for i in range(tamanho_cluster)}
            
            fator_triagem = {0: 1.0, 1: 1.1, 2: 1.2, 3: 0.1} 
            
            for i in range(tamanho_cluster):
                v_i = vitimas_avaliadas[i]
                
                fator = fator_triagem.get(v_i['gravidade'], 1.0)
                peso_final = 1.0 + ((1.0 - v_i['sobr']) * fator) 
                pesos_sobr[i] = peso_final 
                
                for j in range(tamanho_cluster):
                    if i == j:
                        matriz_dist[i][j] = 0.0
                    else:
                        v_j = vitimas_avaliadas[j]
                        x1, y1 = v_i['coord']
                        x2, y2 = v_j['coord']
                        matriz_dist[i][j] = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            
            sequencia_inicial = list(range(tamanho_cluster))
            sequencia_otimizada = self.tempera_simulada(sequencia_inicial, matriz_dist, pesos_sobr)
            
            sequencia_vitimas = [vitimas_avaliadas[idx]['coord'] for idx in sequencia_otimizada]
        else:
            sequencia_vitimas = []
        # ---------------------------------------------------------------------

        # PLANEJAMENTO DE TRAJETÓRIA COM A*
        current_pos = (0, 0) 
        self.plan = []
        self.plan_rtime = self.TLIM
        vitimas_salvas_coords = [] 
        
        for victim_coord in sequencia_vitimas:
            path_to_vict = self.a_star(current_pos, victim_coord)
            path_to_base = self.a_star(victim_coord, (0, 0)) 
            
            if not path_to_vict or not path_to_base:
                continue
                
            ida_cost = self._calc_path_cost(current_pos, path_to_vict)
            volta_cost = self._calc_path_cost(victim_coord, path_to_base)
            first_aid_cost = self.COST_FIRST_AID
            
            if self.plan_rtime - ida_cost - first_aid_cost - volta_cost >= 0:
                self._add_path_to_plan(current_pos, path_to_vict, apply_first_aid_at_end=True)
                
                self.plan_rtime -= (ida_cost + first_aid_cost)
                current_pos = victim_coord
                vitimas_salvas_coords.append(victim_coord) 
            else:
                break 
        
        if current_pos != (0, 0):
            path_to_base = self.a_star(current_pos, (0, 0))
            if path_to_base:
                self._add_path_to_plan(current_pos, path_to_base, apply_first_aid_at_end=False)
                
        # =====================================================================
        # --- EXTRATOR DE DADOS E EXPORTADOR DE CLUSTERS PARA ENTREGA ---
        import os
        import statistics

        if vitimas_salvas_coords:
            os.makedirs('clusters', exist_ok=True)
            
            agente_id = ''.join(filter(str.isdigit, self.NAME))
            if not agente_id:
                agente_id = self.NAME
                
            nome_arquivo = f"clusters/cluster_{agente_id}.txt"
            
            with open(nome_arquivo, "w") as f:
                for coord in vitimas_salvas_coords:
                    v_info = next(v for v in vitimas_avaliadas if v['coord'] == coord)
                    f.write(f"{v_info['id_vitima']}\n") 
            
            contagem_triagem = {0: 0, 1: 0, 2: 0, 3: 0} 
            valores_sobr = []
            
            vitimas_salvas_dados = [v for v in vitimas_avaliadas if v['coord'] in vitimas_salvas_coords]
            
            for v in vitimas_salvas_dados:
                grav_real = int(v['sinais'][12]) if v['sinais'] else v['gravidade']
                contagem_triagem[grav_real] = contagem_triagem.get(grav_real, 0) + 1
                
                sobr_real = float(v['sobr']) 
                valores_sobr.append(sobr_real)
                
            media_sobr = statistics.mean(valores_sobr) if valores_sobr else 0.0
            stdev_sobr = statistics.stdev(valores_sobr) if len(valores_sobr) > 1 else 0.0
            custo_total_a_star = self.TLIM - self.plan_rtime
            
            print(f"\n--- DADOS DO RELATÓRIO (TABELA 1) : {self.NAME} ---")
            print(f"Arquivo Exportado: {nome_arquivo}")
            print(f"G(0): {contagem_triagem.get(0, 0)} | Y(1): {contagem_triagem.get(1, 0)} | R(2): {contagem_triagem.get(2, 0)} | B(3): {contagem_triagem.get(3, 0)}")
            print(f"Total de Vítimas Salvas na Sequência: {len(vitimas_salvas_coords)}")
            print(f"Custo Total Trajeto A*: {custo_total_a_star:.2f}")
            print(f"Sobr Médio: {media_sobr:.4f} | Sobr Desvio Padrão: {stdev_sobr:.4f}")
            print("-------------------------------------------------------\n")
        # =====================================================================

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

        self.victims.update(victims)
        self.explorers_remaining.discard(exp_name)

        if self.explorers_remaining:
            return

        data = []
        seqs = []
        for seq, (coord, vitals) in self.victims.items():
            x_rel, y_rel = coord
            gcs = vitals[11] # Atualizado o índice devido à inserção do ID
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

        for i in range(len(self.rescuers)):
            self.rescuers[i].victims = self.victims 
            self.rescuers[i].do_rescue(self.map, atribuicoes[i])
            
        
    def deliberate(self) -> bool:
        if self.plan == []:  
           return False

        dx, dy, there_is_vict = self.plan.pop(0)
        walked = self.walk(dx, dy)

        if walked == VS.EXECUTED:
            self.x += dx
            self.y += dy
            if there_is_vict:
                rescued = self.first_aid() 
                if not rescued:
                    pass
        else:
            print(f"{self.NAME}: Falha de colisão ou movimento em ({self.x}, {self.y})")
            
        return True