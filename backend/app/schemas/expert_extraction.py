"""Pydantic schemas for expert extraction."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# Confidence levels
ConfidenceLevel = Literal["low", "medium", "high"]

# Status cues
StatusCue = Literal[
    "available",
    "declined",
    "conflict",
    "not_a_fit",
    "no_longer_available",
    "pending",
    "interested",
    "unknown"
]

# Conflict status
ConflictStatus = Literal["cleared", "pending", "conflict"]


class FieldProvenance(BaseModel):
    """Field provenance - stores where a value was extracted from."""
    excerptText: str = Field(description="The exact text excerpt from the email used to extract this value")
    charStart: Optional[int] = Field(None, description="Character offset start in the email")
    charEnd: Optional[int] = Field(None, description="Character offset end in the email")
    confidence: ConfidenceLevel = Field(description="Confidence in the extraction accuracy")


class ScreenerResponse(BaseModel):
    """Screener Q&A pair."""
    question: Optional[str] = Field(None, description="The screener question if identifiable")
    answer: str = Field(description="The response or free text")


class ExtractedExpert(BaseModel):
    """Single extracted expert from an email."""

    # Core identity
    fullName: str = Field(description="Expert full name")
    fullNameProvenance: FieldProvenance

    # Employment
    employer: Optional[str] = Field(None, description="Current employer/company")
    employerProvenance: Optional[FieldProvenance] = None

    title: Optional[str] = Field(None, description="Job title")
    titleProvenance: Optional[FieldProvenance] = None

    # Relevance/bio
    relevanceBullets: Optional[List[str]] = Field(None, description="Relevance bullets or bio points")
    relevanceBulletsProvenance: Optional[FieldProvenance] = None

    # Screener responses
    screenerResponses: Optional[List[ScreenerResponse]] = Field(None, description="Screener Q&A if present")
    screenerResponsesProvenance: Optional[FieldProvenance] = None

    # Conflict
    conflictStatus: Optional[ConflictStatus] = Field(None, description="Conflict status if mentioned")
    conflictId: Optional[str] = Field(None, description="Conflict ID if provided")
    conflictProvenance: Optional[FieldProvenance] = None

    # Availability
    availabilityWindows: Optional[List[str]] = Field(None, description="Available time slots")
    availabilityProvenance: Optional[FieldProvenance] = None

    # Status cues
    statusCue: Optional[StatusCue] = Field(None, description="Explicit status indicator from email")
    statusCueProvenance: Optional[FieldProvenance] = None

    # Overall confidence
    overallConfidence: ConfidenceLevel = Field(description="Overall confidence in extraction quality")


class EmailExtractionResult(BaseModel):
    """Full extraction result from an email."""

    # Email metadata
    inferredNetwork: Optional[str] = Field(None, description="Inferred network from email content")
    networkConfidence: Optional[ConfidenceLevel] = Field(None, description="Confidence in network inference")
    emailDate: Optional[str] = Field(None, description="Parsed email sent date if found (ISO format)")

    # Extracted experts
    experts: List[ExtractedExpert] = Field(description="List of experts extracted from email")

    # Extraction notes
    extractionNotes: Optional[List[str]] = Field(None, description="Notes about extraction quality or issues")


class AIRecommendation(BaseModel):
    """AI recommendation result."""
    recommendation: Literal["strong_fit", "maybe", "low_fit"] = Field(description="Fit recommendation")
    rationale: str = Field(description="1-2 sentence explanation")
    confidence: ConfidenceLevel = Field(description="Confidence in recommendation")
    missingInfo: Optional[List[str]] = Field(None, description="Key missing information that limited confidence")


class ExpertUpdate(BaseModel):
    """Expert field update model."""
    field: str
    value: Optional[str] = None


class DocumentRelevance(BaseModel):
    """Document relevance for expert screening."""
    filename: str = Field(description="Name of the relevant document")
    relevance_score: float = Field(description="Relevance score from 0-1")
    matched_topics: List[str] = Field(description="Topics that matched between expert and document")


class AIScreeningResultWithDocs(BaseModel):
    """AI screening result enhanced with document context."""
    # Base recommendation fields
    recommendation: Literal["strong_fit", "maybe", "low_fit"] = Field(description="Fit recommendation")
    rationale: str = Field(description="1-2 sentence explanation")
    confidence: ConfidenceLevel = Field(description="Confidence in recommendation")
    missingInfo: Optional[List[str]] = Field(None, description="Key missing information")

    # Enhanced scoring breakdown
    background_fit_score: int = Field(description="Background fit score 0-100")
    screener_quality_score: int = Field(description="Screener quality score 0-100")
    document_relevance_score: int = Field(description="Document relevance score 0-100")
    red_flags_score: int = Field(description="Red flags deduction 0-100 (higher = fewer red flags)")

    # Document context
    relevant_documents: Optional[List[DocumentRelevance]] = Field(
        None, description="Documents relevant to this expert"
    )
    overall_score: int = Field(description="Weighted overall score 0-100")
