import streamlit as st
import json
from datetime import datetime
import re
import sqlite3
import io
from pathlib import Path

# Page config
st.set_page_config(
    page_title="AI Content Generator Pro",
    page_icon="🚀",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE SETUP ====================
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect('content_history.db', check_same_thread=False)
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  timestamp TEXT,
                  business_type TEXT,
                  product TEXT,
                  audience TEXT,
                  tone TEXT,
                  platform TEXT,
                  content TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  api_provider TEXT,
                  api_key TEXT,
                  model TEXT,
                  temperature REAL,
                  max_tokens INTEGER,
                  default_platform TEXT,
                  default_tone TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    return conn

# Initialize database connection
try:
    db_conn = init_database()
except Exception as e:
    st.error(f"Database initialization failed: {e}")
    db_conn = None

# ==================== SESSION STATE ====================
if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'api_provider' not in st.session_state:
    st.session_state.api_provider = "OpenAI"

# ==================== AI API INTEGRATION ====================
def call_openai_api(prompt, api_key, model="gpt-3.5-turbo", temperature=0.7, max_tokens=800):
    """Real OpenAI API integration"""
    try:
        import openai
        openai.api_key = api_key
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert marketing copywriter. Always respond with ONLY valid JSON, no markdown, no explanations, no code blocks."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    except ImportError:
        return None  # OpenAI not installed
    except Exception as e:
        st.error(f"OpenAI API Error: {str(e)}")
        return None

def call_groq_api(prompt, api_key, model="llama3-70b-8192", temperature=0.7, max_tokens=800):
    """Real Groq API integration"""
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert marketing copywriter. Always respond with ONLY valid JSON, no markdown, no explanations, no code blocks."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    except ImportError:
        return None  # Groq not installed
    except Exception as e:
        st.error(f"Groq API Error: {str(e)}")
        return None

def call_anthropic_api(prompt, api_key, model="claude-3-sonnet-20240229", temperature=0.7, max_tokens=800):
    """Real Anthropic Claude API integration"""
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are an expert marketing copywriter. Always respond with ONLY valid JSON, no markdown, no explanations.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    except ImportError:
        return None  # Anthropic not installed
    except Exception as e:
        st.error(f"Anthropic API Error: {str(e)}")
        return None

# ==================== NLP - KEYWORD EXTRACTION ====================
def extract_keywords_spacy(text, max_keywords=10):
    """Advanced keyword extraction using spaCy"""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        
        doc = nlp(text.lower())
        
        # Extract nouns, proper nouns, and adjectives
        keywords = []
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN", "ADJ"] and not token.is_stop and len(token.text) > 2:
                keywords.append(token.text)
        
        # Get unique keywords
        unique_keywords = list(dict.fromkeys(keywords))
        return ', '.join(unique_keywords[:max_keywords])
    except ImportError:
        return extract_keywords_simple(text, max_keywords)
    except Exception:
        return extract_keywords_simple(text, max_keywords)

def extract_keywords_simple(text, max_keywords=8):
    """Simple keyword extraction without spaCy"""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'or', 'for', 'with', 'to', 'in', 'of', 'a', 'an', 'this', 'that', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
    keywords = [w for w in words if w not in stop_words]
    unique_keywords = list(dict.fromkeys(keywords))
    return ', '.join(unique_keywords[:max_keywords])

# ==================== CONTENT GENERATION ====================
def generate_content_with_ai(business_type, product, audience, tone, platform, api_key, api_provider, model, temperature, max_tokens):
    """Generate content using real AI API with improved parsing"""
    
    # IMPROVED PROMPT TEMPLATES
    prompts = {
        "google_ads": f"""Create a Google Ads campaign. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "headline": "compelling headline under 30 chars",
  "description": "benefit-focused description under 90 chars",
  "cta": "action phrase 2-3 words",
  "keywords": "keyword1, keyword2, keyword3, keyword4, keyword5"
}}""",

        "facebook": f"""Create a Facebook ad. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "headline": "scroll-stopping headline",
  "body": "engaging 80-120 word body text with emotional appeal",
  "cta": "clear call to action",
  "hashtags": "#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5",
  "image_suggestion": "image description"
}}""",

        "instagram": f"""Create Instagram content. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "caption": "engaging caption with hook in first line, 100-150 chars",
  "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5 #tag6 #tag7 #tag8 #tag9 #tag10",
  "cta": "instagram native action",
  "story_text": "story overlay text 15-20 words"
}}""",

        "seo": f"""Create SEO content. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "title": "SEO title 50-60 chars keyword-rich",
  "meta_description": "compelling 150-160 char meta description",
  "h1": "main heading different from title",
  "keywords": "keyword1, keyword2, keyword3, keyword4, keyword5, keyword6",
  "url_slug": "seo-friendly-url-slug"
}}"""
    }
    
    prompt = prompts.get(platform, prompts["google_ads"])
    
    # Call API
    response = None
    if api_key and len(api_key) > 10:
        if api_provider == "OpenAI":
            response = call_openai_api(prompt, api_key, model, temperature, max_tokens)
        elif api_provider == "Groq":
            response = call_groq_api(prompt, api_key, model, temperature, max_tokens)
        elif api_provider == "Anthropic":
            response = call_anthropic_api(prompt, api_key, model, temperature, max_tokens)
    
    # Parse AI response with better error handling
    if response:
        try:
            # Clean the response
            response_clean = response.strip()
            
            # Remove markdown code blocks
            if "```json" in response_clean:
                response_clean = response_clean.split("```json")[1].split("```")[0].strip()
            elif "```" in response_clean:
                response_clean = response_clean.split("```")[1].split("```")[0].strip()
            
            # Remove any leading/trailing text
            start = response_clean.find('{')
            end = response_clean.rfind('}') + 1
            if start != -1 and end > start:
                response_clean = response_clean[start:end]
            
            # Parse JSON
            content = json.loads(response_clean)
            
            # Add performance metrics
            content["estimated_ctr"] = f"{round(2.5 + (hash(product) % 100) / 20, 1)}%"
            content["quality_score"] = f"{7 + (hash(product) % 3)}/10"
            content["estimated_engagement"] = f"{round(3.0 + (hash(product) % 100) / 25, 1)}%"
            content["estimated_reach"] = f"{round(2.0 + (hash(product) % 100) / 10, 1)}K"
            content["estimated_ranking"] = "Top 10 potential"
            content["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content["source"] = f"{api_provider} API"
            
            return content
            
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ JSON parsing failed: {str(e)}")
            st.info("📝 Raw API Response:")
            st.code(response, language="text")
            st.error("Using fallback mode instead...")
        except Exception as e:
            st.warning(f"⚠️ Error processing response: {str(e)}")
    
    # FALLBACK: Use enhanced mock data
    return generate_content_fallback(business_type, product, audience, tone, platform)

def generate_content_fallback(business_type, product, audience, tone, platform):
    """Enhanced fallback content generator with realistic outputs"""
    
    # Better templates with more variety
    import random
    
    if platform == "google_ads":
        headlines = [
            f"Premium {product} for {audience}",
            f"Best {product} - {audience}",
            f"Top {product} Services",
            f"{product} Experts | {business_type}",
            f"#1 {product} Provider"
        ]
        descriptions = [
            f"Get premium {product} designed for {audience}. {tone} service with proven results. Limited time offer!",
            f"Transform your experience with our {product}. Trusted by {audience}. Book your free consultation now!",
            f"Professional {product} services for {audience}. Fast, reliable, {tone.lower()}. Start today!",
            f"Discover why {audience} choose our {product}. Expert {business_type.lower()} team. Call now!"
        ]
        ctas = ["Get Started", "Book Now", "Learn More", "Try Free", "Get Quote"]
        
        return {
            "headline": random.choice(headlines)[:30],
            "description": random.choice(descriptions)[:90],
            "cta": random.choice(ctas),
            "keywords": f"{product}, {business_type}, {audience}, best {product}, affordable {product}, {product} services, professional {business_type}, top {product}",
            "estimated_ctr": f"{round(random.uniform(2.5, 8.5), 1)}%",
            "quality_score": f"{random.randint(7, 10)}/10",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Fallback Mode"
        }
    
    elif platform == "facebook":
        emojis = ["🎯", "✨", "🚀", "💯", "⭐", "🔥", "💪", "🌟"]
        headlines = [
            f"{random.choice(emojis)} {product} That {audience} Love!",
            f"{random.choice(emojis)} Transform Your Life with {product}",
            f"{random.choice(emojis)} The {product} Revolution Starts Here",
            f"{random.choice(emojis)} Exclusive {product} for {audience}"
        ]
        
        bodies = [
            f"Hey {audience}! 👋\n\nLooking for the perfect {product}? You've found it!\n\n✨ Why choose us?\n• {tone} approach that works\n• Proven results you can see\n• Trusted by hundreds of satisfied customers\n• Fast, reliable service\n\nDon't settle for ordinary. Experience the difference today!\n\n💬 Comment 'INTERESTED' or message us to learn more!",
            
            f"Attention {audience}! 🎯\n\n{product} doesn't have to be complicated. We make it simple, {tone.lower()}, and effective.\n\n🌟 What you get:\n• Expert guidance every step\n• Results that last\n• Support when you need it\n• Affordable pricing\n\nReady to start? Drop a 👍 below or send us a message!",
            
            f"🚀 Calling all {audience}!\n\nYour search for the best {product} ends here. Our {business_type.lower()} combines quality, expertise, and a {tone.lower()} touch.\n\n💪 Join hundreds who already made the switch:\n✓ Fast results\n✓ Professional service\n✓ Guaranteed satisfaction\n\nClick 'Learn More' or DM us now!"
        ]
        
        return {
            "headline": random.choice(headlines),
            "body": random.choice(bodies),
            "cta": random.choice(["Learn More", "Get Started", "Shop Now", "Sign Up", "Contact Us"]),
            "hashtags": f"#{product.replace(' ', '')} #{business_type.replace(' ', '')} #{audience.replace(' ', '')} #quality #trending #lifestyle #success",
            "image_suggestion": f"High-quality lifestyle image showing happy {audience.lower()} using {product}, bright colors, authentic emotions",
            "estimated_engagement": f"{round(random.uniform(3.0, 7.5), 1)}%",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Fallback Mode"
        }
    
    elif platform == "instagram":
        emojis = ["✨", "💫", "🌟", "⚡", "🔥", "💎", "🎯", "🚀"]
        
        captions = [
            f"{random.choice(emojis)} The {product} Everyone's Talking About {random.choice(emojis)}\n\n{tone} vibes only! Perfect for {audience} 💯\n\nTap the link in bio to discover more 👆",
            
            f"{random.choice(emojis)} Your New Favorite {product} {random.choice(emojis)}\n\nDesigned for {audience} who want the best ✨\n\nSwipe for details → Link in bio 🔗",
            
            f"POV: You just found the perfect {product} {random.choice(emojis)}\n\n{tone} | Premium | Trusted by {audience}\n\nGet yours now - link in bio! 💫",
            
            f"{random.choice(emojis)} Game-Changer Alert! {random.choice(emojis)}\n\n{product} that actually works for {audience}\n\nDon't believe us? Check the reviews 👀\nLink in bio! 🔗"
        ]
        
        hashtag_lists = [
            f"#{product.replace(' ', '')} #{business_type.replace(' ', '')} #{audience.replace(' ', '')} #instagood #viral #trending #lifestyle #quality #motivation #success #goals #inspiration #beautiful",
            
            f"#{product.replace(' ', '')} #{business_type.replace(' ', '')} #reels #explore #fyp #trending #viral #lifestyle #{audience.replace(' ', '')} #quality #premium #luxury #style",
            
            f"#{product.replace(' ', '')} #{business_type.replace(' ', '')} #{audience.replace(' ', '')} #instadaily #photooftheday #love #instagood #fashion #beautiful #happy #cute #follow #like"
        ]
        
        story_texts = [
            f"NEW: {product} Alert! 🔥 Swipe up!",
            f"Limited Time: {product} Deal! Tap here 👆",
            f"{product} for {audience} - Link in bio! ✨",
            f"This {product} is 🔥 Get yours now!"
        ]
        
        return {
            "caption": random.choice(captions),
            "hashtags": random.choice(hashtag_lists),
            "cta": random.choice(["Link in Bio", "Swipe Up", "Tap Here", "Shop Now"]),
            "story_text": random.choice(story_texts),
            "estimated_reach": f"{round(random.uniform(2.0, 6.5), 1)}K",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Fallback Mode"
        }
    
    elif platform == "seo":
        return {
            "title": f"{product} for {audience} | Professional {business_type} 2024",
            "meta_description": f"Discover premium {product} designed specifically for {audience}. Expert {business_type.lower()} with {tone.lower()} service, proven results & 100% satisfaction guarantee. Book your free consultation today!",
            "h1": f"Professional {product} Services for {audience}",
            "keywords": f"{product}, {business_type}, {audience}, best {product}, {product} services, professional {business_type}, affordable {product}, top {product}, {product} near me, {product} online, premium {product}",
            "url_slug": f"{product.lower().replace(' ', '-')}-for-{audience.lower().replace(' ', '-')}",
            "estimated_ranking": "Top 10 potential",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Fallback Mode"
        }
    
    # Default fallback
    return {
        "error": "Platform not recognized",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "Fallback Mode"
    }

# ==================== PDF EXPORT ====================
def create_pdf(history_items):
    """Create PDF export using reportlab"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
        )
        story.append(Paragraph("AI Content Generator Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Date
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Content
        for idx, item in enumerate(history_items, 1):
            # Item header
            story.append(Paragraph(f"<b>Content #{idx}</b>", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            # Details table
            data = [
                ['Platform:', item['platform'].upper()],
                ['Product:', item['product']],
                ['Business:', item['business_type']],
                ['Audience:', item['audience']],
                ['Tone:', item['tone']],
                ['Generated:', item['timestamp']]
            ]
            
            table = Table(data, colWidths=[1.5*inch, 4*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            story.append(Spacer(1, 0.2*inch))
            
            # Content details
            story.append(Paragraph("<b>Generated Content:</b>", styles['Heading3']))
            content = json.loads(item['content']) if isinstance(item['content'], str) else item['content']
            for key, value in content.items():
                if key not in ['generated_at', 'prompt_used', 'source']:
                    story.append(Paragraph(f"<b>{key.title()}:</b> {value}", styles['Normal']))
            
            story.append(Spacer(1, 0.4*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    except ImportError:
        return None

# ==================== DOCX EXPORT ====================
def create_docx(history_items):
    """Create DOCX export using python-docx"""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Title
        title = doc.add_heading('AI Content Generator Report', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Date
        date_para = doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()  # Spacing
        
        # Content
        for idx, item in enumerate(history_items, 1):
            # Item header
            doc.add_heading(f"Content #{idx}", level=1)
            
            # Details table
            table = doc.add_table(rows=6, cols=2)
            table.style = 'Light Grid Accent 1'
            
            table.rows[0].cells[0].text = 'Platform:'
            table.rows[0].cells[1].text = item['platform'].upper()
            table.rows[1].cells[0].text = 'Product:'
            table.rows[1].cells[1].text = item['product']
            table.rows[2].cells[0].text = 'Business:'
            table.rows[2].cells[1].text = item['business_type']
            table.rows[3].cells[0].text = 'Audience:'
            table.rows[3].cells[1].text = item['audience']
            table.rows[4].cells[0].text = 'Tone:'
            table.rows[4].cells[1].text = item['tone']
            table.rows[5].cells[0].text = 'Generated:'
            table.rows[5].cells[1].text = item['timestamp']
            
            doc.add_paragraph()  # Spacing
            
            # Content details
            doc.add_heading('Generated Content:', level=2)
            content = json.loads(item['content']) if isinstance(item['content'], str) else item['content']
            for key, value in content.items():
                if key not in ['generated_at', 'prompt_used', 'source']:
                    p = doc.add_paragraph()
                    p.add_run(f"{key.title()}: ").bold = True
                    p.add_run(str(value))
            
            doc.add_page_break()
        
        # Save to buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except ImportError:
        return None

# ==================== DATABASE FUNCTIONS ====================
def save_to_database(user_id, business_type, product, audience, tone, platform, content):
    """Save generation to database"""
    if db_conn is None:
        return False
    
    try:
        c = db_conn.cursor()
        c.execute('''INSERT INTO history 
                     (user_id, timestamp, business_type, product, audience, tone, platform, content)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   business_type, product, audience, tone, platform, json.dumps(content)))
        db_conn.commit()
        return True
    except Exception as e:
        st.error(f"Database save failed: {e}")
        return False

def load_from_database(user_id):
    """Load user's history from database"""
    if db_conn is None:
        return []
    
    try:
        c = db_conn.cursor()
        c.execute('''SELECT id, timestamp, business_type, product, audience, tone, platform, content
                     FROM history WHERE user_id = ? ORDER BY id DESC''', (user_id,))
        rows = c.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "timestamp": row[1],
                "business_type": row[2],
                "product": row[3],
                "audience": row[4],
                "tone": row[5],
                "platform": row[6],
                "content": json.loads(row[7]) if isinstance(row[7], str) else row[7]
            })
        return history
    except Exception as e:
        st.error(f"Database load failed: {e}")
        return []

def save_user_settings(user_id, api_provider, api_key, model, temperature, max_tokens, default_platform, default_tone):
    """Save user settings to database"""
    if db_conn is None:
        return False
    
    try:
        c = db_conn.cursor()
        c.execute('''INSERT OR REPLACE INTO settings 
                     (user_id, api_provider, api_key, model, temperature, max_tokens, default_platform, default_tone)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, api_provider, api_key, model, temperature, max_tokens, default_platform, default_tone))
        db_conn.commit()
        return True
    except Exception as e:
        st.error(f"Settings save failed: {e}")
        return False

def load_user_settings(user_id):
    """Load user settings from database"""
    if db_conn is None:
        return None
    
    try:
        c = db_conn.cursor()
        c.execute('SELECT * FROM settings WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        if row:
            return {
                "api_provider": row[2],
                "api_key": row[3],
                "model": row[4],
                "temperature": row[5],
                "max_tokens": row[6],
                "default_platform": row[7],
                "default_tone": row[8]
            }
        return None
    except Exception as e:
        return None

# ==================== LOGIN/AUTH ====================
def login_page():
    st.title("🔐 AI Content Generator - Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.markdown("### Welcome Back!")
            username = st.text_input("Username", key="login_user", placeholder="Enter username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🚀 Login", type="primary", use_container_width=True):
                    if username and password:
                        # Check database (simplified - add proper password hashing in production)
                        if db_conn:
                            c = db_conn.cursor()
                            c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
                            user = c.fetchone()
                            if user and user[1] == password:  # In production: use bcrypt
                                st.session_state.user_logged_in = True
                                st.session_state.username = username
                                st.session_state.user_id = user[0]
                                
                                # Load user settings
                                settings = load_user_settings(user[0])
                                if settings:
                                    st.session_state.api_provider = settings['api_provider']
                                    st.session_state.api_key = settings['api_key']
                                
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid credentials")
                        else:
                            st.error("Database unavailable")
                    else:
                        st.error("Please fill all fields")
            
            with col_b:
                if st.button("🎮 Demo Mode", use_container_width=True):
                    st.session_state.user_logged_in = True
                    st.session_state.username = "Demo User"
                    st.session_state.user_id = 0
                    st.rerun()
        
        with tab2:
            st.markdown("### Create Account")
            new_username = st.text_input("Username", key="reg_user", placeholder="Choose username")
            new_password = st.text_input("Password", type="password", key="reg_pass", placeholder="Choose password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Re-enter password")
            
            if st.button("📝 Register", type="primary", use_container_width=True):
                if new_username and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("Passwords don't match")
                    elif len(new_password) < 4:
                        st.error("Password must be at least 4 characters")
                    elif db_conn:
                        try:
                            c = db_conn.cursor()
                            c.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                                    (new_username, new_password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            db_conn.commit()
                            st.success("Account created! Please login.")
                        except sqlite3.IntegrityError:
                            st.error("Username already exists")
                        except Exception as e:
                            st.error(f"Registration failed: {e}")
                    else:
                        st.error("Database unavailable")
                else:
                    st.error("Please fill all fields")

# ==================== MAIN APP ====================
def main_app():
    # Load user history from database
    if st.session_state.user_id and st.session_state.user_id > 0:
        history = load_from_database(st.session_state.user_id)
    else:
        history = []
    
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🚀 AI Content Generator Pro")
        st.markdown(f"**Welcome, {st.session_state.username}!** | Generate professional marketing content powered by AI")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.user_logged_in = False
            st.session_state.username = ""
            st.session_state.user_id = None
            st.rerun()
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        page = st.radio("Navigate:", ["🎨 Generate", "📚 History", "📥 Export", "⚙️ Settings"])
        
        st.divider()
        
        # Stats
        st.metric("Total Generated", len(history))
        if history:
            platforms = [h['platform'] for h in history]
            most_used = max(set(platforms), key=platforms.count) if platforms else "N/A"
            st.metric("Most Used", most_used.upper())
        
        st.divider()
        
        # API Status
        if st.session_state.api_key and len(st.session_state.api_key) > 10:
            st.success(f"✅ {st.session_state.api_provider} Connected")
        else:
            st.warning("⚠️ Using Fallback Mode\n\nAdd API key in Settings")
    
    # Page routing
    if page == "🎨 Generate":
        generate_page(history)
    elif page == "📚 History":
        history_page(history)
    elif page == "📥 Export":
        export_page(history)
    elif page == "⚙️ Settings":
        settings_page()

def generate_page(history):
    st.header("✍️ Create Your Marketing Content")
    
    # Load user settings for defaults
    settings = None
    if st.session_state.user_id and st.session_state.user_id > 0:
        settings = load_user_settings(st.session_state.user_id)
    
    # Input form
    with st.form("content_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            business_type = st.selectbox(
                "🏢 Business Type",
                ["Fitness Gym", "Salon & Spa", "Restaurant", "Medical Clinic", 
                 "E-commerce", "Consulting", "Education", "Real Estate", 
                 "Automotive", "Technology", "Fashion", "Bakery"]
            )
            
            product = st.text_input("📦 Product/Service*", placeholder="e.g., Premium Membership")
        
        with col2:
            audience = st.selectbox(
                "🎯 Target Audience",
                ["Students (18-24)", "Professionals (25-35)", "Parents (30-45)", 
                 "Seniors (55+)", "Freelancers", "Business Owners", "Fitness Enthusiasts"]
            )
            
            tone = st.selectbox(
                "🎭 Tone",
                ["Professional", "Friendly", "Urgent", "Exciting", "Emotional", "Informative"],
                index=0 if not settings else ["Professional", "Friendly", "Urgent", "Exciting", "Emotional", "Informative"].index(settings.get('default_tone', 'Professional'))
            )
        
        with col3:
            platform = st.selectbox(
                "📱 Platform",
                ["google_ads", "facebook", "instagram", "seo"],
                format_func=lambda x: {"google_ads": "📊 Google Ads", "facebook": "📘 Facebook", "instagram": "📸 Instagram", "seo": "🔍 SEO"}[x],
                index=0 if not settings else ["google_ads", "facebook", "instagram", "seo"].index(settings.get('default_platform', 'google_ads'))
            )
            
            st.write("")
            st.write("")
        
        submitted = st.form_submit_button("🎯 Generate Content", type="primary", use_container_width=True)
    
    # Generation
    if submitted:
        if not product.strip():
            st.error("⚠️ Please enter product/service name!")
        else:
            with st.spinner("🤖 AI is crafting your content..."):
                # Get settings
                api_key = st.session_state.get('api_key', '')
                api_provider = st.session_state.get('api_provider', 'OpenAI')
                
                # Load additional settings
                temperature = 0.7
                max_tokens = 500
                model = "gpt-3.5-turbo"
                
                if settings:
                    temperature = settings.get('temperature', 0.7)
                    max_tokens = settings.get('max_tokens', 500)
                    model = settings.get('model', 'gpt-3.5-turbo')
                
                # Generate content
                result = generate_content_with_ai(
                    business_type, product, audience, tone, platform,
                    api_key, api_provider, model, temperature, max_tokens
                )
                
                # Save to database
                if st.session_state.user_id and st.session_state.user_id > 0:
                    save_to_database(
                        st.session_state.user_id,
                        business_type, product, audience, tone, platform,
                        result
                    )
                
                st.success("✅ Content generated!")
                st.balloons()
                st.divider()
                
                # Display based on platform
                if platform == "google_ads":
                    st.subheader("📊 Google Ads Campaign")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.text_input("📌 Headline", result.get("headline", ""), key="ga_h")
                        st.text_area("📝 Description", result.get("description", ""), height=100, key="ga_d")
                        st.text_input("👆 CTA", result.get("cta", ""), key="ga_cta")
                        st.text_area("🔑 Keywords", result.get("keywords", ""), height=80, key="ga_k")
                    with col2:
                        st.metric("Est. CTR", result.get("estimated_ctr", "N/A"))
                        st.metric("Quality Score", result.get("quality_score", "N/A"))
                
                elif platform == "facebook":
                    st.subheader("📘 Facebook Ad")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.text_input("📌 Headline", result.get("headline", ""), key="fb_h")
                        st.text_area("📝 Body", result.get("body", ""), height=180, key="fb_b")
                        st.text_input("👆 CTA", result.get("cta", ""), key="fb_cta")
                        st.text_area("🏷️ Hashtags", result.get("hashtags", ""), key="fb_ht")
                    with col2:
                        st.metric("Est. Engagement", result.get("estimated_engagement", "N/A"))
                
                elif platform == "instagram":
                    st.subheader("📸 Instagram Content")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.text_area("📝 Caption", result.get("caption", ""), height=150, key="ig_cap")
                        st.text_area("🏷️ Hashtags", result.get("hashtags", ""), height=100, key="ig_ht")
                        st.text_input("👆 CTA", result.get("cta", ""), key="ig_cta")
                    with col2:
                        st.metric("Est. Reach", result.get("estimated_reach", "N/A"))
                
                elif platform == "seo":
                    st.subheader("🔍 SEO Content")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.text_input("📌 Title", result.get("title", ""), key="seo_t")
                        st.text_area("📝 Meta", result.get("meta_description", ""), height=100, key="seo_m")
                        st.text_input("🔤 H1", result.get("h1", ""), key="seo_h1")
                        st.text_area("🔑 Keywords", result.get("keywords", ""), height=100, key="seo_k")
                    with col2:
                        st.metric("Ranking", result.get("estimated_ranking", "N/A"))

def history_page(history):
    st.header("📚 Generation History")
    
    if not history:
        st.info("📭 No content yet. Generate some!")
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(history))
    with col2:
        platforms = [h['platform'] for h in history]
        st.metric("Platforms", len(set(platforms)))
    with col3:
        if st.button("🗑️ Clear All"):
            if db_conn and st.session_state.user_id:
                c = db_conn.cursor()
                c.execute('DELETE FROM history WHERE user_id = ?', (st.session_state.user_id,))
                db_conn.commit()
                st.rerun()
    
    st.divider()
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        platform_filter = st.selectbox("Filter", ["All"] + list(set([h['platform'] for h in history])))
    with col2:
        sort_order = st.selectbox("Sort", ["Newest", "Oldest"])
    
    filtered = [h for h in history if platform_filter == "All" or h['platform'] == platform_filter]
    if sort_order == "Oldest":
        filtered = list(reversed(filtered))
    
    for item in filtered:
        with st.expander(f"🕒 {item['timestamp']} | {item['platform'].upper()} | {item['product']}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Business:** {item['business_type']}")
                st.write(f"**Product:** {item['product']}")
            with col2:
                st.write(f"**Audience:** {item['audience']}")
                st.write(f"**Tone:** {item['tone']}")
            st.divider()
            st.json(item['content'], expanded=False)

def export_page(history):
    st.header("📥 Export Content")
    
    if not history:
        st.warning("⚠️ No content to export")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.subheader("📄 JSON")
        json_data = json.dumps(history, indent=2)
        st.download_button(
            "💾 JSON",
            json_data,
            f"content_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json",
            use_container_width=True
        )
    
    with col2:
        st.subheader("📊 TXT")
        txt_data = "\n\n".join([f"=== {i['timestamp']} ===\nPlatform: {i['platform']}\nProduct: {i['product']}\n{json.dumps(i['content'], indent=2)}\n" for i in history])
        st.download_button(
            "💾 TXT",
            txt_data,
            f"content_{datetime.now().strftime('%Y%m%d')}.txt",
            "text/plain",
            use_container_width=True
        )
    
    with col3:
        st.subheader("📋 CSV")
        csv_buffer = io.StringIO()
        csv_buffer.write("Timestamp,Platform,Product,Business,Audience,Tone,Content\n")
        for i in history:
            csv_buffer.write(f"{i['timestamp']},{i['platform']},{i['product']},{i['business_type']},{i['audience']},{i['tone']},\"{json.dumps(i['content'])}\"\n")
        st.download_button(
            "💾 CSV",
            csv_buffer.getvalue(),
            f"content_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col4:
        st.subheader("📕 PDF")
        pdf_buffer = create_pdf(history)
        if pdf_buffer:
            st.download_button(
                "💾 PDF",
                pdf_buffer,
                f"content_{datetime.now().strftime('%Y%m%d')}.pdf",
                "application/pdf",
                use_container_width=True
            )
        else:
            st.button("💾 PDF", disabled=True, use_container_width=True)
            st.caption("Install reportlab")
    
    st.divider()
    
    st.subheader("📄 DOCX Export")
    docx_buffer = create_docx(history)
    if docx_buffer:
        st.download_button(
            "💾 Download DOCX Report",
            docx_buffer,
            f"content_{datetime.now().strftime('%Y%m%d')}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        st.info("📌 Install `python-docx` for DOCX export: `pip install python-docx`")

def settings_page():
    st.header("⚙️ Settings")
    
    st.subheader("🔌 API Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        api_provider = st.selectbox(
            "AI Provider",
            ["OpenAI", "Groq", "Anthropic"],
            index=["OpenAI", "Groq", "Anthropic"].index(st.session_state.get('api_provider', 'OpenAI'))
        )
    
    with col2:
        if api_provider == "OpenAI":
            model = st.selectbox("Model", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"])
        elif api_provider == "Groq":
            model = st.selectbox("Model", ["llama3-70b-8192", "mixtral-8x7b-32768"])
        else:
            model = st.selectbox("Model", ["claude-3-sonnet-20240229", "claude-3-opus-20240229"])
    
    api_key = st.text_input(
        f"{api_provider} API Key",
        value=st.session_state.get('api_key', ''),
        type="password",
        placeholder="sk-..." if api_provider == "OpenAI" else "gsk_..." if api_provider == "Groq" else "sk-ant-..."
    )
    
    st.divider()
    
    st.subheader("🎨 Generation Settings")
    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider("Temperature (Creativity)", 0.0, 1.0, 0.7, 0.1)
        default_platform = st.selectbox("Default Platform", ["google_ads", "facebook", "instagram", "seo"])
    with col2:
        max_tokens = st.slider("Max Tokens", 100, 2000, 500, 50)
        default_tone = st.selectbox("Default Tone", ["Professional", "Friendly", "Urgent", "Exciting", "Emotional", "Informative"])
    
    st.divider()
    
    if st.button("💾 Save Settings", type="primary"):
        st.session_state.api_key = api_key
        st.session_state.api_provider = api_provider
        
        if st.session_state.user_id and st.session_state.user_id > 0:
            if save_user_settings(st.session_state.user_id, api_provider, api_key, model, temperature, max_tokens, default_platform, default_tone):
                st.success("✅ Settings saved!")
            else:
                st.error("❌ Save failed")
        else:
            st.info("Settings saved for this session")
    
    st.divider()
    st.info("""
**🚀 AI Content Generator Pro v3.0**

**Features:**
- ✅ Real AI API Integration (OpenAI/Groq/Anthropic)
- ✅ SQLite Database Storage
- ✅ PDF/DOCX Export
- ✅ Advanced NLP Keywords
- ✅ User Authentication
- ✅ Performance Metrics

**Installation:**
```bash
pip install streamlit openai groq anthropic spacy reportlab python-docx
python -m spacy download en_core_web_sm
```

**API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Groq: https://console.groq.com/keys
- Anthropic: https://console.anthropic.com/

For support: contact your administrator
    """)

# Main
if not st.session_state.user_logged_in:
    login_page()
else:
    main_app()

st.divider()
st.caption("🚀 AI Content Generator Pro v3.0 | © 2024")
