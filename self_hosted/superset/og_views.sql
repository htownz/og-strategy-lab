
-- Recent Signals View for Superset
CREATE OR REPLACE VIEW superset_recent_signals AS
SELECT 
    id, 
    symbol, 
    direction, 
    confidence, 
    price_at_signal, 
    timestamp,
    indicators::jsonb,
    CASE 
        WHEN indicators::jsonb->>'strategy' IS NOT NULL THEN indicators::jsonb->>'strategy'
        ELSE 'OG Strategy'
    END as strategy,
    CASE 
        WHEN indicators::jsonb->>'timeframe' IS NOT NULL THEN indicators::jsonb->>'timeframe'
        ELSE '1H'
    END as timeframe
FROM signal
ORDER BY timestamp DESC
LIMIT 100;

-- Signal Performance View
CREATE OR REPLACE VIEW superset_signal_performance AS
SELECT 
    s.id,
    s.symbol,
    s.direction,
    s.confidence,
    s.price_at_signal,
    s.timestamp,
    CASE 
        WHEN s.indicators::jsonb->>'strategy' IS NOT NULL THEN s.indicators::jsonb->>'strategy'
        ELSE 'OG Strategy'
    END as strategy,
    CASE 
        WHEN s.indicators::jsonb->>'timeframe' IS NOT NULL THEN s.indicators::jsonb->>'timeframe'
        ELSE '1H'
    END as timeframe,
    t.status,
    t.order_filled_price,
    t.close_price,
    t.profit_loss,
    t.profit_loss_percent,
    t.trade_duration_minutes
FROM signal s
LEFT JOIN trade t ON s.id = t.signal_id
WHERE t.id IS NOT NULL;

-- Strategy Performance View
CREATE OR REPLACE VIEW superset_strategy_performance AS
SELECT 
    CASE 
        WHEN s.indicators::jsonb->>'strategy' IS NOT NULL THEN s.indicators::jsonb->>'strategy'
        ELSE 'OG Strategy'
    END as strategy,
    CASE 
        WHEN s.indicators::jsonb->>'timeframe' IS NOT NULL THEN s.indicators::jsonb->>'timeframe'
        ELSE '1H'
    END as timeframe,
    COUNT(s.id) as signal_count,
    COUNT(t.id) as trade_count,
    AVG(t.profit_loss) as avg_profit_loss,
    SUM(t.profit_loss) as total_profit_loss,
    COUNT(CASE WHEN t.profit_loss > 0 THEN 1 END)::float / NULLIF(COUNT(t.id), 0) as win_rate
FROM signal s
LEFT JOIN trade t ON s.id = t.signal_id
GROUP BY strategy, timeframe;

-- Confidence Performance View
CREATE OR REPLACE VIEW superset_confidence_performance AS
SELECT 
    CASE
        WHEN confidence < 0.3 THEN 'Low (< 30%)'
        WHEN confidence >= 0.3 AND confidence < 0.7 THEN 'Medium (30-70%)'
        ELSE 'High (> 70%)'
    END as confidence_level,
    COUNT(s.id) as signal_count,
    COUNT(t.id) as trade_count,
    AVG(t.profit_loss) as avg_profit_loss,
    SUM(t.profit_loss) as total_profit_loss,
    COUNT(CASE WHEN t.profit_loss > 0 THEN 1 END)::float / NULLIF(COUNT(t.id), 0) as win_rate
FROM signal s
LEFT JOIN trade t ON s.id = t.signal_id
GROUP BY confidence_level;

-- Daily Performance View
CREATE OR REPLACE VIEW superset_daily_performance AS
SELECT 
    DATE_TRUNC('day', s.timestamp) as day,
    COUNT(s.id) as signal_count,
    COUNT(t.id) as trade_count,
    AVG(t.profit_loss) as avg_profit_loss,
    SUM(t.profit_loss) as total_profit_loss,
    COUNT(CASE WHEN t.profit_loss > 0 THEN 1 END)::float / NULLIF(COUNT(t.id), 0) as win_rate
FROM signal s
LEFT JOIN trade t ON s.id = t.signal_id
GROUP BY day
ORDER BY day DESC;
