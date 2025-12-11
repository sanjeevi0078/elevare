# Module 1: Idea Intelligence Integration Plan

## 🎯 Overview

Integrating the Startup Idea Intelligence system into the existing Elevare platform to provide AI-powered dimensional analysis of startup ideas.

## 📋 Integration Strategy

### Phase 1: Backend Enhancement (Week 1)
**Goal:** Add LLM-powered dimensional analysis to existing agent workflow

**Changes to Existing Code:**

1. **Enhance `services/agent_workflow.py`**
   - Add new node: `dimensional_analysis`
   - Integrate Claude API for dimension extraction
   - Add hybrid analysis (LLM + rule-based)

2. **Update `api/agent.py`**
   - Add new endpoint: `POST /api/v1/agent/analyze-dimensions`
   - Enhance existing `/invoke` to include dimensional scores

3. **Extend Database Schema**
   - Add `idea_dimensions` table
   - Add `dimension_scores` table
   - Extend `ideas` table with new fields

### Phase 2: Frontend Integration (Week 2)
**Goal:** Enhance intake form with dimensional analysis results

**Changes to Existing Code:**

1. **Enhance `static/js/intake.js`**
   - Add dimensional analysis display
   - Show visual score gauges
   - Display recommendations panel

2. **Update `templates/intake.html`**
   - Add results section for dimensions
   - Add recommendation cards
   - Add visual score indicators

### Phase 3: Dashboard Integration (Week 3)
**Goal:** Display dimensional insights on dashboard

**Changes to Existing Code:**

1. **Enhance `static/js/dashboard.js`**
   - Show dimension scores on idea cards
   - Add filtering by domain
   - Add sorting by score dimensions

2. **Update `templates/dashboard.html`**
   - Add dimension badges to cards
   - Add filter controls

---

## 🔧 Implementation Details

### 1. Enhanced Agent Workflow

**File:** `services/agent_workflow.py`

**New Additions:**

```python
# Add to existing workflow
from typing import TypedDict, Literal

class IdeaDimensions(TypedDict):
    """Dimensional analysis results"""
    problem_clarity: float
    problem_significance: float
    solution_specificity: float
    technical_complexity: Literal["low", "medium", "high"]
    market_validation: float
    technical_viability: float
    differentiation: float
    scalability: float

class EnhancedAgentState(AgentState):
    """Extend existing state with dimensions"""
    dimensions: IdeaDimensions
    domain: List[str]
    domain_confidence: float
```

**New Node:**

```python
def dimensional_analysis_node(state: EnhancedAgentState) -> EnhancedAgentState:
    """
    Analyze idea across 8 dimensions using Claude.
    Integrates with existing agent workflow.
    """
    from services.dimensional_analyzer import DimensionalAnalyzer
    
    analyzer = DimensionalAnalyzer()
    
    # Extract idea context from state
    idea_context = {
        'raw_idea': state.get('raw_idea', ''),
        'validation_profile': state.get('validation_profile', {}),
        'market_insights': state.get('market_insights', {})
    }
    
    # Analyze dimensions
    dimensions = analyzer.analyze_dimensions(idea_context)
    
    return {
        **state,
        'dimensions': dimensions['scores'],
        'domain': dimensions['domain'],
        'domain_confidence': dimensions['domain_confidence']
    }
```

**Updated Workflow:**

```python
def create_enhanced_workflow():
    """Enhanced workflow with dimensional analysis"""
    workflow = StateGraph(EnhancedAgentState)
    
    # Existing nodes
    workflow.add_node("idea_validation", idea_validation_node)
    workflow.add_node("dimensional_analysis", dimensional_analysis_node)  # NEW
    workflow.add_node("team_building", team_building_node)
    workflow.add_node("funding_analysis", funding_analysis_node)
    workflow.add_node("legal_compliance", legal_compliance_node)
    workflow.add_node("final_report", final_report_node)
    
    # Updated flow
    workflow.set_entry_point("idea_validation")
    workflow.add_edge("idea_validation", "dimensional_analysis")  # NEW
    workflow.add_edge("dimensional_analysis", "team_building")    # UPDATED
    workflow.add_edge("team_building", "funding_analysis")
    workflow.add_edge("funding_analysis", "legal_compliance")
    workflow.add_edge("legal_compliance", "final_report")
    workflow.add_edge("final_report", END)
    
    return workflow
```

---

### 2. New Service: Dimensional Analyzer

**File:** `services/dimensional_analyzer.py` (NEW)

```python
"""
Dimensional Analysis Service
Analyzes startup ideas across 8 key dimensions using Claude API
"""

import os
import json
from typing import Dict, Any, List
from langchain_groq import ChatGroq

class DimensionalAnalyzer:
    """
    Analyzes startup ideas using Claude API to extract latent dimensions.
    Integrates with existing Elevare agent workflow.
    """
    
    def __init__(self):
        self.model = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-70b-versatile",
            temperature=0.3
        )
    
    def analyze_dimensions(self, idea_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract dimensional scores from idea context.
        
        Args:
            idea_context: Dict containing raw_idea, validation_profile, market_insights
            
        Returns:
            Dict with scores, domain, and confidence
        """
        
        prompt = self._build_analysis_prompt(idea_context)
        
        response = self.model.invoke(prompt)
        
        # Parse JSON response
        try:
            result = json.loads(response.content)
            return self._validate_dimensions(result)
        except json.JSONDecodeError:
            # Fallback to default scores
            return self._get_default_dimensions()
    
    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for dimensional analysis"""
        
        raw_idea = context.get('raw_idea', '')
        validation = context.get('validation_profile', {})
        market = context.get('market_insights', {})
        
        return f"""Analyze this startup idea across 8 key dimensions.

**Idea:** {raw_idea}

**Validation Data:** {json.dumps(validation, indent=2)}

**Market Insights:** {json.dumps(market, indent=2)}

---

Return ONLY a JSON object with this structure:

{{
  "scores": {{
    "problem_clarity": <float 0.0-1.0>,
    "problem_significance": <float 0.0-1.0>,
    "solution_specificity": <float 0.0-1.0>,
    "technical_complexity": <"low" | "medium" | "high">,
    "market_validation": <float 0.0-1.0>,
    "technical_viability": <float 0.0-1.0>,
    "differentiation": <float 0.0-1.0>,
    "scalability": <float 0.0-1.0>
  }},
  "domain": [<list of domains like "edtech", "fintech", etc>],
  "domain_confidence": <float 0.0-1.0>
}}

**Scoring Guidelines:**
- problem_clarity: How well-defined is the problem? (1.0 = crystal clear, 0.0 = vague)
- problem_significance: How important is this problem? (1.0 = critical, 0.0 = trivial)
- solution_specificity: How concrete is the solution? (1.0 = detailed, 0.0 = abstract)
- technical_complexity: Overall difficulty (low/medium/high)
- market_validation: Evidence of demand (1.0 = strong evidence, 0.0 = none)
- technical_viability: Can this be built? (1.0 = definitely, 0.0 = impossible)
- differentiation: How unique? (1.0 = highly unique, 0.0 = commodity)
- scalability: Growth potential (1.0 = massive, 0.0 = limited)

Return ONLY the JSON object."""
    
    def _validate_dimensions(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize dimension scores"""
        
        scores = result.get('scores', {})
        
        # Ensure all scores are in valid range
        for key in ['problem_clarity', 'problem_significance', 'solution_specificity',
                    'market_validation', 'technical_viability', 'differentiation', 'scalability']:
            if key in scores:
                scores[key] = max(0.0, min(1.0, float(scores[key])))
        
        # Validate complexity
        if scores.get('technical_complexity') not in ['low', 'medium', 'high']:
            scores['technical_complexity'] = 'medium'
        
        return {
            'scores': scores,
            'domain': result.get('domain', ['general']),
            'domain_confidence': max(0.0, min(1.0, float(result.get('domain_confidence', 0.5))))
        }
    
    def _get_default_dimensions(self) -> Dict[str, Any]:
        """Return default dimensions if analysis fails"""
        return {
            'scores': {
                'problem_clarity': 0.5,
                'problem_significance': 0.5,
                'solution_specificity': 0.5,
                'technical_complexity': 'medium',
                'market_validation': 0.5,
                'technical_viability': 0.5,
                'differentiation': 0.5,
                'scalability': 0.5
            },
            'domain': ['general'],
            'domain_confidence': 0.3
        }
```

---

### 3. Database Schema Extension

**File:** `db/migrations/001_add_dimensions.sql` (NEW)

```sql
-- Add dimensions table
CREATE TABLE IF NOT EXISTS idea_dimensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    
    -- Dimension scores
    problem_clarity DECIMAL(3,2) CHECK (problem_clarity >= 0 AND problem_clarity <= 1),
    problem_significance DECIMAL(3,2) CHECK (problem_significance >= 0 AND problem_significance <= 1),
    solution_specificity DECIMAL(3,2) CHECK (solution_specificity >= 0 AND solution_specificity <= 1),
    technical_complexity VARCHAR(10) CHECK (technical_complexity IN ('low', 'medium', 'high')),
    market_validation DECIMAL(3,2) CHECK (market_validation >= 0 AND market_validation <= 1),
    technical_viability DECIMAL(3,2) CHECK (technical_viability >= 0 AND technical_viability <= 1),
    differentiation DECIMAL(3,2) CHECK (differentiation >= 0 AND differentiation <= 1),
    scalability DECIMAL(3,2) CHECK (scalability >= 0 AND scalability <= 1),
    
    -- Domain classification
    domains TEXT[],
    domain_confidence DECIMAL(3,2),
    
    -- Metadata
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzer_version VARCHAR(50) DEFAULT 'v1.0'
);

CREATE INDEX idx_dimensions_idea_id ON idea_dimensions(idea_id);
CREATE INDEX idx_dimensions_domains ON idea_dimensions USING GIN(domains);

-- Add overall score calculation function
CREATE OR REPLACE FUNCTION calculate_overall_score(dimension_id UUID)
RETURNS DECIMAL(3,2) AS $$
DECLARE
    score DECIMAL(3,2);
BEGIN
    SELECT 
        (problem_clarity + problem_significance + solution_specificity + 
         market_validation + technical_viability + differentiation + scalability) / 7
    INTO score
    FROM idea_dimensions
    WHERE id = dimension_id;
    
    RETURN COALESCE(score, 0);
END;
$$ LANGUAGE plpgsql;
```

---

### 4. Enhanced Intake Frontend

**File:** `static/js/intake.js` (ENHANCEMENT)

**Add after existing code:**

```javascript
// ============================================================================
// DIMENSIONAL ANALYSIS DISPLAY
// ============================================================================

function displayDimensionalAnalysis(dimensions) {
    const resultsContainer = document.getElementById('dimensional-results');
    if (!resultsContainer) return;
    
    const scores = dimensions.scores;
    const domain = dimensions.domain || [];
    const domainConfidence = dimensions.domain_confidence || 0;
    
    const html = `
        <div class="dimensional-analysis-panel">
            <!-- Domain Tags -->
            <div class="mb-6">
                <h4 class="text-lg font-semibold text-gray-700 mb-3">Domain Classification</h4>
                <div class="flex gap-2 flex-wrap">
                    ${domain.map(d => `
                        <span class="px-4 py-2 bg-indigo-100 text-indigo-800 rounded-full font-medium">
                            ${d}
                        </span>
                    `).join('')}
                    <span class="px-4 py-2 bg-gray-100 text-gray-600 rounded-full text-sm">
                        ${(domainConfidence * 100).toFixed(0)}% confidence
                    </span>
                </div>
            </div>
            
            <!-- Dimension Scores -->
            <div class="mb-6">
                <h4 class="text-lg font-semibold text-gray-700 mb-3">Dimensional Scores</h4>
                <div class="grid grid-cols-2 gap-4">
                    ${Object.entries(scores).map(([key, value]) => `
                        <div class="dimension-score-card">
                            <div class="dimension-label">
                                ${formatDimensionLabel(key)}
                            </div>
                            ${typeof value === 'number' ? `
                                <div class="dimension-gauge">
                                    <div class="gauge-bar">
                                        <div class="gauge-fill ${getScoreClass(value)}" 
                                             style="width: ${value * 100}%">
                                        </div>
                                    </div>
                                    <span class="gauge-value">${(value * 100).toFixed(0)}%</span>
                                </div>
                            ` : `
                                <span class="complexity-badge complexity-${value}">
                                    ${value.toUpperCase()}
                                </span>
                            `}
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <!-- Overall Score -->
            <div class="overall-score-card">
                <div class="score-label">Overall Idea Strength</div>
                <div class="score-value">
                    ${calculateOverallScore(scores).toFixed(0)}%
                </div>
                <div class="score-interpretation">
                    ${getScoreInterpretation(calculateOverallScore(scores))}
                </div>
            </div>
        </div>
    `;
    
    resultsContainer.innerHTML = html;
}

function formatDimensionLabel(key) {
    return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

function getScoreClass(score) {
    if (score >= 0.8) return 'score-excellent';
    if (score >= 0.6) return 'score-good';
    if (score >= 0.4) return 'score-fair';
    return 'score-needs-work';
}

function calculateOverallScore(scores) {
    const numericScores = Object.values(scores).filter(v => typeof v === 'number');
    const sum = numericScores.reduce((a, b) => a + b, 0);
    return (sum / numericScores.length) * 100;
}

function getScoreInterpretation(score) {
    if (score >= 80) return '🚀 Excellent! Strong foundation for a startup';
    if (score >= 60) return '✅ Good potential with some refinements needed';
    if (score >= 40) return '⚠️ Moderate potential - focus on key improvements';
    return '⚙️ Needs significant development before pursuing';
}

// Update existing handleAgentResponse to include dimensions
function handleAgentResponse(data) {
    // ... existing code ...
    
    // Add dimensional analysis if present
    if (data.dimensions) {
        displayDimensionalAnalysis({
            scores: data.dimensions,
            domain: data.domain,
            domain_confidence: data.domain_confidence
        });
    }
}
```

**Add CSS:** (in `templates/intake.html` or separate CSS file)

```css
.dimensional-analysis-panel {
    margin-top: 2rem;
    padding: 2rem;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8ebf0 100%);
    border-radius: 1rem;
}

.dimension-score-card {
    padding: 1rem;
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.dimension-label {
    font-size: 0.875rem;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 0.5rem;
}

.dimension-gauge {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.gauge-bar {
    flex: 1;
    height: 0.5rem;
    background: #e5e7eb;
    border-radius: 1rem;
    overflow: hidden;
}

.gauge-fill {
    height: 100%;
    border-radius: 1rem;
    transition: width 0.5s ease;
}

.score-excellent { background: linear-gradient(90deg, #10b981, #059669); }
.score-good { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.score-fair { background: linear-gradient(90deg, #f59e0b, #d97706); }
.score-needs-work { background: linear-gradient(90deg, #ef4444, #dc2626); }

.gauge-value {
    font-weight: 700;
    color: #1f2937;
    min-width: 3rem;
    text-align: right;
}

.complexity-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
    font-weight: 600;
    font-size: 0.875rem;
}

.complexity-low { background: #d1fae5; color: #065f46; }
.complexity-medium { background: #fed7aa; color: #92400e; }
.complexity-high { background: #fecaca; color: #991b1b; }

.overall-score-card {
    margin-top: 2rem;
    padding: 1.5rem;
    background: white;
    border-radius: 0.75rem;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.score-label {
    font-size: 0.875rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.score-value {
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0.5rem 0;
}

.score-interpretation {
    font-size: 1rem;
    color: #4b5563;
    margin-top: 0.5rem;
}
```

---

### 5. Enhanced Intake Template

**File:** `templates/intake.html` (ENHANCEMENT)

**Add after existing form:**

```html
<!-- Dimensional Analysis Results (Hidden initially) -->
<div id="dimensional-results" class="hidden mt-8">
    <!-- Results will be inserted here by JavaScript -->
</div>

<!-- Add this script reference before closing body tag -->
<script>
// Show dimensional results after analysis completes
function showDimensionalResults() {
    const resultsSection = document.getElementById('dimensional-results');
    if (resultsSection) {
        resultsSection.classList.remove('hidden');
        
        // Smooth scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}
</script>
```

---

## 🚀 Quick Start Implementation

### Step 1: Add Dimensional Analyzer

```bash
# Create new service file
touch /Users/sanjeeviutchav/elevare/services/dimensional_analyzer.py

# Copy the DimensionalAnalyzer class code above
```

### Step 2: Update Agent Workflow

```bash
# Edit existing file
nano /Users/sanjeeviutchav/elevare/services/agent_workflow.py

# Add dimensional_analysis_node (code above)
```

### Step 3: Run Database Migration

```bash
# Create migration file
touch /Users/sanjeeviutchav/elevare/db/migrations/001_add_dimensions.sql

# Apply migration (execute SQL from code above)
```

### Step 4: Enhance Frontend

```bash
# Edit intake.js
nano /Users/sanjeeviutchav/elevare/static/js/intake.js

# Add dimensional analysis display code
```

---

## ✅ Testing Checklist

- [ ] Dimensional analyzer extracts scores correctly
- [ ] Agent workflow includes dimensional analysis node
- [ ] Database stores dimensional data
- [ ] Intake page displays dimensional scores
- [ ] Dashboard shows dimension badges
- [ ] All scores are between 0.0 and 1.0
- [ ] Domain classification works
- [ ] Overall score calculation is accurate

---

## 📈 Success Metrics

- **Analysis Accuracy**: Dimensional scores align with manual expert evaluation (>80%)
- **Response Time**: Dimensional analysis adds < 3 seconds to total workflow
- **User Satisfaction**: Users find dimensional insights helpful (>4/5 rating)
- **Coverage**: All 8 dimensions successfully extracted (>95% of submissions)

---

## 🎯 Next Steps After Integration

1. Collect dimensional data from real idea submissions
2. Analyze patterns across domains
3. Refine scoring thresholds based on feedback
4. Add dimension-based filtering to dashboard
5. Create dimensional comparison views (compare your idea to top ideas)
6. Build recommendation engine based on dimensional gaps

---

This integration plan preserves your existing Elevare functionality while adding powerful dimensional analysis capabilities!
