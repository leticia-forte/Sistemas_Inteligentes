import os

# importa classes
from vs.environment import Env
from exp import Explorer
from soc import Rescuer


def main(vict_folder, env_folder, config_ag_folder):
    # Instantiate the environment
    env = Env(vict_folder, env_folder)

    # config files for the agents
    cfg_exp = []   # arquivos de cfg dos exploradores
    cfg_soc = []   # arquivos de cfg dos socorristas
    exp = []       # agentes exploradores
    soc = []       # agentes socorristas
    
    for i in range(3):
        cfg_exp.append(os.path.join(config_ag_folder, f"exp_{i+1}.txt"))
        cfg_soc.append(os.path.join(config_ag_folder, f"soc_{i+1}.txt"))
        
        # instancia um socorrista e salva na lista
        soc.append(Rescuer(env, cfg_soc[i]))
        
        # exploradores precisam conhecer o socorrista mestre (0) 
        # para enviarem o mapa de exploração
        exp.append(Explorer(env, cfg_exp[i], soc[0]))
        
    # os socorristas precisam se conhecer para executar a estratégia de
    # socorro
    for i in range(3):
        soc[i].set_rescuers(soc)
        
    env.run()


if __name__ == '__main__':
    print("------------------")
    print("--- INICIO SMA ---")
    print("------------------")
    # dataset com sinais vitais das vitimas
    grid_str = "94x94"
    vict_str = "408v"
    vict_folder = os.path.join(".", "datasets/vict/", vict_str)

    # dataset do ambiente (paredes, posicao das vitimas)
    env_folder = path = os.path.join(".", "datasets", "env", f"{grid_str}_{vict_str}")

    # folder das configuracoes dos agentes
    curr = os.getcwd()
    config_ag_folder = os.path.join(curr, "cfg")

    main(vict_folder, env_folder, config_ag_folder)
