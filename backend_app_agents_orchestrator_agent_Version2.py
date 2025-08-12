import logging, json
from typing import AsyncGenerator
from typing_extensions import override
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Enhanced orchestrator:
      1. IntentAgent -> classify
      2. PlanningAgent -> build plan
      3. Execute steps:
         - perception
         - memory summary
         - tool calls (weather/geocode/rag)
         - compose_response (ConversationAgent)
         - reflection (optional -> re-plan)
      4. Final response in final_response.
    State:
      user_query, intent_result, plan_json, tool_results, perception_summary,
      memory_context, interim_response, reflection_result, final_response.
    """

    intent_agent: LlmAgent
    planning_agent: LlmAgent
    reflection_agent: LlmAgent
    conversation_agent: LlmAgent
    perception_agent: LlmAgent
    memory_agent: LlmAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        intent_agent: LlmAgent,
        planning_agent: LlmAgent,
        reflection_agent: LlmAgent,
        conversation_agent: LlmAgent,
        perception_agent: LlmAgent,
        memory_agent: LlmAgent
    ):
        sub_agents = [
            intent_agent, planning_agent, reflection_agent,
            conversation_agent, perception_agent, memory_agent
        ]
        super().__init__(
            name="OrchestratorAgent",
            intent_agent=intent_agent,
            planning_agent=planning_agent,
            reflection_agent=reflection_agent,
            conversation_agent=conversation_agent,
            perception_agent=perception_agent,
            memory_agent=memory_agent,
            sub_agents=sub_agents
        )

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        logger.info("[Orchestrator] Start turn.")
        # Step 1: Intent
        async for e in self.intent_agent.run_async(ctx):
            yield e

        # Step 2: Planning
        async for e in self.planning_agent.run_async(ctx):
            yield e

        # Parse plan
        plan_raw = state.get("plan_json", "")
        try:
            plan_obj = json.loads(plan_raw)
            steps = plan_obj.get("plan", [])
        except Exception:
            logger.warning("Invalid plan JSON; fallback to direct conversation.")
            steps = [{"step":1,"action":"compose_response"}]

        # Execute steps
        tool_results = state.get("tool_results", [])
        for step in steps:
            action = step.get("action")
            if action == "perception" and state.get("image_context"):
                async for ev in self.perception_agent.run_async(ctx):
                    yield ev
            elif action == "memory_summarize" and state.get("retrieved_memory"):
                async for ev in self.memory_agent.run_async(ctx):
                    yield ev
            elif action == "call_tool":
                # Tool executed earlier in main or needs a placeholder
                # For advanced pipeline, you could queue a message to backend tool executor
                pass
            elif action == "retrieve_docs":
                # RAG retrieval already done prior (backend inserted 'rag_snippets')
                pass
            elif action == "compose_response":
                async for ev in self.conversation_agent.run_async(ctx):
                    yield ev
                state["interim_response"] = state.get("final_response","")
            elif action == "reflect":
                async for ev in self.reflection_agent.run_async(ctx):
                    yield ev
                # If reflection calls for followup, you might re-run planning (not implemented for brevity)

        logger.info("[Orchestrator] Completed execution flow.")