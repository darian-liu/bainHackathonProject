"""AI-powered expert extraction service using OpenAI."""

import json
from typing import Tuple, List
from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.expert_extraction import (
    EmailExtractionResult,
    AIRecommendation,
    AIScreeningResult,
    AIScreeningResultWithDocs,
    DocumentRelevance,
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


SCREENING_SYSTEM_PROMPT = """You are a ruthlessly opinionated expert screener for high-stakes consulting engagements.
Your job is to produce DIFFERENTIATED scores that clearly separate strong-fit experts from mediocre or poor fits.

You MUST use the FULL 0-100 range. Most slates should have meaningful spread (30+ point gaps between best and worst).

SCORING DIMENSIONS (all scores 0-100):

1. BACKGROUND FIT (35% weight):
   - Does the expert have DIRECT, FIRST-HAND operating experience in the exact domain?
   - Advisors, vendors, distributors, and consultants who "supported" operators score 20-40 MAX.
   - Only score 70+ if the expert personally OWNED outcomes (P&L, execution, decisions) in the relevant industry.
   - Adjacent industries (e.g., convenience retail vs QSR) cap at 50.

2. SCREENER QUALITY (45% weight):
   - This is the MOST IMPORTANT dimension. If a SCREENER RUBRIC is provided, apply it LITERALLY.
   - Match the expert's responses against each rubric criterion word-for-word.
   - If the rubric says "we are explicitly not prioritizing" a profile type and the expert matches that type, score 10-30.
   - Vague or generic responses ("supported rollout", "evaluated competitively") score 20-40.
   - Only score 70+ if the expert's responses demonstrate EXACTLY the kind of experience the rubric demands.
   - If the expert's role was supportive/advisory rather than ownership, cap screener score at 45.

3. RED FLAGS (20% weight - higher score = fewer red flags):
   - Vendor/distributor/aggregator roles when operator experience is required: score 20-30.
   - "High-level frameworks only" or inability to share specifics: score 30-40.
   - NDA-heavy or evasive conflict answers: score 25-35.
   - Clean, transparent, no-conflict answers with concrete examples: score 80-100.

GRADE THRESHOLDS (be strict):
- "strong": score >= 80 — reserve for experts who are EXACTLY what the rubric demands
- "mixed": score 45-79 — decent but missing key criteria or in a supportive rather than ownership role
- "weak": score < 45 — wrong profile type, adjacent experience, or explicitly de-prioritized by rubric

CRITICAL RULES:
- Do NOT give everyone 75+. If all experts look similar, you are not being opinionated enough.
- A vendor who "supported" restaurant clients is NOT the same as an operator who OWNED the P&L. Score them 30+ points apart.
- Apply the screener rubric's "we are NOT prioritizing" criteria as hard disqualifiers (cap at 45).
- When in doubt, score LOWER. It is better to surface 2-3 true fits than to recommend everyone.

Return detailed scoring breakdown with justification."""


UPDATE_DETECTION_SYSTEM_PROMPT = """You are an expert at analyzing email threads to detect whether experts mentioned are NEW or UPDATES to existing profiles.

KEY DISTINCTIONS:
1. NEW expert: First time mentioned in this project/thread
2. UPDATE: Same expert mentioned before with new information (availability changes, screener updates, status changes)

THREAD INDICATORS (suggest follow-up):
- Subject line: "Re:", "FW:", reply chains
- Body text: "Following up", "Update on", "As discussed"
- References to previous emails or conversations

FIELD CATEGORIZATION:
- GLOBAL fields (apply across all networks): name, employer, title
- NETWORK-SPECIFIC fields (can differ per network): status, availability, screenerResponses, conflictStatus

CRITICAL RULES:
1. If an expert appears multiple times in ONE email thread → consolidate to ONE entry, mark as NEW (it's their first mention in the system)
2. If the email explicitly says "update" or "following up" about a known expert → mark as UPDATE
3. When in doubt, default to NEW
4. Always provide clear provenance for your determination

Return analysis with per-expert breakdown."""


DOCUMENT_SCREENING_SYSTEM_PROMPT = """You are an expert at evaluating experts for consulting engagements.
Given an expert's profile, a project hypothesis, AND relevant document context, score the expert across multiple dimensions.

SCORING DIMENSIONS (all scores 0-100):

1. BACKGROUND FIT (30% weight):
   - How well does the expert's employer, title, and experience match the project needs?
   - Consider industry, role level, and functional expertise

2. SCREENER QUALITY (30% weight):
   - How thorough and relevant are the screener responses?
   - Do they demonstrate deep knowledge of the topics?

3. DOCUMENT RELEVANCE (25% weight):
   - How well does the expert's background align with the provided document context?
   - Are there specific topics in the documents that match their expertise?

4. RED FLAGS (15% weight - higher score = fewer red flags):
   - Are there conflicts of interest?
   - Is their experience too dated?
   - Any gaps or inconsistencies?

RECOMMENDATION LEVELS:
- "strong_fit": Overall score >= 75 and no critical red flags
- "maybe": Overall score 50-74 OR missing key information
- "low_fit": Overall score < 50 OR critical red flags

Return detailed scoring breakdown with justification."""


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

    async def screen_expert_with_documents(
        self,
        expert_name: str,
        employer: str | None,
        title: str | None,
        bio: str | None,
        screener_responses: str | None,
        project_hypothesis: str,
        document_chunks: list[dict]
    ) -> Tuple[AIScreeningResultWithDocs, str, str]:
        """
        Generate enhanced AI screening with document context.

        New scoring weights:
        - Background Fit: 30%
        - Screener Quality: 30%
        - Document Relevance: 25%
        - Red Flags: 15%

        Args:
            expert_name: Expert's full name
            employer: Current employer
            title: Job title
            bio: Bio or relevance bullets
            screener_responses: Screener Q&A text
            project_hypothesis: Project focus/hypothesis
            document_chunks: List of relevant document chunks with metadata

        Returns:
            Tuple of (result, raw_response, prompt)
        """
        # Format document context
        doc_context = ""
        if document_chunks:
            doc_context = "\n\nDOCUMENT CONTEXT (from ingested data room):\n"
            for i, chunk in enumerate(document_chunks[:10], 1):  # Limit to top 10 chunks
                filename = chunk.get("metadata", {}).get("filename", "unknown")
                text = chunk.get("text", "")[:500]  # Truncate long chunks
                doc_context += f"\n[Doc {i}: {filename}]\n{text}\n"
        else:
            doc_context = "\n\nDOCUMENT CONTEXT: No documents available."

        user_prompt = f"""Evaluate this expert for the following project with document context:

PROJECT HYPOTHESIS/FOCUS:
{project_hypothesis}

EXPERT PROFILE:
- Name: {expert_name}
- Employer: {employer or 'Unknown'}
- Title: {title or 'Unknown'}
- Bio/Relevance: {bio or 'Not provided'}
- Screener Responses: {screener_responses or 'Not provided'}
{doc_context}

Provide your detailed scoring as a JSON object:
{{
  "recommendation": "strong_fit" | "maybe" | "low_fit",
  "rationale": "1-2 sentence explanation",
  "confidence": "low" | "medium" | "high",
  "missingInfo": ["info1", "info2"] | null,
  "background_fit_score": 0-100,
  "screener_quality_score": 0-100,
  "document_relevance_score": 0-100,
  "red_flags_score": 0-100,
  "relevant_documents": [
    {{
      "filename": "document name",
      "relevance_score": 0.0-1.0,
      "matched_topics": ["topic1", "topic2"]
    }}
  ] | null,
  "overall_score": 0-100
}}

Calculate overall_score as: (background_fit_score * 0.30) + (screener_quality_score * 0.30) + (document_relevance_score * 0.25) + (red_flags_score * 0.15)"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DOCUMENT_SCREENING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        raw_response = response.choices[0].message.content or ""
        parsed = json.loads(raw_response)
        validated = AIScreeningResultWithDocs(**parsed)

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
        Generate smart fit assessment for expert (auto-scanning).

        New scoring weights:
        - Background Fit: 40%
        - Screener Quality: 40%
        - Red Flags: 20%

        Args:
            expert_name: Expert's full name
            expert_employer: Current employer
            expert_title: Job title
            expert_bio: Bio or relevance bullets
            screener_responses: Screener Q&A text
            screener_config: Screener configuration with questions
            project_hypothesis: Project focus/hypothesis

        Returns:
            Tuple of (result, raw_response, prompt)
        """
        # Build screener rubric section from config
        screener_rubric_text = ""
        if screener_config and screener_config.get("questions"):
            rubric_lines = []
            for q in screener_config["questions"]:
                q_text = q.get("text", "")
                q_ideal = q.get("idealAnswer", "")
                if q_text:
                    rubric_lines.append(f"QUESTION: {q_text}")
                    if q_ideal:
                        rubric_lines.append(f"WHAT WE'RE LOOKING FOR: {q_ideal}")
                    rubric_lines.append("")
            if rubric_lines:
                screener_rubric_text = "\n\nSCREENER RUBRIC (apply this STRICTLY — this is the client's own criteria):\n" + "\n".join(rubric_lines)

        user_prompt = f"""Evaluate this expert for the following project:

PROJECT HYPOTHESIS/FOCUS:
{project_hypothesis}
{screener_rubric_text}

EXPERT PROFILE:
- Name: {expert_name}
- Employer: {expert_employer or 'Unknown'}
- Title: {expert_title or 'Unknown'}
- Bio/Relevance: {expert_bio or 'Not provided'}
- Screener Responses: {screener_responses or 'Not provided'}

INSTRUCTIONS:
1. Score each dimension independently using the FULL 0-100 range.
2. If a SCREENER RUBRIC is provided above, match the expert's profile and responses against it LITERALLY.
3. If the rubric explicitly de-prioritizes a profile type and this expert matches it, cap their screener score at 35.
4. Produce scores that would create CLEAR differentiation across a slate of 6-10 experts.

Provide your detailed scoring as a JSON object:
{{
  "grade": "strong" | "mixed" | "weak",
  "score": 0-100,
  "rationale": "2-3 sentence explanation. Be specific about WHY this expert does or does not match the rubric criteria.",
  "confidence": "low" | "medium" | "high",
  "missingInfo": ["info1", "info2"] | null,
  "suggestedQuestions": ["question1", "question2"] | null,
  "questionScores": [{{"questionId": "q1", "score": 0-100, "notes": "..."}}] | null
}}

Calculate score as: (background_fit_score * 0.35) + (screener_quality_score * 0.45) + (red_flags_score * 0.20)

Grade thresholds (be STRICT):
- strong: score >= 80 (reserve for exact-fit experts only)
- mixed: score 45-79
- weak: score < 45"""

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
        project_hypothesis: str
    ) -> Tuple[EmailUpdateAnalysis, str, str]:
        """
        Analyze whether an email contains updates to existing experts or new experts.

        Args:
            email_text: Raw email content
            project_hypothesis: Project context

        Returns:
            Tuple of (analysis, raw_response, prompt)
        """
        user_prompt = f"""Analyze this email to determine if it contains NEW experts or UPDATES to existing ones.

PROJECT CONTEXT: {project_hypothesis}

EMAIL CONTENT:
---
{email_text}
---

Return a JSON object with this structure:
{{
  "isFollowUp": boolean,
  "threadIndicators": ["Re:", "following up", etc.] | null,
  "updateSummary": "Brief summary of updates" | null,
  "expertUpdates": [
    {{
      "expertName": "Full name",
      "updateType": "new" | "update",
      "updatedFields": ["availability", "screenerResponses"] | null,
      "globalFieldUpdates": {{"employer": "New Corp"}} | null,
      "networkSpecificUpdates": {{"status": "available"}} | null,
      "confidence": "low" | "medium" | "high",
      "updateProvenance": {{
        "excerptText": "Exact quote from email",
        "confidence": "low" | "medium" | "high"
      }} | null
    }}
  ],
  "analysisNotes": ["note1", "note2"] | null
}}"""

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
