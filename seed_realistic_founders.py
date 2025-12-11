"""
Seed realistic cofounder profiles for better matching diversity
Run this to populate database with 20+ realistic startup founders
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user_models import User, Skill, Base
from services.auth_service import AuthService
import random

# Database setup
engine = create_engine('sqlite:///elevare.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# Realistic founder profiles with diverse backgrounds
realistic_founders = [
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@techventures.com",
        "password": "demo123",
        "location": "Bangalore, India",
        "interest": "FinTech, AI/ML, Financial Inclusion",
        "personality": "Strategic thinker with 8 years in fintech. Led product teams at Razorpay. Passionate about democratizing financial services.",
        "commitment_level": 0.95,
        "skills": ["Product Management", "FinTech", "UX Design", "Python", "Strategic Planning"],
        "github_username": "priyatech",
        "linkedin_url": "https://linkedin.com/in/priya-sharma-fintech"
    },
    {
        "name": "Alex Chen",
        "email": "alex.chen@devforge.io",
        "password": "demo123",
        "location": "San Francisco, CA",
        "interest": "Developer Tools, Open Source, Cloud Infrastructure",
        "personality": "Full-stack engineer, 10+ years. Ex-Google. Built dev tools used by 100K+ developers. Love solving hard technical problems.",
        "commitment_level": 0.85,
        "skills": ["Node.js", "React", "Kubernetes", "DevOps", "System Design", "Go"],
        "github_username": "alexchen",
        "linkedin_url": "https://linkedin.com/in/alex-chen-dev"
    },
    {
        "name": "Maria Garcia",
        "email": "maria.garcia@healthtech.co",
        "password": "demo123",
        "location": "Barcelona, Spain",
        "interest": "HealthTech, Telemedicine, Patient Experience",
        "personality": "Healthcare innovation advocate. MD turned entrepreneur. Founded 2 health startups. Obsessed with improving patient outcomes.",
        "commitment_level": 0.92,
        "skills": ["Healthcare", "Product Strategy", "Regulatory Compliance", "Patient Care", "Medical AI"],
        "linkedin_url": "https://linkedin.com/in/maria-garcia-md"
    },
    {
        "name": "Raj Patel",
        "email": "raj.patel@edtech.in",
        "password": "demo123",
        "location": "Mumbai, India",
        "interest": "EdTech, K-12 Education, Learning Analytics",
        "personality": "Former teacher, now EdTech entrepreneur. Built learning platform serving 500K students. Believes technology can democratize education.",
        "commitment_level": 0.88,
        "skills": ["Education", "Curriculum Design", "Learning Science", "Python", "Data Analytics"],
        "github_username": "rajpatel",
        "linkedin_url": "https://linkedin.com/in/raj-patel-edtech"
    },
    {
        "name": "Sarah Johnson",
        "email": "sarah.johnson@sustaintech.com",
        "password": "demo123",
        "location": "Seattle, WA",
        "interest": "Climate Tech, Sustainability, Carbon Markets",
        "personality": "Climate scientist turned entrepreneur. PhD in Environmental Engineering. Passionate about using tech to fight climate change.",
        "commitment_level": 0.90,
        "skills": ["Sustainability", "Carbon Accounting", "Data Science", "Climate Modeling", "Python"],
        "linkedin_url": "https://linkedin.com/in/sarah-johnson-climate"
    },
    {
        "name": "Kenji Tanaka",
        "email": "kenji.tanaka@airesearch.jp",
        "password": "demo123",
        "location": "Tokyo, Japan",
        "interest": "AI/ML, Computer Vision, Robotics",
        "personality": "ML researcher with 15 publications. Ex-OpenAI Japan. Specialized in vision models. Looking for impactful AI applications.",
        "commitment_level": 0.87,
        "skills": ["Machine Learning", "Computer Vision", "TensorFlow", "PyTorch", "Research", "Python"],
        "github_username": "kenjitanaka",
        "linkedin_url": "https://linkedin.com/in/kenji-tanaka-ai"
    },
    {
        "name": "Aisha Mohammed",
        "email": "aisha.mohammed@marketplacepro.com",
        "password": "demo123",
        "location": "Dubai, UAE",
        "interest": "E-commerce, Marketplaces, Regional Expansion",
        "personality": "Built and scaled e-commerce platforms across MENA. Expert in cross-border commerce. Growth hacker at heart.",
        "commitment_level": 0.83,
        "skills": ["E-commerce", "Growth Marketing", "Marketplace Strategy", "Operations", "Arabic Markets"],
        "linkedin_url": "https://linkedin.com/in/aisha-mohammed-ecom"
    },
    {
        "name": "Liam O'Connor",
        "email": "liam.oconnor@blockchaindev.io",
        "password": "demo123",
        "location": "Dublin, Ireland",
        "interest": "Blockchain, Web3, DeFi",
        "personality": "Ethereum core contributor. Built DeFi protocols with $50M TVL. Believes in decentralized future.",
        "commitment_level": 0.91,
        "skills": ["Solidity", "Smart Contracts", "Blockchain", "Web3", "DeFi", "Rust"],
        "github_username": "liamoconnor",
        "linkedin_url": "https://linkedin.com/in/liam-oconnor-web3"
    },
    {
        "name": "Yuki Nakamura",
        "email": "yuki.nakamura@designstudio.jp",
        "password": "demo123",
        "location": "Osaka, Japan",
        "interest": "UI/UX Design, Consumer Products, Mobile-First",
        "personality": "Award-winning product designer. Ex-Apple Japan. Designed apps with 10M+ users. Obsessed with delightful user experiences.",
        "commitment_level": 0.80,
        "skills": ["UI/UX Design", "Figma", "Design Systems", "Mobile Design", "Prototyping"],
        "linkedin_url": "https://linkedin.com/in/yuki-nakamura-design"
    },
    {
        "name": "Carlos Rodriguez",
        "email": "carlos.rodriguez@saasbuilder.com",
        "password": "demo123",
        "location": "Austin, TX",
        "interest": "B2B SaaS, Enterprise Sales, Revenue Operations",
        "personality": "Serial SaaS founder (2 exits). Expert in enterprise go-to-market. Scaled revenue from 0 to $10M ARR twice.",
        "commitment_level": 0.89,
        "skills": ["B2B Sales", "SaaS", "Revenue Ops", "Enterprise", "Sales Strategy"],
        "linkedin_url": "https://linkedin.com/in/carlos-rodriguez-saas"
    },
    {
        "name": "Fatima Al-Hassan",
        "email": "fatima.hassan@dataengineering.com",
        "password": "demo123",
        "location": "London, UK",
        "interest": "Data Engineering, Analytics Platforms, Real-time Data",
        "personality": "Built data infrastructure at scale (100TB+). Ex-Spotify. Loves solving complex distributed systems problems.",
        "commitment_level": 0.86,
        "skills": ["Data Engineering", "Apache Spark", "Kafka", "Python", "SQL", "AWS"],
        "github_username": "fatimahassan",
        "linkedin_url": "https://linkedin.com/in/fatima-hassan-data"
    },
    {
        "name": "Marcus Williams",
        "email": "marcus.williams@cybersec.io",
        "password": "demo123",
        "location": "New York, NY",
        "interest": "Cybersecurity, Zero Trust, Enterprise Security",
        "personality": "White-hat hacker. CISSP certified. Built security products for Fortune 500. Passionate about making the internet safer.",
        "commitment_level": 0.84,
        "skills": ["Cybersecurity", "Penetration Testing", "Security Architecture", "Zero Trust", "Python"],
        "github_username": "marcuswilliams",
        "linkedin_url": "https://linkedin.com/in/marcus-williams-security"
    },
    {
        "name": "Sophia Zhang",
        "email": "sophia.zhang@socialimpact.org",
        "password": "demo123",
        "location": "Singapore",
        "interest": "Social Impact, Nonprofit Tech, Education Access",
        "personality": "Tech for good advocate. Built platforms serving 1M+ underserved communities. Believe technology should empower everyone.",
        "commitment_level": 0.93,
        "skills": ["Social Impact", "Product Management", "Community Building", "NGO Operations"],
        "linkedin_url": "https://linkedin.com/in/sophia-zhang-impact"
    },
    {
        "name": "Omar Hassan",
        "email": "omar.hassan@mobiledev.com",
        "password": "demo123",
        "location": "Cairo, Egypt",
        "interest": "Mobile Development, Cross-Platform Apps, Emerging Markets",
        "personality": "Mobile-first developer. Built apps with 5M+ downloads. Expert in offline-first architecture for low-connectivity markets.",
        "commitment_level": 0.81,
        "skills": ["React Native", "Flutter", "Mobile Development", "iOS", "Android"],
        "github_username": "omarhassan",
        "linkedin_url": "https://linkedin.com/in/omar-hassan-mobile"
    },
    {
        "name": "Emma Thompson",
        "email": "emma.thompson@contentai.co",
        "password": "demo123",
        "location": "Toronto, Canada",
        "interest": "Content Creation, AI Writing, Creator Economy",
        "personality": "Content strategist turned AI entrepreneur. Built tools for 100K+ creators. Passionate about empowering creative professionals.",
        "commitment_level": 0.85,
        "skills": ["Content Strategy", "NLP", "GPT Integration", "Community Management", "Marketing"],
        "linkedin_url": "https://linkedin.com/in/emma-thompson-content"
    },
    {
        "name": "Arjun Kapoor",
        "email": "arjun.kapoor@logistics.in",
        "password": "demo123",
        "location": "Delhi, India",
        "interest": "Logistics Tech, Supply Chain, Last-Mile Delivery",
        "personality": "Operations expert. Scaled delivery networks across India. Obsessed with operational efficiency and route optimization.",
        "commitment_level": 0.88,
        "skills": ["Logistics", "Operations", "Supply Chain", "Optimization", "Data Analytics"],
        "linkedin_url": "https://linkedin.com/in/arjun-kapoor-logistics"
    },
    {
        "name": "Nina Petrov",
        "email": "nina.petrov@gamedev.ru",
        "password": "demo123",
        "location": "Moscow, Russia",
        "interest": "Gaming, Game Design, Multiplayer Systems",
        "personality": "Game developer with 20 shipped titles. Expert in Unity/Unreal. Passionate about building engaging player experiences.",
        "commitment_level": 0.79,
        "skills": ["Unity", "Game Development", "C#", "Multiplayer Systems", "Game Design"],
        "github_username": "ninapetrov",
        "linkedin_url": "https://linkedin.com/in/nina-petrov-gamedev"
    },
    {
        "name": "David Kim",
        "email": "david.kim@quantfinance.com",
        "password": "demo123",
        "location": "Hong Kong",
        "interest": "Quantitative Finance, Algorithmic Trading, Risk Management",
        "personality": "Quant trader for 12 years. Built trading algorithms managing $500M. Now exploring fintech entrepreneurship.",
        "commitment_level": 0.87,
        "skills": ["Quantitative Finance", "Python", "Machine Learning", "Risk Analysis", "Trading Systems"],
        "github_username": "davidkim",
        "linkedin_url": "https://linkedin.com/in/david-kim-quant"
    },
    {
        "name": "Isabella Rossi",
        "email": "isabella.rossi@fashiontech.it",
        "password": "demo123",
        "location": "Milan, Italy",
        "interest": "Fashion Tech, Sustainable Fashion, AR/VR Commerce",
        "personality": "Fashion industry veteran turned tech entrepreneur. Building AR try-on solutions. Passionate about sustainability.",
        "commitment_level": 0.82,
        "skills": ["Fashion", "AR/VR", "E-commerce", "Product Design", "Sustainability"],
        "linkedin_url": "https://linkedin.com/in/isabella-rossi-fashion"
    },
    {
        "name": "James Park",
        "email": "james.park@fitness.tech",
        "password": "demo123",
        "location": "Los Angeles, CA",
        "interest": "Fitness Tech, Wearables, Health Tracking",
        "personality": "Fitness entrepreneur and engineer. Built wearable devices. Expert in IoT and biometric sensors.",
        "commitment_level": 0.86,
        "skills": ["IoT", "Hardware", "Firmware", "Health Tech", "Mobile Apps"],
        "github_username": "jamespark",
        "linkedin_url": "https://linkedin.com/in/james-park-fitness"
    }
]

def seed_realistic_founders():
    """Seed database with diverse, realistic founder profiles"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    print("🌱 Seeding realistic founder profiles...")
    
    for i, founder in enumerate(realistic_founders, 1):
        try:
            # Check if user already exists
            existing = db.query(User).filter(User.email == founder["email"]).first()
            if existing:
                print(f"⏭️  {i}. {founder['name']} already exists, skipping...")
                continue
            
            # Create user
            user = User(
                name=founder["name"],
                email=founder["email"],
                location=founder["location"],
                interest=founder["interest"],
                personality=founder["personality"],
                commitment_level=founder["commitment_level"],
                hashed_password=pwd_context.hash(founder["password"])
            )
            
            # Add optional fields
            if "github_username" in founder:
                user.github_username = founder["github_username"]
            if "linkedin_url" in founder:
                user.linkedin_url = founder["linkedin_url"]
            
            db.add(user)
            db.flush()  # Get user ID
            
            # Add skills
            for skill_name in founder["skills"]:
                skill = db.query(Skill).filter(Skill.name == skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.add(skill)
                    db.flush()
                user.skills.append(skill)
            
            db.commit()
            
            print(f"✅ {i}. Created {founder['name']} - {founder['location']} ({len(founder['skills'])} skills)")
            
        except Exception as e:
            print(f"❌ {i}. Failed to create {founder['name']}: {e}")
            db.rollback()
    
    print(f"\n🎉 Seeding complete! Total users in database: {db.query(User).count()}")
    print("\n📊 Distribution by location:")
    locations = db.query(User.location).distinct().all()
    for loc in locations:
        if loc[0]:
            count = db.query(User).filter(User.location == loc[0]).count()
            print(f"   {loc[0]}: {count} users")

if __name__ == "__main__":
    seed_realistic_founders()
    db.close()
    print("\n✨ Database ready for realistic cofounder matching!")
