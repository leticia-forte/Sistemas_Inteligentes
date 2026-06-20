# Documentação sobre o environment

## Indexação do Grid 2D

O ambiente (`Env`) utiliza uma **grade bidimensional (grid)** 
Isso significa que as coordenadas são pares (x, y) tal que x indica uma **coluna** e y uma **linha**.  

- A **posição (0,0)** está localizada no **canto superior esquerdo** da janela.
- O eixo **x** cresce da **esquerda para a direita**.
- O eixo **y** cresce de **cima para baixo**.

Essa convenção é usada tanto na leitura dos arquivos de configuração (`env_obst.txt`, `env_victims.txt`) quanto na renderização do ambiente com o `pygame`.

---

## Estados Possíveis de um Agente

Os estados dos agentes são definidos por constantes no módulo `VS` (`constants.py`).  
O método do simulador (`Env.run`) realiza as transições de estados automaticamente:

| Estado | Descrição | Transição para |
|--------|------------|----------------|
| `IDLE` | Agente está pronto, mas ainda não começou a deliberar. | → `ACTIVE` quando o simulador chama `deliberate()` pela primeira vez. |
| `ACTIVE` | Agente está deliberando e executando ações. | → `DEAD` se o tempo (`rtime`) se esgota. <br>→ `ENDED` se o agente termina e está na base. <br>→ `DEAD` se o agente termina mas **não** está na base. |
| `ENDED` | Agente finalizou sua missão e está na base. | Estado final. |
| `DEAD` | Agente ficou sem tempo ou tentou terminar fora da base. | Estado final. |

Fluxo simplificado das transições:

```
IDLE → ACTIVE → ENDED
             ↘
              DEAD
```

---

## 📊 Estatísticas Geradas pelo Simulador

O simulador gera duas categorias principais de estatísticas, controladas pelos parâmetros `STATS_PER_AG` e `STATS_ALL_AG`:

### 1. Estatísticas por Agente (`print_results()`)

Para cada agente, são apresentadas:
- **Tempo consumido** (`TLIM - rtime`), rtime significa tempo remanescente
- **Vítimas encontradas** (por triagem e probabilidade de sobrevivência)
- **Vítimas salvas** (idem)
- Percentuais de vítimas encontradas por categoria de gravidade (`Green`, `Yellow`, `Red`, `Black`)
- Veg são as vítimas encontradas por ponderadas por categoria de tri
- Vsg são as vítimas socorridas por ponderadas categoria de tri

### 2. Estatísticas Acumuladas (`print_acum_results()`)

Consolida os resultados de **todos os agentes**:
- Número total de vítimas por categoria de tri (`Green`, `Yellow`, `Red`, `Black`)
- Soma total das probabilidades de sobrevivência (`SSOBR`)
- Vítimas encontradas e salvas por todos os agentes
- Percentuais e totais ponderados
- Versão em formato CSV para exportação dos dados

---
