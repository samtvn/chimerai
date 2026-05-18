"""Service module for Orchestrator - provides high-level interface"""
from api.Orchestrator.orchestrator import CellarOrchestrator


class OrchestratorService:
    """High-level service for orchestrator workflows"""
    
    @staticmethod
    async def analyze_and_decide():
        """
        Run the complete orchestrator workflow:
        1. Analyze wine cellar
        2. Identify missing wine categories
        3. Decide if market analysis is needed
        
        Returns:
            dict: Orchestrator result with analysis and decisions
        """
        orchestrator = CellarOrchestrator()
        return await orchestrator.run()
