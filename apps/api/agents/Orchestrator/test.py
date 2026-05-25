from apps.api.database.database import AsyncReadSessionLocal
from apps.api.database.repositories.cellar_repository import CellarRepository
from apps.api.agents.Orchestrator.new_orchestrator import Orchestrator


cellar_repo = CellarRepository(AsyncReadSessionLocal(), read_only=True)
orchestrator = Orchestrator(cellar_repo)
orchestrator._print_graph(orchestrator.graph)
