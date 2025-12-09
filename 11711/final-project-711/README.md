# Game Project
## Keyword Pair Difficulty Partitioning

We construct difficulty-controlled keyword pair datasets using a semantic similarity pipeline implemented in `partition_dataset.py`.

Starting from the original `key_word_pair.json` containing 600 keyword pairs, the pipeline works as follows:

1. **LLM-based Description Generation**  
   For each word in every pair, GPT is used to generate a concise 2–3 sentence semantic description that captures:
   - Core meaning  
   - Typical usage  
   - Distinguishing characteristics  

2. **Embedding Transformation**  
   Each description is converted into a vector embedding using the `BAAI/bge-m3` embedding model via the SiliconFlow API.

3. **Cosine Similarity Scoring**  
   For each keyword pair, cosine similarity is computed between the two description embeddings.  
   A higher cosine similarity indicates that the two words are more semantically similar and thus harder to distinguish in the SpyGame.

4. **Difficulty Ranking and Splitting**
   All 600 keyword pairs are sorted by cosine similarity (from high to low) and split into:
   - `hard_keyword_pair_200.json` (Top 200, highest similarity)
   - `medium_keyword_pair_200.json` (Middle 200)
   - `easy_keyword_pair_200.json` (Bottom 200, lowest similarity)

5. **Random Subsampling**
   To support small-scale experiments, we further generate:
   - `easy_keyword_pair_50.json`: random subset from Easy-200
   - `easy_keyword_pair_10.json`: random subset from Easy-200

6. **Category-Specific Datasets**
   We also provide manually curated category datasets:
   - `key_word_pair_food.json`
   - `key_word_pair_animal.json`  
   These are used for domain-specific controlled experiments.

This pipeline enables systematic difficulty control over the SpyGame evaluation benchmark.

## Usage

You can run the game scripts directly:

```bash
python single_model_game.py
```

```bash
python multi_model_game.py
```
Both ```single_model_game.py``` and ```multi_model_game.py``` support an optional Dynamic Cheatsheet mechanism for the spy.

To control whether the cheatsheet is used:

Disable cheatsheet (default logic):
Set:
```bash
enable_cheatsheet=False
```

when creating ```PlayerAgent```.

Enable cheatsheet (Dynamic Cheatsheet Learning Mode):
Set:
```bash
enable_cheatsheet=True
```

For example, inside both game scripts, modify the ```PlayerAgent``` initialization:
```bash
all_players.append(
    PlayerAgent(
        model=llm,
        pid=pid,
        role=role,
        word=word,
        enable_cheatsheet=True    # or False
    )
)
```

When ```enable_cheatsheet=True```:
the spy will retrieve and update heuristics using ```SpyCheatSheetManager``` and ```SpyCuratorAgent```.

When ```enable_cheatsheet=False```:
the game runs normally without cheatsheet assistance.

## Other Experiment Configuration

- **`exp_name`**  
  Controls the experiment folder name under:
  ```bash
  results/{exp_name}

- **`data_path`** 
Specifies which keyword pair dataset is used, for example:

    ./data/easy_keyword_pair_10.json
    ./data/medium_keyword_pair_200.json
    ./data/key_word_pair_food.json

- **`n_games`** 
Controls the number of games executed in batch evaluation.
