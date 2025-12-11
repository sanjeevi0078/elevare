"""
Startup Knowledge Base - RAG Service
Manages the vector store for startup case studies, best practices, and domain knowledge.

This service provides:
1. Document ingestion from startup_docs/ directory
2. Vector embeddings using HuggingFace (free and local)
3. Persistent storage with ChromaDB
4. RAG retriever for agent queries
"""

import os
from pathlib import Path
from typing import List

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document


# ============================================================================
# CONFIGURATION
# ============================================================================

CHROMA_DB_PATH = "./chroma_db"
DOCS_PATH = "./startup_docs"

# Embedding model configuration (using HuggingFace - free and local)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Fast and efficient

# Text splitting configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval configuration
DEFAULT_K = 3  # Number of documents to retrieve


# ============================================================================
# VECTOR STORE MANAGEMENT
# ============================================================================

def get_embeddings():
    """Get or create the embeddings model using HuggingFace (free and local)."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},  # Use CPU (change to 'cuda' if GPU available)
        encode_kwargs={'normalize_embeddings': True}  # Normalize for better similarity search
    )


def ensure_docs_directory():
    """Ensure the startup_docs directory exists with sample content."""
    docs_path = Path(DOCS_PATH)
    if not docs_path.exists():
        print(f"📁 Creating {DOCS_PATH} directory...")
        docs_path.mkdir(parents=True, exist_ok=True)
        
        # Create sample startup case studies
        sample_docs = {
            "product_market_fit.txt": """
# Finding Product-Market Fit: A Case Study

## Overview
Product-market fit (PMF) is the critical milestone where a startup's product satisfies a strong market demand.

## Case Study: Airbnb
Airbnb struggled for years before finding PMF. Key insights:

1. **Talk to Users**: The founders physically visited hosts and guests to understand their needs
2. **Iterate Rapidly**: They redesigned the product 7 times based on feedback
3. **Focus on Love**: They prioritized getting 100 users who loved the product over 1000 who liked it
4. **Measure Retention**: PMF was confirmed when 40% of users returned weekly

## Lessons Learned
- PMF is not a one-time event but a continuous process
- Quantitative metrics (retention, NPS) must validate qualitative feedback
- Be willing to pivot based on what users actually want, not what you think they need

## Recommended Metrics
- Weekly Active Users (WAU) / Monthly Active Users (MAU) ratio > 0.6
- Net Promoter Score (NPS) > 50
- Organic growth rate > 20% month-over-month
""",
            "fundraising_strategies.txt": """
# Startup Fundraising Strategies

## Pre-Seed Stage ($100K - $500K)
### Best Sources
- Friends and Family
- Angel Investors
- Accelerators (Y Combinator, Techstars)
- Pre-seed VCs

### What Investors Look For
1. Strong founding team with complementary skills
2. Large addressable market (TAM > $1B)
3. Unique insight or unfair advantage
4. Early traction or prototype

## Seed Stage ($500K - $2M)
### Preparation
- Have a working MVP with early users
- Show 20%+ month-over-month growth
- Clear unit economics model
- Defined go-to-market strategy

### Pitch Deck Must-Haves
1. Problem (Why now?)
2. Solution (What's unique?)
3. Market Size (TAM, SAM, SOM)
4. Business Model (How you make money)
5. Traction (Proof of concept)
6. Team (Why you?)
7. The Ask (How much, what for)

## Common Mistakes
- Raising too much too early (dilution)
- Not having a lead investor
- Ignoring due diligence preparation
- Underestimating time to close (3-6 months average)

## Alternative Funding
- Revenue-based financing
- Grants (SBIR, state programs)
- Crowdfunding (Kickstarter, Republic)
""",
            "team_building.txt": """
# Building Your Startup Team

## Cofounder Selection
### Critical Factors
1. **Complementary Skills**: Technical + Business/Marketing
2. **Shared Vision**: Aligned on company mission and values
3. **Work Ethic Compatibility**: Similar commitment levels
4. **Conflict Resolution**: Ability to disagree productively

### Red Flags
- Met less than 6 months ago
- No prior working relationship
- Unequal commitment levels
- Vague equity split discussions

## Early Hires (Employees 1-10)
### Prioritize
1. **Technical Lead**: If cofounders aren't technical
2. **Sales/BD**: For B2B startups
3. **Product Designer**: For consumer products
4. **Customer Success**: Once you have paying customers

### Hiring Best Practices
- Hire slow, fire fast
- Look for "athletes" who can wear multiple hats
- Use trial projects before full-time offers
- Offer equity to align incentives (0.5% - 5% for early employees)

## Equity Distribution
### Standard Framework
- Founders: 60-80% (split among cofounders)
- Early employees: 10-20% pool
- Advisors: 0.5-2% each
- Investors: Remaining (dilutes over rounds)

### Vesting Schedule
- 4-year vesting with 1-year cliff (standard)
- Apply to ALL team members, including founders
- Ensures commitment and protects company
""",
            "legal_compliance.txt": """
# Legal & Compliance for Startups

## Entity Formation
### Recommended Structure: Delaware C-Corp
Why Delaware?
- Business-friendly laws
- Established case law
- Investor preference
- Easy to scale

### Alternative: LLC
Good for:
- Solo founders
- Consulting businesses
- Not planning to raise VC funding

## Intellectual Property
### Must-Do Actions
1. **Trademark**: Register company name and logo
2. **Patents**: File provisional if novel technology
3. **Copyrights**: Automatic, but register for enforcement
4. **Trade Secrets**: Document and protect proprietary processes

### Employee IP Assignment
- Use CIIAA (Confidential Information and Invention Assignment Agreement)
- Have ALL team members sign before starting work
- Covers inventions created during employment

## Data Privacy & Security
### GDPR Compliance (EU users)
- Obtain explicit consent
- Provide data portability
- Implement right to deletion
- Appoint DPO if processing large-scale data

### CCPA Compliance (California users)
- Disclosure of data collection
- Opt-out mechanisms
- Data deletion requests

## Contracts & Agreements
### Essential Documents
1. Founders Agreement (equity, roles, vesting)
2. Stockholder Agreement
3. Employee Offer Letters
4. Consultant Agreements
5. Terms of Service
6. Privacy Policy

## Common Legal Mistakes
- Not filing 83(b) election within 30 days of stock grant
- Verbal agreements with cofounders
- No IP assignment from contractors
- Missing regulatory compliance (finance, healthcare, etc.)
""",
            "go_to_market_strategies.txt": """
# Go-to-Market Strategies for Startups

## B2B SaaS
### Recommended Approach: Product-Led Growth
1. **Freemium Model**: Free tier to drive adoption
2. **Self-Service Onboarding**: No sales team required initially
3. **Usage-Based Pricing**: Align cost with value
4. **Viral Loops**: Built-in referral mechanisms

### Sales Channels
- **SMB**: Inbound marketing, content, SEO
- **Mid-Market**: Inside sales team, demos
- **Enterprise**: Field sales, account-based marketing

## B2C Mobile Apps
### Launch Strategy
1. **App Store Optimization (ASO)**
   - Keyword-rich title and description
   - High-quality screenshots and video
   - Encourage early reviews (target 4.5+ stars)

2. **Viral Acquisition**
   - Referral program (incentivize sharing)
   - Social proof (show user count, ratings)
   - Network effects (value increases with users)

3. **Paid Acquisition** (when CAC < 1/3 LTV)
   - Facebook/Instagram ads
   - Google App Campaigns
   - Influencer partnerships

## Marketplace (Two-Sided)
### Cold Start Problem Solution
1. **Focus on Supply First** (easier to get than demand)
2. **Geo-Constrain** (dominate one city before expanding)
3. **Subsidize Early Transactions** (reduce friction)

### Example: Uber
- Started with black car service in San Francisco
- Recruited drivers directly, guaranteed income
- Gave free rides to early users to drive demand

## Content/Community
### Growth Flywheel
1. Create exceptional content
2. Build SEO authority
3. Attract organic traffic
4. Convert to email list
5. Monetize through products/services

### Metrics to Track
- **CAC**: Customer Acquisition Cost
- **LTV**: Lifetime Value
- **CAC Payback Period**: Months to recover acquisition cost
- **Rule of 40**: Growth rate + Profit margin ≥ 40%
"""
        }
        
        for filename, content in sample_docs.items():
            file_path = docs_path / filename
            with open(file_path, 'w') as f:
                f.write(content.strip())
            print(f"  ✅ Created {filename}")
        
        print(f"✅ Sample documents created in {DOCS_PATH}/")
    
    return docs_path


def load_documents() -> List[Document]:
    """Load all documents from the startup_docs directory."""
    docs_path = ensure_docs_directory()
    
    # Load text files
    loader = DirectoryLoader(
        str(docs_path),
        glob="**/*.txt",
        loader_cls=TextLoader,
        show_progress=True
    )
    
    documents = loader.load()
    print(f"📚 Loaded {len(documents)} documents")
    
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """Split documents into chunks for better retrieval."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )
    
    splits = text_splitter.split_documents(documents)
    print(f"✂️  Split into {len(splits)} chunks")
    
    return splits


def get_vector_store() -> Chroma:
    """
    Get or create the persistent vector store.
    
    If the vector store doesn't exist, it will:
    1. Load documents from startup_docs/
    2. Split them into chunks
    3. Generate embeddings
    4. Create and persist the ChromaDB store
    
    Returns:
        Chroma vector store instance
    """
    chroma_path = Path(CHROMA_DB_PATH)
    embeddings = get_embeddings()
    
    if not chroma_path.exists() or not list(chroma_path.glob("*.sqlite3")):
        print("🔨 Creating new vector store...")
        
        # Load and process documents
        documents = load_documents()
        splits = split_documents(documents)
        
        # Create vector store
        vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        print(f"✅ Vector store created at {CHROMA_DB_PATH}")
    else:
        # Load existing vector store
        vector_store = Chroma(
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings
        )
        
        print(f"✅ Loaded existing vector store from {CHROMA_DB_PATH}")
    
    return vector_store


def create_rag_retriever(k: int = DEFAULT_K):
    """
    Create a RAG retriever for querying the knowledge base.
    
    Args:
        k: Number of documents to retrieve (default: 3)
        
    Returns:
        Retriever instance configured for RAG queries
    """
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )
    
    print(f"🔍 RAG retriever ready (top-{k} similarity search)")
    return retriever


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def rebuild_vector_store():
    """Rebuild the vector store from scratch (use if documents change)."""
    import shutil
    
    chroma_path = Path(CHROMA_DB_PATH)
    if chroma_path.exists():
        print(f"🗑️  Removing existing vector store at {CHROMA_DB_PATH}")
        shutil.rmtree(chroma_path)
    
    print("🔄 Rebuilding vector store...")
    get_vector_store()
    print("✅ Vector store rebuilt successfully")


def query_knowledge_base(query: str, k: int = 3) -> str:
    """
    Query the knowledge base directly (for testing).
    
    Args:
        query: Question to ask
        k: Number of results to return
        
    Returns:
        Formatted string with results
    """
    retriever = create_rag_retriever(k=k)
    docs = retriever.get_relevant_documents(query)
    
    result = f"Found {len(docs)} relevant documents:\n\n"
    for i, doc in enumerate(docs, 1):
        result += f"--- Document {i} ---\n"
        result += f"Source: {doc.metadata.get('source', 'Unknown')}\n"
        result += f"Content:\n{doc.page_content[:300]}...\n\n"
    
    return result


# ============================================================================
# INITIALIZATION SCRIPT
# ============================================================================

if __name__ == "__main__":
    """
    Run this script to initialize the knowledge base:
    python -m services.knowledge_base
    """
    print("=" * 70)
    print("🚀 Elevare Knowledge Base Initialization")
    print("=" * 70)
    
    # No API key needed for HuggingFace embeddings (local model)
    print("📦 Using HuggingFace embeddings (free and local)")
    
    # Create vector store
    try:
        get_vector_store()
        print("\n" + "=" * 70)
        print("✅ Knowledge base initialized successfully!")
        print("=" * 70)
        
        # Test query
        print("\n🧪 Testing knowledge base with sample query...")
        test_query = "How do I find product-market fit?"
        result = query_knowledge_base(test_query)
        print(f"\nQuery: {test_query}")
        print(result)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
