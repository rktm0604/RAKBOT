"""
RakBot v8 — Agentic Internship Hunter
Raktim Banerjee | NIIT University | March 2026

What's new in v8 (on top of v7):
  1. LLM scoring   — borderline results (score 5-9) sent to local LLaMA for smart evaluation
  2. Skill library — saves winning company patterns, auto-boosts similar future results
  3. FachuBot loop — reads fachubot_v6_log.csv, learns from applied/rejected/positive signals
  4. Deduplication — cross-run dedup using persistent seen_links.json (not just today's CSV)
  5. Auto-apply    — opens Internshala listings in browser for 1-click apply workflow

Run:      python rakbot_v8.py
Schedule: Every 8 hours + Sunday 9AM weekly best-of (same as v7)
"""

import smtplib
import schedule
import time
import datetime
import csv
import os
import re
import sys
import json
import webbrowser
import requests
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ddgs import DDGS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

MY_EMAIL    = os.environ.get("RAKBOT_GMAIL_EMAIL", "raktimbanerjee06@gmail.com")
MY_PASSWORD = os.environ.get("RAKBOT_GMAIL_PASSWORD", "")
if not MY_PASSWORD:
    print("WARNING: RAKBOT_GMAIL_PASSWORD env var not set. Email will fail.")
SEND_TO = "raktimbanerjee06@gmail.com"

CSV_FILE          = "internships_tracker.csv"
PORTAL_CACHE_FILE = "portal_cache.json"
WEEKLY_LOG        = "weekly_log.json"
SEEN_LINKS_FILE   = "seen_links.json"        # v8: persistent cross-run dedup
SKILL_LIBRARY     = "skill_library.json"     # v8: winning company patterns
FACHUBOT_LOG      = "fachubot_v6_log.csv"    # v8: feedback from FachuBot

CURRENT_YEAR = "2026"
STALE_YEARS  = ["2024", "2023", "2022", "2021"]

# LLM config — uses your local Ollama
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
LLM_TIMEOUT  = 30  # seconds per call
LLM_SCORE_THRESHOLD_LOW  = 5   # below this: skip LLM, too weak
LLM_SCORE_THRESHOLD_HIGH = 10  # above this: skip LLM, already strong

# ─── RESUME SKILLS ────────────────────────────────────────────────────────────

STRONG_SKILLS = [
    'rag', 'llm', 'vector database', 'chromadb',
    'large language model', 'sentence transformers',
    'semantic search', 'llama', 'ollama', 'gradio',
    'retrieval augmented', 'ocr', 'tesseract', 'streaming llm',
]
MEDIUM_SKILLS = [
    'python', 'nlp', 'natural language processing', 'machine learning',
    'deep learning', 'transformers', 'pytorch', 'tensorflow',
    'data science', 'ai', 'ml', 'flask', 'fastapi', 'pytest',
]
WEAK_SKILLS = [
    'javascript', 'java', 'sql', 'git', 'github', 'linux',
    'c++', 'jupyter', 'computer architecture', 'vlsi', 'embedded', 'gpu',
    'cuda', 'backend', 'full stack', 'software engineering',
    'developer', 'computer science', 'node.js', 'azure',
]
RESUME_SKILLS = STRONG_SKILLS + MEDIUM_SKILLS + WEAK_SKILLS

# ─── INTERNSHALA CATEGORIES ───────────────────────────────────────────────────

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
    'microsoft research india', 'google research india', 'adobe research',
]

REMOTE_KEYWORDS = [
    'remote', 'work from home', 'wfh', 'virtual internship',
    'online internship', 'fully remote', 'hybrid remote',
    'location independent', 'distributed', 'remote first',
    'telecommute', 'home based', 'global remote', 'worldwide',
]

RELEVANT_KEYWORDS = [
    'intern', 'internship', 'research intern', 'summer intern',
    'fellowship', 'trainee', 'fresher', 'undergraduate', 'student',
]

BLACKLIST_KEYWORDS = [
    'sales intern', 'marketing intern', 'hr intern',
    'finance intern', 'accounting intern', 'legal intern',
    'mechanical', 'civil engineer', 'electrical engineer',
    'senior engineer', '3+ years', '5+ years', '2+ years',
    'full time only', 'permanent only', 'no fresher',
    'business development', 'operations intern',
]

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

CAREER_PORTALS = [
    {"company": "Google",    "url": "https://careers.google.com/jobs/results/?employment_type=INTERN"},
    {"company": "Microsoft", "url": "https://jobs.careers.microsoft.com/global/en/search?q=intern+2026&exp=Internship"},
    {"company": "Intel",     "url": "https://jobs.intel.com/en/search#q=intern+2026&t=Intern"},
    {"company": "AMD",       "url": "https://careers.amd.com/careers-home/jobs?keywords=intern+2026"},
    {"company": "Qualcomm",  "url": "https://careers.qualcomm.com/careers/search?keywords=intern+2026"},
    {"company": "Nvidia",    "url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite?q=intern+2026"},
    {"company": "Apple",     "url": "https://jobs.apple.com/en-us/search?search=intern+2026&sort=newest"},
    {"company": "Samsung",   "url": "https://www.samsung.com/in/aboutsamsung/careers/"},
]

# ─── V8: PERSISTENT DEDUPLICATION ─────────────────────────────────────────────

def load_seen_links() -> set:
    """Cross-run dedup — persists across days unlike v7's CSV-only approach."""
    if not os.path.exists(SEEN_LINKS_FILE):
        # Seed from existing CSV on first run
        seen = set()
        if os.path.exists(CSV_FILE):
            try:
                with open(CSV_FILE, 'r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        seen.add(row.get('link', ''))
                print(f"  Seeded {len(seen)} links from existing CSV into seen_links.json")
            except Exception:
                pass
        save_seen_links(seen)
        return seen
    with open(SEEN_LINKS_FILE, 'r', encoding='utf-8') as f:
        return set(json.load(f))

def save_seen_links(seen: set):
    with open(SEEN_LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(seen), f)

def add_seen_links(new_links: list):
    seen = load_seen_links()
    seen.update(new_links)
    save_seen_links(seen)

# ─── V8: SKILL LIBRARY ────────────────────────────────────────────────────────

def load_skill_library() -> dict:
    """
    Stores winning company patterns.
    Structure: {
      "winning_companies": ["Sarvam AI", "Yellow.ai", ...],
      "winning_keywords":  {"rag": 5, "llm": 8, "python": 3, ...},
      "boost_multiplier":  1.2
    }
    """
    default = {
        "winning_companies": [],
        "winning_keywords": {},
        "boost_multiplier": 1.2,
        "total_applied": 0,
        "total_positive": 0,
    }
    if not os.path.exists(SKILL_LIBRARY):
        return default
    try:
        with open(SKILL_LIBRARY, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {**default, **data}
    except Exception:
        return default

def save_skill_library(lib: dict):
    with open(SKILL_LIBRARY, 'w', encoding='utf-8') as f:
        json.dump(lib, f, indent=2)

def update_skill_library_from_positive(company: str, keywords_found: list):
    """Called when FachuBot marks a company as replied_positive or meeting_scheduled."""
    lib = load_skill_library()
    if company not in lib["winning_companies"]:
        lib["winning_companies"].append(company)
    for kw in keywords_found:
        lib["winning_keywords"][kw] = lib["winning_keywords"].get(kw, 0) + 1
    lib["total_positive"] += 1
    save_skill_library(lib)
    print(f"  Skill library updated: {company} added as winning pattern")

def get_skill_library_boost(title: str, company: str, description: str) -> float:
    """Returns a score multiplier if result matches winning patterns."""
    lib = load_skill_library()
    if not lib["winning_companies"] and not lib["winning_keywords"]:
        return 1.0

    text = (title + ' ' + company + ' ' + description).lower()
    boost = 1.0

    # Company name match
    for wc in lib["winning_companies"]:
        if wc.lower() in text:
            boost = max(boost, lib["boost_multiplier"])
            break

    # Keyword frequency match
    total_kw_weight = sum(lib["winning_keywords"].values()) or 1
    kw_match_weight = 0
    for kw, weight in lib["winning_keywords"].items():
        if kw.lower() in text:
            kw_match_weight += weight
    if kw_match_weight > 0:
        kw_boost = 1.0 + (kw_match_weight / total_kw_weight) * 0.3
        boost = max(boost, kw_boost)

    return boost

# ─── V8: FACHUBOT FEEDBACK LOOP ───────────────────────────────────────────────

def read_fachubot_feedback() -> dict:
    """
    Reads fachubot_v6_log.csv and extracts:
    - Companies with positive replies (boost these)
    - Companies with negative replies (slightly down-weight)
    - Applied companies (mark in CSV)
    Returns dict of {company_name: status}
    """
    feedback = {}
    if not os.path.exists(FACHUBOT_LOG):
        return feedback
    try:
        with open(FACHUBOT_LOG, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                company = row.get('company', '').strip()
                status  = row.get('reply_status', '').strip()
                if company:
                    feedback[company.lower()] = status
    except Exception as e:
        print(f"  FachuBot feedback read error: {e}")
    return feedback

def sync_fachubot_to_skill_library():
    """
    Runs on each RakBot cycle.
    Positive FachuBot replies → update skill library.
    This is the core feedback loop from the agentic patterns repo.
    """
    feedback = read_fachubot_feedback()
    lib = load_skill_library()
    new_positives = 0

    for company, status in feedback.items():
        if status in ['replied_positive', 'meeting_scheduled']:
            if company not in [w.lower() for w in lib["winning_companies"]]:
                # Extract keywords from company name as proxy
                kws = [w for w in company.split() if len(w) > 3]
                update_skill_library_from_positive(company, kws)
                new_positives += 1

    if new_positives:
        print(f"  FachuBot sync: {new_positives} new positive signals learned")
    else:
        print(f"  FachuBot sync: {len(feedback)} companies tracked, no new positives")

def get_fachubot_score_modifier(company: str, feedback: dict) -> int:
    """Returns score modifier based on FachuBot history for this company."""
    status = feedback.get(company.lower(), '')
    modifiers = {
        'replied_positive':    +8,
        'meeting_scheduled':   +12,
        'replied_negative':    -4,
        'no_reply':            -1,
        'waiting':              0,
        'sent':                 +2,
    }
    return modifiers.get(status, 0)

# ─── V8: LLM SCORING ──────────────────────────────────────────────────────────

def llm_score_result(title: str, description: str, company: str) -> dict:
    """
    Uses local LLaMA to evaluate borderline results (score 5-9).
    Returns {"score_boost": int, "reason": str, "relevant": bool}
    Only called for borderline results to avoid slowdown.
    """
    prompt = f"""You are evaluating an internship opportunity for Raktim Banerjee.

His profile:
- 2nd year BTech CSE, NIIT University
- Microsoft Student Ambassador  
- Projects: RAG Study Assistant (streaming, OCR fallback, pytest suite, 90%+ accuracy on RTX 3050), AI Code Review tool (7 languages)
- Skills: Python, LLMs, RAG, ChromaDB, NLP, Gradio, Node.js, Azure
- Goal: AI/ML internship, Summer 2026 (May-August), India or remote

Internship to evaluate:
Title: {title}
Company: {company}
Description: {description[:300]}

Rate this opportunity 1-10 for Raktim. Consider:
- Skill match (RAG, LLM, Python, AI/ML)
- Learning value for a 2nd year student
- Realistic chance of getting it (not too senior)
- Remote/India availability

Respond in this exact format only:
SCORE: [1-10]
RELEVANT: [YES/NO]
REASON: [one sentence max]"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=LLM_TIMEOUT
        )
        if response.status_code == 200:
            text = response.json().get('response', '')
            # Parse response
            score_match   = re.search(r'SCORE:\s*(\d+)', text)
            relevant_match = re.search(r'RELEVANT:\s*(YES|NO)', text, re.IGNORECASE)
            reason_match  = re.search(r'REASON:\s*(.+)', text)

            llm_score    = int(score_match.group(1)) if score_match else 5
            is_relevant  = relevant_match.group(1).upper() == 'YES' if relevant_match else True
            reason       = reason_match.group(1).strip() if reason_match else ''

            # Convert LLM 1-10 to score boost (-3 to +5)
            score_boost = llm_score - 5

            return {"score_boost": score_boost, "reason": reason, "relevant": is_relevant}
    except requests.exceptions.ConnectionError:
        pass  # Ollama not running — silent fallback
    except Exception as e:
        pass  # Any LLM error — silent fallback

    return {"score_boost": 0, "reason": "", "relevant": True}

# ─── V8: AUTO-APPLY WORKFLOW ──────────────────────────────────────────────────

def auto_apply_session(results: list):
    """
    Opens top Internshala listings in browser for 1-click apply.
    Tracks which ones you opened in the CSV.
    Interactive — runs from CLI.
    """
    internshala_results = [r for r in results if r.get('source') == 'Internshala']
    top = sorted(internshala_results, key=lambda x: x.get('score', 0), reverse=True)[:10]

    if not top:
        print("\n  No Internshala results to apply to right now.")
        return

    print("\n" + "=" * 55)
    print("  AUTO-APPLY SESSION — Top Internshala Listings")
    print("=" * 55)
    print(f"  {'#':<4} {'Score':<6} {'Title':<35} {'Company'}")
    print("  " + "-" * 70)
    for i, r in enumerate(top, 1):
        title_short = r['title'][:33]
        company_short = r.get('company', '')[:20]
        print(f"  {i:<4} {r.get('score',0):<6} {title_short:<35} {company_short}")

    print("\n  Options:")
    print("  [1-10] Open that listing in browser")
    print("  [a]    Open ALL top 5 at once")
    print("  [0]    Exit apply session")

    opened = []
    while True:
        choice = input("\n  Choice: ").strip().lower()
        if choice == '0':
            break
        elif choice == 'a':
            for r in top[:5]:
                webbrowser.open(r['link'])
                time.sleep(0.8)
                opened.append(r['link'])
            print(f"  Opened top 5 listings in browser.")
            break
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(top):
                    webbrowser.open(top[idx]['link'])
                    opened.append(top[idx]['link'])
                    print(f"  Opened: {top[idx]['title'][:50]}")
                    mark = input("  Mark as applied? [y/n]: ").strip().lower()
                    if mark == 'y':
                        update_csv_status(top[idx]['link'], 'Applied')
                        print("  Marked as Applied in CSV.")
            except ValueError:
                pass

    if opened:
        print(f"\n  Session done. Opened {len(opened)} listings.")

def update_csv_status(link: str, status: str):
    """Updates status column for a specific link in the CSV."""
    if not os.path.exists(CSV_FILE):
        return
    rows = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row.get('link') == link:
            row['status'] = status
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# ─── CORE PIPELINE (from v7, unchanged) ───────────────────────────────────────

def is_stale(title, body):
    text = (title + ' ' + body).lower()
    for year in STALE_YEARS:
        if year in text and CURRENT_YEAR not in text:
            return True
    return False

def has_current_year(title, body, link=""):
    text = (title + ' ' + body + ' ' + link).lower()
    return any(k in text for k in ['2026', 'summer 2026', 'apply now', 'applications open', 'currently open', 'now hiring'])

def safe_get(url, timeout=15):
    for attempt in range(3):
        try:
            return requests.get(url, headers=SCRAPE_HEADERS, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise
    return None

def get_soup(response_text):
    try:
        return BeautifulSoup(response_text, 'lxml')
    except Exception:
        return BeautifulSoup(response_text, 'html.parser')

def clean_title(title):
    title = re.sub(r'\s+', ' ', title).strip()
    return title[:117] + '...' if len(title) > 120 else title

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
        is_dup = any(
            SequenceMatcher(None, normalized, seen).ratio() > 0.85
            for seen in seen_titles
            if normalized and seen
        )
        if not is_dup:
            seen_titles.append(normalized)
            unique.append(r)
    return unique

# ─── ENHANCED SCORING (v8) ────────────────────────────────────────────────────

def score_result(title, body, link, company="", source="", feedback=None, use_llm=True):
    """
    v8 scoring pipeline:
    1. Keyword score (same as v7)
    2. Skill library boost (new)
    3. FachuBot feedback modifier (new)
    4. LLM evaluation for borderline results (new)
    """
    if feedback is None:
        feedback = {}

    score = 0
    text  = (title + ' ' + body + ' ' + link + ' ' + company).lower()

    # Big tech / research / remote (same weights as v7)
    for c in BIG_TECH_COMPANIES:
        if c in text:
            score += 10
            break
    for i in RESEARCH_INSTITUTES:
        if i in text:
            score += 8
            break
    for k in REMOTE_KEYWORDS:
        if k in text:
            score += 6
            break

    # Tiered skill scoring
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
    score += min(skill_score, 20)

    # Year, stipend, timing boosts
    if CURRENT_YEAR in text:
        score += 4
    if any(k in text for k in ['stipend', 'paid', 'compensation', 'fellowship']):
        score += 3
    if any(k in text for k in ['summer', 'may', 'june', 'july']):
        score += 2
    if source == 'Internshala':
        score += 5

    # v8: Skill library boost
    lib_boost = get_skill_library_boost(title, company, body)
    score = int(score * lib_boost)

    # v8: FachuBot feedback modifier
    score += get_fachubot_score_modifier(company, feedback)

    # v8: LLM scoring for borderline results only
    llm_reason = ""
    if use_llm and LLM_SCORE_THRESHOLD_LOW <= score <= LLM_SCORE_THRESHOLD_HIGH:
        llm_result = llm_score_result(title, body[:200], company)
        score += llm_result.get('score_boost', 0)
        llm_reason = llm_result.get('reason', '')
        if not llm_result.get('relevant', True):
            score = max(0, score - 5)

    return score, llm_reason

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

# ─── SCRAPERS (same as v7) ─────────────────────────────────────────────────────

def scrape_internshala():
    print("\nScraping Internshala...")
    results = []
    seen_titles = set()

    for category in INTERNSHALA_CATEGORIES:
        label, url = category['label'], category['url']
        found = 0
        try:
            response = safe_get(url)
            if not response or response.status_code != 200:
                print(f"  {label}: HTTP {response.status_code if response else 'failed'}")
                continue

            soup = get_soup(response.text)
            cards = (
                soup.find_all('div', class_=re.compile(r'individual_internship|internship-card|internship_meta')) or
                soup.find_all('div', attrs={'data-internship_id': True}) or
                soup.find_all('a', href=re.compile(r'/internship/detail'))
            )

            for card in cards[:12]:
                title_tag   = (card.find(class_=re.compile(r'profile|title|heading|job-title')) or card.find('h3') or card.find('h2') or card.find('a'))
                company_tag = card.find(class_=re.compile(r'company|employer|organization'))
                stipend_tag = card.find(class_=re.compile(r'stipend|salary|compensation'))
                duration_tag= card.find(class_=re.compile(r'duration|months'))
                location_tag= card.find(class_=re.compile(r'location|city|place'))
                link_tag    = card.find('a', href=re.compile(r'/internship'))

                title   = title_tag.get_text(strip=True) if title_tag else ''
                company = company_tag.get_text(strip=True) if company_tag else ''
                if company and company in title:
                    title = title.replace(company, '').strip()

                stipend  = stipend_tag.get_text(strip=True) if stipend_tag else ''
                duration = duration_tag.get_text(strip=True) if duration_tag else ''
                location = location_tag.get_text(strip=True) if location_tag else ''

                href = link_tag.get('href', '') if link_tag else ''
                link = f"https://internshala.com{href}" if href.startswith('/') else href

                if not title or len(title) < 5 or is_stale(title, company):
                    continue

                title_norm = re.sub(r'[^a-z0-9]', '', title.lower())
                if title_norm in seen_titles:
                    continue
                seen_titles.add(title_norm)

                desc_parts = []
                if stipend:  desc_parts.append(f"Stipend: {stipend}")
                if duration: desc_parts.append(f"Duration: {duration}")
                if location: desc_parts.append(f"Location: {location}")
                desc_parts.append(f"Category: {label}")

                results.append({
                    'title': clean_title(title),
                    'company': company,
                    'link': link or url,
                    'description': " | ".join(desc_parts),
                    'source': 'Internshala',
                    'category': 'Internshala',
                    'score': 0,
                    'llm_reason': '',
                })
                found += 1

            print(f"  {label}: {found} listings")
            time.sleep(1.5)

        except Exception as e:
            print(f"  {label}: Error — {e}")

    print(f"Internshala total: {len(results)} scraped")
    return results

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
    cache    = load_portal_cache()
    new_jobs = []

    for portal in CAREER_PORTALS:
        company, url = portal['company'], portal['url']
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
                        'company': company, 'title': clean_title(text),
                        'link': full_url,
                        'description': f"Direct listing from {company} careers portal.",
                        'source': 'Portal', 'category': 'Big Tech', 'score': 15, 'llm_reason': '',
                    })
        except Exception as e:
            print(f"  {company}: Portal error — {e}")

        if not jobs:
            try:
                with DDGS() as ddgs:
                    query = f"{company} internship summer 2026 software AI India OR remote student"
                    for r in list(ddgs.text(query, max_results=3)):
                        title = clean_title(r.get('title', ''))
                        link  = r.get('href', '')
                        body  = r.get('body', '')
                        if title and link and not is_stale(title, body):
                            if any(k in (title + body).lower() for k in ['intern', 'internship']):
                                jobs.append({
                                    'company': company, 'title': title, 'link': link,
                                    'description': body[:200], 'source': 'Portal-Search',
                                    'category': 'Big Tech', 'score': 12, 'llm_reason': '',
                                })
            except Exception:
                pass

        company_cache = cache.get(company, [])
        new_count = 0
        for job in jobs:
            job_id = re.sub(r'[^a-z0-9]', '', job['title'].lower())[:60]
            if job_id not in company_cache:
                new_jobs.append(job)
                company_cache.append(job_id)
                new_count += 1
        cache[company] = company_cache[-100:]
        print(f"  {company}: {new_count} new")

    save_portal_cache(cache)
    print(f"Portal check done: {len(new_jobs)} new")
    return new_jobs

def search_internships():
    print("\nSearching via DuckDuckGo...")
    seen_links = load_seen_links()
    results    = []
    seen_today = set()

    try:
        with DDGS() as ddgs:
            for query in SEARCH_QUERIES:
                try:
                    for r in list(ddgs.text(query, max_results=5)):
                        title = clean_title(r.get('title', ''))
                        link  = r.get('href', '')
                        body  = r.get('body', '')
                        if not title or not link:
                            continue
                        if link in seen_today or link in seen_links:
                            continue
                        seen_today.add(link)
                        if is_stale(title, body) or not is_relevant(title, body):
                            continue
                        results.append({
                            'title': title, 'link': link,
                            'description': body[:250],
                            'score': 0, 'category': get_category(title, body, link),
                            'company': '', 'source': 'Search', 'llm_reason': '',
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"Search error: {e}")

    results = deduplicate(results)
    print(f"Search done: {len(results)} results")
    return results[:20]

# ─── CSV ──────────────────────────────────────────────────────────────────────

def save_to_csv(results):
    if not results:
        return
    fieldnames = ['date', 'title', 'company', 'link', 'description', 'score', 'llm_reason', 'category', 'source', 'status']
    today = datetime.datetime.now().strftime("%d-%m-%Y")
    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in results:
            writer.writerow({
                'date': today,
                'title': r['title'],
                'company': r.get('company', ''),
                'link': r['link'],
                'description': r.get('description', '')[:200],
                'score': r.get('score', 0),
                'llm_reason': r.get('llm_reason', ''),
                'category': r.get('category', 'Other'),
                'source': r.get('source', ''),
                'status': 'Not Applied',
            })
    print(f"Saved {len(results)} results to CSV")

def get_csv_stats():
    if not os.path.exists(CSV_FILE):
        return {'total': 0, 'applied': 0, 'not_applied': 0}
    total = applied = not_applied = 0
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            total += 1
            if row.get('status') == 'Applied':
                applied += 1
            else:
                not_applied += 1
    return {'total': total, 'applied': applied, 'not_applied': not_applied}

# ─── WEEKLY DIGEST (same as v7) ───────────────────────────────────────────────

def load_weekly_log():
    default = {'week_results': [], 'week_start': datetime.datetime.now().strftime("%d-%m-%Y")}
    if not os.path.exists(WEEKLY_LOG):
        return default
    with open(WEEKLY_LOG, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_weekly_log(log):
    with open(WEEKLY_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2)

def update_weekly_log(results):
    log = load_weekly_log()
    log['week_results'].extend([{
        'title': r['title'], 'link': r['link'], 'score': r.get('score', 0),
        'category': r.get('category', ''), 'company': r.get('company', ''),
        'source': r.get('source', ''), 'llm_reason': r.get('llm_reason', ''),
    } for r in results])
    log['week_results'] = sorted(log['week_results'], key=lambda x: x.get('score', 0), reverse=True)[:100]
    save_weekly_log(log)

def send_weekly_digest():
    log          = load_weekly_log()
    week_results = log.get('week_results', [])
    week_start   = log.get('week_start', '')
    today        = datetime.datetime.now().strftime("%d %B %Y")
    stats        = get_csv_stats()
    lib          = load_skill_library()

    if not week_results:
        print("No weekly data yet.")
        return

    top10 = week_results[:10]
    by_category = {}
    for r in week_results:
        cat = r.get('category', 'Other')
        by_category[cat] = by_category.get(cat, 0) + 1

    cards = "".join([f"""
    <div style="background:#f8f9ff;border-left:4px solid #667eea;border-radius:8px;padding:14px;margin:10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <h3 style="margin:0;color:#333;font-size:14px;">{r['title']}</h3>
            <span style="background:#667eea;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">Score: {r['score']}</span>
        </div>
        {"<p style='margin:0 0 6px;color:#764ba2;font-size:11px;font-style:italic;'>AI: " + r['llm_reason'] + "</p>" if r.get('llm_reason') else ""}
        <span style="background:#f0f0f0;color:#666;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:6px;">{r['category']}</span>
        <a href="{r['link']}" style="display:inline-block;margin-top:8px;background:#667eea;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;">View and Apply</a>
    </div>
    """ for r in top10])

    skill_section = ""
    if lib["winning_companies"]:
        skill_section = f"""
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px;margin-top:16px;">
            <h3 style="margin:0 0 6px;color:#166534;font-size:13px;">Skill Library — Winning Patterns Learned</h3>
            <p style="margin:0;color:#166534;font-size:12px;">Companies with positive signals: {', '.join(lib['winning_companies'][:5])}</p>
            <p style="margin:4px 0 0;color:#166534;font-size:12px;">Total positives: {lib['total_positive']} | Applied: {lib['total_applied']}</p>
        </div>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;">
    <div style="max-width:640px;margin:auto;">
        <div style="background:linear-gradient(135deg,#f093fb,#f5576c);border-radius:12px 12px 0 0;padding:28px;text-align:center;">
            <h1 style="color:white;margin:0;font-size:22px;">RakBot v8 Weekly Best-Of</h1>
            <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:13px;">Week of {week_start} → {today} | AI-Enhanced Scoring</p>
        </div>
        <div style="background:#e91e8c;padding:14px 24px;">
            <table width="100%" style="text-align:center;color:white;">
                <tr>
                    <td><div style="font-size:20px;font-weight:bold;">{len(week_results)}</div><div style="font-size:11px;opacity:0.7;">This Week</div></td>
                    <td><div style="font-size:20px;font-weight:bold;">{stats['applied']}</div><div style="font-size:11px;opacity:0.7;">Applied</div></td>
                    <td><div style="font-size:20px;font-weight:bold;color:#ffd700;">{stats['not_applied']}</div><div style="font-size:11px;opacity:0.7;">Pending</div></td>
                    <td><div style="font-size:20px;font-weight:bold;color:#86efac;">{lib['total_positive']}</div><div style="font-size:11px;opacity:0.7;">Positives</div></td>
                </tr>
            </table>
        </div>
        <div style="background:white;padding:24px;border-radius:0 0 12px 12px;">
            <h2 style="font-size:16px;color:#333;margin:0 0 4px;">Top 10 This Week</h2>
            <p style="color:#888;font-size:13px;margin:0 0 16px;">AI-scored + FachuBot feedback-weighted</p>
            {cards}
            {skill_section}
        </div>
    </div>
    </body></html>"""

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"RakBot v8 Weekly: Top {len(top10)} | {today}"
        msg['From']    = MY_EMAIL
        msg['To']      = SEND_TO
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MY_EMAIL, MY_PASSWORD)
            server.sendmail(MY_EMAIL, SEND_TO, msg.as_string())
        print("Weekly digest sent!")
        save_weekly_log({'week_results': [], 'week_start': datetime.datetime.now().strftime("%d-%m-%Y")})
    except Exception as e:
        print(f"Weekly email error: {e}")

# ─── DAILY EMAIL (v8 — adds LLM reason + skill library section) ───────────────

def send_email(search_results, portal_jobs, internshala_results):
    today = datetime.datetime.now().strftime("%d %B %Y")
    stats = get_csv_stats()
    lib   = load_skill_library()

    big_tech = [r for r in search_results if r['category'] == 'Big Tech']
    research = [r for r in search_results if r['category'] == 'Research']
    remote   = [r for r in search_results if r['category'] == 'Remote']
    others   = [r for r in search_results if r['category'] == 'Other']

    def card(r, color):
        llm_note = f"<p style='margin:0 0 6px;color:#7c3aed;font-size:11px;font-style:italic;'>AI note: {r['llm_reason']}</p>" if r.get('llm_reason') else ""
        return f"""
        <div style="background:#f8f9ff;border-left:4px solid {color};border-radius:8px;padding:14px;margin:10px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <h3 style="margin:0;color:#333;font-size:14px;">{r['title']}</h3>
                <span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">Score: {r.get('score',0)}</span>
            </div>
            {llm_note}
            <p style="margin:0 0 8px;color:#888;font-size:12px;">{r.get('description','')[:180]}</p>
            <a href="{r['link']}" style="background:{color};color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;">View and Apply</a>
        </div>"""

    def section(title, emoji, items, color):
        if not items:
            return f"<div style='margin-top:20px;'><h2 style='font-size:15px;color:#333;border-bottom:2px solid {color};padding-bottom:6px;'>{emoji} {title}</h2><p style='color:#bbb;font-size:13px;'>None today.</p></div>"
        return f"<div style='margin-top:24px;'><h2 style='font-size:15px;color:#333;border-bottom:2px solid {color};padding-bottom:6px;'>{emoji} {title} ({len(items)})</h2>{''.join(card(r, color) for r in items)}</div>"

    def internshala_section(items):
        if not items:
            return "<div style='margin-top:24px;'><h2 style='font-size:15px;color:#333;border-bottom:2px solid #00b300;padding-bottom:6px;'>Internshala Direct</h2><p style='color:#bbb;font-size:13px;'>None today.</p></div>"
        cards = "".join([f"""
        <div style="background:#f0fff0;border-left:4px solid #00b300;border-radius:8px;padding:14px;margin:10px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <h3 style="margin:0;color:#333;font-size:14px;">{r['title']}</h3>
                <span style="background:#00b300;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">Score: {r.get('score',0)}</span>
            </div>
            {"<p style='margin:0 0 4px;color:#7c3aed;font-size:11px;font-style:italic;'>AI: " + r['llm_reason'] + "</p>" if r.get('llm_reason') else ""}
            <p style="margin:0 0 4px;color:#555;font-size:13px;font-weight:500;">{r.get('company','')}</p>
            <p style="margin:0 0 8px;color:#888;font-size:12px;">{r.get('description','')[:150]}</p>
            <a href="{r['link']}" style="background:#00b300;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;">View on Internshala</a>
        </div>""" for r in items[:10]])
        return f"<div style='margin-top:24px;'><h2 style='font-size:15px;color:#333;border-bottom:2px solid #00b300;padding-bottom:6px;'>Internshala Direct ({len(items)})</h2>{cards}</div>"

    skill_section = ""
    if lib["winning_companies"]:
        skill_section = f"""
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;margin-top:16px;">
            <p style="margin:0;color:#166534;font-size:12px;"><strong>Skill Library active:</strong> Boosting results similar to {', '.join(lib['winning_companies'][:3])} based on your positive reply history.</p>
        </div>"""

    content = internshala_section(internshala_results) + section("Big Tech", "🏢", big_tech, "#4f46e5") + section("Remote", "🌐", remote, "#0891b2") + section("Research", "🎓", research, "#059669") + section("Other", "💼", others, "#d97706") + skill_section

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;">
    <div style="max-width:640px;margin:auto;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px 12px 0 0;padding:28px;text-align:center;">
            <h1 style="color:white;margin:0;font-size:22px;">RakBot v8 Daily Digest</h1>
            <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;font-size:13px;">{today} | AI-Enhanced Scoring | FachuBot-Linked</p>
        </div>
        <div style="background:#4f46e5;padding:14px 24px;">
            <table width="100%" style="text-align:center;color:white;">
                <tr>
                    <td><div style="font-size:18px;font-weight:bold;">{len(internshala_results)}</div><div style="font-size:11px;opacity:0.7;">Internshala</div></td>
                    <td><div style="font-size:18px;font-weight:bold;">{len(portal_jobs)}</div><div style="font-size:11px;opacity:0.7;">Portals</div></td>
                    <td><div style="font-size:18px;font-weight:bold;">{len(search_results)}</div><div style="font-size:11px;opacity:0.7;">Search</div></td>
                    <td><div style="font-size:18px;font-weight:bold;color:#86efac;">{stats['applied']}</div><div style="font-size:11px;opacity:0.7;">Applied</div></td>
                    <td><div style="font-size:18px;font-weight:bold;color:#ffd700;">{lib['total_positive']}</div><div style="font-size:11px;opacity:0.7;">Positives</div></td>
                </tr>
            </table>
        </div>
        <div style="background:white;padding:24px;border-radius:0 0 12px 12px;">{content}</div>
        <div style="text-align:center;padding:14px;">
            <p style="margin:0;color:#999;font-size:11px;">RakBot v8 | LLM-Scored + FachuBot-Linked | Total: {stats['total']} | Applied: {stats['applied']}</p>
        </div>
    </div></body></html>"""

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"RakBot v8: {len(internshala_results)} Internshala + {len(portal_jobs)} Portal | {today}"
        msg['From']    = MY_EMAIL
        msg['To']      = SEND_TO
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MY_EMAIL, MY_PASSWORD)
            server.sendmail(MY_EMAIL, SEND_TO, msg.as_string())
        print("Daily email sent!")
    except Exception as e:
        print(f"Email error: {e}")

# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

def run_rakbot(interactive=False):
    print("\nRakBot v8 running...")
    print("=" * 55)

    # v8: Sync FachuBot feedback before scoring
    print("\nSyncing FachuBot feedback...")
    sync_fachubot_to_skill_library()
    feedback = read_fachubot_feedback()
    print(f"  {len(feedback)} companies tracked in FachuBot")

    # 1. Scrape Internshala
    internshala_results = scrape_internshala()

    # 2. Monitor portals
    portal_jobs = monitor_portals()

    # 3. DuckDuckGo search
    search_results = search_internships()

    # 4. Score everything with v8 pipeline
    seen_links = load_seen_links()
    print("\nScoring results (LLM for borderline cases)...")

    new_internshala = []
    llm_calls = 0
    for r in internshala_results:
        if r['link'] not in seen_links:
            score, llm_reason = score_result(
                r['title'], r.get('description', ''), r['link'],
                r.get('company', ''), 'Internshala', feedback, use_llm=True
            )
            if llm_reason:
                llm_calls += 1
            r['score']      = score
            r['llm_reason'] = llm_reason
            new_internshala.append(r)

    for r in search_results:
        score, llm_reason = score_result(
            r['title'], r.get('description', ''), r['link'],
            r.get('company', ''), 'Search', feedback, use_llm=True
        )
        if llm_reason:
            llm_calls += 1
        r['score']      = score
        r['llm_reason'] = llm_reason

    new_internshala = sorted(new_internshala, key=lambda x: x['score'], reverse=True)
    search_results  = sorted(search_results,  key=lambda x: x['score'], reverse=True)
    print(f"  LLM evaluated {llm_calls} borderline results")

    # 5. Save + deduplicate
    all_results = new_internshala + portal_jobs + search_results
    save_to_csv(all_results)
    update_weekly_log(all_results)

    # v8: Update persistent seen links
    add_seen_links([r['link'] for r in all_results if r.get('link')])

    # 6. Send email
    send_email(search_results, portal_jobs, new_internshala)

    print(f"\nDone!")
    print(f"  Internshala : {len(new_internshala)} new")
    print(f"  Portals     : {len(portal_jobs)} new")
    print(f"  Search      : {len(search_results)} new")
    print(f"  LLM calls   : {llm_calls}")
    print(f"  Total saved : {len(all_results)}")

    # 7. v8: Auto-apply session (interactive mode only)
    if interactive:
        print("\nWould you like to open top listings for quick apply?")
        if input("  Launch apply session? [y/n]: ").strip().lower() == 'y':
            auto_apply_session(all_results)

    print("\nNext run in 8 hours.\n")

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RakBot v8")
    parser.add_argument('--apply',       action='store_true', help='Launch apply session after run')
    parser.add_argument('--apply-only',  action='store_true', help='Only run apply session on existing CSV data')
    parser.add_argument('--sync-fachu',  action='store_true', help='Only sync FachuBot feedback')
    parser.add_argument('--show-library',action='store_true', help='Show skill library status')
    args = parser.parse_args()

    print("=" * 55)
    print("RakBot v8 — Agentic Internship Hunter")
    print("=" * 55)
    print("  + LLM scoring (local LLaMA, borderline only)")
    print("  + Skill library (learns winning patterns)")
    print("  + FachuBot feedback loop")
    print("  + Persistent cross-run deduplication")
    print("  + Auto-apply session")
    print("=" * 55)

    if args.show_library:
        lib = load_skill_library()
        print(f"\nSkill Library Status:")
        print(f"  Winning companies : {lib['winning_companies']}")
        print(f"  Top keywords      : {sorted(lib['winning_keywords'].items(), key=lambda x: x[1], reverse=True)[:5]}")
        print(f"  Total positives   : {lib['total_positive']}")
        sys.exit(0)

    if args.sync_fachu:
        sync_fachubot_to_skill_library()
        sys.exit(0)

    if args.apply_only:
        data = []
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                data = list(csv.DictReader(f))
        auto_apply_session(data)
        sys.exit(0)

    run_rakbot(interactive=args.apply)

    print("\nScheduled: Every 8 hours | Weekly Sunday 9:00 AM")
    print("Keep this window open. Ctrl+C to stop.\n")

    schedule.every(8).hours.do(run_rakbot)
    schedule.every().sunday.at("09:00").do(send_weekly_digest)

    while True:
        schedule.run_pending()
        time.sleep(60)
