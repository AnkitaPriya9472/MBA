"""Trade network topology and flow recalculation.

Story 15: TradeNetwork - loads trade routes and recalculates flows based on policy changes.
"""

import json
from pathlib import Path
from pydantic import BaseModel
from models.market import TradeRoute, MarketState
from models.events import WorldEvent


class TradeNetwork:
    """Manages bilateral trade routes and recalculates flows based on policies.
    
    Loads baseline trade network from JSON and dynamically adjusts:
    - Tariff rates (from government actions)
    - Friction levels (from capital controls, sanctions)
    - Trade volumes (from price attractiveness and policy effects)
    """

    MARKET_FLOOD_THRESHOLD = 0.40  # 40% volume increase in one round

    def __init__(self, routes: list[TradeRoute]):
        """Initialize with a list of trade routes."""
        self.routes = routes
        self._baseline_volumes = {self._route_key(r): r.volume for r in routes}
        self._previous_routes: list[TradeRoute] | None = None

    @classmethod
    def load(cls, path: str) -> "TradeNetwork":
        """Load trade network from JSON file.
        
        Expected JSON format:
        {
            "routes": [
                {
                    "from_country": "IN",
                    "to_country": "US",
                    "commodity": "steel_hrc",
                    "baseline_volume_mt": 2100000,
                    "baseline_tariff_pct": 25,
                    "friction": 0.15
                },
                ...
            ]
        }
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Trade network file not found: {path}")

        data = json.loads(file_path.read_text())
        routes_data = data.get("routes", [])

        routes = []
        for route_dict in routes_data:
            route = TradeRoute(
                from_country=route_dict["from_country"],
                to_country=route_dict["to_country"],
                commodity=route_dict["commodity"],
                volume=route_dict["baseline_volume_mt"],
                tariff_rate=route_dict["baseline_tariff_pct"],
                friction=route_dict.get("friction", 0.0),
            )
            routes.append(route)

        return cls(routes)

    def _route_key(self, route: TradeRoute) -> tuple[str, str, str]:
        """Generate unique key for a trade route."""
        return (route.from_country, route.to_country, route.commodity)

    def apply_policy(
        self,
        action: str,
        actor_country: str,
        target_country: str,
        commodity: str,
        magnitude: float,
    ) -> None:
        """Apply a policy action to matching trade routes.
        
        Args:
            action: Policy instrument ("retaliatory_tariff", "subsidy", "capital_controls")
            actor_country: Country implementing the policy
            target_country: Country targeted by the policy (if applicable)
            commodity: Commodity affected (if applicable)
            magnitude: Policy magnitude (tariff rate, subsidy amount, etc.)
        """
        for route in self.routes:
            if action == "retaliatory_tariff":
                # Increase tariff on imports from target country
                if route.to_country == actor_country and route.from_country == target_country:
                    if commodity == "all" or route.commodity == commodity:
                        route.tariff_rate += magnitude

            elif action == "subsidy":
                # Reduce effective tariff (modeled as negative tariff)
                if route.from_country == actor_country:
                    if commodity == "all" or route.commodity == commodity:
                        # Floor at 0 - subsidies can't make tariffs negative
                        route.tariff_rate = max(0.0, route.tariff_rate - magnitude)

            elif action == "capital_controls":
                # Increase friction on all routes from actor country
                if route.from_country == actor_country:
                    route.friction = min(1.0, route.friction + 0.1)  # Cap at 1.0

    def recalculate_flows(self, market_states: dict[str, MarketState]) -> list[TradeRoute]:
        """Recalculate trade volumes based on current tariffs, friction, and prices.
        
        Formula per route:
            volume = baseline × (1 - tariff/100) × (1 - friction) × price_attractiveness
            
        Where price_attractiveness = target_market_price / global_average_price
        (Higher-price markets attract more exports)
        
        Args:
            market_states: Current market states for price data
            
        Returns:
            List of updated TradeRoute objects
        """
        # Save previous routes for event detection
        self._previous_routes = [
            TradeRoute(
                from_country=r.from_country,
                to_country=r.to_country,
                commodity=r.commodity,
                volume=r.volume,
                tariff_rate=r.tariff_rate,
                friction=r.friction,
            )
            for r in self.routes
        ]

        # Calculate global average prices by commodity
        avg_prices = {}
        for commodity, state in market_states.items():
            avg_prices[commodity] = state.spot_price

        # Recalculate each route's volume
        for route in self.routes:
            baseline = self._baseline_volumes[self._route_key(route)]
            
            # Tariff effect (higher tariff → lower volume)
            tariff_factor = max(0.0, 1.0 - route.tariff_rate / 100)
            
            # Friction effect (higher friction → lower volume)
            friction_factor = 1.0 - route.friction
            
            # Price attractiveness (higher destination price → more attractive)
            price_attractiveness = 1.0  # Default if no market data
            if route.commodity in avg_prices:
                # Simplified: assume all markets have similar prices
                # In full implementation, would track per-country prices
                # For now, use spot price as proxy
                price_attractiveness = 1.0  # Neutral

            # Calculate new volume
            new_volume = baseline * tariff_factor * friction_factor * price_attractiveness
            
            # Clamp to [0, baseline × 2.0]
            new_volume = max(0.0, min(baseline * 2.0, new_volume))
            
            route.volume = new_volume

        return self.routes

    def get_routes(
        self,
        from_country: str | None = None,
        commodity: str | None = None,
    ) -> list[TradeRoute]:
        """Filter routes by origin country and/or commodity."""
        result = self.routes
        
        if from_country is not None:
            result = [r for r in result if r.from_country == from_country]
        
        if commodity is not None:
            result = [r for r in result if r.commodity == commodity]
        
        return result

    def detect_events(
        self,
        current_round: int,
    ) -> list[WorldEvent]:
        """Detect trade-related events based on route changes.
        
        Events:
        - MARKET_FLOOD: Single route volume increase > 40%
        - TRADE_WAR_ESCALATION: Tariffs increased bidirectionally
        
        Args:
            current_round: Current simulation round
            
        Returns:
            List of WorldEvent objects
        """
        events = []
        
        if self._previous_routes is None:
            # First round - no events
            return events

        # Build lookup for previous routes
        prev_by_key = {self._route_key(r): r for r in self._previous_routes}

        # Track tariff increases by country pair
        tariff_increases: dict[tuple[str, str], list[str]] = {}

        for route in self.routes:
            key = self._route_key(route)
            if key not in prev_by_key:
                continue

            prev_route = prev_by_key[key]

            # Check for MARKET_FLOOD
            if prev_route.volume > 0:
                volume_change_pct = (route.volume - prev_route.volume) / prev_route.volume
                if volume_change_pct > self.MARKET_FLOOD_THRESHOLD:
                    events.append(WorldEvent(
                        event_type="MARKET_FLOOD",
                        round=current_round,
                        description=(
                            f"Export flood detected: {route.from_country} → {route.to_country} "
                            f"{route.commodity} volume increased {volume_change_pct*100:.1f}% "
                            f"to {route.volume:,.0f} MT."
                        ),
                        affected_agents=[],  # Would map to agent IDs in full implementation
                        data={
                            "from_country": route.from_country,
                            "to_country": route.to_country,
                            "commodity": route.commodity,
                            "volume_change_pct": volume_change_pct,
                            "new_volume_mt": route.volume,
                        },
                    ))

            # Track tariff increases for TRADE_WAR_ESCALATION detection
            if route.tariff_rate > prev_route.tariff_rate:
                pair = (route.from_country, route.to_country)
                if pair not in tariff_increases:
                    tariff_increases[pair] = []
                tariff_increases[pair].append(route.commodity)

        # Check for TRADE_WAR_ESCALATION (bidirectional tariff increases)
        checked_pairs = set()
        for (from_c, to_c), commodities in tariff_increases.items():
            # Check if reverse direction also increased tariffs
            reverse_pair = (to_c, from_c)
            if reverse_pair in tariff_increases and (from_c, to_c) not in checked_pairs:
                # Bidirectional tariff increase detected
                events.append(WorldEvent(
                    event_type="TRADE_WAR_ESCALATION",
                    round=current_round,
                    description=(
                        f"Trade war escalation: {from_c} and {to_c} both increased tariffs "
                        f"on each other's exports in the same round."
                    ),
                    affected_agents=[],
                    data={
                        "country_a": from_c,
                        "country_b": to_c,
                        "commodities_a_to_b": commodities,
                        "commodities_b_to_a": tariff_increases[reverse_pair],
                    },
                ))
                checked_pairs.add((from_c, to_c))
                checked_pairs.add((to_c, from_c))

        return events

    def get_total_volume(self, commodity: str) -> float:
        """Get total trade volume for a commodity across all routes."""
        return sum(r.volume for r in self.routes if r.commodity == commodity)

    def get_route(self, from_country: str, to_country: str, commodity: str) -> TradeRoute | None:
        """Get a specific route by key."""
        for route in self.routes:
            if (route.from_country == from_country and 
                route.to_country == to_country and 
                route.commodity == commodity):
                return route
        return None
