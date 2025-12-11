-- ============================================================================
-- Migration: Add Dimensional Analysis Support
-- Created: November 2025
-- Purpose: Add tables and functions for 8-dimensional idea analysis
-- ============================================================================

-- Create idea_dimensions table
CREATE TABLE IF NOT EXISTS idea_dimensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id INTEGER REFERENCES ideas(id) ON DELETE CASCADE,
    
    -- Dimension scores (0.0 to 1.0)
    problem_clarity DECIMAL(3,2) CHECK (problem_clarity >= 0 AND problem_clarity <= 1),
    problem_significance DECIMAL(3,2) CHECK (problem_significance >= 0 AND problem_significance <= 1),
    solution_specificity DECIMAL(3,2) CHECK (solution_specificity >= 0 AND problem_significance <= 1),
    technical_complexity VARCHAR(10) CHECK (technical_complexity IN ('low', 'medium', 'high')),
    market_validation DECIMAL(3,2) CHECK (market_validation >= 0 AND market_validation <= 1),
    technical_viability DECIMAL(3,2) CHECK (technical_viability >= 0 AND technical_viability <= 1),
    differentiation DECIMAL(3,2) CHECK (differentiation >= 0 AND differentiation <= 1),
    scalability DECIMAL(3,2) CHECK (scalability >= 0 AND scalability <= 1),
    
    -- Domain classification
    domains TEXT[],  -- Array of domain tags
    domain_confidence DECIMAL(3,2) CHECK (domain_confidence >= 0 AND domain_confidence <= 1),
    
    -- Overall score (calculated)
    overall_score DECIMAL(3,2),
    
    -- Metadata
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzer_version VARCHAR(50) DEFAULT 'v1.0'
);

-- Create indexes for performance
CREATE INDEX idx_dimensions_idea_id ON idea_dimensions(idea_id);
CREATE INDEX idx_dimensions_domains ON idea_dimensions USING GIN(domains);
CREATE INDEX idx_dimensions_overall_score ON idea_dimensions(overall_score DESC);
CREATE INDEX idx_dimensions_analyzed_at ON idea_dimensions(analyzed_at DESC);

-- ============================================================================
-- Function: Calculate Overall Score
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_dimensional_score(dimension_id UUID)
RETURNS DECIMAL(3,2) AS $$
DECLARE
    score DECIMAL(3,2);
BEGIN
    -- Weighted average of all dimensions
    -- Weights: problem_significance (0.20), market_validation (0.20),
    --          problem_clarity (0.15), differentiation (0.15),
    --          solution_specificity (0.10), technical_viability (0.10),
    --          scalability (0.10)
    SELECT 
        (problem_clarity * 0.15 + 
         problem_significance * 0.20 + 
         solution_specificity * 0.10 + 
         market_validation * 0.20 + 
         technical_viability * 0.10 + 
         differentiation * 0.15 + 
         scalability * 0.10)
    INTO score
    FROM idea_dimensions
    WHERE id = dimension_id;
    
    RETURN COALESCE(score, 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Trigger: Auto-calculate overall score on insert/update
-- ============================================================================

CREATE OR REPLACE FUNCTION update_overall_score()
RETURNS TRIGGER AS $$
BEGIN
    NEW.overall_score := calculate_dimensional_score(NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_overall_score
    BEFORE INSERT OR UPDATE ON idea_dimensions
    FOR EACH ROW
    EXECUTE FUNCTION update_overall_score();

-- ============================================================================
-- View: Ideas with Dimensional Analysis
-- ============================================================================

CREATE OR REPLACE VIEW v_ideas_with_dimensions AS
SELECT 
    i.id as idea_id,
    i.title,
    i.problem,
    i.solution,
    i.category,
    i.created_at,
    
    -- Dimensional scores
    d.problem_clarity,
    d.problem_significance,
    d.solution_specificity,
    d.technical_complexity,
    d.market_validation,
    d.technical_viability,
    d.differentiation,
    d.scalability,
    d.overall_score,
    d.domains,
    d.domain_confidence,
    d.analyzed_at
    
FROM ideas i
LEFT JOIN idea_dimensions d ON i.id = d.idea_id
ORDER BY i.created_at DESC;

-- ============================================================================
-- View: Top Ideas by Dimension
-- ============================================================================

CREATE OR REPLACE VIEW v_top_ideas_by_dimension AS
SELECT 
    i.id,
    i.title,
    i.problem,
    d.overall_score,
    d.problem_significance,
    d.market_validation,
    d.scalability,
    d.domains,
    
    -- Rank by overall score
    RANK() OVER (ORDER BY d.overall_score DESC) as overall_rank,
    
    -- Rank by problem significance
    RANK() OVER (ORDER BY d.problem_significance DESC) as significance_rank,
    
    -- Rank by market validation
    RANK() OVER (ORDER BY d.market_validation DESC) as validation_rank
    
FROM ideas i
INNER JOIN idea_dimensions d ON i.id = d.idea_id
WHERE d.overall_score IS NOT NULL
ORDER BY d.overall_score DESC
LIMIT 100;

-- ============================================================================
-- View: Domain Analytics
-- ============================================================================

CREATE OR REPLACE VIEW v_domain_analytics AS
SELECT 
    unnest(domains) as domain,
    COUNT(*) as idea_count,
    AVG(overall_score) as avg_overall_score,
    AVG(problem_clarity) as avg_problem_clarity,
    AVG(market_validation) as avg_market_validation,
    AVG(scalability) as avg_scalability,
    MAX(overall_score) as max_score,
    MIN(overall_score) as min_score
FROM idea_dimensions
WHERE domains IS NOT NULL
GROUP BY domain
ORDER BY idea_count DESC;

-- ============================================================================
-- Function: Get Similar Ideas by Domain
-- ============================================================================

CREATE OR REPLACE FUNCTION get_similar_ideas_by_domain(
    target_idea_id INTEGER,
    limit_count INTEGER DEFAULT 5
)
RETURNS TABLE (
    idea_id INTEGER,
    title TEXT,
    similarity_score DECIMAL(3,2),
    shared_domains TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.title,
        -- Similarity based on shared domains and score proximity
        (
            (SELECT COUNT(*) 
             FROM unnest(d1.domains) dom1
             WHERE dom1 = ANY(d2.domains)) * 0.5 +
            (1 - ABS(d1.overall_score - d2.overall_score)) * 0.5
        )::DECIMAL(3,2) as similarity,
        (
            SELECT ARRAY_AGG(DISTINCT dom)
            FROM unnest(d1.domains) dom
            WHERE dom = ANY(d2.domains)
        ) as shared_domains
    FROM ideas i
    JOIN idea_dimensions d2 ON i.id = d2.idea_id
    CROSS JOIN idea_dimensions d1
    WHERE d1.idea_id = target_idea_id
      AND i.id != target_idea_id
      AND d2.domains && d1.domains  -- Has at least one overlapping domain
    ORDER BY similarity DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample Data for Testing
-- ============================================================================

-- Insert sample dimensional analysis
-- (This will be populated by the dimensional_analyzer service)

INSERT INTO idea_dimensions (
    idea_id,
    problem_clarity,
    problem_significance,
    solution_specificity,
    technical_complexity,
    market_validation,
    technical_viability,
    differentiation,
    scalability,
    domains,
    domain_confidence
)
SELECT 
    id,
    0.75,
    0.80,
    0.70,
    'medium',
    0.65,
    0.85,
    0.72,
    0.78,
    ARRAY['edtech', 'saas'],
    0.85
FROM ideas
WHERE id = (SELECT MIN(id) FROM ideas)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Analytics Queries (for monitoring)
-- ============================================================================

-- Average scores across all ideas
COMMENT ON VIEW v_domain_analytics IS 
'Provides aggregate statistics for each domain including average scores and idea count';

-- Create materialized view for performance (refresh periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dimension_stats AS
SELECT 
    DATE(analyzed_at) as analysis_date,
    COUNT(*) as total_analyses,
    AVG(overall_score) as avg_overall_score,
    AVG(problem_clarity) as avg_problem_clarity,
    AVG(market_validation) as avg_market_validation,
    COUNT(DISTINCT unnest(domains)) as unique_domains
FROM idea_dimensions
GROUP BY DATE(analyzed_at)
ORDER BY analysis_date DESC;

CREATE UNIQUE INDEX idx_mv_dimension_stats_date 
    ON mv_dimension_stats(analysis_date);

-- Refresh function for materialized view
CREATE OR REPLACE FUNCTION refresh_dimension_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dimension_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Permissions (adjust as needed)
-- ============================================================================

-- Grant read access to application role (if you have one)
-- GRANT SELECT ON idea_dimensions TO app_user;
-- GRANT SELECT ON v_ideas_with_dimensions TO app_user;
-- GRANT SELECT ON v_top_ideas_by_dimension TO app_user;
-- GRANT SELECT ON v_domain_analytics TO app_user;

-- ============================================================================
-- Migration Complete
-- ============================================================================

SELECT 'Dimensional analysis tables and functions created successfully!' as status;
