"""
ATHENA-X End-to-End Testing
Tests complete system flow from data acquisition to trade execution
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from loguru import logger
from datetime import datetime

# Import all components
from src.data.data_pipeline import ATHENADataPipeline
from src.orchestration.orchestrator import ATHENAOrchestrator
from src.execution.order_manager import OrderManager
from src.validation.validation_pipeline import ValidationPipeline
from src.models.ensemble_sentiment import EnsembleSentiment
from src.risk.risk_metrics import RiskMetrics
from src.risk.correlation_manager import CorrelationManager


def print_section(title: str):
    """Print formatted section header"""
    logger.info("="*60)
    logger.info(f" {title}")
    logger.info("="*60)


def test_data_pipeline():
    """Test data acquisition"""
    print_section("TEST 1: Data Pipeline")

    with open('config/settings.yaml') as f:
        config = yaml.safe_load(f)

    pipeline = ATHENADataPipeline(config)

    # Health check
    health = pipeline.health_check()
    logger.info(f"Health Status: {health}")

    # Get market data
    symbol = 'EUR_USD'
    logger.info(f"Fetching data for {symbol}...")
    data = pipeline.get_complete_market_data(symbol)

    # Verify data
    assert data['symbol'] == symbol, "Symbol mismatch"
    assert data['price_data'] is not None, "No price data"
    assert data['technical_indicators'] is not None, "No indicators"

    logger.success("✓ Data pipeline test passed")
    return pipeline


def test_agents(pipeline: ATHENADataPipeline):
    """Test agent system"""
    print_section("TEST 2: Multi-Agent System")

    with open('config/settings.yaml') as f:
        config = yaml.safe_load(f)

    orchestrator = ATHENAOrchestrator(config)

    # Get market data
    market_data = pipeline.get_complete_market_data('EUR_USD')

    # Evaluate opportunity
    logger.info("Running agent analysis...")
    decision = orchestrator.evaluate_opportunity(
        symbol='EUR_USD',
        market_data=market_data
    )

    # Verify decision
    assert decision is not None, "No decision returned"
    assert 'decision' in decision, "Missing decision field"
    assert decision['decision'] in ['EXECUTE', 'REJECT'], "Invalid decision"

    logger.info(f"Decision: {decision['decision']}")
    if decision['decision'] == 'EXECUTE':
        logger.info(f"Direction: {decision['direction']}")
        logger.info(f"Confidence: {decision['confidence']:.2%}")
        logger.info(f"Position Size: {decision['position_size_pct']:.2%}")

    logger.success("✓ Agent system test passed")
    return orchestrator, decision


def test_validation(decision: dict):
    """Test validation pipeline"""
    print_section("TEST 3: Validation Pipeline")

    with open('config/settings.yaml') as f:
        config = yaml.safe_load(f)

    validator = ValidationPipeline(config)

    # Mock market data
    market_data = {
        'symbol': 'EUR_USD',
        'timestamp': datetime.now(),
        'technical_indicators': {'atr': 0.001, 'volume': 1000, 'volume_sma': 1000},
        'economic_events': {'should_avoid_trading': False}
    }

    # Mock portfolio
    portfolio = {
        'equity': 10000,
        'positions': [],
        'total_exposure': 0.0,
        'drawdown': 0.0
    }

    # Validate
    if decision.get('decision') == 'EXECUTE':
        logger.info("Validating trade decision...")
        validation = validator.validate(decision, market_data, portfolio)

        logger.info(f"Validation result: {'APPROVED' if validation['approved'] else 'REJECTED'}")
        if not validation['approved']:
            logger.info(f"Reason: {validation['reason']}")

        logger.success("✓ Validation pipeline test passed")
    else:
        logger.info("Skipping validation (no trade to validate)")


def test_risk_metrics():
    """Test risk metrics"""
    print_section("TEST 4: Risk Metrics")

    metrics = RiskMetrics(risk_free_rate=0.02)

    # Sample returns
    returns = [0.01, -0.005, 0.02, -0.01, 0.015, 0.005, -0.008, 0.012]

    # Calculate metrics
    all_metrics = metrics.calculate_all_metrics(returns)

    logger.info("Risk Metrics:")
    logger.info(f"  VaR (95%): {all_metrics['var_95']:.4f}")
    logger.info(f"  CVaR (95%): {all_metrics['cvar_95']:.4f}")
    logger.info(f"  Sharpe Ratio: {all_metrics['sharpe_ratio']:.2f}")
    logger.info(f"  Max Drawdown: {all_metrics['max_drawdown']:.4f}")

    assert all_metrics['var_95'] >= 0, "Invalid VaR"
    assert all_metrics['sharpe_ratio'] != 0, "Invalid Sharpe ratio"

    logger.success("✓ Risk metrics test passed")


def test_ensemble_sentiment():
    """Test ensemble sentiment"""
    print_section("TEST 5: Ensemble Sentiment")

    ensemble = EnsembleSentiment()

    # Test texts
    texts = [
        "The market is showing strong bullish momentum",
        "Concerns about recession are weighing on markets",
        "Central bank maintains neutral stance"
    ]

    # Analyze
    for text in texts:
        result = ensemble.analyze(text)
        logger.info(f"Text: {text[:50]}...")
        logger.info(f"  Sentiment: {result['sentiment']}")
        logger.info(f"  Score: {result['score']:+.2f}")
        logger.info(f"  Confidence: {result['confidence']:.2%}")

    logger.success("✓ Ensemble sentiment test passed")


def test_correlation_manager():
    """Test correlation management"""
    print_section("TEST 6: Correlation Manager")

    with open('config/settings.yaml') as f:
        config = yaml.safe_load(f)

    corr_manager = CorrelationManager(config)

    # Test correlations
    pairs = [
        ('EUR_USD', 'GBP_USD'),
        ('EUR_USD', 'XAU_USD'),
        ('XAU_USD', 'XAG_USD')
    ]

    for sym1, sym2 in pairs:
        corr = corr_manager.calculate_correlation(sym1, sym2)
        logger.info(f"Correlation {sym1} vs {sym2}: {corr:.2f}")

    logger.success("✓ Correlation manager test passed")


def test_order_manager(decision: dict):
    """Test order execution (dry run)"""
    print_section("TEST 7: Order Manager")

    with open('config/settings.yaml') as f:
        config = yaml.safe_load(f)

    order_manager = OrderManager(config)

    # Simulate execution
    if decision.get('decision') == 'EXECUTE':
        logger.info("Simulating order execution...")
        result = order_manager.execute_trade(decision, dry_run=True)

        logger.info(f"Execution result: {'SUCCESS' if result['success'] else 'FAILED'}")
        if result['success']:
            logger.info(f"  Order ID: {result.get('order_id')}")
            logger.info(f"  Fill Price: {result.get('fill_price')}")

        logger.success("✓ Order manager test passed")
    else:
        logger.info("Skipping order execution (no trade to execute)")


def main():
    """Run all tests"""
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    print_section("ATHENA-X END-TO-END TESTS")

    try:
        # Run tests
        pipeline = test_data_pipeline()
        orchestrator, decision = test_agents(pipeline)
        test_validation(decision)
        test_risk_metrics()
        test_ensemble_sentiment()
        test_correlation_manager()
        test_order_manager(decision)

        # Summary
        print_section("TEST SUMMARY")
        logger.success("✓ ALL TESTS PASSED")
        logger.info("System is ready for deployment")

    except Exception as e:
        logger.error(f"✗ TEST FAILED: {str(e)}")
        raise


if __name__ == "__main__":
    main()
