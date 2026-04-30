"""BaseAgent — LLM interface and retry logic for agent decision-making.

This module implements Story 12 of the implementation plan:
- AsyncOpenAI client pointed at OpenRouter
- Retry logic with parse error recovery
- Memory management across rounds
- Fallback responses when LLM fails
- Integration with ResponseParser and PromptBuilder
"""

import os
import asyncio
from typing import Any

import time

from openai import AsyncOpenAI, OpenAI
import openai
import nest_asyncio

from models.agent_types import AgentProfile, AgentState, RoundResponse
from models.world_state import RoundContext
from agents.parser import ResponseParser, ParseError
from agents.prompts import PromptBuilder


# Enable nested asyncio for Jupyter compatibility
nest_asyncio.apply()


class BaseAgent:
    """LLM-powered agent that makes strategic decisions each round.
    
    This is the ONLY class in the codebase that makes external LLM API calls.
    All other modules are pure Python.
    """
    
    MAX_RETRIES = 2
    
    def __init__(self, profile: AgentProfile, model: str = "moonshotai/kimi-k2"):
        """Initialize agent with profile and LLM model.
        
        Args:
            profile: Agent profile with objectives, constraints, and data
            model: OpenRouter model slug (default: moonshotai/kimi-k2)
        """
        self.profile = profile
        self.model = model
        self.state = AgentState.initial(profile)
        self.memory: list[RoundResponse] = []
        
        # Initialize LLM client
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.sync_client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Initialize parser and prompt builder
        self.parser = ResponseParser()
        self.prompt_builder = PromptBuilder()
    
    @property
    def agent_id(self) -> str:
        """Get agent ID from profile."""
        return self.profile.agent_id
    
    async def act_async(self, context: RoundContext) -> RoundResponse:
        """Make an asynchronous decision for the current round.
        
        Args:
            context: Round context with shock, signals, market state
        
        Returns:
            RoundResponse with agent's decision
        """
        # Build prompts
        system_prompt = self.prompt_builder.build_system_prompt(
            self.profile,
            context.capture_bias
        )
        user_message = self.prompt_builder.build_round_message(
            context,
            self.profile,
            self.memory
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Get available actions for constraint checking
        available_actions = self.prompt_builder.get_available_actions(
            self.profile,
            self.state
        )
        available_action_ids = [
            action["action_id"] 
            for action in available_actions 
            if action["available"]
        ]
        
        # Prepare state dict for parser
        state_dict = {
            "cash_usd_mn": self.profile.data.get("cash_reserves_usd_bn", 0) * 1000,
            "fear_greed_index": self.state.fear_greed_index,
            "financial_health": self.state.financial_health
        }
        
        # Retry loop
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # Call LLM
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                raw = response.choices[0].message.content
                
                # Parse response
                try:
                    parsed = self.parser.parse(
                        raw,
                        self.profile.agent_type.value,
                        state_dict,
                        available_action_ids,
                        attempt
                    )
                    
                    # Convert to RoundResponse
                    round_response = self.parser.to_round_response(
                        parsed,
                        self.profile.agent_id,
                        context.round,
                        raw
                    )
                    
                    # Store in memory
                    self.memory.append(round_response)
                    
                    return round_response
                    
                except ParseError as e:
                    if attempt == self.MAX_RETRIES:
                        # Max retries reached, use fallback
                        fallback = RoundResponse.fallback(
                            self.profile.agent_id,
                            context.round
                        )
                        self.memory.append(fallback)
                        return fallback
                    
                    # Add retry prompt to conversation
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": e.retry_prompt})
                    
            except openai.RateLimitError as e:
                # Exponential backoff for rate limits
                wait_time = 2 ** attempt
                print(f"[WARN] Rate limit hit, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                
                if attempt == self.MAX_RETRIES:
                    fallback = RoundResponse.fallback(
                        self.profile.agent_id,
                        context.round
                    )
                    self.memory.append(fallback)
                    return fallback
                    
            except openai.APIError as e:
                print(f"[ERROR] OpenAI API error: {e}")
                
                if attempt == self.MAX_RETRIES:
                    fallback = RoundResponse.fallback(
                        self.profile.agent_id,
                        context.round
                    )
                    self.memory.append(fallback)
                    return fallback
        
        # Should never reach here, but defensive
        fallback = RoundResponse.fallback(
            self.profile.agent_id,
            context.round
        )
        self.memory.append(fallback)
        return fallback
    
    def act(self, context: RoundContext) -> RoundResponse:
        """Synchronous decision-making using the sync OpenAI client.

        Safe to call from threads (e.g. ThreadPoolExecutor) without asyncio
        conflicts.  The async variant act_async() is kept for direct async use.

        Args:
            context: Round context with shock, signals, market state

        Returns:
            RoundResponse with agent's decision
        """
        # Build prompts (same as act_async)
        system_prompt = self.prompt_builder.build_system_prompt(
            self.profile,
            context.capture_bias
        )
        user_message = self.prompt_builder.build_round_message(
            context,
            self.profile,
            self.memory
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        available_actions = self.prompt_builder.get_available_actions(
            self.profile,
            self.state
        )
        available_action_ids = [
            action["action_id"]
            for action in available_actions
            if action["available"]
        ]

        state_dict = {
            "cash_usd_mn": self.profile.data.get("cash_reserves_usd_bn", 0) * 1000,
            "fear_greed_index": self.state.fear_greed_index,
            "financial_health": self.state.financial_health,
        }

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self.sync_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                )
                raw = response.choices[0].message.content

                try:
                    parsed = self.parser.parse(
                        raw,
                        self.profile.agent_type.value,
                        state_dict,
                        available_action_ids,
                        attempt,
                    )
                    round_response = self.parser.to_round_response(
                        parsed,
                        self.profile.agent_id,
                        context.round,
                        raw,
                    )
                    self.memory.append(round_response)
                    return round_response

                except ParseError as e:
                    if attempt == self.MAX_RETRIES:
                        fallback = RoundResponse.fallback(
                            self.profile.agent_id, context.round
                        )
                        self.memory.append(fallback)
                        return fallback
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": e.retry_prompt})

            except openai.RateLimitError:
                wait_time = 2 ** attempt
                print(f"[WARN] Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
                if attempt == self.MAX_RETRIES:
                    fallback = RoundResponse.fallback(
                        self.profile.agent_id, context.round
                    )
                    self.memory.append(fallback)
                    return fallback

            except openai.APIError as e:
                print(f"[ERROR] OpenAI API error: {e}")
                if attempt == self.MAX_RETRIES:
                    fallback = RoundResponse.fallback(
                        self.profile.agent_id, context.round
                    )
                    self.memory.append(fallback)
                    return fallback

        fallback = RoundResponse.fallback(self.profile.agent_id, context.round)
        self.memory.append(fallback)
        return fallback
    
    def update_state(self, patch: dict[str, Any]) -> None:
        """Apply state updates from resolver.
        
        Args:
            patch: Partial state dict to merge into current state
        """
        self.state.apply_updates(patch)

    def reset(self):
        """Clear agent memory for a fresh simulation run."""
        self.memory.clear()

    def __repr__(self) -> str:
        return f"Agent({self.profile.name}, role={self.profile.agent_type.value})"
