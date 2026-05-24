from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database.database import AsyncSessionLocal
from apps.api.database.models.alerts import Alert, AlertSeverity
from apps.api.database.dependencies import get_demo_user_id


def make_alert_tools() -> list:
    """Create alert management tools for the orchestrator."""

    @tool
    async def create_alert(message: str, severity: str = "info", source_agent: str = "orchestrator") -> str:
        """
        Creates an alert in the system for the sommelier to review.
        
        Args:
            message: The alert message (e.g. "Wine X is low stock but sells slowly")
            severity: One of 'info', 'warning', 'error' (default: 'info')
            source_agent: Which agent generated the alert (default: 'orchestrator')
        
        Returns:
            Confirmation message
        """
        # Validate and normalize severity
        try:
            severity_enum = AlertSeverity(severity.lower())
        except ValueError:
            severity_enum = AlertSeverity.INFO

        try:
            async with AsyncSessionLocal() as db:
                user_id = await get_demo_user_id(db)

                alert = Alert(
                    user_id=user_id,
                    message=message,
                    severity=severity_enum,
                    source_agent=source_agent,
                    read=False,
                )
                db.add(alert)
                await db.commit()

                return f"Alert created: {severity.upper()} — {message}"

        except Exception as e:
            return f"Error creating alert: {str(e)}"

    return [create_alert]
