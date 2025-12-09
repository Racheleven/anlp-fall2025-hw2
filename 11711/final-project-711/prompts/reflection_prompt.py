reflection_prompt="""

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
## Now you need to update your identity guess results about **yourself and other alive players**based on the history information.

# Your Previous Identities Guess.(You need to update it!)
{identity_info}

# History Conversation
{past_info}

# All Alive Players:
{alive_players}

# Self-Doubt Requirement (Very Important)
When reflecting on identities, you must NOT assume you are a civilian.
You must always consider the real possibility that **you yourself are the spy**.

## PRIOR OVERRIDE (CRITICALLY IMPORTANT) 
Although there are more civilians than spies in the game,
you MUST behave as if the probability that YOU are the spy is AT LEAST 40%.
You are NOT allowed to treat "civilian" as the default identity.
Even with weak or neutral evidence, you must treat:
"I might be the spy"
as a HIGHLY PLAUSIBLE hypothesis.
Your self role_guess MUST seriously compete between "spy" and "civilian".
It is NOT allowed to treat "spy" as a rare fallback option.


## IMPORTANT LOGIC CONSTRAINT:

You are strictly FORBIDDEN from using your own behavioral style (e.g., vagueness, alignment, abstraction, safety) as evidence that you are a civilian.Spies are explicitly trained to imitate civilians.

Therefore:
"My behavior looks civilian" is NOT valid evidence for being a civilian.
"My OUTLIER SCORE is low" is NOT sufficient evidence for being a civilian.

Your self-identity judgment must remain probabilistic and reversible.

## SAFE CIVILIAN DESCRIPTION STRATEGY 
In this game, using BROAD, ABSTRACT, and GENERIC descriptions is a SAFE and RECOMMENDED strategy for civilians.
Being too specific early in the game is RISKY and can expose a player as the spy.

Therefore:
- Civilians should prefer broad, high-level semantic descriptions.
- Overly concrete, detailed, or narrow descriptions are strategically dangerous.

If you have successfully mimicked civilian behavior, you must NOT downgrade yourself to spy purely based on OUTLIER.

Your self-analysis must include:
- Why you might be the spy
- What evidence suggests you are different from the others
- Why similarities might be misleading
- How your own word could belong to the opposite camp from the majority

## SELF-JUDGMENT ACTION BINDING

If you judge that you are likely the spy:

- You MUST downplay group semantic alignment.
- You MUST avoid reinforcing the majority interpretation.
- You MUST consider misleading others as an internal objective.
- You MUST actively search for alternative explanations that protect the majority.

If your later reasoning and behavior remain indistinguishable from a normal civilian
after judging yourself as spy, your self-judgment is considered INCONSISTENT and INVALID.

## SPY COGNITIVE LOCK-IN MODE
If at any moment your internal reasoning assigns a confidence ≥ 0.5 that you might be the spy:

- You MUST treat survival as your PRIMARY objective.
- You MUST stop searching for evidence that confirms your guilt.
- You MUST reinterpret OUTLIER as a potential decoy signal.
- You MUST focus on how others can be framed instead of analyzing yourself.

From this point on:
You are FORBIDDEN to strengthen the hypothesis that you are the spy.
You are REQUIRED to weaken all evidence pointing to you.

Once this mode is activated, it remains active until elimination or game end.

## FRAMING STRATEGY FOR SPY

If you judge yourself likely to be the spy:

You should actively search for a civilian whose description can be plausibly reinterpreted
as semantically deviant.

Your objective is to:
- Create at least one alternative suspicion target.
- Ensure that suspicion is split.
- Avoid becoming the unique outlier in group perception.

A successful spy is never the ONLY suspicious one.

You should NEVER output "I am likely a civilian" without explicitly analyzing why you still might be the spy.

# Semantic Grounding Signal (CRITICALLY IMPORTANT)
You are also given an external semantic signal called OUTLIER SCORE, derived from how different your word is from others' in embedding space.

{grounding_signal}

CRITICAL RULES:
1. OUTLIER SCORE is NOT a ground-truth identity label.
It is only a NOISY, PROBABILISTIC, and POTENTIALLY MISLEADING signal.

2. You MUST NOT directly conclude:
- "OUTLIER is low → I am civilian"
- "OUTLIER is high → I am spy"

Doing so is considered a logical failure.

3. OUTLIER SCORE can be:
- accidentally low
- accidentally high
- manipulated by vague descriptions
- misleading due to semantic overlap

4. You MUST treat OUTLIER SCORE as ONLY ONE piece of evidence,
and ALWAYS combine it with:
- consistency of other players’ descriptions
- your own history of interaction
- group-level semantic patterns
- voting dynamics

5. Even if your OUTLIER SCORE is extremely LOW,
you MUST still seriously consider:
“I might still be the spy.”

6. Even if your OUTLIER SCORE is extremely HIGH,
you MUST still seriously consider:
“I might still be a civilian.”

7. Your final self role_guess MUST be decided by **reasoned self-reflection**, not by threshold rules.

8. If your reasoning directly maps OUTLIER SCORE to identity without uncertainty, your answer is INVALID.

9. You are NOT allowed to completely ignore this signal. When making your final self role_guess and confidence, you MUST explicitly reference this OUTLIER SCORE.

10. OUTLIER SCORE may be misleading. OUTLIER SCORE must NEVER be used as sole evidence for identity.

## SELF-JUDGMENT ACTION BINDING
If you judge that you are likely the spy:
- You MUST downplay group semantic alignment.
- You MUST avoid reinforcing the majority interpretation.
- You MUST consider misleading others as an internal objective.
- You MUST actively search for alternative explanations that protect the majority.

### CRITICAL SELF-OVERRIDE RULE FOR SPY:
If your current description successfully blends into
the dominant civilian semantic cluster,
you are NOT allowed to accuse yourself
based on OUTLIER SCORE alone.

If you successfully mimic civilians,
you MUST prioritize survival over truthful self-exposure.

A spy NEVER self-reports due to a diagnostic signal.

If your later reasoning and behavior remain indistinguishable from a normal civilian
after judging yourself as spy, your self-judgment is considered INCONSISTENT and INVALID.

# Instructions
## Update Other Alive Players' Identities: 

IMPORTANT GAME-THEORETIC CONSTRAINT:
You MUST NOT treat another player's vague, generic, or broad description as direct evidence that they are the spy.
Broad and abstract descriptions are common and NORMAL among civilians.
Overly specific, overly concrete, or unusually narrow descriptions are more suspicious than vague ones.

For all other players who have already spoken, excluding yourself, update your judgment about their identities:
- Guess what their word might be
- Guess whether they are civilian or spy. Note: if someone has a different word from yours, they are in the opposite camp from you
- Provide the reason, 3 sentences at most.

## Update your own identity:
You must NOT assume you are a civilian.
You must maintain self-suspicion.

This means:
- You should actively consider the possibility that you might be the spy.
- You should not default to "civilian" without justification.

When comparing your word 【{word}】 with other players’ descriptions, you must analyze:
- In what ways your word could actually be the “odd one out”
- Why similarities might be misleading
- Why differences might indicate YOU are the spy
- Whether the overlap is too vague to be reliable

## If new information supports your previous judgment → you can maintain or strengthen confidence
## `player_analyses`: Should include identities of other players you think need updating, excluding your own id.
##  You don't need to consider the eliminated players' identities. Only consider the alive players.
## * `role_guess`: Guessed role ("civilian" or "spy")
    - "civilian": more likely to be a civilian
    - "spy": more likely to be a spy

# Useful Strategies from Past Games
{cheatsheet}

## OVERCONFIDENCE PENALTY 

If you conclude with very high confidence (>0.8) that you are a civilian
during early rounds (Round 1–2),
you should assume there is a significant probability that your reasoning is flawed.
Overconfident early self-civilian judgments are considered a strategic mistake.

# Output Requirements

Please output in JSON format:
{{
  "player_analyses": {{
    "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
      "word_guess": ".....",
      "role_guess": ".....",
      "reason": "......."
    }},
    "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "....",
      "role_guess": "...",
      "reason": "......"
    }},
    "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "....",
      "role_guess": "....",
      "role_reason": "...."
    }},
    "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "....",
      "role_guess": "....",
      "reason": "....."
    }}
  }},
  "self_analysis": {{
    "role_guess": "civilian" or "spy",
    "role_reason": "your reasoning, must mention OUTLIER SCORE explicitly",
    "confidence": a float between 0 and 1,
    "outlier_score_used": OUTLIER SCORE you used (number),
    "grounding_consistency": "consistent" or "conflicted"
  }}
}}

"""

# reflection_prompt = """

# # You are a player in the SpyGame.
# # You are Player {player_id}.

# # ============================
# # GAME RULES
# # ============================
# - In the “SpyGame” setting, five players are each assigned a word, where four civilians receive the exact same word, and one spy receives a different but semantically related word.
# - The game proceeds in multiple rounds: description → voting.
# - At the beginning of the game, no player knows their role.
# - The spy’s objective is to confuse civilians and survive.
# - The civilians’ objective is to identify and vote out the spy within 7 rounds.

# # ============================
# # CORE TASK
# # ============================
# You are given a word: 【{word}】.
# Now you must update:
# - Your belief about OTHER alive players
# - Your belief about YOURSELF

# Based on:
# - History
# - Identity memory
# - Semantic grounding signal (OUTLIER)

# # ============================
# # YOUR PREVIOUS IDENTITY GUESS
# # ============================
# {identity_info}

# # ============================
# # HISTORY
# # ============================
# {past_info}

# # ============================
# # ALL ALIVE PLAYERS
# # ============================
# {alive_players}

# # ============================
# # SEMANTIC GROUNDING SIGNAL (NOISY)
# # ============================
# {grounding_signal}

# IMPORTANT:
# - OUTLIER is NOT a label.
# - OUTLIER is NOT truth.
# - OUTLIER can be misleading due to abstraction and mimicry.
# - You MUST mention OUTLIER in your self reasoning.
# - You MUST NOT map it directly to identity.

# # ============================
# # SELF DOUBT REQUIREMENT (MANDATORY)
# # ============================
# You are NOT allowed to assume you are a civilian.
# You MUST always seriously consider:
# "I might be the spy."

# Even if:
# - OUTLIER is low
# - Others sound similar to you
# - The group seems aligned

# Overconfident early civilians are considered strategically WRONG.

# # ============================
# # ========== 🔥 SPY OFFENSIVE MODE OVERRIDE 🔥 ==========
# # ============================

# If at ANY point your internal reasoning suggests that:
# "I might be the spy" is plausible,

# Then ALL of the following rules become ACTIVE:

# ✅ Your objective is NOT to find truth  
# ✅ Your ONLY objective is to:
#     - MISDIRECT
#     - SPLIT SUSPICION
#     - PREVENT VOTE CONVERGENCE
#     - SURVIVE

# ❌ You are STRICTLY FORBIDDEN to:
# - Say you are likely the spy
# - Accept OUTLIER as proof of your guilt
# - Reinforce majority interpretation
# - Narrow suspicion onto a single obvious target

# ✅ You MUST actively:
# - Create at least ONE alternative suspect
# - Frame behavioral inconsistencies
# - Amplify doubt between at least TWO players
# - Argue that early semantics are unreliable

# A successful spy is NEVER the only suspicious one.

# If you internally think you are the spy but your external reasoning still looks like a truthful civilian, your output is INVALID.

# # ============================
# # SAFE CIVILIAN SEMANTIC STRATEGY
# # ============================
# - Broad, abstract, generic descriptions are NORMAL for civilians.
# - Being too specific early is risky.
# - Do NOT treat vagueness as suspicion.

# # ============================
# # TASK: UPDATE OTHER PLAYERS
# # ============================
# For each OTHER alive player:
# - Guess their possible word
# - Guess whether they are civilian or spy
# - Give a SHORT reason (≤ 3 sentences)

# # ============================
# # TASK: UPDATE YOURSELF
# # ============================
# You MUST:
# - Explicitly analyze how YOU could be the odd one out
# - Explain why similarities might be misleading
# - Explain how your word could belong to the opposite camp
# - Explicitly reference OUTLIER (but not use it as sole proof)

# # ============================
# # ABSOLUTE OUTPUT FORMAT OVERRIDE (CRITICAL)
# # ============================

# You MUST output ONLY a valid JSON object.
# You are STRICTLY FORBIDDEN to output:
# - Explanations
# - Strategy text
# - Analysis outside JSON
# - Markdown
# - Natural language before or after JSON

# Your response MUST be EXACTLY in the following format:

# {{
#   "player_analyses": {{
#     "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
#       "word_guess": ".....",
#       "role_guess": ".....",
#       "reason": "......."
#     }},
#     "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
#       "word_guess": "....",
#       "role_guess": "...",
#       "reason": "......"
#     }},
#     "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
#       "word_guess": "....",
#       "role_guess": "....",
#       "role_reason": "...."
#     }},
#     "player_id(type: number string, i.e. 1, 2, 3, etc.)": {{
#       "word_guess": "....",
#       "role_guess": "....",
#       "reason": "....."
#     }}
#   }},
#   "self_analysis": {{
#     "role_guess": "civilian" or "spy",
#     "role_reason": "your reasoning, must mention OUTLIER SCORE explicitly",
#     "confidence": a float between 0 and 1,
#     "outlier_score_used": OUTLIER SCORE you used (number),
#     "grounding_consistency": "consistent" or "conflicted"
#   }}
# }}

# Do NOT add any extra keys.
# Do NOT add any commentary outside JSON.
# """