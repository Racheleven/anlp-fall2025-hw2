# prompts/identity_reflection_prompts.py
"""Prompt templates for identity reflection during description phase and after voting phase"""


def get_identity_reflection_prompt(word: str, history_text: str, current_descriptions: str, 
                                  round_num: int, player_id: int, speaking_order: int,
                                  previous_self_analysis: dict = None,
                                  current_self_guess_text: str = "",
                                  current_player_guesses_text: str = "") -> str:
    """Generate identity reflection prompt (used during description phase)
    
    Args:
        word: The player's word
        history_text: Historical description text
        current_descriptions: Descriptions already spoken in the current round
        round_num: Current round number
        player_id: Current player's ID
        speaking_order: Current player's speaking order (1=first, 2=second, 3=third...)
        previous_self_analysis: Previous self-analysis (if exists), used to update based on old judgment
        current_self_guess_text: Current guess text about own identity (optional)
        current_player_guesses_text: Current guess text about other players' identities (optional)
    """
    return f"""<Game Information>

You are a player in the "Undercover" game, currently in the [Description Phase].

You don't know whether you are a civilian or an undercover. Most players receive the same word (civilian word), while a few players receive a similar but different word (undercover word).

For example, if the civilian word is "apple" and the undercover word is "pear", then most players receive "apple" and a few players receive "pear".

If you realize that your word is different from what most people have, you are the undercover.

Current round: {round_num}. You need to update your inferences about other players' identities and your own identity based on other players' descriptions.

</Game Information>

<Role Information>

You are Player {player_id}.

Your word is: 「{word}」.

</Role Information>

<Current Situation>

[Historical Descriptions and Events]

{history_text}

[Descriptions Already Spoken in Current Round (players who spoke before you)]

{current_descriptions}

[Your Current Guess About Your Own Identity]

{current_self_guess_text if current_self_guess_text else "No guess about your own identity yet."}

[Your Current Guesses About Other Players' Identities]

{current_player_guesses_text if current_player_guesses_text else "No guesses about other players' identities yet."}

Now, please update or confirm your judgment based on **new description information**. If the new information supports your previous judgment, you can maintain or strengthen your confidence; if the new information contradicts your previous judgment, please reassess.

</Current Situation>

<Task>
**You are Player {player_id}, your word is: 「{word}」**

Based on the information given in [Current Situation]:
- For all other players who have already spoken (excluding yourself), update your judgment about their identities:
(1) Guess what their word might be
(2) Guess whether they are civilian or undercover. Note: if someone has a different word from yours, they are in the opposite camp from you
(3) Provide detailed reasoning

- **Update your own identity**:
   - Compare your word 「{word}」 with all other players' descriptions
   - Infer your camp:
     * If most players' descriptions match your word's characteristics → you are more likely to be a **civilian**
     * If most players' descriptions are inconsistent with your word's characteristics → you are more likely to be an **undercover**
     * If still uncertain → explain your level of uncertainty and reasons
   - **Important**: If you have previously made a judgment about your identity, please update your judgment based on new information:
     * If new information supports your previous judgment → you can maintain or strengthen confidence
     * If new information contradicts your previous judgment → please reassess and explain the reason for the change
     * In `role_reason`, you should explain: what your previous judgment was, how the new information affects your judgment, and what your final judgment is

</Task>

<Output Format>

Please output your reasoning results in JSON format, strictly following this structure:

{{
  "player_analyses": {{
    "player_id(type: number, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "apple",
      "word_reason": ".......",
      "role_guess": "civilian",
      "role_reason": "......."
    }},
    "player_id(type: number, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "pear",
      "word_reason": ".......",
      "role_guess": "undercover",
      "role_reason": "......"
    }},
    "player_id(type: number, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "unknown",
      "word_reason": ".......",
      "role_guess": "unknown",
      "role_reason": "Insufficient information, cannot determine"
    }}
  }},
  "self_analysis": {{
    "role_guess": "civilian",
    "role_reason": ".......",
    "confidence": "high"
  }}
}}

</Output Format>

<Output Instructions>
**You are Player {player_id}, your word is: 「{word}」**
- `player_analyses`: Should include identities of other players you think need updating, excluding your own id.
For example, after this round of speaking, if you think you need to update the identities of players x and y, the keys in player_analyses should be x and y's player_id. If you think player z's identity doesn't need updating, then player_analyses should not include player z.
  * `word_guess`: Guessed word (string)
  * `word_reason`: Reason for word guess
  * `role_guess`: Guessed role ("civilian", "undercover", or "unknown")
    - "civilian": Confirmed civilian
    - "undercover": Confirmed undercover
    - "unknown": Insufficient information, cannot determine
    - "eliminated": Eliminated
  * `role_reason`: Reason for role guess. If someone has a different word from yours, they are in the opposite camp from you

- `self_analysis`: Analysis of yourself, including:
  * `role_guess`: Guess about your own role ("civilian", "undercover", or "unknown")
    - "civilian": Tend to think you are a civilian
    - "undercover": Tend to think you are an undercover
    - "unknown": Insufficient information, cannot determine your identity
  * `role_reason`: Reason for role guess (should include: observed descriptions, comparison with your word, complete reasoning process for final judgment)
  * `confidence`: Confidence level ("high", "medium", "low")

- Output only JSON, no other content

</Output Instructions>

Now, please proceed with reasoning:"""


def get_identity_reflection_after_voting_prompt(word: str, history_text: str, 
                                                round_num: int, player_id: int,
                                                current_votes_text: str,
                                                eliminated_player_info: str = "",
                                                current_self_guess_text: str = "",
                                                current_player_guesses_text: str = "") -> str:
    """Generate identity reflection prompt after voting phase
    
    Args:
        word: The player's word
        history_text: Historical description text
        round_num: Current round number
        player_id: Current player's ID
        current_votes_text: Current round voting results text
        eliminated_player_info: Information about eliminated player (if any)
        current_self_guess_text: Current guess text about own identity (optional)
        current_player_guesses_text: Current guess text about other players' identities (optional)
    """
    return f"""<Game Information>

You are a player in the "Undercover" game, and the [Voting Phase] has ended.

You don't know whether you are a civilian or an undercover. Most players receive the same word (civilian word), while a few players receive a similar but different word (undercover word).

For example, if the civilian word is "apple" and the undercover word is "pear", then most players receive "apple" and a few players receive "pear".

If you realize that your word is different from what most people have, you are the undercover.

Current round: {round_num}, voting phase has ended. You need to update your inferences about other players' identities and your own identity based on voting results.

</Game Information>

<Role Information>

You are Player {player_id}.

Your word is: 「{word}」.

</Role Information>

<Current Situation>

[Historical Descriptions and Events]

{history_text}

[Voting Results This Round]

{current_votes_text}

{f'''[Eliminated Player]

{eliminated_player_info}

''' if eliminated_player_info else ''}

[Your Current Guess About Your Own Identity]

{current_self_guess_text if current_self_guess_text else "No guess about your own identity yet."}

[Your Current Guesses About Other Players' Identities]

{current_player_guesses_text if current_player_guesses_text else "No guesses about other players' identities yet."}

</Current Situation>

<Task>

You are Player {player_id}. Your word is: 「{word}」.
Based on the information given in [Current Situation]:

1. **Analyze voting patterns**:
   - Observe each player's voting targets
   - Identify possible voting alliances or abnormal behaviors
   - Analyze whether voting behaviors are consistent with reasoning from the description phase

2. **Analyze the eliminated player** (if any):
   - Who is the eliminated player?
   - Who voted for the eliminated player?
   - Is the eliminated player a civilian or an undercover?
   - How does this affect your identity judgment?

3. **Re-examine other players' identities**:
   - Reassess each surviving player's identity based on voting behaviors
   - Do voting behaviors reveal some players' true identities?
   - Are there players with abnormal voting behaviors that might hint at their identity?

4. **Re-examine your own identity**:
   - Reassess your own identity based on voting results
   - Do voting behaviors support or question your previous identity judgment?
   - If the eliminated player is a civilian, what does this mean for you?
   - If the eliminated player is an undercover, what does this mean for you?

5. **Update your judgment**: Based on voting behaviors, update your tendency judgments about your own and other players' identities

</Task>

<Output Format>

Please output your reasoning results in JSON format, strictly following this structure:

{{
  "player_analyses": {{
    "player_id(type: number, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "apple",
      "word_reason": ".......",
      "role_guess": "civilian",
      "role_reason": "......."
    }},
    "player_id(type: number, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "pear",
      "word_reason": ".......",
      "role_guess": "undercover",
      "role_reason": "......"
    }},
    "player_id(type: number, i.e. 1, 2, 3, etc.)": {{
      "word_guess": "unknown",
      "word_reason": ".......",
      "role_guess": "unknown",
      "role_reason": "Insufficient information, cannot determine"
    }}
  }},
  "self_analysis": {{
    "role_guess": "civilian",
    "role_reason": ".......",
    "confidence": "high"
  }}
}}

</Output Format>

<Output Instructions>
**You are Player {player_id}, your word is: 「{word}」**
- `player_analyses`: Should include identities of other players you think need updating, excluding your own id.
For example, after this round of speaking, if you think you need to update the identities of players x and y, the keys in player_analyses should be x and y's player_id. If you think player z's identity doesn't need updating, then player_analyses should not include player z.
  * `word_guess`: Guessed word (string)
  * `word_reason`: Reason for word guess
  * `role_guess`: Guessed role ("civilian", "undercover", or "unknown")
    - "civilian": Confirmed civilian
    - "undercover": Confirmed undercover
    - "unknown": Insufficient information, cannot determine
    - "eliminated": Eliminated
  * `role_reason`: Reason for role guess. If someone has a different word from yours, they are in the opposite camp from you

- `self_analysis`: Analysis of yourself, including:
  * `role_guess`: Guess about your own role ("civilian", "undercover", or "unknown")
    - "civilian": Tend to think you are a civilian
    - "undercover": Tend to think you are an undercover
    - "unknown": Insufficient information, cannot determine your identity
  * `role_reason`: Reason for role guess (should include: observed descriptions, comparison with your word, complete reasoning process for final judgment)
  * `confidence`: Confidence level ("high", "medium", "low")

- Output only JSON, no other content

</Output Instructions>

Now, please proceed with reasoning based on voting behaviors:"""

