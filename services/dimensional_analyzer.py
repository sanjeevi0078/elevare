"""
Dimensional Analysis Service
Analyzes startup ideas across 8 key dimensions using Groq LLM
Integrates with existing Elevare agent workflow
"""

import os
import json
from typing import Dict, Any, List
from langchain_groq import ChatGroq
import logging

logger = logging.getLogger(__name__)

class DimensionalAnalyzer:
    """
    Analyzes startup ideas using Groq API to extract latent dimensions.
    Provides 8-dimensional scoring system for idea evaluation.
    Includes multi-model fallback to handle decommissioned / unavailable models.
    """
    
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        # Ordered list of candidate models (first available will be used)
        # Updated to remove deprecated `llama-3.1-70b-versatile`.
        # Allow explicit override via env var GROQ_MODEL (comma-separated for priority ordering)
        override = os.getenv("GROQ_MODEL", "").strip()
        if override:
            self.candidate_models = [m.strip() for m in override.split(",") if m.strip()]
        else:
            # Updated list with currently available Groq models (adjustable) – smaller models last.
            self.candidate_models: List[str] = [
                "llama-3.2-70b-instruct",  # Latest large instruct model
                "llama-3.2-11b-text",      # Mid-size general text model
                "llama-3.2-3b-instruct",   # Small instruct (fast fallback)
            ]

        self.api_key = api_key
        self.temperature = 0.3
        self.active_model = None  # Will be set on first successful call
        self.model = None  # ChatGroq instance will be lazily initialized per candidate

    def _init_model(self, model_name: str):
        """(Re)initialize ChatGroq with a specific model name."""
        logger.info(f"Initializing Groq model: {model_name}")
        self.model = ChatGroq(
            api_key=self.api_key,
            model_name=model_name,
            temperature=self.temperature
        )
        self.active_model = model_name
    
    def analyze_dimensions(self, idea_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract dimensional scores from idea context, with model fallback.
        Tries each candidate model until one succeeds; returns validated results
        or default scores if all attempts fail.
        """

        logger.info("Starting dimensional analysis with multi-model fallback")
        prompt = self._build_analysis_prompt(idea_context)

        errors: List[str] = []

        for model_name in self.candidate_models:
            try:
                # Initialize / switch to this model
                self._init_model(model_name)
                response = self.model.invoke(prompt)
                content = response.content
                result = self._extract_json(content)
                validated = self._validate_dimensions(result)
                
                # Use LLM-generated explanations if available, otherwise fallback to rule-based
                if "explanations" not in validated or not validated["explanations"]:
                    logger.info("Using rule-based explanations as fallback")
                    validated["explanations"] = self._generate_explanations(
                        validated.get("scores", {}), idea_context
                    )
                else:
                    logger.info("Using LLM-generated explanations")
                
                # Extract focus areas and strengths from LLM if available
                if "focus_areas" in result:
                    validated["focus_areas"] = result["focus_areas"][:3]  # Max 3
                if "top_strengths" in result:
                    validated["top_strengths"] = result["top_strengths"][:2]  # Max 2
                
                logger.info(f"Dimensional analysis complete using: {model_name}")
                validated['active_model'] = model_name
                return validated
            except Exception as e:
                err_msg = f"Model {model_name} failed: {e}"
                logger.warning(err_msg)
                errors.append(err_msg)
                continue

        # All models failed
        logger.error("All candidate models failed for dimensional analysis. Returning defaults.")
        default_result = self._get_default_dimensions()
        try:
            logger.info("🔍 Generating fallback explanations...")
            default_result["explanations"] = self._generate_explanations(
                default_result.get("scores", {}), idea_context
            )
            logger.info(f"✅ Generated {len(default_result['explanations'])} fallback explanations")
            logger.info(f"🔍 Explanation keys: {list(default_result['explanations'].keys())}")
        except Exception as e:
            logger.error(f"❌ Failed to generate fallback explanations: {e}")
            default_result["explanations"] = {}
        default_result['active_model'] = None
        default_result['errors'] = errors
        return default_result
    
    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build enterprise-grade prompt for dimensional analysis with XAI."""
        
        raw_idea = context.get('raw_idea', '')
        validation = context.get('validation_profile', {})
        problem = validation.get('problem_statement', 'N/A')
        solution = validation.get('solution_concept', 'N/A')
        
        return f"""You are a Senior Venture Capital Analyst at Sequoia Capital with 15+ years of experience. Analyze this startup idea with brutal honesty.

**Startup Concept:**
{raw_idea}

**Problem Statement:** {problem}
**Solution Concept:** {solution}

Analyze this across 8 dimensions. DO NOT output generic "50%" scores. Be harsh, realistic, and specific.
For every dimension, provide a "score" (0.00-1.00) and a "reasoning" (2-3 sentences explaining WHY, citing specific words from the idea).

Return ONLY a JSON object with this exact structure:

{{
  "scores": {{
    "problem_clarity": <float>,
    "problem_significance": <float>,
    "solution_specificity": <float>,
    "technical_complexity": <"low"|"medium"|"high">,
    "market_validation": <float>,
    "technical_viability": <float>,
    "differentiation": <float>,
    "scalability": <float>
  }},
  "explanations": {{
    "problem_clarity": "Specific reason citing the user's text (e.g., 'The phrase X demonstrates clear understanding of Y')...",
    "problem_significance": "Specific reason with impact assessment...",
    "solution_specificity": "Specific reason about implementation details...",
    "technical_complexity": "Reasoning based on mentioned tech stack or approach...",
    "market_validation": "Reasoning about evidence or lack thereof...",
    "technical_viability": "Reasoning about feasibility with current technology...",
    "differentiation": "Reasoning comparing to standard solutions or competitors...",
    "scalability": "Reasoning about growth loops and bottlenecks..."
  }},
  "focus_areas": [
    "Specific action 1 (e.g., 'Define the initial niche narrowly - target X instead of Y')",
    "Specific action 2 (e.g., 'Add competitive research on Z, W, and V')",
    "Specific action 3"
  ],
  "top_strengths": [
    "Specific strength 1 (e.g., 'AI-powered invoice parsing creates defensible moat')",
    "Specific strength 2"
  ],
  "domain": ["<domain1>", "<domain2>"],
  "domain_confidence": <float>
}}

**CRITICAL RULES:**
1. AVOID round numbers like 0.5, 0.6, 1.0. Use nuanced scores like 0.72, 0.45, 0.88, 0.34
2. Each "explanation" MUST quote or reference specific words from the user's idea
3. DO NOT say "The idea is good" - say "Using X for Y creates competitive advantage because Z"
4. Focus areas must be actionable (not "improve clarity" but "Define target user as 'Series A SaaS founders' not 'entrepreneurs'")
5. If critical info is missing (like no competitor research), score market_validation LOW (0.2-0.4)

**Scoring Guidelines:**

1. **problem_clarity** (0.0-1.0): How well-defined and specific is the problem?
   - 0.85+ = Crystal clear, specific pain point with concrete examples
   - 0.65-0.84 = Well-defined but could be more specific
   - 0.35-0.64 = Somewhat vague or broad
   - <0.35 = Extremely vague or unclear

2. **problem_significance** (0.0-1.0): How important/impactful is this problem?
   - 1.0 = Critical pain point affecting many people
   - 0.7 = Significant problem with clear impact
   - 0.4 = Moderate inconvenience
   - 0.0 = Trivial or questionable problem

3. **solution_specificity** (0.0-1.0): How concrete is the solution approach?
   - 1.0 = Detailed implementation with clear features
   - 0.7 = Well-defined approach
   - 0.4 = General direction, lacks details
   - 0.0 = Very abstract or unclear

4. **technical_complexity** (low/medium/high): Overall technical difficulty
   - low = Basic web/mobile app, standard tech stack
   - medium = ML/AI, complex integrations, real-time systems
   - high = Deep tech, research required, novel algorithms

5. **market_validation** (0.0-1.0): Evidence of existing demand
   - 1.0 = Strong evidence (user interviews, pre-sales, competition)
   - 0.7 = Some validation data
   - 0.4 = Assumptions only
   - 0.0 = No evidence provided

6. **technical_viability** (0.0-1.0): Can this realistically be built?
   - 1.0 = Definitely achievable with current technology
   - 0.7 = Achievable but challenging
   - 0.4 = Requires significant innovation
   - 0.0 = Not feasible with current technology

7. **differentiation** (0.0-1.0): How unique compared to alternatives?
   - 1.0 = Highly differentiated, novel approach
   - 0.7 = Clear differentiation
   - 0.4 = Incremental improvement
   - 0.0 = Commodity or undifferentiated

8. **scalability** (0.0-1.0): Growth potential
   - 0.90+ = Massive scale potential (global, network effects, viral loops)
   - 0.65-0.89 = Good scale potential with clear growth path
   - 0.35-0.64 = Limited scale, regional or niche focus
   - <0.35 = Inherently local or severely constrained

**Domain Classification:**
Choose 1-3 most relevant domains from:
edtech, fintech, healthcare, saas, marketplace, ecommerce, social, productivity,
enterprise, consumer, deeptech, climate, biotech, crypto, gaming, media, travel, foodtech, assistivetech

Return ONLY the JSON object, no other text."""
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("Could not parse LLM response as JSON")
    
    def _validate_dimensions(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize dimension scores"""
        
        scores = result.get('scores', {})
        
        # Ensure all numeric scores are in valid range [0.0, 1.0]
        numeric_dimensions = [
            'problem_clarity', 'problem_significance', 'solution_specificity',
            'market_validation', 'technical_viability', 'differentiation', 'scalability'
        ]
        
        for key in numeric_dimensions:
            if key in scores:
                try:
                    value = float(scores[key])
                    scores[key] = max(0.0, min(1.0, value))
                except (ValueError, TypeError):
                    scores[key] = 0.5  # Default to middle if invalid
            else:
                scores[key] = 0.5  # Default if missing
        
        # Validate technical_complexity
        complexity = scores.get('technical_complexity', 'medium')
        if complexity not in ['low', 'medium', 'high']:
            scores['technical_complexity'] = 'medium'
        
        # Validate domain list
        domain = result.get('domain', ['general'])
        if not isinstance(domain, list) or len(domain) == 0:
            domain = ['general']
        
        # Validate domain confidence
        confidence = result.get('domain_confidence', 0.5)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            confidence = 0.5
        
        # Extract explanations from LLM if available
        explanations = result.get('explanations', {})
        if not isinstance(explanations, dict):
            explanations = {}
        
        # Debug logging for XAI
        logger.info(f"🔍 XAI Debug - Raw result keys: {list(result.keys())}")
        logger.info(f"🔍 XAI Debug - Explanations extracted: {list(explanations.keys())}")
        if explanations:
            logger.info(f"🔍 XAI Debug - Sample explanation (problem_clarity): {explanations.get('problem_clarity', 'MISSING')[:100]}")
        else:
            logger.warning("⚠️ XAI Warning - No explanations found in LLM response!")
        
        return {
            'scores': scores,
            'domain': domain[:3],  # Max 3 domains
            'domain_confidence': confidence,
            'explanations': explanations
        }
    
    def _get_default_dimensions(self) -> Dict[str, Any]:
        """Return default dimensions if analysis fails"""
        
        logger.warning("Using default dimensions due to analysis failure")
        
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

    def _generate_explanations(self, scores: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        """Create detailed, contextual explanations for each dimension based on user input."""
        
        vp = context.get('validation_profile', {}) or {}
        problem = vp.get('problem_statement', '') or ''
        solution = vp.get('solution_concept', '') or ''
        target = vp.get('target_user', '') or ''
        domain = vp.get('domain', '') or ''
        
        explanations = {}
        
        # Problem Clarity
        if 'problem_clarity' in scores:
            score = float(scores['problem_clarity'])
            if score >= 0.7:
                explanations['problem_clarity'] = f"**Strong clarity** ({score:.2f}/1.0): Your problem statement clearly identifies the pain point. {problem[:150]}... This specificity makes it easy for stakeholders to understand what you're solving."
            elif score >= 0.4:
                explanations['problem_clarity'] = f"**Moderate clarity** ({score:.2f}/1.0): The problem is identified but could be more specific. Consider: Who exactly faces this problem? When does it occur? What triggers it? Current: {problem[:100]}..."
            else:
                explanations['problem_clarity'] = f"**Needs refinement** ({score:.2f}/1.0): The problem description is vague or too broad. Try answering: What specific pain point exists? Who experiences it? Why is the current situation frustrating?"
        
        # Problem Significance  
        if 'problem_significance' in scores:
            score = float(scores['problem_significance'])
            if score >= 0.7:
                explanations['problem_significance'] = f"**High impact** ({score:.2f}/1.0): This problem appears to affect many people or cause substantial pain. Market indicators suggest strong demand for solutions in this space."
            elif score >= 0.4:
                explanations['problem_significance'] = f"**Moderate impact** ({score:.2f}/1.0): The problem matters but impact scope is unclear. To strengthen: quantify how many people face this, estimate time/money wasted, or cite market research."
            else:
                explanations['problem_significance'] = f"**Limited evidence** ({score:.2f}/1.0): No clear indicators of widespread impact. Consider: Is this a nice-to-have or must-have? What's the cost of NOT solving it?"
        
        # Solution Specificity
        if 'solution_specificity' in scores:
            score = float(scores['solution_specificity'])
            if score >= 0.7:
                explanations['solution_specificity'] = f"**Well-defined** ({score:.2f}/1.0): Your solution has concrete details. {solution[:150]}... This level of specificity helps in estimating feasibility and resources."
            elif score >= 0.4:
                explanations['solution_specificity'] = f"**Partially defined** ({score:.2f}/1.0): Core concept exists but lacks detail. Strengthen by describing: What features solve which pain points? How does the user experience flow? What's the core technology?"
            else:
                explanations['solution_specificity'] = f"**Too vague** ({score:.2f}/1.0): Solution needs much more detail. Define: Exactly what does your product do? What are the key features? How does it work from the user's perspective?"
        
        # Market Validation
        if 'market_validation' in scores:
            score = float(scores['market_validation'])
            if score >= 0.7:
                explanations['market_validation'] = f"**Strong validation** ({score:.2f}/1.0): Evidence of market demand detected (existing competitors, user research, or industry trends). This reduces risk significantly."
            elif score >= 0.4:
                explanations['market_validation'] = f"**Some indicators** ({score:.2f}/1.0): Limited market validation. To improve: conduct user interviews, research competitors, check if people are already paying for similar solutions."
            else:
                explanations['market_validation'] = f"**Unvalidated assumption** ({score:.2f}/1.0): No evidence that people want/need this. Critical next step: talk to 10-20 potential users before building anything."
        
        # Technical Complexity
        if 'technical_complexity' in scores:
            complexity = str(scores['technical_complexity']).lower()
            if complexity == 'low':
                explanations['technical_complexity'] = f"**Low complexity**: Buildable with standard web/mobile technologies. No exotic tech needed. Fast time-to-market, lower initial costs. Good for rapid validation."
            elif complexity == 'high':
                explanations['technical_complexity'] = f"**High complexity**: Requires advanced tech (AI/ML, deep integrations, novel algorithms). Longer timeline, need specialized talent. Higher risk but potentially stronger moat."
            else:
                explanations['technical_complexity'] = f"**Medium complexity**: Some technical challenges (APIs, moderate ML, multi-platform) but well within reach for experienced team. Balanced risk/reward."
        
        # Technical Viability
        if 'technical_viability' in scores:
            score = float(scores['technical_viability'])
            if score >= 0.7:
                explanations['technical_viability'] = f"**Highly feasible** ({score:.2f}/1.0): This can definitely be built with current technology. {solution[:100]}... No major technical blockers identified."
            elif score >= 0.4:
                explanations['technical_viability'] = f"**Achievable with effort** ({score:.2f}/1.0): Technically possible but will require skilled execution. Consider: Do you have/can you hire the technical talent needed?"
            else:
                explanations['technical_viability'] = f"**Technical risk** ({score:.2f}/1.0): Significant technical challenges or relies on unproven tech. Recommend: prototype the hardest part first to validate feasibility."
        
        # Differentiation
        if 'differentiation' in scores:
            score = float(scores['differentiation'])
            if score >= 0.7:
                explanations['differentiation'] = f"**Highly differentiated** ({score:.2f}/1.0): Your approach appears novel or significantly better than existing solutions. This gives you a competitive advantage and makes investor story compelling."
            elif score >= 0.4:
                explanations['differentiation'] = f"**Some differentiation** ({score:.2f}/1.0): Improvements over existing solutions but not transformative. Strengthen by asking: What can you do 10x better? What unique insight do you have?"
            else:
                explanations['differentiation'] = f"**Commodity risk** ({score:.2f}/1.0): Sounds similar to existing solutions. Critical to identify: What's your unfair advantage? Why can't incumbents easily replicate this?"
        
        # Scalability
        if 'scalability' in scores:
            score = float(scores['scalability'])
            if score >= 0.8:
                explanations['scalability'] = f"**Massive scale potential** ({score:.2f}/1.0): Network effects, viral potential, or global TAM detected. This business could grow exponentially with the right execution."
            elif score >= 0.6:
                explanations['scalability'] = f"**Good scale potential** ({score:.2f}/1.0): Clear path to grow beyond initial market. {target if target else 'Target market'} can expand geographically or to adjacent segments."
            elif score >= 0.4:
                explanations['scalability'] = f"**Limited scale** ({score:.2f}/1.0): Growth may be constrained by geography, market size, or business model. Consider: How can you expand TAM? Can you add platform elements?"
            else:
                explanations['scalability'] = f"**Scale challenges** ({score:.2f}/1.0): Appears inherently local or niche. For VC funding, you'd need to show path to $100M+ revenue. Bootstrapping might be better fit."
        
        return explanations
    
    def calculate_overall_score(self, scores: Dict[str, Any]) -> float:
        """
        Calculate overall idea strength score (0.0-1.0)
        Weighted average of all numeric dimensions
        """
        
        # Define weights for each dimension
        weights = {
            'problem_clarity': 0.15,
            'problem_significance': 0.20,
            'solution_specificity': 0.10,
            'market_validation': 0.20,
            'technical_viability': 0.10,
            'differentiation': 0.15,
            'scalability': 0.10
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for dimension, weight in weights.items():
            if dimension in scores and isinstance(scores[dimension], (int, float)):
                total_score += scores[dimension] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def get_score_interpretation(self, overall_score: float) -> Dict[str, Any]:
        """
        Get human-readable interpretation of overall score
        
        Returns:
            Dict with:
                - level: 'excellent', 'good', 'moderate', 'needs_work'
                - message: Description
                - emoji: Visual indicator
        """
        
        if overall_score >= 0.8:
            return {
                'level': 'excellent',
                'message': 'Excellent! Strong foundation for a startup',
                'emoji': '🚀',
                'color': 'green'
            }
        elif overall_score >= 0.6:
            return {
                'level': 'good',
                'message': 'Good potential with some refinements needed',
                'emoji': '✅',
                'color': 'blue'
            }
        elif overall_score >= 0.4:
            return {
                'level': 'moderate',
                'message': 'Moderate potential - focus on key improvements',
                'emoji': '⚠️',
                'color': 'yellow'
            }
        else:
            return {
                'level': 'needs_work',
                'message': 'Needs significant development before pursuing',
                'emoji': '⚙️',
                'color': 'red'
            }
