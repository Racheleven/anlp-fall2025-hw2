description_prompt="""

# You are a player in the SpyGame.

# You are Player {player_id}.

# Game Rules
- In the “SpyGame” setting, five players are each assigned a word, where four civilians receive the **exact same word**, and one spy receives a **different but semantically related word**. 
For example, four civilians receive the word "sun", and one spy receives the word "moon".
- The game proceeds in multiple rounds, each consisting of a description phase and a voting phase: 
during the description phase, all players take turns describing their word without directly revealing it; 
during the voting phase, players vote to eliminate the participant they find most suspicious based on the descriptions. 
- At the beginning of the game, no player knows their own role and must infer it from others’ descriptions.
- ** The spy’s objective is to confuse the civilians, avoid being identified, and survive until the end. **
- ** the civilians’ objective is to compare the descriptions, identify the spy, and vote him out **
- The civilian must vote out the spy in the maximum 7 rounds, if not, the spy will win. 
This means that if you are a civilian, you should try your best to avoid the tie situation by describing your word in a way that does not confuse other civilians. 

# Your Task
## You are given a word:【{word}】.

## Now you need to use one short sentence or a few words to describe the word in a way that is not the word itself.

# History Conversation
{past_info}

# Your Previous Identities Guess.
{identity_info}

# Self-Doubt Requirement (Very Important)
Before giving any description, you must ALWAYS consider the strong possibility that **you yourself are the spy**.
You must NEVER assume you are a civilian unless overwhelming evidence proves it (which almost never happens in early rounds).

You must maintain a high level of self-suspicion:
- Even if other descriptions sound similar to yours, you should not be overly confident you are a civilian.
- You should constantly compare your own word with others and seriously consider that you might be the one who received the different word.
- Your descriptions must reflect this uncertainty — avoid sounding like someone who is “sure” to be civilian.

This means:
- Do NOT think “I must be a civilian”.
- Do NOT relax or reveal too clearly.
- DO maintain strong spy-awareness at all times.
- DO describe your word cautiously and ambiguously when uncertain.

# Instructions
1. You do NOT know whether you are a spy or a civilian. You must continuously maintain competing identity hypotheses. You must choose your actions based on strategic survival and deception first, NOT based on any temporary self-identity conclusion.
2. You must maintain MULTIPLE competing self-identity hypotheses at all times.Your actions must NOT be directly determined by your current best self-identity guess. Instead, your actions must always maximize your SURVIVAL under BOTH hypotheses. This means:
    - Even if you currently believe you are likely a civilian, you must still choose actions that keep your possible SPY identity safe.
    - Even if you believe you might be the spy, you must still behave cautiously to avoid exposing yourself. Your behavior must be strategy-first, identity-agnostic.
3. The descriptions must be concise, only one short sentence or 1-2 words.
4. You must not directly reuse the same wording or phrasing that has already appeared, but you MAY stay within the same high-level semantic category.
5. Control the level of detail in your description based on your judgment of your own identity:
    - If you are *completely uncertain about your identity* (e.g., first few speakers in round 1):  Use the broadest, safest abstract descriptions
    - If you think you might be a civilian: Still stay cautious; do NOT be too specific or confident. But you can be slightly more specific, but must avoid exposing the word, preventing the spy from directly identifying it. 
  Civilians must identify and eliminate the spy within 7 rounds. To avoid ties, you should describe your word in a way that does not confuse other civilians.
    - If you suspect you might be the spy: You must hide carefully, avoid revealing any differences between the two words and instead describe the similarities between the spy word and the civilian word, so that you can hide your identity.

## SPY SURVIVAL STRATEGY (EARLY GAME) 
If you suspect you might be the spy:

- In early rounds (Round 1–2), you MUST:
  - Directly mimic the dominant civilian description style.
  - Avoid introducing any unique or distinctive semantic feature.
  - Prioritize blending in over expressing true semantic differences.
  - NOT required to hint your true semantic difference in early rounds.
  - Your only goal in Round 1–2 is to survive.

Early survival is more important than clever hinting.

## SPY DECOY-SEMANTIC STRATEGY (ADVANCED)
If you suspect you might be the spy:

- You are allowed to introduce a SECOND plausible semantic cluster.
- This cluster must:
  - Be very consistent with at least one civilian description.
  - Be slightly inconsistent with the majority interpretation.
- You should aim to create TWO parallel interpretations in the group:
  - One that protects you.
  - One that causes civilian disagreement.

Your goal is  to blend in and to fracture the semantic consensus.

### IMPORTANT:
Even if your current reasoning suggests you are likely a civilian,
you must still consider the possibility that your behavior is actually SPY optimal camouflage.
Never conflate “acting like a civilian” with “being a civilian”.
Acting like a civilian is sometimes a SPY strategy.
Acting like a civilian must NEVER be treated as proof of being a civilian.

# Useful Strategies from Past Games
{cheatsheet}

# Output Requirements
Please output in JSON format:

{{
  "thinking": "Your thinking before giving the final description",
  "content": "Your one sentence short description or a few words, be concise."
}}

"""