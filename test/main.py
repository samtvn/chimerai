from backend.schemas import UpdateProfileRequest
from orchestrator.runner import run_workflow


def demo_run() -> None:
	payload = UpdateProfileRequest(
		user_id="u_123",
		comment="I dislike wines that dry my mouth.",
		rating=2,
	)
	state = run_workflow(payload)
	print(f"state_id={state.state_id} tags={state.semantic_tags} scores={state.scores}")


if __name__ == "__main__":
	demo_run()
