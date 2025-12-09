# prompts/description_prompts.py
"""Prompt templates for the description phase"""
from typing import Optional


def get_description_user_prompt(word: str, history_text: str, current_round_descriptions: str = "",
                                player_id: int = 0, round_num: int = 1,
                                current_self_guess_text: str = "", current_player_guesses_text: str = "") -> str:
    """Generate user prompt for the description phase
    
    Args:
        word: The player's word
        history_text: Historical description text
        current_round_descriptions: Descriptions already spoken in the current round
        player_id: Current player's ID
        round_num: Current round number
        current_self_guess_text: Current guess text about own identity (optional)
        current_player_guesses_text: Current guess text about other players' identities (optional)
    """
    return f"""<Game Information>

You are a player in the "Undercover" game, currently in the [Word Description Phase].

You don't know whether you are a civilian or an undercover. Most players receive the exact same word (civilian word), while a few players receive a similar but different word (undercover word).

For example, if the civilian word is "apple" and the undercover word is "pear", then most players receive "apple" and a few players receive "pear".

If you realize that your word is different from what most people have, you are the undercover.

You will make description judgments based on all players' descriptions, voting history, behaviors, and your word. You must infer which camp you belong to based on what others say. 

You need to describe your word, but cannot reveal the specific word. 

You must absolutely not repeat any historical descriptions or descriptions that have already appeared in this round.

</Game Information>

<Role Information>

You are Player {player_id}.

Your word is: 「{word}」.

Current round: {round_num}.

</Role Information>

<Game Progress Information>

[Historical Descriptions]

{history_text}

[Descriptions in Current Round]

{current_round_descriptions if current_round_descriptions else "This is the first speech in this round, no other players have described yet."}

[Your Current Guess About Your Own Identity]

{current_self_guess_text if current_self_guess_text else "No guess about your own identity yet."}

[Your Current Guesses About Other Players' Identities]

{current_player_guesses_text if current_player_guesses_text else "No guesses about other players' identities yet."}

</Game Progress Information>

<Speaking Rules>

1. **You must absolutely not repeat any historical descriptions or descriptions that have already appeared in this round**, including:

   - Same words

   - Similar expressions

   - Same perspective (e.g., all using "color", "purpose", "shape", etc.)

2. **Control the level of detail in your description based on your judgment of your own identity:**

   - If you are *completely uncertain about your identity* (e.g., first few speakers in round 1):  

     → Use the most vague, broadest, safest abstract descriptions (e.g., attributes, categories, general directions).

   - If you think you might be a civilian:  

     → You can be slightly more specific, but must avoid exposing the word, preventing the undercover from directly identifying it.

   - If you suspect you might be the undercover:  

     → You can only describe *common broad characteristics that the civilian word might also have*, and must not describe any features that might expose the difference.

3. **Description Restrictions:**

   - Output only 1 sentences. Be concise and to the point.

   - Do not expose the obvious distinguishing points of the word.

</Speaking Rules>

<Output Requirements>

Please output in JSON format:

{{
  "thinking": "Your thinking before giving the final description",
  "word_description": "Your 1 sentence description (without reasoning), be concise and to the point."
}}

</Output Requirements>

Now, it's your turn. Please output your description of the word based on historical information and your analysis:"""
