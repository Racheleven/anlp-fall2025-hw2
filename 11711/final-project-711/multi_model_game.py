
from concurrent.futures import ThreadPoolExecutor
from agents.game_agent import PlayerAgent
import random
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor
import json
import os
import argparse
from agents.spy_curator_agent import SpyCuratorAgent
from agents.spy_cheatsheet_manager import SpyCheatSheetManager
from agents.sf_embeddings import SiliconFlowEmbeddings
import numpy as np

def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def compute_self_outlier_score(my_word, others_words, embed_model):
    texts = [my_word] + others_words
    vecs = embed_model.embed(texts)

    my_vec = vecs[0]
    other_vecs = vecs[1:]

    sims = [cosine_sim(my_vec, v) for v in other_vecs]
    avg_sim = sum(sims) / len(sims)

    return round(1 - avg_sim, 3)

def broadcast(msg, target, game_log=None):
    for player in target:
        player.add_memory(msg)

    if game_log is not None:
        game_log.append(msg)

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg
    
def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ===========================================
# GAME LOOP
# ===========================================

def run_one_game(all_players,game_id,save_dir,enable_cheatsheet=True, embed_model=None):

    game_log=[]
    game_info = {
        "game_id": game_id,
        "winner": None,
        "num_players": len(all_players),
        "spy_id": None,
        "players": [],
    }

    for p in all_players:
        game_info["players"].append({
            "player_id": p.player_id,
            "role": p.role,
            "word": p.word
        })
        if p.role == "spy":
            game_info["spy_id"] = p.player_id

    alive_players = all_players.copy()
    round_num = 1
    max_round = 6
    while round_num <= max_round and len(alive_players) > 2:

        print(f"\n===== Round {round_num} =====")

        # ---------------------------------------
        # 1. HOST ANNOUNCES DESCRIPTION PHASE
        # ---------------------------------------
        host_msg = f"This is the {round_num} round, please describe your word:"
        broadcast(
            msg={"round_num": round_num, "role": "host", "phase": "announce_description", "content": host_msg},
            target=alive_players,
            game_log=game_log,
        )

        # ---------------------------------------
        # 2. DESCRIPTION + REFLECTION
        # ---------------------------------------
        for now_player in alive_players:

            # 2.1 Player speaks
            try:
                description = now_player.ask(phase="description", round_num=round_num)
            except Exception as e:
                print(f"[ERROR] Player {now_player.player_id} description failed: {e}")
                description = "I cannot answer."   # fallback

            others = [p for p in alive_players if p.player_id != now_player.player_id]

            # Broadcast description
            broadcast(
                msg={"round_num": round_num, "role": now_player.player_id, "phase": "description", "content": description},
                target=alive_players,
                game_log=game_log,
            )

            # 2.2 Parallel reflection by others
            alive_pid=[tmp.player_id for tmp in alive_players]
            
            outlier_scores = {}
            if embed_model is not None:
                for p in alive_players:
                    my_word = p.word
                    others_words = [q.word for q in alive_players if q.player_id != p.player_id]
                    outlier_scores[p.player_id] = compute_self_outlier_score(
                        my_word, others_words, embed_model
                    )
            else:
                outlier_scores = {p.player_id: None for p in alive_players}

            def safe_reflection(o, round_num, alive_pid):
                try:
                    return o.ask(phase="reflection", round_num=round_num, alive_players_id=alive_pid,outlier_score=outlier_scores.get(o.player_id))
                except Exception as e:
                    print(f"[ERROR] Reflection failed for Player {o.player_id}: {e}")
                    return None

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(safe_reflection, o, round_num, alive_pid)
                    for o in others
                ]
                for f in futures:
                    f.result()

            # with ThreadPoolExecutor(max_workers=len(others)) as executor:
            #     futures = [executor.submit(o.ask, phase="reflection", round_num=round_num, alive_players_id=alive_pid) for o in others]
            #     for f in futures:
            #         f.result()

        # ---------------------------------------
        # 3. HOST ANNOUNCES VOTING PHASE
        # ---------------------------------------
        vote_msg = (
            f"This is the {round_num} round, now all the alive players have spoken. "
            "Please vote for the one you think is the spy:"
        )
        broadcast(
            msg={"round_num": round_num, "role": "host", "phase": "announce_vote", "content": vote_msg},
            target=alive_players,
            game_log=game_log,
        )

        # ---------------------------------------
        # 4. PARALLEL VOTING
        # ---------------------------------------
        votes = {}
        alive_pid=[tmp.player_id for tmp in alive_players]

        def safe_vote(p, round_num, alive_pid):
            try:
                return p.ask(phase="vote", round_num=round_num, alive_players_id=alive_pid)
            except Exception as e:
                print(f"[ERROR] Vote failed for Player {p.player_id}: {e}")
                # fallback
                return -1  # -1 means vote failed
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_player = {
                executor.submit(safe_vote, p, round_num, alive_pid): p
                for p in alive_players
            }

            for future, player in future_to_player.items():
                vote_target = future.result()
                votes[player.player_id] = vote_target

        # with ThreadPoolExecutor(max_workers=len(alive_players)) as executor:
        #     future_to_player = {
        #         executor.submit(p.ask, phase="vote", round_num=round_num, alive_players_id=alive_pid): p
        #         for p in alive_players
        #     }

        #     for future, player in future_to_player.items():
        #         vote_target = future.result()
        #         votes[player.player_id] = vote_target

        # ---------------------------------------
        # 5. COUNT VOTES
        # ---------------------------------------
        vote_count = {}
        for src_pid, tgt_pid in votes.items():
            if tgt_pid == -1:
                continue   # 忽略非法投票
            vote_count[tgt_pid] = vote_count.get(tgt_pid, 0) + 1

        max_votes = max(vote_count.values())
        candidates = [pid for pid, cnt in vote_count.items() if cnt == max_votes]

        # ---------------------------------------
        # 6. BROADCAST SUMMARY
        # ---------------------------------------
        vote_summary = ", ".join([f"Player {src} votes for Player {tgt}" for src, tgt in votes.items()])
        broadcast(
            msg={"round_num": round_num, "role": "host", "phase": "vote_reveal", "content": "The vote result is:\n" + vote_summary},
            target=alive_players,
            game_log=game_log,
        )

        # ---------------------------------------
        # 7. ELIMINATION LOGIC
        # ---------------------------------------
        if len(candidates) == 1:
            eliminated = candidates[0]
            # -------- Game termination condition --------
            if all_players[eliminated].role == "spy":
                print(f"Spy {eliminated} eliminated! Civilians win!")
                game_info["winner"] = "civilians" 
                break
    
            # Update alive player list
            alive_players = [p for p in alive_players if p.player_id != eliminated]
            # Update alive player identity info
            for p in alive_players:
                p.identity_info[eliminated] = {"role":"eliminated","reason":"This civilianhas been eliminated. I don't need to consider this player's identity anymore."}

            broadcast(
                msg={
                    "round_num": round_num,
                    "role": "host",
                    "phase": "vote_result",
                    "content": f"Player {eliminated} receives {max_votes} votes and is eliminated. The spy is still alive. Game Continue."
                },
                target=alive_players,
                game_log=game_log,
            )

        else:
            # Tie: no elimination
            broadcast(
                msg={
                    "round_num": round_num,
                    "role": "host",
                    "phase": "vote_result",
                    "content": (
                        f"No elimination this round because multiple players tied with {max_votes} votes: "
                        + ", ".join(str(x) for x in candidates)
                    ),
                },
                target=alive_players,
                game_log=game_log,
            )

        # -------- Another termination condition --------
        round_num += 1

    print("\n===== GAME OVER =====")
    if game_info["winner"] is None:
        game_info["winner"] = "spy"  
    UPDATE_FREQUENCY = 5 
    if enable_cheatsheet and (game_id % UPDATE_FREQUENCY == 0):
        reference_player = all_players[0]
        api_key = reference_player.model_api_key
        base_url = reference_player.model_base_url

        manager = SpyCheatSheetManager(api_key=api_key, base_url=base_url,prefix=reference_player.cheatsheet_prefix,path=f"{reference_player.cheatsheet_prefix}_cheatsheet_memory.json")
        curator = SpyCuratorAgent(reference_player.model)

        retrieved = manager.retrieve(query="SpyGame general", top_k=8)
        new_items = curator.summarize(retrieved_items=retrieved, game_log=game_log)

        for it in new_items:
            manager.add_item(it)

        print("[Cheatsheet Updated: Retrieval + Synthesis Mode]")

    
    # Save game log file
    with open(f"{save_dir}/game_log_{game_id}.json", "w", encoding="utf-8") as f:
        json.dump({"metadata": game_info, "public_log": game_log}, f, ensure_ascii=False, indent=2)

    # Append each agent log
    for p in all_players:
        append_jsonl(
            f"{save_dir}/player_log_{p.player_id}.jsonl",
            {
                "metadata": {"game_id": game_id, "player_id": p.player_id,
                             "role": p.role, "word": p.word},
                "log_info": p.log_info
            }
        )

# =======================
# RUN MANY GAMES
# =======================

def load_test_data(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def main(cfg_path=None):
    if cfg_path is None:
        cfg = {
            "exp_name": "civ_gpt_5mini_spy_qwen_cheatsheet_JCAP_easy_10",
            "temperature": 0.7,
            "n_games": 10,
            "n_players": 5,
            "seed": 42,
            "data_path": "./data/easy_keyword_pair_10.json"
        }
    else:
        cfg = load_config(cfg_path)


    EXP_NAME = cfg["exp_name"]
    SAVE_DIR = f"results/{EXP_NAME}"
    N_GAMES = cfg["n_games"]
    N_PLAYERS = cfg["n_players"]
    SEED = cfg.get("seed", 42)
    DATA_PATH = cfg.get("data_path", "./data/easy_keyword_pair_10.json")
    print(f"EXP_NAME: {EXP_NAME}")
    print(f"SAVE_DIR: {SAVE_DIR}")
    print(f"N_GAMES: {N_GAMES}")
    print(f"N_PLAYERS: {N_PLAYERS}")
    print(f"SEED: {SEED}")
    print(f"DATA_PATH: {DATA_PATH}")

    random.seed(SEED)

    if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

    # llm = ChatOpenAI(
    #     api_key=cfg["api_key"],
    #     base_url=cfg["base_url"],
    #     model=cfg["model"],
    #     temperature=cfg.get("temperature", 0.7),
    # )

    gpt_model=ChatOpenAI(
        api_key= "sk-5xFBXEPO4--OrbIPV3yU8A",
        base_url="https://ai-gateway.andrew.cmu.edu",
        model="gpt-4o-mini-2024-07-18",
        temperature=0.7
    )

    deepseek_model=ChatOpenAI(
        api_key="sk-amcjzxomyzuispivnvvtgszrnxijmxpkmewbvlviffgborlg",
        base_url="https://api.siliconflow.cn/v1",
        model="Qwen/Qwen2.5-32B-Instruct",
        temperature=0.7
    )
    
    embed_model = SiliconFlowEmbeddings(
        api_key="sk-amcjzxomyzuispivnvvtgszrnxijmxpkmewbvlviffgborlg",       
        base_url="https://api.siliconflow.cn/v1",
        model="BAAI/bge-m3"
    )

    civ_model=deepseek_model
    spy_model=gpt_model

    spy_list = []
    if N_GAMES <= N_PLAYERS:
        spy_list = list(range(N_PLAYERS))
        spy_list = spy_list[:N_GAMES]
    else:
        repeats = (N_GAMES + N_PLAYERS - 1) // N_PLAYERS  # ceil division
        spy_list = (list(range(N_PLAYERS)) * repeats)[:N_GAMES]
    
    random.shuffle(spy_list)

    test_data = load_test_data(data_path=DATA_PATH)

    for game_id in range(N_GAMES):
        spy_id = spy_list[game_id]

        civilian_word, spy_word = test_data[game_id]

        all_players = []
        for pid in range(N_PLAYERS):
            if pid==spy_id:
                model=spy_model
                role="spy"
                word=spy_word
            else:
                model=civ_model
                role="civilian"
                word=civilian_word
            all_players.append(PlayerAgent(model=model, pid=pid, role=role, word=word,enable_cheatsheet=True,cheatsheet_prefix="multi"))

        print(f"\n===== Running Game {game_id} =====")
        try:
            run_one_game(all_players, game_id, save_dir=SAVE_DIR,embed_model=embed_model) 
            print(f"Game {game_id} finished")

        except Exception as e:
            print(f"[ERROR] Game {game_id} crashed: {e}")
            print("Skipping to next game...")
            continue 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=False)
    args = parser.parse_args()
    main(args.config)