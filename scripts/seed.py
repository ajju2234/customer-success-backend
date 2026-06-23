"""Seed the database with demo users, customers and interactions.

Idempotent: re-running skips work if the demo data already exists.
Run against any target by setting DATABASE_URL, e.g.:

    DATABASE_URL="postgresql+asyncpg://...:5432/postgres?ssl=require" \
        python -m scripts.seed

Every demo account uses the password: Test@1234
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.ai_insight import AIInsight
from app.models.customer import Customer
from app.models.enums import CustomerStatus, InsightStatus, InteractionType, Role, Sentiment
from app.models.interaction import Interaction
from app.models.user import User

PASSWORD = "Test@1234"

USERS = [
    ("Sarah Chen", "sarah.chen@csp.com", Role.admin),
    ("Michael Rodriguez", "michael.rodriguez@csp.com", Role.manager),
    ("Priya Sharma", "priya.sharma@csp.com", Role.manager),
    ("David Thompson", "david.thompson@csp.com", Role.manager),
    ("Emily Watson", "emily.watson@csp.com", Role.csm),
    ("James Park", "james.park@csp.com", Role.csm),
    ("Aisha Khan", "aisha.khan@csp.com", Role.csm),
    ("Carlos Mendez", "carlos.mendez@csp.com", Role.csm),
    ("Nina Petrov", "nina.petrov@csp.com", Role.csm),
]

# name, company, email, phone, status, health, owner_email
CUSTOMERS = [
    ("Acme Corp", "Acme Corporation", "ops@acme.com", "+1 415 555 0101", CustomerStatus.active, 88, "emily.watson@csp.com"),
    ("Globex Inc", "Globex", "hello@globex.com", "+1 415 555 0102", CustomerStatus.at_risk, 42, "emily.watson@csp.com"),
    ("Cyberdyne Systems", "Cyberdyne", "contact@cyberdyne.com", "+1 415 555 0103", CustomerStatus.active, 85, "emily.watson@csp.com"),
    ("Initech", "Initech LLC", "support@initech.com", "+1 408 555 0111", CustomerStatus.active, 76, "james.park@csp.com"),
    ("Umbrella LLC", "Umbrella", "info@umbrella.com", "+1 408 555 0112", CustomerStatus.churned, 15, "james.park@csp.com"),
    ("Stark Industries", "Stark Industries", "team@stark.com", "+1 212 555 0121", CustomerStatus.active, 94, "aisha.khan@csp.com"),
    ("Wayne Enterprises", "Wayne Enterprises", "bd@wayne.com", "+1 212 555 0122", CustomerStatus.prospect, 55, "aisha.khan@csp.com"),
    ("Gekko & Co", "Gekko Capital", "deals@gekko.com", "+1 212 555 0123", CustomerStatus.at_risk, 45, "aisha.khan@csp.com"),
    ("Soylent Co", "Soylent", "hi@soylent.com", "+1 503 555 0131", CustomerStatus.at_risk, 38, "carlos.mendez@csp.com"),
    ("Hooli", "Hooli Inc", "partners@hooli.com", "+1 503 555 0132", CustomerStatus.active, 81, "carlos.mendez@csp.com"),
    ("Pied Piper", "Pied Piper", "richard@piedpiper.com", "+1 650 555 0141", CustomerStatus.prospect, 60, "nina.petrov@csp.com"),
    ("Vehement Capital", "Vehement Capital Partners", "ops@vehement.com", "+1 650 555 0142", CustomerStatus.active, 70, "nina.petrov@csp.com"),
    ("Massive Dynamic", "Massive Dynamic", "contact@massivedynamic.com", "+1 650 555 0143", CustomerStatus.churned, 22, "nina.petrov@csp.com"),
]

# customer_email, type, title, notes, days_ago, sentiment, summary, action_items, risks
INTERACTIONS = [
    ("ops@acme.com", InteractionType.meeting, "Q3 business review", "Great QBR — Acme is expanding usage to two more teams next quarter and is very happy with the new dashboard.", 1, Sentiment.positive,
     "Acme is thrilled with the platform and plans to expand to two more teams next quarter.", ["Prepare expansion proposal for 2 new teams", "Share dashboard onboarding guide"], []),
    ("hello@globex.com", InteractionType.call, "Escalation: onboarding delays", "Globex is frustrated about repeated onboarding delays and slow support responses. Considering pausing the contract.", 2, Sentiment.negative,
     "Globex is frustrated with onboarding delays and slow support; contract is at risk.", ["Assign a dedicated onboarding specialist", "Schedule weekly check-ins"], ["Risk of contract pause/churn", "SLA breach on support response times"]),
    ("contact@cyberdyne.com", InteractionType.meeting, "Roadmap alignment", "Discussed upcoming features; Cyberdyne is satisfied and interested in the AI insights add-on.", 3, Sentiment.positive,
     "Cyberdyne is satisfied and interested in the AI insights add-on.", ["Send AI insights pricing", "Book follow-up demo"], []),
    ("support@initech.com", InteractionType.email, "Renewal discussion", "Initech confirmed renewal for another year. Asked about volume discounts.", 4, Sentiment.positive,
     "Initech confirmed annual renewal and asked about volume discounts.", ["Send volume discount options"], []),
    ("info@umbrella.com", InteractionType.call, "Cancellation notice", "Umbrella has decided to churn due to budget cuts. Offboarding requested.", 6, Sentiment.negative,
     "Umbrella is churning due to budget cuts and requested offboarding.", ["Start offboarding process", "Conduct churn exit interview"], ["Lost account — budget-driven churn"]),
    ("team@stark.com", InteractionType.meeting, "Executive sponsor sync", "Stark exec sponsor very supportive; wants to feature us in an internal case study.", 1, Sentiment.positive,
     "Stark's executive sponsor is highly supportive and wants an internal case study.", ["Draft case study outline", "Get marketing approval"], []),
    ("bd@wayne.com", InteractionType.meeting, "Discovery call", "Initial discovery with Wayne Enterprises. Evaluating us against two competitors.", 5, Sentiment.neutral,
     "Wayne Enterprises is in discovery and evaluating us against two competitors.", ["Send competitive comparison sheet", "Schedule technical deep-dive"], ["Active competitive evaluation"]),
    ("deals@gekko.com", InteractionType.call, "Usage drop check-in", "Gekko's usage has dropped 30% this month. Champion left the company.", 3, Sentiment.negative,
     "Gekko's usage dropped 30% after their champion left the company.", ["Identify and engage a new champion", "Run a value-realization workshop"], ["Champion departure", "Declining product usage"]),
    ("hi@soylent.com", InteractionType.note, "Support ticket follow-up", "Several unresolved tickets. Soylent is unhappy with response times but open to staying.", 2, Sentiment.negative,
     "Soylent is unhappy with support response times but open to staying if resolved.", ["Escalate open tickets to engineering", "Provide a remediation timeline"], ["Unresolved support backlog", "Satisfaction at risk"]),
    ("partners@hooli.com", InteractionType.meeting, "Expansion planning", "Hooli wants to roll out to their EMEA team. Positive momentum.", 4, Sentiment.positive,
     "Hooli plans to roll out to their EMEA team — strong expansion momentum.", ["Prepare EMEA rollout plan", "Confirm data residency requirements"], []),
    ("richard@piedpiper.com", InteractionType.call, "Trial kickoff", "Started a 30-day trial with Pied Piper. Engineering team is excited about the API.", 7, Sentiment.positive,
     "Pied Piper started a 30-day trial and is excited about the API.", ["Set trial success criteria", "Schedule mid-trial review"], []),
    ("ops@vehement.com", InteractionType.email, "Quarterly check-in", "Vehement is steady. No major issues, moderate engagement.", 8, Sentiment.neutral,
     "Vehement is a steady account with moderate engagement and no major issues.", ["Share new feature highlights"], []),
    ("contact@massivedynamic.com", InteractionType.call, "Win-back attempt", "Tried to win back Massive Dynamic after churn. They've committed to a competitor for now.", 9, Sentiment.negative,
     "Win-back attempt failed; Massive Dynamic has committed to a competitor.", ["Keep on nurture list for 6 months"], ["Lost to competitor"]),
    ("ops@acme.com", InteractionType.call, "Feature request triage", "Acme requested SSO and audit logs. Generally positive call.", 10, Sentiment.neutral,
     "Acme requested SSO and audit logs; overall a positive call.", ["Log SSO + audit-log feature requests", "Share roadmap timing"], []),
    ("team@stark.com", InteractionType.email, "Adoption metrics", "Shared adoption metrics — Stark's active users up 20% MoM.", 6, Sentiment.positive,
     "Stark's active users grew 20% month-over-month.", ["Celebrate milestone with the account"], []),
    ("support@initech.com", InteractionType.note, "Billing question", "Initech had a billing question; resolved quickly. Neutral sentiment.", 11, Sentiment.neutral,
     "Initech had a billing question that was resolved quickly.", [], []),
    ("hi@soylent.com", InteractionType.meeting, "Recovery plan review", "Reviewed recovery plan with Soylent. Cautiously optimistic but still tense.", 0, Sentiment.neutral,
     "Reviewed a recovery plan with Soylent — cautiously optimistic but still tense.", ["Track remediation milestones weekly"], ["Relationship still fragile"]),
    ("partners@hooli.com", InteractionType.call, "Security review", "Hooli's security team approved us. Green light for rollout.", 0, Sentiment.positive,
     "Hooli's security team approved the platform — cleared for rollout.", ["Begin EMEA provisioning"], []),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Idempotency guard
        existing = await db.scalar(select(User).where(User.email == "sarah.chen@csp.com"))
        if existing:
            print("Demo data already present — nothing to do.")
            return

        users: dict[str, User] = {}
        for name, email, role in USERS:
            u = User(name=name, email=email, hashed_password=hash_password(PASSWORD), role=role)
            db.add(u)
            users[email] = u
        await db.flush()

        customers: dict[str, Customer] = {}
        for name, company, email, phone, status, health, owner_email in CUSTOMERS:
            c = Customer(
                name=name, company=company, email=email, phone=phone,
                status=status, health_score=health, owner_id=users[owner_email].id,
            )
            db.add(c)
            customers[email] = c
        await db.flush()

        now = datetime.now(timezone.utc)
        for (cust_email, itype, title, notes, days_ago, sentiment, summary, actions, risks) in INTERACTIONS:
            cust = customers[cust_email]
            interaction = Interaction(
                customer_id=cust.id, user_id=cust.owner_id, type=itype,
                title=title, notes=notes, meeting_date=now - timedelta(days=days_ago, hours=2),
            )
            db.add(interaction)
            await db.flush()
            db.add(AIInsight(
                interaction_id=interaction.id, summary=summary, sentiment=sentiment,
                action_items=actions, risks=risks, model="gemini-2.5-flash",
                status=InsightStatus.success,
            ))

        await db.commit()
        print(f"Seeded {len(USERS)} users, {len(CUSTOMERS)} customers, {len(INTERACTIONS)} interactions.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
