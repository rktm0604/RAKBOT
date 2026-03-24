import smtplib
import schedule
import time
import datetime
import csv
import os
import re
import sys
import json
import requests
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ddgs import DDGS

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional — use system env vars directly

# ============================================
# CONFIGURATION
# ============================================
MY_EMAIL = os.environ.get("RAKBOT_GMAIL_EMAIL", "raktimbanerjee06@gmail.com")
MY_PASSWORD = os.environ.get("RAKBOT_GMAIL_PASSWORD", "")
if not MY_PASSWORD:
    print("⚠️  WARNING: RAKBOT_GMAIL_PASSWORD env var not set!")
    print("   Create a .env file with: RAKBOT_GMAIL_PASSWORD=your_app_password")
    print("   Or set it in your system environment variables.")
    print("   Email sending will fail without this.\n")
SEND_TO = "raktimbanerjee06@gmail.com"
CSV_FILE = "internships_tracker.csv"
PORTAL_CACHE_FILE = "portal_cache.json"
WEEKLY_LOG = "weekly_log.json"
CURRENT_YEAR = "2026"
STALE_YEARS = ["2024", "2023", "2022", "2021"]

# ============================================
# YOUR RESUME SKILLS — tiered for smart scoring
# ============================================
STRONG_SKILLS = [
    'rag', 'llm', 'vector database', 'chromadb',
    'large language model', 'sentence transformers',
    'semantic search', 'llama', 'ollama', 'gradio',
]
MEDIUM_SKILLS = [
    'python', 'nlp', 'natural language processing', 'machine learning',
    'deep learning', 'transformers', 'pytorch', 'tensorflow',
    'data science', 'ai', 'ml', 'flask', 'fastapi',
]
WEAK_SKILLS = [
    'javascript', 'java', 'sql', 'git', 'github', 'linux',
    'c++', 'jupyter', 'computer architecture', 'vlsi', 'embedded', 'gpu',
    'cuda', 'backend', 'full stack', 'software engineering',
    'developer', 'computer science',
]
# Combined list for backward compat
RESUME_SKILLS = STRONG_SKILLS + MEDIUM_SKILLS + WEAK_SKILLS

# ============================================
# INTERNSHALA CATEGORIES
# ============================================
INTERNSHALA_CATEGORIES = [
    {"label": "AI & ML",          "url": "https://internshala.com/internships/artificial-intelligence-internship/"},
    {"label": "Machine Learning", "url": "https://internshala.com/internships/machine-learning-internship/"},
    {"label": "Python",           "url": "https://internshala.com/internships/python-internship/"},
    {"label": "Data Science",     "url": "https://internshala.com/internships/data-science-internship/"},
    {"label": "Software Dev",     "url": "https://internshala.com/internships/software-development-internship/"},
    {"label": "Computer Science", "url": "https://internshala.com/internships/computer-science-internship/"},
    {"label": "WFH AI",           "url": "https://internshala.com/internships/work-from-home-artificial-intelligence-internship/"},
    {"label": "WFH Python",       "url": "https://internshala.com/internships/work-from-home-python-internship/"},
    {"label": "WFH ML",           "url": "https://internshala.com/internships/work-from-home-machine-learning-internship/"},
    {"label": "Deep Learning",    "url": "https://internshala.com/internships/deep-learning-internship/"},
    {"label": "NLP",              "url": "https://internshala.com/internships/natural-language-processing-internship/"},
    {"label": "Full Stack",       "url": "https://internshala.com/internships/full-stack-development-internship/"},
]

SCRAPE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://internshala.com/',
}

# ============================================
# BIG TECH + RESEARCH LISTS
# ============================================
BIG_TECH_COMPANIES = [
    'google', 'meta', 'facebook', 'amazon', 'apple', 'netflix',
    'microsoft', 'amd', 'intel', 'nvidia', 'qualcomm', 'ibm',
    'oracle', 'salesforce', 'adobe', 'linkedin', 'uber',
    'stripe', 'openai', 'deepmind', 'anthropic', 'samsung',
    'cisco', 'atlassian', 'shopify', 'palantir', 'databricks',
    'hugging face', 'cohere', 'groq', 'razorpay', 'flipkart',
    'freshworks', 'zoho', 'browserstack', 'thoughtworks',
    'wipro', 'infosys', 'tcs', 'accenture',
]

RESEARCH_INSTITUTES = [
    'iit', 'iisc', 'iiser', 'nit', 'bits pilani', 'bits',
    'tifr', 'isro', 'drdo', 'csir', 'iiit', 'dtu', 'nsut',
    'indian institute', 'indian statistical', 'isi kolkata',
    'research intern', 'research fellowship', 'summer research',
    'srfp', 'surge', 'mitacs', 'daad', 'cvit',
    'microsoft research india', 'google research india', 'adobe research'
]

REMOTE_KEYWORDS = [
    'remote', 'work from home', 'wfh', 'virtual internship',
    'online internship', 'fully remote', 'hybrid remote',
    'location independent', 'distributed', 'remote first',
    'telecommute', 'home based', 'global remote', 'worldwide'
]

RELEVANT_KEYWORDS = [
    'intern', 'internship', 'research intern', 'summer intern',
    'fellowship', 'trainee', 'fresher', 'undergraduate', 'student'
]

BLACKLIST_KEYWORDS = [
    'sales intern', 'marketing intern', 'hr intern',
    'finance intern', 'accounting intern', 'legal intern',
    'mechanical', 'civil engineer', 'electrical engineer',
    'senior engineer', '3+ years', '5+ years', '2+ years',
    'full time only', 'permanent only', 'no fresher',
    'business development', 'operations intern'
]

# ============================================
# SEARCH QUERIES
# ============================================
SEARCH_QUERIES = [
    "remote AI ML internship 2026 paid undergraduate stipend",
    "remote software engineering internship 2026 India fresher",
    "remote machine learning internship summer 2026 undergraduate",
    "remote Python developer internship 2026 fresher stipend",
    "remote data science internship 2026 CS student paid",
    "virtual internship AI 2026 work from home stipend",
    "remote deep learning internship 2026 student paid",
    "remote NLP internship 2026 undergraduate stipend",
    "fully remote software internship summer 2026 stipend",
    "IIT summer research internship 2026 CS AI ML",
    "IISc research internship 2026 machine learning",
    "summer research fellowship India 2026 CS AI",
    "SRFP 2026 computer science India",
    "IIIT Hyderabad research internship summer 2026",
    "Microsoft Research India internship 2026",
    "Google Research India internship 2026",
    "Google internship India 2026 software engineering student",
    "Microsoft internship India 2026 AI ML undergraduate",
    "Nvidia internship India 2026 AI ML",
    "Intel internship India 2026 CS undergraduate",
    "AMD internship India 2026 software engineer",
    "Qualcomm internship India 2026 software",
    "MITACS 2026 India CS student research",
    "LLM RAG internship 2026 India remote",
    "NLP engineer intern 2026 India remote stipend",
]

# ============================================
# YEAR FILTER
# ============================================
def is_stale(title, body):
    text = (title + ' ' + body).lower()
    for year in STALE_YEARS:
        if year in text and CURRENT_YEAR not in text:
            return True
    return False

def has_current_year(title, body, link=""):
    text = (title + ' ' + body + ' ' + link).lower()
    return any(k in text for k in [
        '2026', 'summer 2026', 'apply now',
        'applications open', 'currently open', 'now hiring'
    ])

# ============================================
# INTERNSHALA SCRAPER
# ============================================
def safe_get(url, timeout=15):
    """HTTP GET with retry logic (up to 3 attempts with backoff)."""
    for attempt in range(3):
        try:
            response = requests.get(url, headers=SCRAPE_HEADERS, timeout=timeout)
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < 2:
                wait = 2 ** attempt  # 1s, 2s
                print(f"    Retry {attempt+1}/3 after {wait}s... ({e.__class__.__name__})")
                time.sleep(wait)
            else:
                raise
    return None

def get_soup(response_text):
    """Parse HTML with lxml fallback to html.parser."""
    try:
        return BeautifulSoup(response_text, 'lxml')
    except Exception:
        return BeautifulSoup(response_text, 'html.parser')

def scrape_internshala():
    print("\nScraping Internshala directly...")
    results = []
    seen_titles = set()

    for category in INTERNSHALA_CATEGORIES:
        label = category['label']
        url = category['url']
        found = 0

        try:
            response = safe_get(url)
            if response is None:
                print(f"  {label}: Request failed")
                continue

            if response.status_code == 403:
                print(f"  {label}: Blocked (403)")
                continue
            if response.status_code != 200:
                print(f"  {label}: HTTP {response.status_code}")
                continue

            soup = get_soup(response.text)

            # Try multiple selectors — Internshala uses different class names
            cards = (
                soup.find_all('div', class_=re.compile(r'individual_internship|internship-card|internship_meta')) or
                soup.find_all('div', attrs={'data-internship_id': True}) or
                soup.find_all('a', href=re.compile(r'/internship/detail'))
            )

            for card in cards[:12]:
                # Title
                title_tag = (
                    card.find(class_=re.compile(r'profile|title|heading|job-title')) or
                    card.find('h3') or card.find('h2') or card.find('a')
                )
                title = title_tag.get_text(strip=True) if title_tag else ''

                # Company
                company_tag = card.find(class_=re.compile(r'company|employer|organization'))
                company = company_tag.get_text(strip=True) if company_tag else ''

                # Strip company name from title if it was included (common with nested tags)
                if company and company in title:
                    title = title.replace(company, '').strip()

                # Stipend
                stipend_tag = card.find(class_=re.compile(r'stipend|salary|compensation'))
                stipend = stipend_tag.get_text(strip=True) if stipend_tag else ''

                # Duration
                duration_tag = card.find(class_=re.compile(r'duration|months'))
                duration = duration_tag.get_text(strip=True) if duration_tag else ''

                # Location
                location_tag = card.find(class_=re.compile(r'location|city|place'))
                location = location_tag.get_text(strip=True) if location_tag else ''

                # Link
                link_tag = card.find('a', href=re.compile(r'/internship'))
                link = ''
                if link_tag:
                    href = link_tag.get('href', '')
                    link = f"https://internshala.com{href}" if href.startswith('/') else href

                if not title or len(title) < 5:
                    continue
                if is_stale(title, company):
                    continue

                title_norm = re.sub(r'[^a-z0-9]', '', title.lower())
                if title_norm in seen_titles:
                    continue
                seen_titles.add(title_norm)

                # Build description
                desc_parts = []
                if stipend:
                    desc_parts.append(f"Stipend: {stipend}")
                if duration:
                    desc_parts.append(f"Duration: {duration}")
                if location:
                    desc_parts.append(f"Location: {location}")
                desc_parts.append(f"Category: {label}")
                description = " | ".join(desc_parts)

                results.append({
                    'title': clean_title(title),
                    'company': company,
                    'link': link or url,
                    'description': description,
                    'source': 'Internshala',
                    'category': 'Internshala',
                    'score': 0
                })
                found += 1

            print(f"  {label}: {found} listings")
            time.sleep(1.5)  # polite crawl delay

        except requests.exceptions.Timeout:
            print(f"  {label}: Timeout")
        except requests.exceptions.ConnectionError:
            print(f"  {label}: Connection failed")
        except Exception as e:
            print(f"  {label}: Error — {e}")

    print(f"Internshala total: {len(results)} listings scraped!")
    return results

# ============================================
# RESUME-BASED SCORING
# ============================================
def score_result(title, body, link, company="", source=""):
    score = 0
    text = (title + ' ' + body + ' ' + link + ' ' + company).lower()

    # Big tech match
    for c in BIG_TECH_COMPANIES:
        if c in text:
            score += 10
            break

    # Research institute match
    for i in RESEARCH_INSTITUTES:
        if i in text:
            score += 8
            break

    # Remote work
    for k in REMOTE_KEYWORDS:
        if k in text:
            score += 6
            break

    # Resume skill match — tiered scoring
    skill_score = 0
    for skill in STRONG_SKILLS:
        if skill in text:
            skill_score += 4
    for skill in MEDIUM_SKILLS:
        if skill in text:
            skill_score += 2
    for skill in WEAK_SKILLS:
        if skill in text:
            skill_score += 1
    score += min(skill_score, 20)  # max +20 from skills

    # Current year boost
    if CURRENT_YEAR in text:
        score += 4

    # Stipend mentioned
    if any(k in text for k in ['stipend', 'paid', 'compensation', 'fellowship', 'remuneration']):
        score += 3

    # Summer timing
    if any(k in text for k in ['summer', 'may', 'june', 'july']):
        score += 2

    # Internshala source bonus — high quality India listings
    if source == 'Internshala':
        score += 5

    return score

def get_category(title, body, link, source=""):
    if source == 'Internshala':
        return 'Internshala'
    text = (title + ' ' + body + ' ' + link).lower()
    if any(c in text for c in BIG_TECH_COMPANIES):
        return 'Big Tech'
    if any(i in text for i in RESEARCH_INSTITUTES):
        return 'Research'
    if any(k in text for k in REMOTE_KEYWORDS):
        return 'Remote'
    return 'Other'

def clean_title(title):
    title = re.sub(r'\s+', ' ', title).strip()
    if len(title) > 120:
        title = title[:117] + '...'
    return title

def is_relevant(title, body):
    text = (title + ' ' + body).lower()
    if not any(k in text for k in RELEVANT_KEYWORDS):
        return False
    if any(k in text for k in BLACKLIST_KEYWORDS):
        return False
    return True

def deduplicate(results):
    seen_titles = []
    unique = []
    for r in results:
        normalized = re.sub(r'[^a-z0-9]', '', r['title'].lower())
        is_dup = False
        for seen in seen_titles:
            if len(normalized) > 0 and len(seen) > 0:
                ratio = SequenceMatcher(None, normalized, seen).ratio()
                if ratio > 0.85:
                    is_dup = True
                    break
        if not is_dup:
            seen_titles.append(normalized)
            unique.append(r)
    return unique

# ============================================
# PORTAL MONITORING
# ============================================
CAREER_PORTALS = [
    {"company": "Google",    "url": "https://careers.google.com/jobs/results/?employment_type=INTERN", "color": "#4285f4"},
    {"company": "Microsoft", "url": "https://jobs.careers.microsoft.com/global/en/search?q=intern+2026&exp=Internship", "color": "#00a4ef"},
    {"company": "Intel",     "url": "https://jobs.intel.com/en/search#q=intern+2026&t=Intern", "color": "#0071c5"},
    {"company": "AMD",       "url": "https://careers.amd.com/careers-home/jobs?keywords=intern+2026", "color": "#ed1c24"},
    {"company": "Qualcomm",  "url": "https://careers.qualcomm.com/careers/search?keywords=intern+2026", "color": "#3253dc"},
    {"company": "Nvidia",    "url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite?q=intern+2026", "color": "#76b900"},
    {"company": "Apple",     "url": "https://jobs.apple.com/en-us/search?search=intern+2026&sort=newest", "color": "#555555"},
    {"company": "Samsung",   "url": "https://www.samsung.com/in/aboutsamsung/careers/", "color": "#1428a0"},
]

def load_portal_cache():
    if not os.path.exists(PORTAL_CACHE_FILE):
        return {}
    with open(PORTAL_CACHE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_portal_cache(cache):
    with open(PORTAL_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)

def monitor_portals():
    print("\nMonitoring company portals...")
    cache = load_portal_cache()
    new_jobs = []

    for portal in CAREER_PORTALS:
        company = portal['company']
        url = portal['url']
        jobs = []

        try:
            response = safe_get(url)
            if response and response.status_code == 200:
                soup = get_soup(response.text)
                for tag in soup(['script', 'style', 'nav', 'footer']):
                    tag.decompose()

                for link in soup.find_all('a', href=True):
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if not text or len(text) < 5 or len(text) > 200:
                        continue
                    if not any(k in text.lower() for k in ['intern', 'internship', 'student', 'trainee']):
                        continue
                    if is_stale(text, ''):
                        continue
                    full_url = f"https://{url.split('/')[2]}{href}" if href.startswith('/') else href
                    jobs.append({
                        'company': company,
                        'title': clean_title(text),
                        'link': full_url,
                        'description': f"Direct listing from {company} careers portal.",
                        'source': 'Portal',
                        'category': 'Big Tech',
                        'score': 15
                    })
            elif response:
                print(f"  {company}: HTTP {response.status_code}")

        except Exception as e:
            print(f"  {company}: Portal error — {e}")

        # Fallback to search if portal blocked
        if not jobs:
            try:
                with DDGS() as ddgs:
                    query = f"{company} internship summer 2026 software AI India OR remote student"
                    hits = list(ddgs.text(query, max_results=3))
                    for r in hits:
                        title = clean_title(r.get('title', '').strip())
                        link = r.get('href', '').strip()
                        body = r.get('body', '').strip()
                        if not title or not link:
                            continue
                        if is_stale(title, body):
                            continue
                        if any(k in (title + body).lower() for k in ['intern', 'internship']):
                            jobs.append({
                                'company': company,
                                'title': title,
                                'link': link,
                                'description': body[:200],
                                'source': 'Portal-Search',
                                'category': 'Big Tech',
                                'score': 12
                            })
            except Exception as e:
                print(f"  {company}: Search fallback error — {e}")

        # Only keep new jobs
        company_cache = cache.get(company, [])
        for job in jobs:
            job_id = re.sub(r'[^a-z0-9]', '', job['title'].lower())[:60]
            if job_id not in company_cache:
                new_jobs.append(job)
                company_cache.append(job_id)
        cache[company] = company_cache[-100:]

        print(f"  {company}: {len([j for j in jobs if re.sub(r'[^a-z0-9]','',j['title'].lower())[:60] not in cache.get(company,[])])} new")

    save_portal_cache(cache)
    print(f"Portal check done: {len(new_jobs)} new!")
    return new_jobs

# ============================================
# DDGS SEARCH
# ============================================
def search_internships():
    print(f"\nSearching via DuckDuckGo...")
    seen_links = load_seen_links()
    results = []
    seen_today = set()

    try:
        with DDGS() as ddgs:
            for query in SEARCH_QUERIES:
                try:
                    hits = list(ddgs.text(query, max_results=5))
                    for r in hits:
                        title = clean_title(r.get('title', '').strip())
                        link = r.get('href', '').strip()
                        body = r.get('body', '').strip()

                        if not title or not link:
                            continue
                        if link in seen_today or link in seen_links:
                            continue
                        seen_today.add(link)

                        if is_stale(title, body):
                            continue
                        if not is_relevant(title, body):
                            continue

                        score = score_result(title, body, link)
                        if has_current_year(title, body, link):
                            score += 3
                        category = get_category(title, body, link)

                        results.append({
                            'title': title,
                            'link': link,
                            'description': body[:250] if body else 'Click to view.',
                            'score': score,
                            'category': category,
                            'company': '',
                            'source': 'Search'
                        })
                except Exception as e:
                    continue
    except Exception as e:
        print(f"Search error: {e}")

    results = deduplicate(results)
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    print(f"Search done: {len(results)} results")
    return results[:20]

# ============================================
# CSV TRACKER
# ============================================
def load_seen_links():
    seen = set()
    if not os.path.exists(CSV_FILE):
        return seen
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seen.add(row.get('link', ''))
    return seen

def save_to_csv(results):
    if not results:
        return
    fieldnames = ['date', 'title', 'company', 'link', 'description', 'score', 'category', 'source', 'status']
    today = datetime.datetime.now().strftime("%d-%m-%Y")

    # Check if existing CSV has the correct header
    file_exists = os.path.exists(CSV_FILE)
    needs_header = not file_exists
    if file_exists:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            expected_header = ','.join(fieldnames)
            if first_line != expected_header:
                print(f"  ⚠️ CSV header mismatch — expected 9 columns, found: {first_line[:60]}...")
                print(f"  Run the migration script or delete the CSV to fix.")

    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if needs_header:
            writer.writeheader()
        for r in results:
            writer.writerow({
                'date': today,
                'title': r['title'],
                'company': r.get('company', ''),
                'link': r['link'],
                'description': r.get('description', '')[:200],
                'score': r.get('score', 0),
                'category': r.get('category', 'Other'),
                'source': r.get('source', ''),
                'status': 'Not Applied'
            })
    print(f"Saved {len(results)} results to CSV")

def get_csv_stats():
    if not os.path.exists(CSV_FILE):
        return {'total': 0, 'applied': 0, 'not_applied': 0}
    total = applied = not_applied = 0
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get('status') == 'Applied':
                applied += 1
            else:
                not_applied += 1
    return {'total': total, 'applied': applied, 'not_applied': not_applied}

# ============================================
# WEEKLY DIGEST
# ============================================
def load_weekly_log():
    if not os.path.exists(WEEKLY_LOG):
        return {'week_results': [], 'week_start': datetime.datetime.now().strftime("%d-%m-%Y")}
    with open(WEEKLY_LOG, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_weekly_log(log):
    with open(WEEKLY_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2)

def update_weekly_log(results):
    log = load_weekly_log()
    log['week_results'].extend([{
        'title': r['title'],
        'link': r['link'],
        'score': r.get('score', 0),
        'category': r.get('category', ''),
        'company': r.get('company', ''),
        'source': r.get('source', '')
    } for r in results])
    # Keep only top 100 per week
    log['week_results'] = sorted(log['week_results'], key=lambda x: x.get('score', 0), reverse=True)[:100]
    save_weekly_log(log)

def send_weekly_digest():
    log = load_weekly_log()
    week_results = log.get('week_results', [])
    week_start = log.get('week_start', '')
    today = datetime.datetime.now().strftime("%d %B %Y")
    stats = get_csv_stats()

    if not week_results:
        print("No weekly data yet.")
        return

    # Top 10 of the week
    top10 = week_results[:10]
    by_category = {}
    for r in week_results:
        cat = r.get('category', 'Other')
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += 1

    cards = "".join([f"""
    <div style="background:#f8f9ff;border-left:4px solid #667eea;border-radius:8px;padding:14px;margin:10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <h3 style="margin:0;color:#333;font-size:14px;">{r['title']}</h3>
            <span style="background:#667eea;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">Score: {r['score']}</span>
        </div>
        <div style="margin-bottom:8px;">
            <span style="background:#f0f0f0;color:#666;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:6px;">{r['category']}</span>
            <span style="background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:4px;font-size:11px;">{r.get('source','')}</span>
        </div>
        <a href="{r['link']}" style="background:#667eea;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;">View and Apply</a>
    </div>
    """ for r in top10])

    category_stats = "".join([f"""
    <div style="text-align:center;padding:8px;">
        <div style="font-size:18px;font-weight:bold;color:white;">{count}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.7);">{cat}</div>
    </div>
    """ for cat, count in by_category.items()])

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;">
        <div style="max-width:640px;margin:auto;">
            <div style="background:linear-gradient(135deg,#f093fb,#f5576c);border-radius:12px 12px 0 0;padding:28px;text-align:center;">
                <h1 style="color:white;margin:0;font-size:22px;">RakBot Weekly Best-Of</h1>
                <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:13px;">Week of {week_start} → {today}</p>
            </div>
            <div style="background:#e91e8c;padding:14px 24px;display:flex;justify-content:space-around;">
                <div style="text-align:center;">
                    <div style="font-size:20px;font-weight:bold;color:white;">{len(week_results)}</div>
                    <div style="font-size:11px;color:rgba(255,255,255,0.7);">Total This Week</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:20px;font-weight:bold;color:white;">{stats['applied']}</div>
                    <div style="font-size:11px;color:rgba(255,255,255,0.7);">Applied</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:20px;font-weight:bold;color:#ffd700;">{stats['not_applied']}</div>
                    <div style="font-size:11px;color:rgba(255,255,255,0.7);">Pending</div>
                </div>
            </div>
            <div style="background:white;padding:24px;border-radius:0 0 12px 12px;">
                <h2 style="font-size:16px;color:#333;margin:0 0 4px;">🏆 Top 10 Opportunities This Week</h2>
                <p style="color:#888;font-size:13px;margin:0 0 16px;">Ranked by relevance to your resume skills (RAG, LLM, Python, ML)</p>
                {cards}
                <div style="background:#fff3cd;border:1px solid #fcd34d;border-radius:8px;padding:14px;margin-top:20px;">
                    <p style="margin:0;color:#92400e;font-size:13px;"><strong>Weekly Goal:</strong> Apply to at least 5 of these before next Sunday. Update your CSV tracker!</p>
                </div>
            </div>
            <div style="text-align:center;padding:14px;">
                <p style="margin:0;color:#999;font-size:11px;">RakBot v7 Weekly Digest | Total Tracked: {stats['total']} | Applied: {stats['applied']}</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"RakBot Weekly Best-Of: Top {len(top10)} Opportunities | {today}"
        msg['From'] = MY_EMAIL
        msg['To'] = SEND_TO
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MY_EMAIL, MY_PASSWORD)
            server.sendmail(MY_EMAIL, SEND_TO, msg.as_string())
        print("Weekly digest email sent!")

        # Reset weekly log
        save_weekly_log({'week_results': [], 'week_start': datetime.datetime.now().strftime("%d-%m-%Y")})

    except Exception as e:
        print(f"Weekly email error: {e}")

# ============================================
# DAILY EMAIL
# ============================================
def send_email(search_results, portal_jobs, internshala_results):
    today = datetime.datetime.now().strftime("%d %B %Y")
    stats = get_csv_stats()

    big_tech = [r for r in search_results if r['category'] == 'Big Tech']
    research = [r for r in search_results if r['category'] == 'Research']
    remote = [r for r in search_results if r['category'] == 'Remote']
    others = [r for r in search_results if r['category'] == 'Other']

    def render_section(title, emoji, items, color):
        if not items:
            return f"""
            <div style="margin-top:20px;">
                <h2 style="font-size:15px;color:#333;border-bottom:2px solid {color};padding-bottom:6px;">{emoji} {title}</h2>
                <p style="color:#bbb;font-size:13px;padding:8px 0;">No new {title.lower()} found today.</p>
            </div>"""
        cards = "".join([f"""
        <div style="background:#f8f9ff;border-left:4px solid {color};border-radius:8px;padding:14px;margin:10px 0;">
            <h3 style="margin:0 0 6px;color:#333;font-size:14px;">{r['title']}</h3>
            <p style="margin:0 0 8px;color:#888;font-size:12px;">{r.get('description','')[:180]}...</p>
            <a href="{r['link']}" style="background:{color};color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;">View and Apply</a>
            <span style="margin-left:8px;background:#f0f0f0;color:#666;padding:3px 8px;border-radius:4px;font-size:11px;">Score: {r.get('score',0)}</span>
        </div>""" for r in items])
        return f"""
        <div style="margin-top:24px;">
            <h2 style="font-size:15px;color:#333;border-bottom:2px solid {color};padding-bottom:6px;">{emoji} {title} ({len(items)})</h2>
            {cards}
        </div>"""

    def render_internshala_section(items):
        if not items:
            return """
            <div style="margin-top:24px;">
                <h2 style="font-size:15px;color:#333;border-bottom:2px solid #00b300;padding-bottom:6px;">🎯 Internshala Direct</h2>
                <p style="color:#bbb;font-size:13px;padding:8px 0;">No new Internshala listings today — site may have blocked scraping. Check manually at internshala.com</p>
            </div>"""
        cards = "".join([f"""
        <div style="background:#f0fff0;border-left:4px solid #00b300;border-radius:8px;padding:14px;margin:10px 0;">
            <h3 style="margin:0 0 4px;color:#333;font-size:14px;">{r['title']}</h3>
            <p style="margin:0 0 4px;color:#555;font-size:13px;font-weight:500;">{r.get('company','')}</p>
            <p style="margin:0 0 8px;color:#888;font-size:12px;">{r.get('description','')[:150]}</p>
            <a href="{r['link']}" style="background:#00b300;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;">View on Internshala</a>
            <span style="margin-left:8px;background:#e6ffe6;color:#006600;padding:3px 8px;border-radius:4px;font-size:11px;">Score: {r.get('score',0)}</span>
        </div>""" for r in items[:10]])
        return f"""
        <div style="margin-top:24px;">
            <h2 style="font-size:15px;color:#333;border-bottom:2px solid #00b300;padding-bottom:6px;">🎯 Internshala Direct ({len(items)} listings)</h2>
            <p style="color:#666;font-size:12px;margin:0 0 12px;">Scraped directly from Internshala — freshest India listings!</p>
            {cards}
        </div>"""

    def render_portal_section(jobs):
        if not jobs:
            return """
            <div style="margin-top:24px;">
                <h2 style="font-size:15px;color:#333;border-bottom:2px solid #e11d48;padding-bottom:6px;">🏭 Company Portal Hits</h2>
                <p style="color:#bbb;font-size:13px;padding:8px 0;">No new portal listings today.</p>
            </div>"""
        by_company = {}
        for j in jobs:
            c = j['company']
            if c not in by_company:
                by_company[c] = []
            by_company[c].append(j)
        sections = ""
        for company, cjobs in by_company.items():
            cards = "".join([f"""
            <div style="background:#fff5f5;border-left:4px solid #e11d48;border-radius:8px;padding:12px;margin:8px 0;">
                <h3 style="margin:0 0 6px;color:#333;font-size:13px;">{j['title']}</h3>
                <a href="{j['link']}" style="background:#e11d48;color:white;padding:5px 12px;border-radius:6px;text-decoration:none;font-size:12px;">Apply Directly</a>
                <span style="margin-left:8px;background:#ffe4e6;color:#be123c;padding:3px 8px;border-radius:4px;font-size:11px;">NEW</span>
            </div>""" for j in cjobs[:5]])
            sections += f"<h3 style='font-size:13px;color:#e11d48;margin:12px 0 4px;'>{company}</h3>{cards}"
        return f"""
        <div style="margin-top:24px;">
            <h2 style="font-size:15px;color:#333;border-bottom:2px solid #e11d48;padding-bottom:6px;">🏭 Company Portal Hits ({len(jobs)})</h2>
            {sections}
        </div>"""

    content = (
        render_internshala_section(internshala_results) +
        render_portal_section(portal_jobs) +
        render_section("FAANG and Big Tech", "🏢", big_tech, "#4f46e5") +
        render_section("Remote Internships", "🌐", remote, "#0891b2") +
        render_section("Research Institutes India", "🎓", research, "#059669") +
        render_section("Other Opportunities", "💼", others, "#d97706")
    )

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;">
        <div style="max-width:640px;margin:auto;">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px 12px 0 0;padding:28px;text-align:center;">
                <h1 style="color:white;margin:0;font-size:22px;">RakBot v7 Daily Digest</h1>
                <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;font-size:13px;">{today} | Summer 2026 | Resume-Matched</p>
            </div>
            <div style="background:#4f46e5;padding:14px 24px;">
                <table width="100%" style="text-align:center;color:white;">
                    <tr>
                        <td><div style="font-size:18px;font-weight:bold;">{len(internshala_results)}</div><div style="font-size:11px;opacity:0.7;">Internshala</div></td>
                        <td><div style="font-size:18px;font-weight:bold;">{len(portal_jobs)}</div><div style="font-size:11px;opacity:0.7;">Portals</div></td>
                        <td><div style="font-size:18px;font-weight:bold;">{len(search_results)}</div><div style="font-size:11px;opacity:0.7;">Search</div></td>
                        <td><div style="font-size:18px;font-weight:bold;">{len(remote)}</div><div style="font-size:11px;opacity:0.7;">Remote</div></td>
                        <td><div style="font-size:18px;font-weight:bold;color:#86efac;">{stats['applied']}</div><div style="font-size:11px;opacity:0.7;">Applied</div></td>
                    </tr>
                </table>
            </div>
            <div style="background:white;padding:24px;border-radius:0 0 12px 12px;">
                <p style="color:#555;margin:0 0 4px;">Hey Raktim! Results scored against your resume skills (RAG, LLM, Python, NLP):</p>
                {content}
                <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:14px;margin-top:20px;">
                    <p style="margin:0;color:#92400e;font-size:13px;"><strong>Tip:</strong> Internshala section has the most relevant India listings. Weekly best-of arrives every Sunday!</p>
                </div>
            </div>
            <div style="text-align:center;padding:14px;">
                <p style="margin:0;color:#999;font-size:11px;">RakBot v7 | Sources: Internshala + Portals + Search | Total: {stats['total']} | Applied: {stats['applied']}</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"RakBot v7: {len(internshala_results)} Internshala + {len(portal_jobs)} Portal + {len(search_results)} Search | {today}"
        msg['From'] = MY_EMAIL
        msg['To'] = SEND_TO
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MY_EMAIL, MY_PASSWORD)
            server.sendmail(MY_EMAIL, SEND_TO, msg.as_string())
        print(f"Daily email sent!")
    except Exception as e:
        print(f"Email error: {e}")

# ============================================
# MAIN JOB
# ============================================
def run_rakbot():
    print("\nRakBot v7 running...")
    print("=" * 50)

    # 1. Scrape Internshala directly
    internshala_results = scrape_internshala()

    # 2. Monitor company portals
    portal_jobs = monitor_portals()

    # 3. DuckDuckGo search
    search_results = search_internships()

    # 4. Score Internshala results
    seen_links = load_seen_links()
    new_internshala = []
    for r in internshala_results:
        if r['link'] not in seen_links:
            r['score'] = score_result(r['title'], r.get('description', ''), r['link'], r.get('company', ''), 'Internshala')
            new_internshala.append(r)

    new_internshala = sorted(new_internshala, key=lambda x: x['score'], reverse=True)

    # 5. Save all to CSV
    all_results = new_internshala + portal_jobs + search_results
    save_to_csv(all_results)

    # 6. Update weekly log
    update_weekly_log(all_results)

    # 7. Send daily email
    send_email(search_results, portal_jobs, new_internshala)

    print(f"\nDone!")
    print(f"  Internshala: {len(new_internshala)} new")
    print(f"  Portals:     {len(portal_jobs)} new")
    print(f"  Search:      {len(search_results)} new")
    print(f"  Total saved: {len(all_results)}")
    print("Next run at 8:00 AM tomorrow.\n")

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("RakBot v7 - Internshala + Portal + Search")
    print("=" * 50)
    print("Improvements:")
    print("  + Internshala direct scraper (12 categories)")
    print("  + Resume-based scoring (RAG, LLM, Python, ML)")
    print("  + Weekly best-of digest every Sunday")
    print("  + Source column in CSV")
    print("=" * 50)
    print("Running now...")

    run_rakbot()

    print("Scheduled: Daily at 8:00 AM")
    print("           Weekly digest every Sunday at 9:00 AM")
    print("Keep this window open. Ctrl+C to stop.\n")

    schedule.every().day.at("08:00").do(run_rakbot)
    schedule.every().sunday.at("09:00").do(send_weekly_digest)

    while True:
        schedule.run_pending()
        time.sleep(60)