"""
Flask web application for Kalshi Trading Bot Dashboard.
"""
import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS

try:
    from kalshi_bot.config import BotConfig
    from kalshi_bot.kalshi.auth import KalshiSigner
    from kalshi_bot.kalshi.http import KalshiHTTPClient, RateLimiter
    from kalshi_bot.kalshi.api import KalshiAPI
    from kalshi_bot.strategy import MarketSnapshot, FeeAwareFairValueStrategy, FeeAwareConfig
    from kalshi_bot.fair_prob import StaticFairProbProvider, LiveDataWinProbProvider
    from kalshi_bot.risk import RiskManager, RiskLimits
    from kalshi_bot.execution import Executor
    from kalshi_bot.database import Database
    from kalshi_bot.monitoring import MonitoringSystem
    from kalshi_bot.order_manager import OrderManager
    from kalshi_bot.performance import PerformanceAnalyzer
    from kalshi_bot.logging_config import setup_logging, get_logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
bot_state = {
    'running': False,
    'paper_mode': True,
    'last_update': None,
    'stats': {},
}
bot_thread: Optional[threading.Thread] = None
bot_components: Dict[str, Any] = {}
logger = setup_logging(log_dir="logs", log_level="INFO")


def init_bot_components():
    """Initialize bot components"""
    try:
        cfg = BotConfig.load()
        
        signer = KalshiSigner.from_pem_file(cfg.api_key_id, cfg.private_key_path)
        http = KalshiHTTPClient(
            host=cfg.host,
            signer=signer,
            read_rl=RateLimiter(per_second=15.0),
            write_rl=RateLimiter(per_second=8.0),
            timeout_s=10.0,
        )
        api = KalshiAPI(http)
        
        db = Database(db_path="kalshi_bot.db")
        monitoring = MonitoringSystem(db)
        order_manager = OrderManager(api, db)
        
        provider = (
            LiveDataWinProbProvider(
                api=api,
                fair_probs_yes=cfg.fair_probs,
                coef_score_diff=cfg.coef_score_diff,
                coef_time_left_min=cfg.coef_time_left_min,
                coef_prior=cfg.coef_prior,
            )
            if cfg.use_live_data
            else StaticFairProbProvider(cfg.fair_probs)
        )
        
        strat = FeeAwareFairValueStrategy(
            FeeAwareConfig(
                edge_threshold=cfg.edge_threshold,
                fee_kind=cfg.fee_kind,
                taker_fee_rate=cfg.taker_fee_rate,
                maker_fee_rate=cfg.maker_fee_rate,
                min_net_ev_per_contract=cfg.min_net_ev_per_contract,
                post_only=cfg.post_only,
            ),
            provider=provider,
            order_count=min(5, cfg.max_order_count),
        )
        
        risk = RiskManager(api, RiskLimits(cfg.max_order_count, cfg.max_position_per_ticker))
        exe = Executor(api, risk, paper=bot_state['paper_mode'], db=db, monitoring=monitoring)
        
        bot_components.update({
            'config': cfg,
            'api': api,
            'db': db,
            'monitoring': monitoring,
            'order_manager': order_manager,
            'strategy': strat,
            'executor': exe,
            'performance_analyzer': PerformanceAnalyzer(db),
        })
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize bot components: {e}")
        return False


def bot_loop():
    """Main bot trading loop"""
    global bot_state
    
    if 'config' not in bot_components:
        logger.error("Bot components not initialized")
        return
    
    cfg = bot_components['config']
    api = bot_components['api']
    strategy = bot_components['strategy']
    executor = bot_components['executor']
    db = bot_components['db']
    monitoring = bot_components['monitoring']
    
    loop_count = 0
    while bot_state['running']:
        try:
            loop_count += 1
            
            # Fetch market data
            snaps = []
            for t in cfg.tickers:
                try:
                    ob = api.get_orderbook(t, depth=10)
                    best = api.best_prices_from_orderbook(ob)
                    snaps.append(MarketSnapshot(ticker=t, best=best))
                    
                    # Save snapshot
                    db.save_market_snapshot(
                        ticker=t,
                        yes_bid=best.yes_bid,
                        yes_ask=best.yes_ask,
                        no_bid=best.no_bid,
                        no_ask=best.no_ask,
                    )
                except Exception as e:
                    logger.error(f"Error fetching orderbook for {t}: {e}")
            
            # Generate signals
            intents = strategy.generate(snaps)
            
            # Execute orders
            if intents:
                results = executor.execute(intents)
                bot_state['stats']['last_trades'] = len(results)
                bot_state['stats']['last_executed'] = sum(1 for r in results if r.ok)
            
            # Update stats
            bot_state['stats'].update({
                'loop_count': loop_count,
                'last_update': datetime.utcnow().isoformat(),
                'active_orders': len(bot_components['order_manager'].get_active_orders()),
            })
            
            # Emit update via WebSocket
            socketio.emit('bot_update', bot_state['stats'])
            
            time.sleep(cfg.poll_seconds)
            
        except Exception as e:
            logger.error(f"Error in bot loop: {e}")
            time.sleep(5)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get bot status"""
    health = {}
    if 'monitoring' in bot_components:
        health = bot_components['monitoring'].check_health()
    
    return jsonify({
        'running': bot_state['running'],
        'paper_mode': bot_state['paper_mode'],
        'stats': bot_state['stats'],
        'health': health,
    })


@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    global bot_thread
    
    if bot_state['running']:
        return jsonify({'error': 'Bot is already running'}), 400
    
    if not init_bot_components():
        return jsonify({'error': 'Failed to initialize bot components'}), 500
    
    data = request.get_json() or {}
    bot_state['paper_mode'] = data.get('paper_mode', True)
    bot_state['running'] = True
    
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    
    logger.info("Bot started")
    return jsonify({'status': 'started'})


@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    bot_state['running'] = False
    logger.info("Bot stopped")
    return jsonify({'status': 'stopped'})


@app.route('/api/orders')
def get_orders():
    """Get orders"""
    if 'order_manager' not in bot_components:
        return jsonify({'orders': []})
    
    status = request.args.get('status', 'all')
    ticker = request.args.get('ticker')
    
    if status == 'active':
        orders = bot_components['order_manager'].get_active_orders()
        return jsonify({'orders': [order.__dict__ for order in orders]})
    else:
        orders = bot_components['order_manager'].get_order_history(ticker=ticker, limit=100)
        return jsonify({'orders': orders})


@app.route('/api/orders/<order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Cancel an order"""
    if 'order_manager' not in bot_components:
        return jsonify({'error': 'Order manager not initialized'}), 500
    
    success = bot_components['order_manager'].cancel_order(order_id)
    return jsonify({'success': success})


@app.route('/api/orders/cancel-all', methods=['POST'])
def cancel_all_orders():
    """Cancel all active orders"""
    if 'order_manager' not in bot_components:
        return jsonify({'error': 'Order manager not initialized'}), 500
    
    ticker = request.args.get('ticker')
    count = bot_components['order_manager'].cancel_all_orders(ticker=ticker)
    return jsonify({'cancelled': count})


@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    if 'performance_analyzer' not in bot_components:
        return jsonify({'error': 'Performance analyzer not initialized'}), 500
    
    days = int(request.args.get('days', 30))
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    metrics = bot_components['performance_analyzer'].analyze_performance(
        start_date=start_date,
        end_date=end_date,
    )
    
    return jsonify({
        'metrics': {
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'win_rate': metrics.win_rate,
            'total_pnl': metrics.total_pnl,
            'net_pnl': metrics.net_pnl,
            'sharpe_ratio': metrics.sharpe_ratio,
            'profit_factor': metrics.profit_factor,
        }
    })


@app.route('/api/markets')
def get_markets():
    """Get market data"""
    if 'api' not in bot_components:
        return jsonify({'markets': []})
    
    try:
        cfg = bot_components['config']
        markets = []
        
        for ticker in cfg.tickers:
            try:
                ob = bot_components['api'].get_orderbook(ticker, depth=10)
                best = bot_components['api'].best_prices_from_orderbook(ob)
                markets.append({
                    'ticker': ticker,
                    'yes_bid': best.yes_bid,
                    'yes_ask': best.yes_ask,
                    'no_bid': best.no_bid,
                    'no_ask': best.no_ask,
                    'mid_price': best.mid_yes,
                })
            except Exception as e:
                logger.error(f"Error fetching market {ticker}: {e}")
        
        return jsonify({'markets': markets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def get_health():
    """Get system health"""
    if 'monitoring' not in bot_components:
        return jsonify({'status': 'unknown'})
    
    health = bot_components['monitoring'].check_health()
    return jsonify(health)


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("Client connected")
    emit('connected', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info("Client disconnected")


if __name__ == '__main__':
    # Initialize bot components
    init_bot_components()
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

