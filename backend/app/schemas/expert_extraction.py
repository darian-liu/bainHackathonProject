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


class AIScreeningResult(BaseModel):
    """Smart Fit Assessment result."""
    grade: Literal["strong", "mixed", "weak"] = Field(description="Overall screening grade")
    score: int = Field(ge=0, le=100, description="Numeric score 0-100")
    rationale: str = Field(description="2-3 sentence explanation covering background fit and screener assessment")
    confidence: ConfidenceLevel = Field(description="Confidence in the screening assessment")
    missingInfo: Optional[List[str]] = Field(None, description="Missing information that would improve assessment")
    suggestedQuestions: Optional[List[str]] = Field(None, description="Questions to ask the expert or network")
    questionScores: Optional[List[dict]] = Field(
        None, 
        description="Per-question scores: [{questionId, score, notes}]"
    )


class ExpertUpdate(BaseModel):
    """Expert field update model."""
    field: str
    value: Optional[str] = None


class ExpertUpdateInfo(BaseModel):
    """Update information for a single expert."""
    expertName: str = Field(description="Name of the expert being updated")
    updateType: Literal["new", "update"] = Field(description="Whether this is a new expert or an update")
    
    # Updated fields (only populated if updateType == "update")
    updatedFields: Optional[List[str]] = Field(
        None, 
        description="List of field names that have updates (e.g., 'availability', 'screenerResponses', 'conflictStatus')"
    )
    
    # Global fields apply across all networks
    globalFieldUpdates: Optional[dict] = Field(
        None, 
        description="Updates to global fields: name, employer, title corrections"
    )
    
    # Network-specific updates
    networkSpecificUpdates: Optional[dict] = Field(
        None, 
        description="Updates specific to a network: status, availability, screenerResponses"
    )
    
    # Confidence in the update detection
    confidence: ConfidenceLevel = Field(default="medium")
    
    # Provenance for the update
    updateProvenance: Optional[FieldProvenance] = None


class EmailUpdateAnalysis(BaseModel):
    """Analysis of whether an email contains updates vs new experts."""
    
    isFollowUp: bool = Field(
        description="Whether this email appears to be a follow-up to previous communications"
    )
    
    threadIndicators: Optional[List[str]] = Field(
        None, 
        description="Indicators that this is part of a thread (Re:, FW:, reply references)"
    )
    
    updateSummary: Optional[str] = Field(
        None, 
        description="Brief summary of what updates are contained in this email"
    )
    
    expertUpdates: List[ExpertUpdateInfo] = Field(
        description="Per-expert analysis of new vs update status"
    )
    
    analysisNotes: Optional[List[str]] = Field(
        None, 
        description="Notes about the analysis"
    )
