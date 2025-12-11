import os
import json
import logging
import requests
from groq import Groq
from datetime import datetime

logger = logging.getLogger(__name__)

class EventScout:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.serp_api_key = os.getenv("SERP_API_KEY")

    def find_events(self, interest: str, location: str, stage: str) -> dict:
        """
        Searches for real-time events and uses LLM to format them.
        
        Args:
            interest: Domain/industry (e.g., "HealthTech", "FinTech")
            location: City or region (e.g., "London", "San Francisco")
            stage: Startup stage - "early", "growth", or "scale"
            
        Returns:
            Dictionary with "events" array containing structured event data
        """
        # 1. Construct Search Queries based on Stage
        queries = [
            f"upcoming {interest} startup conferences {location} 2025",
            f"{interest} startup networking events {location} this month",
        ]
        
        if stage == "early":
            queries.append(f"{interest} hackathons and workshops {location}")
        elif stage == "growth":
            queries.append(f"startup pitch competitions {interest} {location} 2025")
        
        logger.info(f"🔍 Event Scout: Searching for {interest} events in {location} (stage: {stage})")

        # 2. Perform Live Google Search (using SerpAPI)
        search_results = []
        if self.serp_api_key:
            for q in queries:
                try:
                    # Using SerpAPI
                    url = "https://serpapi.com/search"
                    params = {
                        'q': q,
                        'api_key': self.serp_api_key,
                        'num': 5,
                        'engine': 'google'
                    }
                    response = requests.get(url, params=params, timeout=10)
                    data = response.json()
                    organic_results = data.get("organic_results", [])[:3]
                    formatted_results = [
                        {
                            'title': result.get('title', ''),
                            'link': result.get('link', ''),
                            'snippet': result.get('snippet', '')
                        }
                        for result in organic_results
                    ]
                    search_results.extend(formatted_results)
                    logger.info(f"✅ Found {len(formatted_results)} results for: {q}")
                except Exception as e:
                    logger.error(f"❌ Search failed for '{q}': {e}")
        else:
            logger.warning("⚠️ SERP_API_KEY missing - using curated fallback events")
            # Minimal synthetic search results so LLM can still format, or return direct fallback
            search_results = [
                {
                    'title': 'TechCrunch Disrupt 2026',
                    'link': 'https://techcrunch.com/events/disrupt',
                    'snippet': 'TechCrunch Disrupt returns in 2026 with top founders, VCs, and product leaders.'
                },
                {
                    'title': 'Slush Helsinki 2025',
                    'link': 'https://www.slush.org/events',
                    'snippet': 'The world’s leading startup event, late Nov/Dec 2025 in Helsinki.'
                },
                {
                    'title': f'{interest} Founders Networking – ${location}',
                    'link': 'https://www.meetup.com/find',
                    'snippet': f'Local meetup for {interest} founders in {location}, monthly sessions.'
                },
            ]

        if not search_results:
            logger.warning(f"⚠️ No search results found for {interest} in {location}")
            # Hard fallback: return example events so UI is never empty during demo
            return {
                "events": [
                    {
                        "title": "Example: TechCrunch Disrupt",
                        "category": "Conference",
                        "date": "Sep 2026",
                        "location": "San Francisco, CA",
                        "description": "The world’s leading authority in debuting revolutionary startups.",
                        "price": "Pricing varies",
                        "url": "https://techcrunch.com/events/disrupt",
                        "tag": "Tier 1 Event"
                    }
                ]
            }

        # 3. AI Extraction & Structuring
        current_date = datetime.now().strftime("%B %Y")
        
        prompt = f"""
        Act as a Startup Event Curator. Today is {current_date}.
        
        I have scraped raw search results for a '{interest}' startup founder in '{location}'.
        Extract 6 REAL, UPCOMING events from this raw data.
        
        Raw Data: {str(search_results)[:3000]}
        
        CRITICAL RULES:
        - Only include events happening in the FUTURE (December 2025 onwards)
        - Extract real dates from the snippets (e.g., "Dec 15", "Jan 2026")
        - Use actual event titles from the search results
        - Extract registration/event URLs from the links
        - If price isn't mentioned, assume "Free"
        - Mark the most prestigious/relevant event with "tag": "Featured"
        
        Return ONLY valid JSON with this structure:
        {{
            "events": [
                {{
                    "title": "Event Name",
                    "category": "Conference" | "Networking" | "Pitch" | "Workshop",
                    "date": "Date (e.g. Dec 15, 2025)",
                    "location": "City or 'Virtual'",
                    "description": "One short punchy sentence.",
                    "price": "Free" or "$Price",
                    "url": "Link to event",
                    "tag": "Featured" (optional, for top 1 event only)
                }}
            ]
        }}
        """

        try:
            if os.getenv("GROQ_API_KEY"):
                logger.info("🤖 Asking Groq to structure event data...")
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                result = json.loads(chat_completion.choices[0].message.content)
                event_count = len(result.get("events", []))
                logger.info(f"✅ AI extracted {event_count} structured events")
                # If LLM returns empty, still provide curated examples
                if event_count == 0:
                    raise ValueError("LLM returned zero events")
                return result
            else:
                logger.warning("⚠️ GROQ_API_KEY missing - returning curated example events")
                return {
                    "events": [
                        {
                            "title": "Example: TechCrunch Disrupt",
                            "category": "Conference",
                            "date": "Sep 2026",
                            "location": "San Francisco, CA",
                            "description": "The world’s leading authority in debuting revolutionary startups.",
                            "price": "Pricing varies",
                            "url": "https://techcrunch.com/events/disrupt",
                            "tag": "Tier 1 Event"
                        },
                        {
                            "title": "Founders Networking Night",
                            "category": "Networking",
                            "date": "Dec 2025",
                            "location": location,
                            "description": f"Monthly meetup for {interest} founders with lightning intros and mentor office hours.",
                            "price": "Free",
                            "url": "https://www.meetup.com/find"
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"❌ LLM Event Parsing failed: {e}")
            # Final fallback: curated examples
            return {
                "events": [
                    {
                        "title": "Example: TechCrunch Disrupt",
                        "category": "Conference",
                        "date": "Sep 2026",
                        "location": "San Francisco, CA",
                        "description": "The world’s leading authority in debuting revolutionary startups.",
                        "price": "Pricing varies",
                        "url": "https://techcrunch.com/events/disrupt",
                        "tag": "Tier 1 Event"
                    }
                ]
            }
