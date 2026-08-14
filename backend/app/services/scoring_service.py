from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, LeadScoreRule


DEFAULT_SCORE_RULES = [
    ("course_interest", "Course interest selected", 10),
    ("parent_involved", "Parent involved", 15),
    ("asked_about_admission", "Asked about admission", 20),
    ("requested_brochure", "Requested brochure", 10),
    ("attended_counselling", "Attended counselling", 20),
    ("campus_visit", "Campus visit", 15),
    ("follow_up_response", "Follow-up response (HOT)", 10),
    ("registration_discussion", "Registration discussion", 20),
]


async def ensure_default_score_rules(db: AsyncSession) -> None:
    existing = await db.scalars(select(LeadScoreRule))
    keys = {r.factor_key for r in existing}
    for key, name, points in DEFAULT_SCORE_RULES:
        if key not in keys:
            db.add(LeadScoreRule(factor_key=key, display_name=name, points=points, is_enabled=True))
    await db.flush()


async def calculate_lead_score(db: AsyncSession, lead: Lead) -> int:
    rules = {
        r.factor_key: r.points
        for r in (await db.scalars(select(LeadScoreRule).where(LeadScoreRule.is_enabled.is_(True)))).all()
    }
    score = 0
    if lead.course_id:
        score += rules.get("course_interest", 0)
    if lead.parent_involved:
        score += rules.get("parent_involved", 0)
    if lead.asked_about_admission:
        score += rules.get("asked_about_admission", 0)
    if lead.requested_brochure:
        score += rules.get("requested_brochure", 0)
    if lead.attended_counselling:
        score += rules.get("attended_counselling", 0)
    if lead.campus_visit_done:
        score += rules.get("campus_visit", 0)
    if lead.temperature and lead.temperature.value == "hot":
        score += rules.get("follow_up_response", 0)
    if lead.registration_discussion:
        score += rules.get("registration_discussion", 0)
    return min(score, 100)
