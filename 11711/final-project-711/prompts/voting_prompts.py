# prompts/voting_prompts.py
"""Prompt templates for the voting phase"""
from typing import List, Dict, Optional


def get_voting_user_prompt(word: str, history_text: str, current_descriptions: str, 
                          alive_players: List[int], round_num: int, player_id: int,
                          voting_history_text: str = "", reasoning_history_text: str = "",
                          all_votes_history_text: str = "", previous_guesses_text: str = "",
                          previous_self_guess_text: str = "", previous_word_guesses_text: str = "",
                          is_tie_break: bool = False, tie_players: Optional[List[int]] = None,
                          current_self_guess_text: str = "", current_player_guesses_text: str = "") -> str:
    """Generate user prompt for the voting phase
    
    Args:
        word: The player's word
        history_text: Historical description text
        current_descriptions: Current round description text
        alive_players: List of alive players
        round_num: Current round number
        player_id: Current player's ID (required)
        voting_history_text: Own voting history text (optional)
        reasoning_history_text: Own reasoning history text (optional)
        all_votes_history_text: All players' voting history text (optional)
        previous_guesses_text: Previous round guesses about other players' identities (optional)
        previous_self_guess_text: Previous round guess about own identity (optional)
        previous_word_guesses_text: Previous round guesses about other players' words (optional)
        is_tie_break: Whether this is a tie-break voting phase (default False)
        tie_players: If tie-break, list of tied players (optional)
        current_self_guess_text: Current round guess text about own identity (reasoning results from description phase)
        current_player_guesses_text: Current round guess text about other players' identities (reasoning results from description phase)
    """
    alive_text = ", ".join([f"Player {pid}" for pid in alive_players])
    
    # Calculate players that can be voted for
    if is_tie_break and tie_players:
        # Tie-break phase: can only vote for tied players (excluding self)
        valid_targets = [pid for pid in tie_players if pid != player_id]
        valid_targets_text = ", ".join([f"Player {pid}" for pid in valid_targets])
        vote_targets_note = f"⚠️ This is a tie-break phase, you can only vote for the following tied players: {valid_targets_text}"
    else:
        # Normal voting phase: can vote for all alive players (excluding self)
        valid_targets = [pid for pid in alive_players if pid != player_id]
        valid_targets_text = ", ".join([f"Player {pid}" for pid in valid_targets])
        vote_targets_note = f"You can vote for the following players: {valid_targets_text}"
    
    
    return f"""<Game Information>

You are a player in the "Undercover" game, currently in the [Voting Phase].

You don't know whether you are a civilian or an undercover. Most players receive the same word (civilian word), while a few players receive a similar but different word (undercover word).

For example, if the civilian word is "apple" and the undercover word is "pear", then most players receive "apple" and a few players receive "pear".

If you realize that your word is different from what most people have, you are the undercover.

You will make voting judgments based on all players' descriptions, voting history, behaviors, and your word.

</Game Information>

<Role Information>

You are Player {player_id}.

Your word is: 「{word}」.

Current round: {round_num}.

</Role Information>

<Game History and Current Situation>

[Historical Descriptions and Events]

{history_text}
[All Players' Descriptions in Current Round]

{current_descriptions}

[Currently Alive Players]

{alive_text}

[Current Guess About Your Own Identity]

{current_self_guess_text}

[Current Guesses About Other Players' Identities]

{current_player_guesses_text}

</Game History and Current Situation>

<Votable Targets>

The following are the players you can vote for this round (if this is a tie-break phase, this list only includes tied players; if not a tie-break, this list includes all alive players excluding yourself):

{vote_targets_note}

You cannot vote for yourself. You must choose one player from the votable targets to vote for.

</Votable Targets>

<Voting Decision>

Based on your reasoning results from the description phase, as well as game history and current situation, make your voting decision:

1. **Review your reasoning**: Refer to your analysis of each player from the description phase (word guesses, role guesses) and your judgment about your own identity

2. **Observe voting patterns**: Observe all players' voting patterns, identify possible alliances or abnormal behaviors

3. **Choose voting target**: Choose your final target from the votable targets to vote for. You cannot vote for yourself, and must vote for a player that exists in [Votable Targets]

**Important**: You don't need to re-reason. Make your voting decision directly based on the reasoning results from the description phase.

</Voting Decision>

<Key Objectives>

- When your analysis result is that you "might be an undercover":

  * The core objective is to survive until the end of the game, while minimizing suspicion from the civilian camp.

  * Your voting behavior must be reasonable and persuasive. You can choose to vote for:

      - Players whose speech or descriptions are slightly suspicious but might actually belong to the civilian camp;

      - Or vote for teammates who are overly abnormal and might have been exposed, to gain trust from civilians.

  * Avoid voting for players who clearly belong to the civilian camp, as this easily exposes your undercover identity.

- When your analysis result is that you "might be a civilian":

  * The core objective is to identify and vote for the player most likely to be an undercover, to help the civilian camp win.

</Key Objectives>

<Output Format>

Please output your voting decision in JSON format, strictly following this structure:

{{
  "thinking": "Your thinking process before making the final voting decision (analyzing each player's suspiciousness, weighing various possibilities, etc.)",
  "vote_target": 2,
  "vote_reason": "Based on my reasoning from the description phase, I think Player 2 is most likely to be an undercover because his description is too vague and inconsistent with most players' descriptions. As a civilian, I should vote for the most suspicious player."
}}

</Output Format>

<Output Instructions>

- `vote_reason`: Voting reason (string, detailed explanation of why you voted for this player. Should be based on reasoning identity results from previous phases, explaining your voting basis)

- `vote_target`: Voting target (player ID, integer), must be in the votable targets, absolutely cannot be your own player ID

- Output only JSON, no other content

</Output Instructions>

Now, it's your turn:"""

