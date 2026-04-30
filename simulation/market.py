"""Market clearing engine for supply/demand matching and price discovery.

Story 13: MarketClearing - deterministic double-auction mechanism.
"""

from pydantic import BaseModel, field_validator
from models.market import MarketState


class SupplyOffer(BaseModel):
    """A supply offer from a supplier or producer agent."""
    agent_id: str
    product: str  # "steel_hrc", "iron_ore", "ev_battery"
    volume_mt: float  # metric tons
    min_price_usd_per_mt: float  # minimum acceptable price

    @field_validator('volume_mt')
    @classmethod
    def volume_positive(cls, v):
        if v <= 0:
            raise ValueError('volume_mt must be > 0')
        return v

    @field_validator('min_price_usd_per_mt')
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError('min_price_usd_per_mt must be > 0')
        return v


class DemandRequest(BaseModel):
    """A demand request from a consumer or buyer agent."""
    agent_id: str
    product: str
    volume_mt: float
    max_price_usd_per_mt: float

    @field_validator('volume_mt')
    @classmethod
    def volume_positive(cls, v):
        if v <= 0:
            raise ValueError('volume_mt must be > 0')
        return v

    @field_validator('max_price_usd_per_mt')
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError('max_price_usd_per_mt must be > 0')
        return v


class MarketClearing:
    """Deterministic double-auction market clearing mechanism.
    
    Matches supply offers with demand requests to determine:
    - Clearing price
    - Volume traded
    - Unmet demand/supply
    - Price changes from previous round
    """

    PRICE_CHANGE_CAP_PCT = 25.0  # Maximum price change per round
    SUPPLY_SURPLUS_FACTOR = 0.10  # Downward pressure coefficient
    DEMAND_SURPLUS_FACTOR = 0.15  # Upward pressure coefficient
    FLOATING_POINT_EPSILON = 1e-6  # Residual volume threshold

    def clear_product(
        self,
        product: str,
        supply_offers: list[SupplyOffer],
        demand_requests: list[DemandRequest],
        round_number: int,
        prev_price: float | None = None,
        tariff_lookup: dict[tuple[str, str, str], float] | None = None,
    ) -> MarketState:
        """Clear a single product market using double-auction mechanism.
        
        Args:
            product: Commodity identifier (e.g., "steel_hrc")
            supply_offers: All supply offers for this product
            demand_requests: All demand requests for this product
            round_number: Current simulation round
            prev_price: Price from previous round (None for round 1)
            tariff_lookup: Optional dict[(from_country, to_country, commodity)] -> tariff_rate_pct
            
        Returns:
            MarketState with clearing price, volume, unmet demand, etc.
        """
        if not supply_offers and not demand_requests:
            # No market activity
            return MarketState(
                commodity=product,
                spot_price=prev_price or 100.0,  # Default price if no history
                prev_price=prev_price,
                price_change_pct=None,
                demand=0.0,
                supply=0.0,
                volume_cleared=0.0,
                unmet_demand=0.0,
                unmet_demand_pct=0.0,
                price_history=[],
            )

        # Sort supply ascending (lowest ask first), demand descending (highest bid first)
        sorted_supply = sorted(supply_offers, key=lambda x: x.min_price_usd_per_mt)
        sorted_demand = sorted(demand_requests, key=lambda x: x.max_price_usd_per_mt, reverse=True)

        # Calculate total supply and demand
        total_supply = sum(offer.volume_mt for offer in supply_offers)
        total_demand = sum(req.volume_mt for req in demand_requests)

        # Greedy matching
        volume_cleared = 0.0
        trade_prices = []  # Track all successful trade prices for averaging

        supply_remaining = {offer.agent_id: offer.volume_mt for offer in sorted_supply}
        demand_remaining = {req.agent_id: req.volume_mt for req in sorted_demand}

        s_idx = 0
        d_idx = 0

        while s_idx < len(sorted_supply) and d_idx < len(sorted_demand):
            offer = sorted_supply[s_idx]
            request = sorted_demand[d_idx]

            # Check if trade is possible
            ask = offer.min_price_usd_per_mt
            bid = request.max_price_usd_per_mt

            if bid < ask:
                # No more profitable trades
                break

            # Apply tariff if lookup provided
            # TODO: In full implementation, map agent_ids to countries
            effective_price = ask  # Simplified - tariffs would increase this
            
            if effective_price > bid:
                # Tariff pushed price above buyer's max
                d_idx += 1
                continue

            # Calculate clearing price as midpoint
            clearing_price = (ask + bid) / 2.0

            # Determine volume to trade
            supply_available = supply_remaining[offer.agent_id]
            demand_needed = demand_remaining[request.agent_id]
            trade_volume = min(supply_available, demand_needed)

            if trade_volume < self.FLOATING_POINT_EPSILON:
                # Exhausted - move to next
                if supply_available < self.FLOATING_POINT_EPSILON:
                    s_idx += 1
                if demand_needed < self.FLOATING_POINT_EPSILON:
                    d_idx += 1
                continue

            # Execute trade
            volume_cleared += trade_volume
            trade_prices.append(clearing_price)
            supply_remaining[offer.agent_id] -= trade_volume
            demand_remaining[request.agent_id] -= trade_volume

            # Move to next offer/request if exhausted
            if supply_remaining[offer.agent_id] < self.FLOATING_POINT_EPSILON:
                s_idx += 1
            if demand_remaining[request.agent_id] < self.FLOATING_POINT_EPSILON:
                d_idx += 1

        # Calculate clearing price
        if trade_prices:
            spot_price = sum(trade_prices) / len(trade_prices)
        elif prev_price is not None:
            # No trades cleared - adjust price based on supply/demand imbalance
            if total_supply > total_demand:
                # Excess supply → price decreases
                surplus_pct = (total_supply - total_demand) / total_demand if total_demand > 0 else 1.0
                price_delta = -surplus_pct * self.SUPPLY_SURPLUS_FACTOR * prev_price
                spot_price = prev_price + price_delta
            else:
                # Excess demand → price increases
                surplus_pct = (total_demand - total_supply) / total_supply if total_supply > 0 else 1.0
                price_delta = surplus_pct * self.DEMAND_SURPLUS_FACTOR * prev_price
                spot_price = prev_price + price_delta
        else:
            # Round 1 with no trades - use mid-range of bids/asks
            if sorted_supply and sorted_demand:
                spot_price = (sorted_supply[0].min_price_usd_per_mt + sorted_demand[0].max_price_usd_per_mt) / 2.0
            elif sorted_supply:
                spot_price = sorted_supply[0].min_price_usd_per_mt
            elif sorted_demand:
                spot_price = sorted_demand[0].max_price_usd_per_mt
            else:
                spot_price = 100.0  # Default fallback

        # Apply price change cap
        if prev_price is not None:
            price_change_pct = ((spot_price - prev_price) / prev_price) * 100
            
            if abs(price_change_pct) > self.PRICE_CHANGE_CAP_PCT:
                # Cap the change
                capped_change = self.PRICE_CHANGE_CAP_PCT if price_change_pct > 0 else -self.PRICE_CHANGE_CAP_PCT
                spot_price = prev_price * (1 + capped_change / 100)
                price_change_pct = capped_change
        else:
            price_change_pct = None  # Round 1

        # Calculate unmet demand
        unmet_demand = max(0.0, total_demand - volume_cleared)
        unmet_demand_pct = (unmet_demand / total_demand * 100) if total_demand > 0 else 0.0

        return MarketState(
            commodity=product,
            spot_price=spot_price,
            prev_price=prev_price,
            price_change_pct=price_change_pct,
            demand=total_demand,
            supply=total_supply,
            volume_cleared=volume_cleared,
            unmet_demand=unmet_demand,
            unmet_demand_pct=unmet_demand_pct,
            price_history=[spot_price],
        )

    def clear_all_products(
        self,
        all_offers: list[SupplyOffer],
        all_requests: list[DemandRequest],
        round_number: int,
        prev_market_states: dict[str, MarketState] | None = None,
        tariff_lookup: dict[tuple[str, str, str], float] | None = None,
    ) -> dict[str, MarketState]:
        """Clear all product markets in parallel.
        
        Args:
            all_offers: All supply offers across all products
            all_requests: All demand requests across all products
            round_number: Current simulation round
            prev_market_states: Previous round's market states (for price history)
            tariff_lookup: Optional tariff rates by route
            
        Returns:
            Dict mapping product -> MarketState
        """
        # Group by product — always include previously known commodities so their
        # state (price history, etc.) is preserved even when no bids arrive this round.
        products = set(offer.product for offer in all_offers) | set(req.product for req in all_requests)
        if prev_market_states:
            products |= set(prev_market_states.keys())
        
        result = {}
        for product in products:
            product_offers = [o for o in all_offers if o.product == product]
            product_requests = [r for r in all_requests if r.product == product]

            prev_state = prev_market_states.get(product) if prev_market_states else None
            prev_price = prev_state.spot_price if prev_state else None

            new_state = self.clear_product(
                product=product,
                supply_offers=product_offers,
                demand_requests=product_requests,
                round_number=round_number,
                prev_price=prev_price,
                tariff_lookup=tariff_lookup,
            )

            # Carry forward accumulated price history from previous rounds.
            if prev_state and prev_state.price_history:
                new_state.price_history = prev_state.price_history + [new_state.spot_price]
            elif not new_state.price_history:
                new_state.price_history = [new_state.spot_price]

            result[product] = new_state
        
        return result
