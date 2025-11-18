"""
ATHENA-X System Validation Test
Tests core system components without external dependencies
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import yaml


def test_import_structure():
    """Test that all core modules can be imported"""
    logger.info("="*60)
    logger.info(" TEST 1: Module Import Structure")
    logger.info("="*60)

    modules_to_test = [
        ("Base Agent", "src.agents.base_agent", ["BaseAgent", "VetoAgent"]),
        ("Technical Agent", "src.agents.technical_agent", ["TechnicalAnalysisAgent"]),
        ("Sentiment Agent", "src.agents.sentiment_agent", ["SentimentAnalysisAgent"]),
        ("Risk Agent", "src.agents.risk_agent", ["RiskManagementAgent"]),
        ("Orchestrator", "src.orchestration.orchestrator", ["ATHENAOrchestrator"]),
        ("Validation Pipeline", "src.validation.validation_pipeline", ["ValidationPipeline"]),
        ("Risk Metrics", "src.risk.risk_metrics", ["RiskMetrics"]),
        ("Correlation Manager", "src.risk.correlation_manager", ["CorrelationManager"]),
        ("Ensemble Sentiment", "src.models.ensemble_sentiment", ["EnsembleSentiment"]),
    ]

    passed = 0
    failed = 0

    for name, module_path, classes in modules_to_test:
        try:
            module = __import__(module_path, fromlist=classes)
            for cls in classes:
                if hasattr(module, cls):
                    logger.success(f"✓ {name}: {cls} imported successfully")
                    passed += 1
                else:
                    logger.error(f"✗ {name}: {cls} not found in module")
                    failed += 1
        except ImportError as e:
            logger.error(f"✗ {name}: Import failed - {str(e)}")
            failed += 1
        except Exception as e:
            logger.error(f"✗ {name}: Unexpected error - {str(e)}")
            failed += 1

    logger.info(f"\nImport Tests: {passed} passed, {failed} failed")
    return passed, failed


def test_config_structure():
    """Test configuration file structure"""
    logger.info("\n" + "="*60)
    logger.info(" TEST 2: Configuration Structure")
    logger.info("="*60)

    config_file = Path('config/settings.yaml')
    if not config_file.exists():
        logger.error("✗ config/settings.yaml not found")
        return 0, 1

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)

        required_sections = ['agents', 'risk', 'data', 'consensus']
        passed = 0
        failed = 0

        for section in required_sections:
            if section in config:
                logger.success(f"✓ Config section '{section}' exists")
                passed += 1
            else:
                logger.error(f"✗ Config section '{section}' missing")
                failed += 1

        logger.info(f"\nConfig Tests: {passed} passed, {failed} failed")
        return passed, failed

    except Exception as e:
        logger.error(f"✗ Failed to load config: {str(e)}")
        return 0, 1


def test_risk_metrics():
    """Test risk metrics calculations"""
    logger.info("\n" + "="*60)
    logger.info(" TEST 3: Risk Metrics Calculations")
    logger.info("="*60)

    try:
        from src.risk.risk_metrics import RiskMetrics

        metrics = RiskMetrics(risk_free_rate=0.02)

        # Sample returns
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, 0.005, -0.008, 0.012]

        # Calculate metrics
        all_metrics = metrics.calculate_all_metrics(returns)

        logger.info("Risk Metrics Calculated:")
        logger.info(f"  VaR (95%): {all_metrics['var_95']:.4f}")
        logger.info(f"  CVaR (95%): {all_metrics['cvar_95']:.4f}")
        logger.info(f"  Sharpe Ratio: {all_metrics['sharpe_ratio']:.2f}")
        logger.info(f"  Max Drawdown: {all_metrics['max_drawdown']:.4f}")

        # Validation
        assert all_metrics['var_95'] >= 0, "Invalid VaR"
        assert isinstance(all_metrics['sharpe_ratio'], float), "Invalid Sharpe ratio"

        logger.success("✓ Risk metrics test passed")
        return 1, 0

    except Exception as e:
        logger.error(f"✗ Risk metrics test failed: {str(e)}")
        return 0, 1


def test_agent_initialization():
    """Test agent initialization with mock config"""
    logger.info("\n" + "="*60)
    logger.info(" TEST 4: Agent Initialization")
    logger.info("="*60)

    mock_config = {
        'weight': 0.35,
        'enabled': True,
        'thresholds': {
            'min_confidence': 0.60,
            'strong_trend_adx': 25
        }
    }

    try:
        from src.agents.technical_agent import TechnicalAnalysisAgent
        from src.agents.sentiment_agent import SentimentAnalysisAgent
        from src.agents.risk_agent import RiskManagementAgent

        # Initialize agents
        tech_agent = TechnicalAnalysisAgent(config=mock_config)
        logger.success(f"✓ Technical Agent initialized: weight={tech_agent.weight}")

        sent_agent = SentimentAnalysisAgent(config=mock_config)
        logger.success(f"✓ Sentiment Agent initialized: weight={sent_agent.weight}")

        risk_config = {
            **mock_config,
            'position_limits': {'max_position_pct': 0.02, 'max_total_exposure': 0.06},
            'circuit_breakers': {
                'max_daily_loss_pct': 0.05,
                'max_drawdown_pct': 0.15,
                'max_consecutive_losses': 5
            }
        }
        risk_agent = RiskManagementAgent(config=risk_config)
        logger.success(f"✓ Risk Agent initialized: VETO power={hasattr(risk_agent, 'veto_power')}")

        logger.success("✓ All agents initialized successfully")
        return 3, 0

    except Exception as e:
        logger.error(f"✗ Agent initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0, 1


def test_file_structure():
    """Test that all required files exist"""
    logger.info("\n" + "="*60)
    logger.info(" TEST 5: File Structure")
    logger.info("="*60)

    required_files = [
        "src/agents/base_agent.py",
        "src/agents/technical_agent.py",
        "src/agents/sentiment_agent.py",
        "src/agents/risk_agent.py",
        "src/orchestration/orchestrator.py",
        "src/validation/validation_pipeline.py",
        "src/risk/risk_metrics.py",
        "src/risk/correlation_manager.py",
        "src/models/ensemble_sentiment.py",
        "src/execution/order_manager.py",
        "src/backtesting/vectorbt_engine.py",
        "config/settings.yaml",
        "scripts/deploy.py",
        "PHASE_3_COMPLETE.md",
        "CURRENT_STATUS.md"
    ]

    passed = 0
    failed = 0

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            logger.success(f"✓ {file_path}")
            passed += 1
        else:
            logger.error(f"✗ {file_path} missing")
            failed += 1

    logger.info(f"\nFile Structure Tests: {passed} passed, {failed} failed")
    return passed, failed


def main():
    """Run all validation tests"""
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    logger.info("="*60)
    logger.info(" ATHENA-X SYSTEM VALIDATION TESTS")
    logger.info("="*60)

    total_passed = 0
    total_failed = 0

    try:
        # Run tests
        p, f = test_file_structure()
        total_passed += p
        total_failed += f

        p, f = test_config_structure()
        total_passed += p
        total_failed += f

        p, f = test_import_structure()
        total_passed += p
        total_failed += f

        p, f = test_agent_initialization()
        total_passed += p
        total_failed += f

        p, f = test_risk_metrics()
        total_passed += p
        total_failed += f

        # Summary
        logger.info("\n" + "="*60)
        logger.info(" TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Passed: {total_passed}")
        logger.info(f"Total Failed: {total_failed}")
        logger.info(f"Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")

        if total_failed == 0:
            logger.success("\n✓ ALL VALIDATION TESTS PASSED")
            logger.info("System structure is valid and ready for deployment")
        else:
            logger.warning(f"\n⚠ {total_failed} test(s) failed")
            logger.info("Please review the failures above")

    except Exception as e:
        logger.error(f"✗ VALIDATION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
