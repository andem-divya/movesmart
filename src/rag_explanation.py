"""
Generates personalized RAG-based relocation explanations for a given CBSA.
Flow:
    i/p: user preferences + text query + CBSA scores + CBSA summary
    o/p: 2-3 sentence personalized explanation
"""

import json
import logging

logger = logging.getLogger(__name__)


def _priority_label(val: float) -> str:
    """Convert a 0-5 slider value to a human-readable priority label.

    Args:
        val: Slider value between 0 and 5.

    Returns:
        One of 'high priority', 'moderate priority', or 'low priority'.
    """
    if val >= 4:
        return "high priority"
    elif val >= 2:
        return "moderate priority"
    else:
        return "low priority"


def _build_rag_explanation_prompt(
    user_prefs: dict,
    user_query: str,
    cbsa_name: str,
    theme_scores: dict,
    cbsa_summary: str,
) -> str:
    """Build the prompt for the RAG explanation LLM call.

    Combines user slider preferences, free-text query, CBSA theme scores,
    and the LLM-generated CBSA summary into a single grounded prompt.

    Args:
        user_prefs:    Dict of slider values keyed by metric name
                       e.g. {"affordability_score": 4.0, "safety_score": 3.0}
        user_query:    Free-text query entered by the user.
        cbsa_name:     Display name of the CBSA being evaluated.
        theme_scores:  Dict of computed theme scores for this CBSA
                       e.g. {"affordability": 6.2, "safety": 7.1}
        cbsa_summary:  LLM-generated summary of the CBSA from wiki sources.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    
    prefs_readable = "\n".join(
        f"  {k.replace('_score', '').replace('_', ' ').title()}: "
        f"{float(v):.1f}/5 ({_priority_label(float(v))})"
        for k, v in user_prefs.items()
    )

    scores_readable = "\n".join(
        f"  {k.replace('_', ' ').title()}: {float(v):.1f}/5"
        for k, v in theme_scores.items() if "_score" in k
    )

    return f"""A user is looking for a place to relocate in the US.

User's stated preferences (0-5 scale):
{prefs_readable}

User's own words: "{user_query}"

CBSA being evaluated: {cbsa_name}

Theme scores for this CBSA (0-10 scale):
{scores_readable}

What people say about this metro (from local sources):
{cbsa_summary}

These are already the best matching cities from a pool of 500+ US metros, 
selected based on the user's combined preferences.

In 2-3 sentences, explain what stands out about {cbsa_name} for this user 
based on their top priorities. Frame it as strengths — do not say it is a 
bad fit or suggest alternatives. If a priority has a moderate score, 
present it as a tradeoff, not a failure.

Rules:
- Only reference the summary and scores above — no outside knowledge
- Directly connect the user's high-priority preferences to the CBSA's scores
- If the summary does not mention something the user cares about, say so honestly
- Be specific and conversational, no hype or flowery language
- Do not repeat the city name more than once
"""


def _call_llm(client, prompt: str) -> str | None:
    """Invoke Claude Haiku on AWS Bedrock with the given prompt.

    Args:
        client: Boto3 bedrock-runtime client.
        prompt: Fully formatted prompt string.

    Returns:
        Response text from the model, or None if the call fails.
    """
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
        })

        response = client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body,
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    except Exception as e:
        logger.error("Bedrock call failed for RAG explanation: %s", e)
        return None


def generate_explanation(
    client,
    user_prefs: dict,
    user_query: str,
    cbsa_name: str,
    theme_scores: dict,
    cbsa_summary: str,
) -> str | None:
    """Generate a personalized relocation explanation for a CBSA using RAG.

    Retrieves context from the CBSA summary (the 'augmentation' step) and
    passes it along with user preferences to the LLM to generate a grounded,
    personalized explanation (the 'generation' step).

    Args:
        client:        Boto3 bedrock-runtime client.
        user_prefs:    Dict of slider values keyed by metric name.
        user_query:    Free-text query entered by the user.
        cbsa_name:     Display name of the CBSA being evaluated.
        theme_scores:  Dict of computed theme scores for this CBSA.
        cbsa_summary:  LLM-generated CBSA summary from wiki sources.

    Returns:
        2-3 sentence explanation string, or None if the LLM call failed.
    """
    prompt = _build_rag_explanation_prompt(
        user_prefs, user_query, cbsa_name, theme_scores, cbsa_summary
    )
    return _call_llm(client, prompt)