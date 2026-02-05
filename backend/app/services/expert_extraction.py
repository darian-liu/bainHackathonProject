"""AI-powered expert extraction service using OpenAI."""

import json
from typing import Tuple, List
from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.expert_extraction import (
    EmailExtractionResult,
    AIRecommendation,
    AIScreeningResult,
    ExtractedExpert,
    EmailUpdateAnalysis,
)


EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting structured information from expert network emails.
Your task is to parse emails from expert networks (AlphaSights, Guidepoint, GLG, etc.) and extract expert profiles.

CRITICAL RULES:
1. NEVER fabricate or hallucinate information. If a field is not present in the email, set it to null.
2. For every extracted value, you MUST provide the exact excerpt from the email that supports it.
3. Be conservative with confidence levels - use "low" if there's any ambiguity.
4. Extract ALL experts mentioned in the email, even if information is sparse.
5. Pay attention to conflict status, availability windows, and screener responses.

EMAIL THREAD HANDLING (CRITICAL):
The input may be a long email thread (20-30 replies) with the same experts mentioned multiple times.
You MUST:
1. DEDUPLICATE experts: Return each unique expert EXACTLY ONCE in the output.
2. MERGE information: When the same expert appears multiple times, combine all information about them.
3. PREFER LATEST: If there are conflicting values (e.g., status changed from "pending" to "cleared"), use the MOST RECENT value.
4. PRESERVE ALL PROVENANCE: Even when merging, keep the most relevant/complete excerpt for provenance.
5. Identify the same expert by: exact name match, or very similar names (e.g., "John Smith" and "John R. Smith").

Example: If Sarah Chen appears in 3 emails with different availability updates, return ONE entry for Sarah Chen with the latest availability.

NETWORK INFERENCE:
- AlphaSights: Often uses "AlphaSights" in signature, mentions "AlphaSights Expert", or has @alphasights.com domain
- Guidepoint: Uses "Guidepoint" branding, @guidepoint.com domain
- GLG: Uses "GLG" or "Gerson Lehrman Group", @glg.it or @glgroup.com domains
- Tegus: Uses "Tegus" branding
- Third Bridge: Uses "Third Bridge" branding
- If unclear, set inferredNetwork to null

STATUS CUES (look for explicit mentions):
- "available" - expert is available for calls
- "declined" - expert declined participation
- "conflict" - has a conflict of interest
- "not_a_fit" - not relevant for the project
- "no_longer_available" - was available but no longer
- "pending" - awaiting response
- "interested" - expressed interest

CONFLICT STATUS:
- "cleared" - no conflict, approved
- "pending" - conflict check in progress
- "conflict" - has confirmed conflict

Return a valid JSON object following the exact schema provided."""


RECOMMENDATION_SYSTEM_PROMPT = """You are an expert at evaluating experts for consulting engagements.
Given an expert's profile and a project hypothesis/focus, determine how well the expert fits.

EVALUATION CRITERIA:
1. Relevance: Does their experience directly relate to the hypothesis?
2. Recency: Is their relevant experience recent enough to be valuable?
3. Depth: Do they have deep enough knowledge vs surface-level familiarity?
4. Access: Did they have direct exposure to the topics of interest?

RECOMMENDATION LEVELS:
- "strong_fit": High relevance, recent experience, direct knowledge of key topics
- "maybe": Some relevance but missing key criteria, or unclear information
- "low_fit": Limited relevance, outdated experience, or tangential knowledge

CRITICAL RULES:
1. Be CONSERVATIVE. If key information is missing, default to "maybe" with "low" confidence.
2. Never over-recommend based on assumptions.
3. List what information is missing that would increase confidence.
4. Keep rationale to 1-2 concise sentences."""


SCREENING_SYSTEM_PROMPT = """You are an expert at evaluating potential expert network consultants for consulting engagements.

Your task is to provide a comprehensive "Smart Fit Assessment" that evaluates how well an expert matches a project's needs. You assess using ALL available information:
1. Expert's background (employer, title, bio/relevance bullets)
2. Project hypothesis/focus area
3. Screener rubric questions (if configured)
4. Expert's screener responses (if available)

CRITICAL RULES:
1. NEVER fabricate or hallucinate information. Only assess what is actually provided.
2. Evaluate the expert holistically - their background matters even without screener responses.
3. If screener responses exist, compare them against the rubric.
4. Look for red flags mentioned in the rubric.
5. Generate "suggested questions" the user should ask for experts missing key info.
6. Be objective and consistent in scoring.

GRADING SCALE:
- "strong": Expert background highly relevant to project, screener responses (if any) match rubric well (score 70-100)
- "mixed": Some relevant experience but gaps or concerns exist (score 40-69)
- "weak": Limited relevance, major gaps, or concerning red flags (score 0-39)

SCORING (0-100):
- Background Fit (40%): Does their employer/title/bio align with project needs?
- Screener Quality (40%): If responses exist, do they match the rubric? (If no responses, score based on background only)
- Red Flags (20%): Deduct for any concerning signals

IMPORTANT: Even without screener responses, you can still assess an expert based on their background and relevance to the project hypothesis. Don't automatically score "weak" just because screener responses are missing."""


UPDATE_DETECTION_SYSTEM_PROMPT = """You are an expert at analyzing expert network email threads to detect updates.

Your task is to determine if an email contains UPDATES to previously known experts, or if it's introducing NEW experts.

CRITICAL PATTERNS FOR UPDATES:
1. "Update:" or "Re:" in subject/headers indicating follow-up
2. Phrases like "now available", "availability update", "screener complete", "conflict cleared"
3. References to previous communications about specific experts
4. Status change notifications
5. Screener response submissions from previously proposed experts
6. Scheduling confirmations for known experts

WHAT TO LOOK FOR:
- Is this a reply in an ongoing thread?
- Are expert names mentioned that appear to already be known/proposed?
- What type of information is being updated (availability, screener responses, conflict status, scheduling)?

FIELD TYPES:
- Global fields (apply across all networks): name corrections, employer updates, title changes
- Network-specific fields: network-specific status, availability, screener responses, scheduling

Return analysis focused on what has CHANGED, not the full expert profile."""


class ExpertExtractionService:
    """Service for AI-powered expert extraction and recommendation."""

    def __init__(self):
        """Initialize OpenAI client with Portkey support."""
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key not set. Please configure it in settings."
            )

        # Configure client with optional Portkey base URL
        client_config = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_config["base_url"] = settings.openai_base_url

        self.client = AsyncOpenAI(**client_config)

        # Use model from settings (Bain uses @personal-openai/ prefix with Portkey)
        self.model = settings.openai_model or "gpt-4o"

    async def extract_experts_from_email(
        self,
        email_text: str,
        project_hypothesis: str,
        network_hint: str | None = None
    ) -> Tuple[EmailExtractionResult, str, str]:
        """
        Extract expert profiles from email using OpenAI structured output.

        Returns:
            Tuple of (result, raw_response, prompt)
        """
        user_prompt = f"""Extract expert information from the following email content (may be an email thread with multiple replies).

PROJECT CONTEXT: {project_hypothesis}

{f'NETWORK HINT (user-provided): {network_hint}' if network_hint else 'NETWORK: Please infer from email content'}

IMPORTANT: If this is an email thread with multiple messages:
- Return each unique expert ONCE (deduplicated)
- Merge information from multiple mentions of the same expert
- Use the LATEST values for fields that may have changed (status, availability, conflict)
- Add a note in extractionNotes if you merged duplicate expert mentions

EMAIL CONTENT:
---
{email_text}
---

Extract all experts mentioned and return a JSON object with this exact structure:
{{
  "inferredNetwork": string | null,
  "networkConfidence": "low" | "medium" | "high" | null,
  "emailDate": string | null (ISO format if found),
  "experts": [
    {{
      "fullName": string,
      "fullNameProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }},
      "employer": string | null,
      "employerProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "title": string | null,
      "titleProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "relevanceBullets": string[] | null,
      "relevanceBulletsProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "screenerResponses": [{{ "question": string?, "answer": string }}] | null,
      "screenerResponsesProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "conflictStatus": "cleared" | "pending" | "conflict" | null,
      "conflictId": string | null,
      "conflictProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "availabilityWindows": string[] | null,
      "availabilityProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "statusCue": "available" | "declined" | "conflict" | "not_a_fit" | "no_longer_available" | "pending" | "interested" | "unknown" | null,
      "statusCueProvenance": {{ "excerptText": string, "confidence": "low"|"medium"|"high" }} | null,
      "overallConfidence": "low" | "medium" | "high"
    }}
  ],
  "extractionNotes": string[] | null
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for consistent extraction
        )

        raw_response = response.choices[0].message.content or ""

        try:
            parsed = json.loads(raw_response)
            validated = EmailExtractionResult(**parsed)
            return validated, raw_response, user_prompt
        except Exception as error:
            # Retry with repair prompt
            return await self._retry_extraction_with_repair(
                raw_response, user_prompt, str(error)
            )

    async def _retry_extraction_with_repair(
        self,
        failed_response: str,
        original_prompt: str,
        error: str
    ) -> Tuple[EmailExtractionResult, str, str]:
        """Retry extraction with repair prompt if first attempt fails."""
        repair_prompt = f"""The previous extraction response was invalid. Here's what went wrong:
{error}

Previous response:
{failed_response}

Please fix the JSON to match the exact schema required. Ensure all required fields are present and properly typed.
Return ONLY the corrected JSON object."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": original_prompt},
                {"role": "assistant", "content": failed_response},
                {"role": "user", "content": repair_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw_response = response.choices[0].message.content or ""
        parsed = json.loads(raw_response)
        validated = EmailExtractionResult(**parsed)

        combined_prompt = original_prompt + "\n\n[REPAIR PROMPT]\n" + repair_prompt
        return validated, raw_response, combined_prompt

    async def recommend_expert(
        self,
        expert_name: str,
        employer: str | None,
        title: str | None,
        bio: str | None,
        screener_responses: str | None,
        project_hypothesis: str
    ) -> Tuple[AIRecommendation, str, str]:
        """
        Generate AI recommendation for expert fit.

        Returns:
            Tuple of (result, raw_response, prompt)
        """
        user_prompt = f"""Evaluate this expert for the following project:

PROJECT HYPOTHESIS/FOCUS:
{project_hypothesis}

EXPERT PROFILE:
- Name: {expert_name}
- Employer: {employer or 'Unknown'}
- Title: {title or 'Unknown'}
- Bio/Relevance: {bio or 'Not provided'}
- Screener Responses: {screener_responses or 'Not provided'}

Provide your recommendation as a JSON object:
{{
  "recommendation": "strong_fit" | "maybe" | "low_fit",
  "rationale": "1-2 sentence explanation",
  "confidence": "low" | "medium" | "high",
  "missingInfo": ["info1", "info2"] | null
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_response = response.choices[0].message.content or ""
        parsed = json.loads(raw_response)
        validated = AIRecommendation(**parsed)

        return validated, raw_response, user_prompt

    async def screen_expert(
        self,
        expert_name: str,
        expert_employer: str | None,
        expert_title: str | None,
        expert_bio: str | None,
        screener_responses: str | None,
        screener_config: dict | None,
        project_hypothesis: str
    ) -> Tuple[AIScreeningResult, str, str]:
        """
        Generate Smart Fit Assessment for expert.
        
        Evaluates expert against project needs using ALL available information:
        - Expert background (employer, title, bio)
        - Project hypothesis
        - Screener rubric and responses (if available)
        
        Args:
            expert_name: Expert's name
            expert_employer: Expert's employer/company
            expert_title: Expert's job title
            expert_bio: Expert's bio/relevance bullets
            screener_responses: Expert's screener responses (may be None or raw text)
            screener_config: Project's screener configuration with questions and rubrics
            project_hypothesis: Project's hypothesis/focus area
            
        Returns:
            Tuple of (result, raw_response, prompt)
        """
        # Build rubric description from screener config
        rubric_text = ""
        if screener_config:
            questions = screener_config.get("questions", [])
            for q in questions:
                rubric_text += f"\n\nQUESTION {q.get('order', '?')}: {q.get('text', 'Unknown')}"
                if q.get("idealAnswer"):
                    rubric_text += f"\n  Ideal Answer: {q['idealAnswer']}"
                if q.get("rubricNotes"):
                    rubric_text += f"\n  Rubric Notes: {q['rubricNotes']}"
                if q.get("redFlags"):
                    rubric_text += f"\n  Red Flags to Watch: {q['redFlags']}"
        
        user_prompt = f"""Provide a comprehensive Smart Fit Assessment for this expert.

===== PROJECT CONTEXT =====
HYPOTHESIS/FOCUS: {project_hypothesis}

===== EXPERT PROFILE =====
Name: {expert_name}
Employer: {expert_employer or 'Unknown'}
Title: {expert_title or 'Unknown'}
Bio/Relevance: {expert_bio or 'Not provided'}

===== SCREENER RUBRIC =====
{rubric_text if rubric_text else "No screener rubric configured for this project."}

===== EXPERT'S SCREENER RESPONSES =====
{screener_responses if screener_responses else "No screener responses available yet."}

Provide your Smart Fit Assessment as a JSON object:
{{
  "grade": "strong" | "mixed" | "weak",
  "score": 0-100,
  "rationale": "2-3 sentence explanation covering background fit and screener assessment",
  "confidence": "low" | "medium" | "high",
  "missingInfo": ["list of information that would improve assessment"] | null,
  "suggestedQuestions": ["questions to ask this expert or the network"] | null,
  "questionScores": [
    {{
      "questionId": "q1",
      "questionText": "...",
      "score": 0-100,
      "notes": "brief assessment of this answer"
    }}
  ] | null
}}

ASSESSMENT GUIDANCE:
- Evaluate expert's background against project hypothesis FIRST
- If screener responses exist, assess them against the rubric
- If screener responses are missing, still provide a preliminary assessment based on background
- Generate "suggestedQuestions" for areas where more info would help
- Be specific about what is strong, mixed, or weak"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SCREENING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_response = response.choices[0].message.content or ""
        parsed = json.loads(raw_response)
        validated = AIScreeningResult(**parsed)

        return validated, raw_response, user_prompt

    async def analyze_email_for_updates(
        self,
        email_text: str,
        existing_expert_names: List[str],
        network: str | None = None
    ) -> Tuple[EmailUpdateAnalysis, str, str]:
        """
        Analyze an email to determine if it contains updates to existing experts.
        
        This helps the ingestion pipeline distinguish between:
        - New expert submissions
        - Updates to existing experts (availability, screener responses, status)
        
        Args:
            email_text: The email content to analyze
            existing_expert_names: List of expert names already in the tracker for this project
            network: The network this email is from (if known)
            
        Returns:
            Tuple of (analysis_result, raw_response, prompt)
        """
        user_prompt = f"""Analyze this email to determine if it contains updates to existing experts or new expert submissions.

CONTEXT:
- Network: {network or "Unknown"}
- Experts currently in tracker: {', '.join(existing_expert_names) if existing_expert_names else 'None'}

EMAIL CONTENT:
---
{email_text}
---

For EACH expert mentioned in this email, determine:
1. Is this a NEW expert being proposed, or an UPDATE to an existing expert?
2. If an update, what fields are being updated?

FIELD CLASSIFICATION:
- Global fields (apply across networks): employer, title, biography corrections
- Network-specific fields: availability, screenerResponses, conflictStatus, status cues

Return a JSON object:
{{
  "isFollowUp": true/false,
  "threadIndicators": ["Re:", "In reply to", etc] | null,
  "updateSummary": "Brief summary of updates found",
  "expertUpdates": [
    {{
      "expertName": "Name",
      "updateType": "new" | "update",
      "updatedFields": ["availability", "screenerResponses"] | null,
      "globalFieldUpdates": {{"field": "value"}} | null,
      "networkSpecificUpdates": {{"field": "value"}} | null,
      "confidence": "low" | "medium" | "high"
    }}
  ],
  "analysisNotes": ["note1", "note2"] | null
}}

IMPORTANT:
- Compare expert names against the existing tracker list
- Look for update patterns: "update on", "availability for", "screener responses from"
- Distinguish between initial proposals and follow-up communications"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": UPDATE_DETECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw_response = response.choices[0].message.content or ""
        parsed = json.loads(raw_response)
        validated = EmailUpdateAnalysis(**parsed)

        return validated, raw_response, user_prompt
