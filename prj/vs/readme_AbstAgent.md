# AbstAgent — Classe Abstrata de Agente

Esta classe abstrata define a estrutura básica e os métodos padrão para todos os agentes que operam em um ambiente de simulação.  
As classes concretas devem herdar desta classe e implementar o método `deliberate()`.

---

## Método Abstrato

### `deliberate() -> bool`
**Descrição:**  
Define o processo de tomada de decisão do agente para escolher a próxima ação.  
Este método é chamado pelo simulador a cada ciclo de raciocínio, **somente se o agente estiver ativo**.  
Cada deliberação deve executar **no máximo uma ação de movimento** (`walk`).

**Retornos:**
- `True` — Há uma ou mais ações a serem executadas.  
- `False` — Não há mais ações a serem executadas (o agente concluiu sua missão).

---

## Métodos Públicos

### `get_rtime() -> float`
**Descrição:**  
Retorna o tempo operacional restante (ou “bateria”) do agente.  
Quando o tempo restante é negativo, o agente é considerado **morto**.

**Retorna:**
- Tempo restante (`float`).

---

### `get_state()`
**Descrição:**  
Obtém o estado atual do agente (por exemplo, ativo, inativo ou morto).  
Os estados específicos dependem da implementação do ambiente de simulação.

**Retorna:**
- Estado atual (dependente da implementação).

---

### `set_state(value)`
**Descrição:**  
Atualiza o estado interno do agente.  
Normalmente é usado pelo ambiente para alterar o status do agente.

**Parâmetros:**
- `value` — Novo valor de estado a ser atribuído.

---

### `get_env()`
**Descrição:**  
Fornece acesso ao ambiente em que o agente está inserido.

**Retorna:**
- Referência para a instância do ambiente associada a este agente.

---

### `walk(dx: int, dy: int)`
**Descrição:**  
Move o corpo do agente uma célula na direção especificada, se possível.  
O movimento consome tempo e pode ser limitado por paredes ou bordas do grid.

**Parâmetros:**
- `dx` — Deslocamento no eixo x.  
- `dy` — Deslocamento no eixo y.

**Retornos:**
- `VS.BUMPED` — O agente colidiu com uma parede ou limite do grid.  
- `VS.TIME_EXCEEDED` — O agente não tinha tempo suficiente para se mover.  
- `VS.EXECUTED` — O movimento foi executado com sucesso.

---

### `check_walls_and_lim()`
**Descrição:**  
Verifica a presença de paredes e limites do grid nas posições ao redor do agente.

**Retorna:**
- Um vetor de oito inteiros indexado no sentido horário, começando pela posição acima do agente.  
  Cada posição do vetor pode conter:
  - `VS.CLEAR` — Não há obstáculo.  
  - `VS.WALL` — Há uma parede.  
  - `VS.END` — Fim do grid.

---

### `check_for_victim()`
**Descrição:**  
Verifica se há uma vítima na posição atual do agente.  
As vítimas são numeradas sequencialmente a partir de 0 (de acordo com os arquivos do ambiente).

**Retorna:**
- Número sequencial da vítima (`int`), ou  
- `VS.NO_VICTIM` se não houver vítima na posição atual.

---

### `read_vital_signals()`
**Descrição:**  
Lê os sinais vitais de uma vítima na mesma posição do agente.  
Cada tentativa consome tempo, mesmo que não haja vítima presente.

**Retornos:**
- `VS.TIME_EXCEEDED` — O agente não tinha tempo suficiente para realizar a leitura.  
- `list` — Lista de sinais vitais, se houver uma vítima presente.  
- `[]` — Lista vazia, se não houver vítima.

---

### `first_aid()`
**Descrição:**  
Entrega um kit de primeiros socorros à vítima na posição atual do agente.  
A ação consome tempo de operação.

**Retornos:**
- `VS.TIME_EXCEEDED` — O agente não tinha tempo suficiente para realizar a ação.  
- `True` — Kit de primeiros socorros entregue com sucesso.  
- `False` — Não há vítima na posição atual.

---

## 🧩 Observações
- Todos os métodos que interagem com o ambiente **consomem tempo operacional** (`TLIM`).  
- A classe `AbstAgent` é **abstrata** e deve ser herdada.  
- A configuração do agente (custos, cores, limite de tempo, etc.) é carregada a partir de um arquivo de configuração durante a inicialização.

