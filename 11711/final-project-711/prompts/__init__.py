# prompts package
"""Prompt templates for the Undercover game agents"""

from .description_prompts import (
    get_description_user_prompt
)
from .voting_prompts import (
    get_voting_user_prompt
)

__all__ = [
    'get_description_user_prompt',
    'get_voting_user_prompt',
]

