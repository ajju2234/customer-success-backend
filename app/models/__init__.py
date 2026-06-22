"""Import all models so they register on Base.metadata (used by Alembic autogenerate)."""
from app.models.ai_insight import AIInsight
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.user import User

__all__ = ["User", "Customer", "Interaction", "AIInsight"]
