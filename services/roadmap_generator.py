import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

class RoadmapGenerator:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def generate_roadmap(self, idea_context: dict) -> dict:
        """
        Generates a 3-phase strategic roadmap based on the idea context.
        """
        title = idea_context.get('idea_title', 'Startup')
        domain = idea_context.get('core_domain', 'General')
        solution = idea_context.get('solution_concept', '')

        prompt = f"""
        Act as a Veteran CTO and Product Manager. Create a personalized, step-by-step Execution Roadmap for this startup:
        
        **Startup:** {title} ({domain})
        **Solution:** {solution}

        Generate a 3-Phase Roadmap (Phase 1: MVP Validation, Phase 2: Go-to-Market, Phase 3: Scaling).
        For EACH phase, provide 3-4 specific milestones.
        
        CRITICAL: The milestones must be specific to the domain (e.g., if HealthTech, mention HIPAA; if Fintech, mention Compliance).
        
        Return ONLY valid JSON with this structure:
        {{
            "phases": [
                {{
                    "phase_name": "Phase 1: MVP & Validation",
                    "duration": "Weeks 1-8",
                    "goal": "Prove the concept with minimal code",
                    "milestones": [
                        {{
                            "title": "Specific Task Name",
                            "description": "Detailed explanation of what to do.",
                            "category": "Tech" (or Business/Legal/Design),
                            "tools": ["Tool1", "Tool2"]
                        }}
                    ]
                }}
            ]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Roadmap generation failed: {e}")
            return {"error": "Failed to generate roadmap"}
