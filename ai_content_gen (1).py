import streamlit as st
import json
from datetime import datetime
import re
import sqlite3
import io

# Page config
st.set_page_config(page_title="AI Content Generator Pro", page_icon="🚀", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton>button { width: 100%; }
    .success-box { padding: 1rem; border-radius: 0.5rem; background-color: #d4edda; border: 1px solid #c3e6cb; margin: 1rem 0; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 0.5rem; color: white; }
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE SETUP ====================
def init_database():
    conn = sqlite3.connect('content_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, business_type TEXT, product TEXT, audience TEXT, tone TEXT, platform TEXT, content TEXT, FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, api_provider TEXT, api_key TEXT, model TEXT, temperature REAL, max_tokens INTEGER, default_platform TEXT, default_tone TEXT, FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    return conn

try:
    db_conn = init_database()
except Exception as e:
    st.error(f"Database error: {e}")
    db_conn = None

# ==================== SESSION STATE ====================
if 'user_logged_in' not in st.session_state: st.session_state.user_logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'api_provider' not in st.session_state: st.session_state.api_provider = "Groq"

# ==================== AI API INTEGRATION - UPDATED ====================
def call_openai_api(prompt, api_key, model="gpt-4o-mini", temperature=0.7, max_tokens=800):
    """OpenAI API - UPDATED TO LATEST"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert marketing copywriter. Respond with ONLY valid JSON, no markdown, no explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except ImportError:
        st.warning("⚠️ Run: pip install openai")
        return None
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return None

def call_groq_api(prompt, api_key, model="llama-3.3-70b-versatile", temperature=0.7, max_tokens=800):
    """Groq API - UPDATED TO LATEST"""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert marketing copywriter. Respond with ONLY valid JSON, no markdown, no explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except ImportError:
        st.warning("⚠️ Run: pip install groq")
        return None
    except Exception as e:
        st.error(f"Groq Error: {str(e)}")
        return None

def call_anthropic_api(prompt, api_key, model="claude-sonnet-4-20250514", temperature=0.7, max_tokens=800):
    """Anthropic API - UPDATED TO LATEST"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are an expert marketing copywriter. Respond with ONLY valid JSON, no markdown, no explanations.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except ImportError:
        st.warning("⚠️ Run: pip install anthropic")
        return None
    except Exception as e:
        st.error(f"Anthropic Error: {str(e)}")
        return None

# ==================== CONTENT GENERATION ====================
def generate_content_with_ai(business_type, product, audience, tone, platform, api_key, api_provider, model, temperature, max_tokens):
    prompts = {
        "google_ads": f"""Create Google Ads campaign. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Return ONLY JSON (minimum 150 characters for description):
{{"headline": "compelling 25-30 char headline", "description": "detailed 150-200 character benefit-focused description with clear value proposition and urgency", "cta": "strong 2-3 word action", "keywords": "10 relevant high-converting keywords comma separated"}}""",

        "facebook": f"""Create Facebook ad. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Return ONLY JSON (minimum 200 characters for body):
{{"headline": "attention-grabbing emotional headline", "body": "engaging 200-300 character body text with storytelling, emotional appeal, clear benefits, social proof, and strong call to action that resonates with the target audience", "cta": "clear action phrase", "hashtags": "10 trending relevant hashtags", "image_suggestion": "detailed image description"}}""",

        "instagram": f"""Create Instagram post. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Return ONLY JSON (minimum 150 characters for caption):
{{"caption": "engaging 150-250 character caption with strong hook, value proposition, emotional connection, and clear benefit for the audience", "hashtags": "15 trending relevant hashtags", "cta": "instagram-native action", "story_text": "compelling 20-30 word story text with urgency"}}""",

        "seo": f"""Create SEO content. Business: {business_type}, Product: {product}, Audience: {audience}, Tone: {tone}

Return ONLY JSON (minimum 150 characters for meta):
{{"title": "keyword-rich 55-65 character SEO title", "meta_description": "compelling 155-165 character meta description with keywords, benefits, call to action, and strong relevance to search intent", "h1": "engaging different h1 heading", "keywords": "15 high-value SEO keywords including long-tail", "url_slug": "seo-optimized-url-slug"}}"""
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
    
    # Parse response
    if response:
        try:
            response_clean = response.strip()
            if "```json" in response_clean:
                response_clean = response_clean.split("```json")[1].split("```")[0].strip()
            elif "```" in response_clean:
                response_clean = response_clean.split("```")[1].split("```")[0].strip()
            start = response_clean.find('{')
            end = response_clean.rfind('}') + 1
            if start != -1 and end > start:
                response_clean = response_clean[start:end]
            
            content = json.loads(response_clean)
            content["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content["source"] = f"✅ {api_provider} API"
            return content
        except Exception as e:
            st.warning(f"Parse error: {e}")
            st.code(response)
    
    # Fallback
    st.info("ℹ️ Using Fallback - Add API key for AI content")
    return generate_fallback(business_type, product, audience, tone, platform)

def generate_fallback(business_type, product, audience, tone, platform):
    import random
    if platform == "google_ads":
        descriptions = [
            f"Discover premium {product} designed specifically for {audience}. Our {tone.lower()} {business_type.lower()} service delivers proven results with expert guidance. Limited time offer - transform your experience today with guaranteed satisfaction!",
            f"Experience the best {product} for {audience}. {tone} service backed by years of expertise. Join thousands of satisfied customers who trust our {business_type.lower()} for quality, reliability, and outstanding results. Book your free consultation now!",
            f"Transform your life with our {product} tailored for {audience}. Our {business_type.lower()} combines cutting-edge solutions with {tone.lower()} care. Fast results, affordable pricing, 100% satisfaction guaranteed. Don't wait - start your journey today!"
        ]
        return {
            "headline": f"Premium {product} for {audience}"[:30],
            "description": random.choice(descriptions)[:200],
            "cta": random.choice(["Get Started Today", "Book Free Consultation", "Learn More Now", "Claim Your Offer"]),
            "keywords": f"{product}, {business_type}, {audience}, best {product}, affordable {product}, professional {product} services, top rated {business_type}, {product} near me, expert {product}, quality {business_type}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "🤖 Fallback Mode"
        }
    elif platform == "facebook":
        bodies = [
            f"Hey {audience}! 👋 Looking for the perfect {product}? You've found it!\n\n✨ Why choose our {business_type}?\n• {tone} approach that actually works\n• Proven results backed by hundreds of success stories\n• Expert team with years of experience\n• Fast, reliable, and affordable service\n• 100% satisfaction guaranteed\n\nDon't settle for ordinary when you can have extraordinary! Join our community of happy customers today.\n\n💬 Comment 'INTERESTED' below or send us a message to learn more! Limited spots available.",
            
            f"Attention {audience}! 🎯\n\n{product} doesn't have to be complicated or expensive. Our {business_type.lower()} makes it simple, {tone.lower()}, and incredibly effective.\n\n🌟 What makes us different:\n• Personalized solutions designed for YOU\n• Results that last and transform lives\n• Support whenever you need it\n• Transparent, fair pricing\n• Money-back guarantee\n\nReady to make a change? This is your sign! Drop a 👍 below or send us a DM. Your journey to success starts here!",
            
            f"🚀 Calling all {audience}!\n\nYour search for exceptional {product} ends right here. Our {business_type.lower()} perfectly combines quality, expertise, innovation, and that {tone.lower()} touch you deserve.\n\n💪 Join hundreds who've already made the switch:\n✓ Lightning-fast results you can see\n✓ Professional service that exceeds expectations\n✓ Guaranteed satisfaction or money back\n✓ Community support every step\n\nClick 'Learn More' to discover why we're the #1 choice, or DM us now for exclusive offers!"
        ]
        return {
            "headline": f"✨ Amazing {product} That {audience} Absolutely Love!",
            "body": random.choice(bodies),
            "cta": random.choice(["Learn More Today", "Get Started Now", "Shop Now", "Sign Up Free", "Contact Us Today"]),
            "hashtags": f"#{product.replace(' ','')} #{business_type.replace(' ','')} #{audience.replace(' ','')} #quality #premium #trending #viral #lifestyle #success #motivation #goals #transformation #community",
            "image_suggestion": f"High-quality lifestyle image showing happy, diverse {audience.lower()} successfully using {product} in a bright, modern setting with authentic smiles and natural lighting, conveying trust and results",
            "estimated_engagement": f"{round(random.uniform(3.0, 7.5), 1)}%",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "🤖 Fallback Mode"
        }
    elif platform == "instagram":
        captions = [
            f"✨ The {product} Everyone's Raving About! ✨\n\nPerfect for {audience} who demand the best. Our {tone.lower()} approach delivers real results that transform lives. 💯\n\nSwipe to see why we're different 👉\nTap the link in bio to start your journey! 🔗\n\nTag a friend who needs this! 👇",
            
            f"🌟 Your New Favorite {product} Just Dropped 🌟\n\nSpecially designed for ambitious {audience} who refuse to settle. Experience the difference that {tone.lower()} expertise makes! ✨\n\nWhat you'll love:\n• Real, lasting results 💪\n• Expert guidance 🎯\n• Amazing community 🤝\n\nReady? Link in bio! Don't miss out 🔥",
            
            f"POV: You just discovered the perfect {product} 🎯\n\n{tone} | Premium | Trusted by thousands of {audience}\n\nThis is what you've been searching for. Results that actually last, service that actually cares. 💫\n\nYour transformation starts here 👆\nLink in bio - limited availability! ⚡",
            
            f"🔥 Game-Changer Alert for {audience}! 🔥\n\n{product} that actually delivers on its promises. Revolutionary {business_type.lower()} experience with proven results. 💯\n\nWhy wait? Success is just a click away!\n\n✓ Check the reviews 👀\n✓ See the results 💪\n✓ Join the movement 🚀\n\nLink in bio NOW! ⚡"
        ]
        return {
            "caption": random.choice(captions),
            "hashtags": f"#{product.replace(' ','')} #{business_type.replace(' ','')} #{audience.replace(' ','')} #instagood #viral #trending #lifestyle #quality #motivation #success #goals #inspiration #beautiful #amazing #explore #fyp #reels #love",
            "cta": random.choice(["Link in Bio 🔗", "Swipe Up Now ⬆️", "Tap Here 👆", "Shop Now 🛍️", "DM Us 💬"]),
            "story_text": f"🔥 EXCLUSIVE: New {product} Alert! Perfect for {audience}. Limited time only - swipe up before it's gone! ⚡",
            "estimated_reach": f"{round(random.uniform(2.0, 6.5), 1)}K",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "🤖 Fallback Mode"
        }
    else:  # SEO
        return {
            "title": f"Best {product} for {audience} | Professional {business_type} Services 2024",
            "meta_description": f"Discover premium {product} designed specifically for {audience}. Our expert {business_type.lower()} delivers {tone.lower()} service with proven results, guaranteed satisfaction & free consultation. Transform your experience today!",
            "h1": f"Professional {product} Services Tailored for {audience}",
            "keywords": f"{product}, {business_type}, {audience}, best {product}, professional {product} services, affordable {product}, top rated {business_type}, {product} near me, expert {product}, quality {business_type}, {product} online, premium {product}, certified {business_type}, {product} consultation, leading {product} provider",
            "url_slug": f"{product.lower().replace(' ','-')}-for-{audience.lower().replace(' ','-')}-professional-services",
            "estimated_ranking": "Top 10 potential",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "🤖 Fallback Mode"
        }
    
    return {
        "error": "Platform not recognized",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "🤖 Fallback Mode"
    }

# ==================== DATABASE FUNCTIONS ====================
def save_to_db(user_id, business_type, product, audience, tone, platform, content):
    if not db_conn: return False
    try:
        c = db_conn.cursor()
        c.execute('INSERT INTO history (user_id, timestamp, business_type, product, audience, tone, platform, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), business_type, product, audience, tone, platform, json.dumps(content)))
        db_conn.commit()
        return True
    except: return False

def load_from_db(user_id):
    if not db_conn: return []
    try:
        c = db_conn.cursor()
        c.execute('SELECT * FROM history WHERE user_id = ? ORDER BY id DESC', (user_id,))
        return [{"id": r[0], "timestamp": r[2], "business_type": r[3], "product": r[4], "audience": r[5], "tone": r[6], "platform": r[7], "content": json.loads(r[8])} for r in c.fetchall()]
    except: return []

def save_settings(user_id, api_provider, api_key, model, temp, tokens, plat, tone):
    if not db_conn: return False
    try:
        c = db_conn.cursor()
        c.execute('INSERT OR REPLACE INTO settings VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)', (user_id, api_provider, api_key, model, temp, tokens, plat, tone))
        db_conn.commit()
        return True
    except: return False

def load_settings(user_id):
    if not db_conn: return None
    try:
        c = db_conn.cursor()
        c.execute('SELECT * FROM settings WHERE user_id = ?', (user_id,))
        r = c.fetchone()
        return {"api_provider": r[2], "api_key": r[3], "model": r[4], "temperature": r[5], "max_tokens": r[6], "default_platform": r[7], "default_tone": r[8]} if r else None
    except: return None

# ==================== LOGIN ====================
def login_page():
    st.title("🔐 AI Content Generator - Login")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            st.markdown("### Welcome Back!")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🚀 Login", type="primary", use_container_width=True):
                    if username and password and db_conn:
                        c = db_conn.cursor()
                        c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
                        user = c.fetchone()
                        if user and user[1] == password:
                            st.session_state.user_logged_in = True
                            st.session_state.username = username
                            st.session_state.user_id = user[0]
                            settings = load_settings(user[0])
                            if settings:
                                st.session_state.api_provider = settings['api_provider']
                                st.session_state.api_key = settings['api_key']
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    else:
                        st.error("Fill all fields")
            with col_b:
                if st.button("🎮 Demo Mode", use_container_width=True):
                    st.session_state.user_logged_in = True
                    st.session_state.username = "Demo User"
                    st.session_state.user_id = 0
                    st.rerun()
        with tab2:
            st.markdown("### Create Account")
            new_user = st.text_input("Username", key="reg_user")
            new_pass = st.text_input("Password", type="password", key="reg_pass")
            confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            if st.button("📝 Register", type="primary", use_container_width=True):
                if new_user and new_pass and confirm:
                    if new_pass != confirm:
                        st.error("Passwords don't match")
                    elif len(new_pass) < 4:
                        st.error("Password too short")
                    elif db_conn:
                        try:
                            c = db_conn.cursor()
                            c.execute('INSERT INTO users VALUES (NULL, ?, ?, ?)', (new_user, new_pass, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            db_conn.commit()
                            st.success("Account created! Please login.")
                        except sqlite3.IntegrityError:
                            st.error("Username exists")
                else:
                    st.error("Fill all fields")

# ==================== MAIN APP ====================
def main_app():
    history = load_from_db(st.session_state.user_id) if st.session_state.user_id is not None else []
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🚀 AI Content Generator Pro")
        st.markdown(f"**Welcome, {st.session_state.username}!**")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.user_logged_in = False
            st.rerun()
    
    st.divider()
    
    with st.sidebar:
        st.header("📊 Dashboard")
        page = st.radio("Navigate:", ["🎨 Generate", "📚 History", "⚙️ Settings"])
        st.divider()
        st.metric("Total Generated", len(history))
        if st.session_state.api_key and len(st.session_state.api_key) > 10:
            st.success(f"✅ {st.session_state.api_provider}")
        else:
            st.warning("⚠️ Fallback Mode")
    
    if page == "🎨 Generate":
        generate_page(history)
    elif page == "📚 History":
        history_page(history)
    elif page == "⚙️ Settings":
        settings_page()

def generate_page(history):
    st.header("✍️ Create Marketing Content")
    settings = load_settings(st.session_state.user_id) if st.session_state.user_id and st.session_state.user_id > 0 else None
    
    with st.form("content_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            business = st.selectbox("🏢 Business", ["Fitness Gym", "Salon", "Restaurant", "Clinic", "E-commerce", "Consulting", "Education", "Real Estate"])
            product = st.text_input("📦 Product*", placeholder="e.g., Membership")
        with col2:
            audience = st.selectbox("🎯 Audience", ["Students (18-24)", "Professionals (25-35)", "Parents (30-45)", "Seniors (55+)", "Business Owners"])
            tone = st.selectbox("🎭 Tone", ["Professional", "Friendly", "Urgent", "Exciting"], index=0 if not settings else ["Professional", "Friendly", "Urgent", "Exciting"].index(settings.get('default_tone', 'Professional')))
        with col3:
            platform = st.selectbox("📱 Platform", ["google_ads", "facebook", "instagram", "seo"], format_func=lambda x: {"google_ads": "📊 Google Ads", "facebook": "📘 Facebook", "instagram": "📸 Instagram", "seo": "🔍 SEO"}[x])
        
        submitted = st.form_submit_button("🎯 Generate", type="primary", use_container_width=True)
    
    if submitted and product.strip():
        with st.spinner("🤖 Generating..."):
            temp = 0.7
            tokens = 800
            model = "llama-3.3-70b-versatile"
            if settings:
                temp = settings.get('temperature', 0.7)
                tokens = settings.get('max_tokens', 800)
                model = settings.get('model', 'llama-3.3-70b-versatile')
            
            result = generate_content_with_ai(business, product, audience, tone, platform, st.session_state.get('api_key', ''), st.session_state.get('api_provider', 'Groq'), model, temp, tokens)
            
            # Save to database (works for demo mode too)
            if st.session_state.user_id is not None:
                save_to_db(st.session_state.user_id, business, product, audience, tone, platform, result)
            
            st.success("✅ Generated!")
            st.balloons()
            st.divider()
            
            if platform == "google_ads":
                st.subheader("📊 Google Ads")
                st.text_input("📌 Headline", result.get("headline", ""))
                st.text_area("📝 Description", result.get("description", ""))
                st.text_input("👆 CTA", result.get("cta", ""))
                st.text_area("🔑 Keywords", result.get("keywords", ""))
            elif platform == "facebook":
                st.subheader("📘 Facebook Ad")
                st.text_input("📌 Headline", result.get("headline", ""))
                st.text_area("📝 Body", result.get("body", ""), height=150)
                st.text_input("👆 CTA", result.get("cta", ""))
                st.text_area("🏷️ Hashtags", result.get("hashtags", ""))
            elif platform == "instagram":
                st.subheader("📸 Instagram")
                st.text_area("📝 Caption", result.get("caption", ""))
                st.text_area("🏷️ Hashtags", result.get("hashtags", ""))
            else:
                st.subheader("🔍 SEO")
                st.text_input("📌 Title", result.get("title", ""))
                st.text_area("📝 Meta", result.get("meta_description", ""))
                st.text_area("🔑 Keywords", result.get("keywords", ""))
            
            st.info(f"Source: {result.get('source', 'Unknown')}")

def history_page(history):
    st.header("📚 History")
    if not history:
        st.info("📭 No content yet")
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric("Total", len(history))
    with col2:
        if st.button("🗑️ Clear"):
            if db_conn and st.session_state.user_id:
                c = db_conn.cursor()
                c.execute('DELETE FROM history WHERE user_id = ?', (st.session_state.user_id,))
                db_conn.commit()
                st.rerun()
    
    for item in history:
        with st.expander(f"🕒 {item['timestamp']} | {item['platform'].upper()} | {item['product']}"):
            st.json(item['content'])

def settings_page():
    st.header("⚙️ Settings")
    st.subheader("🔌 API Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        api_provider = st.selectbox("Provider", ["Groq", "OpenAI", "Anthropic"], index=["Groq", "OpenAI", "Anthropic"].index(st.session_state.get('api_provider', 'Groq')))
    with col2:
        if api_provider == "OpenAI":
            model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"])
        elif api_provider == "Groq":
            model = st.selectbox("Model", ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-70b-versatile"])
        else:
            model = st.selectbox("Model", ["claude-sonnet-4-20250514", "claude-opus-4-20250514"])
    
    api_key = st.text_input(f"{api_provider} API Key", value=st.session_state.get('api_key', ''), type="password")
    
    st.divider()
    st.subheader("🎨 Defaults")
    col1, col2 = st.columns(2)
    with col1:
        temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        plat = st.selectbox("Platform", ["google_ads", "facebook", "instagram", "seo"])
    with col2:
        tokens = st.slider("Max Tokens", 100, 2000, 800, 50)
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Urgent", "Exciting"])
    
    if st.button("💾 Save Settings", type="primary"):
        st.session_state.api_key = api_key
        st.session_state.api_provider = api_provider
        if st.session_state.user_id and st.session_state.user_id > 0:
            if save_settings(st.session_state.user_id, api_provider, api_key, model, temp, tokens, plat, tone):
                st.success("✅ Saved!")
        else:
            st.info("Session saved")
    
    st.divider()
    st.info("""
**🚀 AI Content Generator Pro v4.0**

**Updates:**
- ✅ Latest AI models (Llama 3.3, GPT-4o, Claude Sonnet 4)
- ✅ Improved API integration
- ✅ Better error handling

**Setup:**
```bash
pip install streamlit openai groq anthropic
```

**Get API Keys:**
- Groq (FREE): https://console.groq.com/keys
- OpenAI: https://platform.openai.com/api-keys  
- Anthropic: https://console.anthropic.com/
""")

# Main
if not st.session_state.user_logged_in:
    login_page()
else:
    main_app()

st.divider()
st.caption("🚀 AI Content Generator Pro v4.0 | © 2024")
