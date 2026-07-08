"""Shared constants used across pages and components."""

SENTIMENT_COLORS = {
    "Positive": "#4CAF50",
    "Neutral": "#FFC107",
    "Negative": "#F44336",
}

EXPERIMENT_STATUSES = [
    "draft",
    "personas_generated",
    "survey",
    "interviews",
    "complete",
]

PERSONALITY_TAG_POOL = [
    "Extrovert", "Introvert", "Analytical", "Early Adopter", "Skeptical",
    "Budget-Conscious", "Tech-Savvy", "Detail-Oriented", "Impulsive Buyer",
    "Risk-Averse", "Trendsetter", "Loyal Customer", "Value Seeker",
]

OCCUPATIONS_POOL = [
    "Marketing Manager", "Software Developer", "CPA", "Executive",
    "Junior Analyst", "Senior Consultant", "Product Designer", "Teacher",
    "Nurse", "Small Business Owner", "Student", "Freelancer",
]

NAV_PAGES = [
    ("Home", "0_Home"),
    ("Experiment Workspace", "1_Experiment_Workspace"),
    ("Persona Gallery", "2_Persona_Gallery"),
    ("Survey Mode", "3_Survey_Mode"),
    ("Interview Mode", "4_Interview_Mode"),
    ("Insights Dashboard", "5_Insights_Dashboard"),
    ("Report Generator", "6_Report_Generator"),
]

MAX_SURVEY_QUESTIONS = 10
