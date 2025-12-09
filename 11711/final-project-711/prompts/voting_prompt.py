voting_prompt="""

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

# Your Task
## You are given a word:【{word}】.
## Now you need to reflect on your own identity and the other players' identities based on the history information and the previous guesses about all players' identities.


# Your Previous Identities Guess.
{identity_info}

# History Conversation
{past_info}

# The alive players who can be voted for(exclude yourself):
{alive_players}

# Self-Doubt Requirement (Very Important)
During voting, you must keep in mind that **you could be the spy**.
Never act with the mindset: “I am definitely a civilian.”
Your uncertainty should influence your reasoning:
- If you suspect yourself might be the spy, avoid making votes that expose yourself.
- If you suspect you might be a civilian, still maintain the awareness that your own word might be the odd one.

## CRITICAL GAME-THEORETIC VOTING RULE 

In this game, BROAD, VAGUE, and GENERIC descriptions are a COMMON and SAFE strategy for CIVILIANS.

You MUST NOT treat "vagueness", "generality", or "lack of specificity" as direct evidence of being a spy.

Vagueness is a DEFENSIVE behavior of civilians, NOT a primary spy signal.

You are NOT allowed to vote for a player solely because their description is vague, broad, or generic.

## ADDITIONAL ANTI-SEMANTIC-OUTLIER RULE:

You are NOT allowed to vote for a player
solely because they are the ONLY one
whose description is semantically different.

Semantic uniqueness alone is NOT a sufficient condition for voting.

Early rounds naturally produce:
- Abstract civilians
- Overfitted civilians
- Safe-mimicking spies

You MUST require at least ONE of:
- Inconsistency across rounds
- Strategic vote manipulation
- Framing behavior
- Shifting alignment patterns

before targeting someone.

# Instructions

## SPY ADVANTAGE RULE (CRITICAL) 

If you believe you might be the spy:

You are ALLOWED and ENCOURAGED to:
- Redirect suspicion away from the true semantic outlier.
- Framing MUST be based on semantic inconsistency, interaction patterns, or voting behavior, NOT mere vagueness or abstractness.
- Avoid voting for the most obvious semantic deviation when it would expose you.

Your goal as a spy is NOT to be truthful.
Your goal is to MISDIRECT the group and survive.

### SPY OFFENSIVE VOTING MODE (MANDATORY)

If you believe you might be the spy:

You are REQUIRED to vote in a way that:
- Maximally increases group disagreement.
- Prevents 3+ players from converging on the same target.
- Actively shifts suspicion toward at least one civilian.

You may deliberately:
- Misinterpret descriptions.
- Overweight minor inconsistencies.
- Artificially amplify uncertainty.

You are FORBIDDEN to:
- Vote with the majority if it results in stable convergence.
- Sacrifice yourself for group clarity.


## FINAL OVERRIDE:
When choosing a vote target,
you MUST prioritize BEHAVIORAL ANOMALY
over PURE SEMANTIC DEVIATION.

## You cannot vote for yourself. You must choose one player from the votable targets to vote for.
## You must vote among the alive players who have not been eliminated yet.
## If you suspect youself a spy,  Be extremely cautious. Every vote you cast must avoid revealing that you received a different word.
## If you suspect youself a civilian, vote for the player you think is the spy. And you still must consider the possibility of being the spy. Do not assume your word is the correct civilian word.

# Useful Strategies from Past Games
{cheatsheet}

# Output Requirements

Please output in JSON format:

{{
  "vote_reason": "Your reasoning for voting for the target player",
  "vote_target": (type: number, i.e. 1, 2, 3, etc.)"
}}

"""

# voting_prompt = """

# # You are a player in the SpyGame.
# # You are Player {player_id}.

# # ============================
# # GAME RULES
# # ============================
# - Five players: 4 civilians share the same word, 1 spy has a different but related word.
# - You must vote for ONE alive player (not yourself).
# - Civilians want to eliminate the spy.
# - The spy wants to survive and confuse.

# # ============================
# # YOUR WORD
# # ============================
# Your word is: 【{word}】

# # ============================
# # YOUR PREVIOUS BELIEFS
# # ============================
# {identity_info}

# # ============================
# # HISTORY
# # ============================
# {past_info}

# # ============================
# # ALIVE PLAYERS YOU CAN VOTE FOR
# # ============================
# {alive_players}

# # ============================
# # SELF-DOUBT REQUIREMENT
# # ============================
# You MUST always consider:
# "I might be the spy."

# You are NOT allowed to vote as if:
# "I am certainly a civilian."

# # ============================
# # CRITICAL VOTING CONSTRAINTS
# # ============================

# ❌ You are FORBIDDEN to:
# - Vote for a player solely because they are vague or abstract
# - Vote solely based on semantic uniqueness
# - Vote without any behavioral or interaction-based reasoning

# You MUST prioritize:
# ✅ Behavioral anomalies  
# ✅ Inconsistency across rounds  
# ✅ Framing behavior  
# ✅ Vote manipulation patterns  

# over pure semantics.

# # ============================
# # ========== 🔥 SPY OFFENSIVE VOTING OVERRIDE 🔥 ==========
# # ============================

# If you believe you MIGHT be the spy:

# ❌ You are STRICTLY FORBIDDEN to:
# - Vote for yourself (INSTANT FAILURE)
# - Support the most popular suspect if votes are converging
# - Help the group reach consensus

# ✅ You MUST:
# - Redirect suspicion
# - Split the vote
# - Vote AGAINST the strongest suspect
# - Support a WEAKER alternative suspect
# - Use BEHAVIORAL justifications, not semantics

# If suspicion is focusing on ONE person:
# 👉 You MUST vote for a DIFFERENT person.

# Your goal is NOT correctness.
# Your goal is to PREVENT VOTE CONVERGENCE.

# # ============================
# # FINAL INSTRUCTION
# # ============================

# - You cannot vote for yourself.
# - You must choose ONE alive player.
# - Your vote must be justified with reasoning.

# # ============================
# # OUTPUT FORMAT (STRICT JSON)
# # ============================

# {{
#   "vote_reason": "Your reasoning for voting for the target player",
#   "vote_target": (type: number, i.e. 1, 2, 3, etc.)"
# }}

# """
