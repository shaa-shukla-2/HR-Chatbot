"""Custom NeMo Guardrails actions for the HR assistant."""

import re
from typing import Optional

from nemoguardrails.actions import action

# Matches policy IDs like HR-POL-01 followed by a section such as "Section 2.1" or "§2.1"
CITATION_PATTERN = re.compile(r"HR[-\u2010-\u2015\u2212]POL[-\u2010-\u2015\u2212]\d{2}", re.IGNORECASE)

# Predefined bot replies from hr_rails.co (greeting, refusals, fallback). These are fixed
# texts, so they need no citation. Matched by prefix so an LLM answer cannot skip a
# citation just by mentioning "contact HR" somewhere in the middle.
CANNED_PREFIXES = (
    "hello! i'm the network india property hr policy assistant",
    "you're welcome",
    "i can only help with hr policy questions",
    "i can't give legal advice",
    "i can't judge or decide the outcome",
    "i can't share personal or payroll details",
    "i can only answer questions about network india property hr policies",
    "i can't help with that request",
    "i couldn't find this in the hr policy documents",
)


@action(is_system_action=True)
async def check_has_citation(context: Optional[dict] = None) -> bool:
    """Return True if the bot answer cites a policy document or is a predefined reply."""
    bot_message = ((context or {}).get("bot_message", "") or "").strip()
    if bot_message.lower().startswith(CANNED_PREFIXES):
        return True
    return bool(CITATION_PATTERN.search(bot_message))
