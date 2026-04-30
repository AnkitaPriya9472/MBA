"""Unit tests for MarketClearing.

Story 20: Test double-auction clearing logic, price discovery, and constraints.
"""

import pytest

from simulation.market import MarketClearing, SupplyOffer, DemandRequest


def test_excess_supply_decreases_price():
    """When supply > demand, price should decrease."""
    market = MarketClearing()
    
    # 2× supply relative to demand
    supply_offers = [
        SupplyOffer(agent_id="supplier1", product="steel_hrc", volume_mt=2000.0, min_price_usd_per_mt=600.0),
        SupplyOffer(agent_id="supplier2", product="steel_hrc", volume_mt=2000.0, min_price_usd_per_mt=600.0),
    ]
    
    demand_requests = [
        DemandRequest(agent_id="buyer1", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=700.0),
        DemandRequest(agent_id="buyer2", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=700.0),
    ]
    
    prev_price = 680.0
    
    result = market.clear_product(
        product="steel_hrc",
        supply_offers=supply_offers,
        demand_requests=demand_requests,
        round_number=2,
        prev_price=prev_price,
    )
    
    # Price should decrease due to excess supply
    assert result.spot_price < prev_price
    assert result.supply == 4000.0
    assert result.demand == 2000.0
    assert result.volume_cleared == 2000.0  # All demand met


def test_excess_demand_increases_price():
    """When demand > supply, price should increase."""
    market = MarketClearing()
    
    # 2× demand relative to supply
    supply_offers = [
        SupplyOffer(agent_id="supplier1", product="steel_hrc", volume_mt=1000.0, min_price_usd_per_mt=600.0),
    ]
    
    demand_requests = [
        DemandRequest(agent_id="buyer1", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=750.0),
        DemandRequest(agent_id="buyer2", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=750.0),
    ]
    
    prev_price = 680.0
    
    result = market.clear_product(
        product="steel_hrc",
        supply_offers=supply_offers,
        demand_requests=demand_requests,
        round_number=2,
        prev_price=prev_price,
    )
    
    # Price should increase due to excess demand
    assert result.spot_price > prev_price
    assert result.supply == 1000.0
    assert result.demand == 2000.0
    assert result.volume_cleared == 1000.0  # All supply cleared
    assert result.unmet_demand == 1000.0


def test_price_change_capped_at_25_percent():
    """Price change should be capped at ±25% per round."""
    market = MarketClearing()
    
    # Extreme excess demand to trigger large price increase
    supply_offers = [
        SupplyOffer(agent_id="supplier1", product="steel_hrc", volume_mt=100.0, min_price_usd_per_mt=500.0),
    ]
    
    demand_requests = [
        DemandRequest(agent_id="buyer1", product="steel_hrc", volume_mt=10000.0, max_price_usd_per_mt=2000.0),
    ]
    
    prev_price = 600.0
    
    result = market.clear_product(
        product="steel_hrc",
        supply_offers=supply_offers,
        demand_requests=demand_requests,
        round_number=2,
        prev_price=prev_price,
    )
    
    # Price change should be capped at +25%
    max_allowed_price = prev_price * 1.25
    assert result.spot_price <= max_allowed_price + 0.01  # Allow small floating point error
    assert result.price_change_pct == pytest.approx(25.0, abs=0.1)


def test_unmet_demand_pct_calculated_correctly():
    """Unmet demand percentage should be correct."""
    market = MarketClearing()
    
    supply_offers = [
        SupplyOffer(agent_id="supplier1", product="steel_hrc", volume_mt=700.0, min_price_usd_per_mt=600.0),
    ]
    
    demand_requests = [
        DemandRequest(agent_id="buyer1", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=750.0),
    ]
    
    result = market.clear_product(
        product="steel_hrc",
        supply_offers=supply_offers,
        demand_requests=demand_requests,
        round_number=1,
    )
    
    # 700 MT supplied, 1000 MT demanded → 300 MT unmet → 30%
    assert result.unmet_demand == 300.0
    assert result.unmet_demand_pct == pytest.approx(30.0, abs=0.1)


def test_tariff_above_buyer_max_prevents_trade():
    """If effective price with tariff > buyer max, no trade should occur."""
    # This test requires tariff lookup implementation
    # For now, we'll test the basic no-trade scenario
    market = MarketClearing()
    
    # Seller asks 700, buyer bids max 650 → no trade
    supply_offers = [
        SupplyOffer(agent_id="supplier1", product="steel_hrc", volume_mt=1000.0, min_price_usd_per_mt=700.0),
    ]
    
    demand_requests = [
        DemandRequest(agent_id="buyer1", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=650.0),
    ]
    
    result = market.clear_product(
        product="steel_hrc",
        supply_offers=supply_offers,
        demand_requests=demand_requests,
        round_number=1,
    )
    
    # No trade should clear (bid < ask)
    assert result.volume_cleared == 0.0
    assert result.unmet_demand == 1000.0


def test_round_one_price_change_is_none():
    """In round 1, price_change_pct should be None, not 0.0."""
    market = MarketClearing()
    
    supply_offers = [
        SupplyOffer(agent_id="supplier1", product="steel_hrc", volume_mt=1000.0, min_price_usd_per_mt=600.0),
    ]
    
    demand_requests = [
        DemandRequest(agent_id="buyer1", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=700.0),
    ]
    
    result = market.clear_product(
        product="steel_hrc",
        supply_offers=supply_offers,
        demand_requests=demand_requests,
        round_number=1,
        prev_price=None,  # Round 1 = no previous price
    )
    
    # Round 1 should have None, not 0.0
    assert result.price_change_pct is None
    assert result.prev_price is None


def test_clear_all_products_groups_correctly():
    """clear_all_products should group offers/requests by product."""
    market = MarketClearing()
    
    all_offers = [
        SupplyOffer(agent_id="steel_supplier", product="steel_hrc", volume_mt=1000.0, min_price_usd_per_mt=600.0),
        SupplyOffer(agent_id="ore_supplier", product="iron_ore", volume_mt=5000.0, min_price_usd_per_mt=100.0),
    ]
    
    all_requests = [
        DemandRequest(agent_id="steel_buyer", product="steel_hrc", volume_mt=1000.0, max_price_usd_per_mt=700.0),
        DemandRequest(agent_id="ore_buyer", product="iron_ore", volume_mt=5000.0, max_price_usd_per_mt=120.0),
    ]
    
    results = market.clear_all_products(
        all_offers=all_offers,
        all_requests=all_requests,
        round_number=1,
    )
    
    # Should have two product markets
    assert "steel_hrc" in results
    assert "iron_ore" in results
    
    # Each should have correct volumes
    assert results["steel_hrc"].volume_cleared == 1000.0
    assert results["iron_ore"].volume_cleared == 5000.0
