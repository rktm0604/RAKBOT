import csv
import json
import webbrowser
import argparse
import sys
from datetime import datetime
import urllib.parse

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

# ─────────────────────────────────────────────
#  FACHUBOT v5 — AI/ML Startup Outreach
#  Raktim Banerjee | NIIT University | Mar 2026
#  Replaces v4 semiconductor targets with
#  Indian AI/ML startups + product companies
# ─────────────────────────────────────────────

LOG_FILE = "fachubot_v5_log.csv"

# ─── TARGET COMPANIES ────────────────────────
# Tier 3 = funded AI startups (best odds)
# Tier 2 = known product companies (stretch)

COMPANIES = [
    # ── Tier 3: AI/ML Startups (best bet) ──
    {"name": "Sarvam AI",         "tier": 3, "domain": "AI/LLM",        "location": "Bangalore", "careers": "sarvam.ai/careers",           "linkedin_search": "Sarvam AI engineer intern hiring"},
    {"name": "Krutrim",           "tier": 3, "domain": "AI/LLM",        "location": "Bangalore", "careers": "krutrim.com",                  "linkedin_search": "Krutrim AI intern hiring"},
    {"name": "Dhruva AI",         "tier": 3, "domain": "AI/NLP",        "location": "Bangalore", "careers": "dhruva.ai",                    "linkedin_search": "Dhruva AI engineer hiring"},
    {"name": "Gnani.ai",          "tier": 3, "domain": "NLP/Voice",     "location": "Bangalore", "careers": "gnani.ai/careers",             "linkedin_search": "Gnani AI intern NLP hiring"},
    {"name": "Observe.AI",        "tier": 3, "domain": "AI/NLP",        "location": "Bangalore", "careers": "observe.ai/careers",           "linkedin_search": "Observe AI engineer intern"},
    {"name": "Yellow.ai",         "tier": 3, "domain": "Conversational AI","location": "Bangalore","careers": "yellow.ai/careers",          "linkedin_search": "Yellow AI intern hiring engineer"},
    {"name": "Haptik",            "tier": 3, "domain": "Conversational AI","location": "Mumbai",  "careers": "haptik.ai/careers",           "linkedin_search": "Haptik AI intern engineer hiring"},
    {"name": "Mihup",             "tier": 3, "domain": "Voice AI",      "location": "Kolkata",   "careers": "mihup.com/careers",            "linkedin_search": "Mihup AI intern Kolkata"},
    {"name": "Vernacular.ai",     "tier": 3, "domain": "NLP",           "location": "Bangalore", "careers": "vernacular.ai",                "linkedin_search": "Vernacular AI NLP intern hiring"},
    {"name": "Entropik Tech",     "tier": 3, "domain": "Emotion AI",    "location": "Bangalore", "careers": "entropik.io/careers",          "linkedin_search": "Entropik Tech intern engineer"},
    {"name": "Scaler",            "tier": 3, "domain": "EdTech/AI",     "location": "Bangalore", "careers": "scaler.com/careers",           "linkedin_search": "Scaler intern software engineer hiring"},
    {"name": "Mudrex",            "tier": 3, "domain": "FinTech/AI",    "location": "Bangalore", "careers": "mudrex.com/careers",           "linkedin_search": "Mudrex intern engineer hiring"},
    {"name": "Leena AI",          "tier": 3, "domain": "HR AI",         "location": "Bangalore", "careers": "leena.ai/careers",             "linkedin_search": "Leena AI intern engineer hiring"},
    {"name": "Sigtuple",          "tier": 3, "domain": "Medical AI",    "location": "Bangalore", "careers": "sigtuple.com/careers",         "linkedin_search": "Sigtuple AI intern engineer"},
    {"name": "Niramai",           "tier": 3, "domain": "Medical AI",    "location": "Bangalore", "careers": "niramai.com/careers",          "linkedin_search": "Niramai AI intern ML engineer"},
    {"name": "Mad Street Den",    "tier": 3, "domain": "Retail AI",     "location": "Chennai",   "careers": "madstreetden.com/careers",     "linkedin_search": "Mad Street Den intern engineer"},
    {"name": "Frugal Testing",    "tier": 3, "domain": "AI Testing",    "location": "Remote",    "careers": "frugaltesting.com",            "linkedin_search": "Frugal Testing intern engineer hiring"},
    {"name": "Voicezen",          "tier": 3, "domain": "Voice AI",      "location": "Mumbai",    "careers": "voicezen.ai",                  "linkedin_search": "Voicezen AI intern engineer"},
    {"name": "Fyle",              "tier": 3, "domain": "FinTech/AI",    "location": "Bangalore", "careers": "fylehq.com/careers",           "linkedin_search": "Fyle intern software engineer"},
    {"name": "Wysa",              "tier": 3, "domain": "Mental Health AI","location":"Bangalore", "careers": "wysa.io/careers",             "linkedin_search": "Wysa AI intern engineer hiring"},

    # ── Tier 2: Known Product Companies (stretch) ──
    {"name": "Freshworks",        "tier": 2, "domain": "SaaS/AI",       "location": "Chennai",   "careers": "freshworks.com/company/careers","linkedin_search": "Freshworks intern software engineer 2026"},
    {"name": "Postman",           "tier": 2, "domain": "DevTools/AI",   "location": "Bangalore", "careers": "postman.com/company/careers",  "linkedin_search": "Postman intern engineer 2026"},
    {"name": "Razorpay",          "tier": 2, "domain": "FinTech",       "location": "Bangalore", "careers": "razorpay.com/careers",         "linkedin_search": "Razorpay intern engineer 2026"},
    {"name": "Chargebee",         "tier": 2, "domain": "SaaS",          "location": "Chennai",   "careers": "chargebee.com/careers",        "linkedin_search": "Chargebee intern software engineer"},
    {"name": "BrowserStack",      "tier": 2, "domain": "DevTools",      "location": "Mumbai",    "careers": "browserstack.com/careers",     "linkedin_search": "BrowserStack intern engineer 2026"},
    {"name": "Hasura",            "tier": 2, "domain": "GraphQL/AI",    "location": "Bangalore", "careers": "hasura.io/careers",            "linkedin_search": "Hasura intern engineer hiring"},
    {"name": "Clevertap",         "tier": 2, "domain": "Analytics/AI",  "location": "Mumbai",    "careers": "clevertap.com/careers",        "linkedin_search": "Clevertap intern engineer 2026"},
    {"name": "Darwinbox",         "tier": 2, "domain": "HR Tech/AI",    "location": "Hyderabad", "careers": "darwinbox.com/careers",        "linkedin_search": "Darwinbox intern engineer hiring"},
    {"name": "Unacademy",         "tier": 2, "domain": "EdTech/AI",     "location": "Bangalore", "careers": "unacademy.com/careers",        "linkedin_search": "Unacademy intern engineer 2026"},
    {"name": "Meesho",            "tier": 2, "domain": "eCommerce/AI",  "location": "Bangalore", "careers": "meesho.io/careers",            "linkedin_search": "Meesho intern engineer 2026"},
]

# ─── YOUR PROFILE ─────────────────────────────
PROFILE = {
    "name": "Raktim Banerjee",
    "college": "NIIT University",
    "year": "2nd year BTech CSE",
    "credential": "Microsoft Student Ambassador",
    "project1": "RAG Study Assistant (90%+ accuracy, runs locally on RTX 3050)",
    "project2": "AI Code Review tool supporting 7 languages",
    "github": "github.com/rktm0604",
    "linkedin": "linkedin.com/in/raktimbanerjee-4421b6322",
    "goal": "AI/ML or software internship, Summer 2026",
}

# ─── DM TEMPLATES ─────────────────────────────
# Short = connection request note (< 300 chars)
# Long  = follow-up DM after they accept

def generate_short_dm(company):
    domain = company["domain"]
    name   = company["name"]
    note = (
        f"Hi, I'm Raktim — 2nd year CSE, Microsoft Student Ambassador. "
        f"Built a RAG system (90%+ accuracy, local GPU) and AI Code Review tool. "
        f"Interested in interning at {name} this summer. GitHub: {PROFILE['github']}"
    )
    if len(note) > 300:
        print(f"  ⚠️  Note is {len(note)} chars — truncating to 300 (LinkedIn limit)")
    return note[:299]

def generate_follow_up_dm(company):
    domain = company["domain"]
    name   = company["name"]
    return f"""Hi [Name],

Thanks for connecting! I'm Raktim, a 2nd year CSE student at NIIT University and Microsoft Student Ambassador.

I've built two live AI projects:
• RAG Study Assistant — processes 100+ page PDFs with 90%+ accuracy, runs locally on RTX 3050
• AI Code Review tool — detects bugs and security issues across 7 languages

Both are live on GitHub: {PROFILE['github']}

I'm genuinely interested in {name}'s work in {domain} and would love to contribute this summer (May 29 – Aug 3, 2026). I'm flexible on remote or hybrid.

Would you be open to a quick chat, or could you point me to the right person for internship applications?

Thank you,
Raktim"""

# ─── LINKEDIN SEARCH URL ──────────────────────
def get_linkedin_search_url(company):
    query = company["linkedin_search"]
    encoded = urllib.parse.quote(query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}"

# ─── CSV LOGGING ──────────────────────────────
def load_log():
    log = {}
    try:
        with open(LOG_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                log[row["company"]] = row
    except FileNotFoundError:
        pass
    return log

def save_log(log):
    if not log:
        return
    fields = ["company", "tier", "domain", "location", "short_dm_sent",
              "followup_sent", "status", "notes", "date_added", "last_updated"]
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in log.values():
            writer.writerow(row)

def ensure_logged(log, company):
    name = company["name"]
    if name not in log:
        log[name] = {
            "company":       name,
            "tier":          company["tier"],
            "domain":        company["domain"],
            "location":      company["location"],
            "short_dm_sent": "No",
            "followup_sent": "No",
            "status":        "Not contacted",
            "notes":         "",
            "date_added":    datetime.now().strftime("%Y-%m-%d"),
            "last_updated":  datetime.now().strftime("%Y-%m-%d"),
        }

# ─── MENUS ────────────────────────────────────
def print_header():
    print("\n" + "═"*52)
    print("  FACHUBOT v5 — AI/ML Startup Outreach")
    print("  Raktim Banerjee | NIIT University")
    print("═"*52)
    if not HAS_CLIPBOARD:
        print("ℹ️  Tip: Install pyperclip for auto clipboard copy (pip install pyperclip)")

def main_menu():
    print_header()
    print("\n  1. Browse companies + generate DMs")
    print("  2. View outreach tracker (CSV summary)")
    print("  3. Mark a company status")
    print("  4. Open LinkedIn search for a company")
    print("  5. Exit")
    return input("\n  Choose: ").strip()

def handle_generation(log, company):
    """Generate DMs for a single company."""
    print(f"\n  ── {company['name']} ──────────────────────────")
    print(f"  Tier: {company['tier']} | {company['domain']} | {company['location']}")
    print(f"  Careers page: {company['careers']}")

    print("\n  ── CONNECTION REQUEST NOTE (< 300 chars) ──")
    short = generate_short_dm(company)
    print(f"\n  {short}")
    print(f"\n  ({len(short)} chars)")
    
    # Auto-copy connection note
    if HAS_CLIPBOARD:
        pyperclip.copy(short)
        print("  ✅ Copied to clipboard!")

    print("\n  ── FOLLOW-UP DM (after they accept) ───────")
    followup = generate_follow_up_dm(company)
    print(followup)
    
    if HAS_CLIPBOARD:
        copy_dm = input("\n  Copy follow-up DM to clipboard? [y/n]: ").strip().lower()
        if copy_dm == 'y':
            pyperclip.copy(followup)
            print("  ✅ Follow-up DM copied to clipboard!")

    action = input("\n  Mark short DM as sent? [y/n]: ").strip().lower()
    if action == "y":
        log[company["name"]]["short_dm_sent"] = "Yes"
        log[company["name"]]["status"] = "DM sent"
        log[company["name"]]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_log(log)
        print("  ✓ Logged.")

    open_li = input("  Open LinkedIn search for this company? [y/n]: ").strip().lower()
    if open_li == "y":
        url = get_linkedin_search_url(company)
        webbrowser.open(url)
        print(f"  ✓ Opened: {url}")

def browse_and_generate(log):
    tier_filter = input("\n  Show tier? [2 = known companies / 3 = AI startups / all]: ").strip()
    
    filtered = COMPANIES
    if tier_filter in ("2", "3"):
        filtered = [c for c in COMPANIES if c["tier"] == int(tier_filter)]

    print(f"\n  {'#':<4} {'Company':<20} {'Domain':<20} {'Location':<12} {'Status'}")
    print("  " + "-"*70)
    for i, c in enumerate(filtered, 1):
        ensure_logged(log, c)
        status = log[c["name"]]["status"]
        print(f"  {i:<4} {c['name']:<20} {c['domain']:<20} {c['location']:<12} {status}")

    choice = input("\n  Enter number to generate DMs (or 0 to go back): ").strip()
    if choice == "0" or not choice.isdigit():
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(filtered):
        print("  Invalid choice.")
        return

    company = filtered[idx]
    ensure_logged(log, company)
    
    handle_generation(log, company)

def view_tracker(log):
    print(f"\n  {'Company':<22} {'Tier':<6} {'DM':<6} {'Follow-up':<12} {'Status'}")
    print("  " + "-"*65)
    not_contacted = 0
    dm_sent = 0
    for c in COMPANIES:
        ensure_logged(log, c)
        r = log[c["name"]]
        print(f"  {r['company']:<22} {r['tier']:<6} {r['short_dm_sent']:<6} {r['followup_sent']:<12} {r['status']}")
        if r["status"] == "Not contacted":
            not_contacted += 1
        if r["short_dm_sent"] == "Yes":
            dm_sent += 1

    print(f"\n  Total companies: {len(COMPANIES)}")
    print(f"  DMs sent:        {dm_sent}")
    print(f"  Not contacted:   {not_contacted}")

def mark_status(log):
    print("\n  Enter company name (partial ok): ", end="")
    query = input().strip().lower()
    matches = [c for c in COMPANIES if query in c["name"].lower()]

    if not matches:
        print("  No match found.")
        return
    if len(matches) > 1:
        for i, c in enumerate(matches, 1):
            print(f"  {i}. {c['name']}")
        choice = input("  Pick number: ").strip()
        if not choice.isdigit():
            return
        company = matches[int(choice)-1]
    else:
        company = matches[0]

    ensure_logged(log, company)
    print(f"\n  Current status: {log[company['name']]['status']}")
    print("  New status options:")
    statuses = ["Not contacted", "DM sent", "Connected", "Replied", 
                "Interview scheduled", "Rejected", "Offer received"]
    for i, s in enumerate(statuses, 1):
        print(f"    {i}. {s}")
    
    pick = input("  Choose: ").strip()
    if pick.isdigit() and 1 <= int(pick) <= len(statuses):
        log[company["name"]]["status"] = statuses[int(pick)-1]
        log[company["name"]]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        if statuses[int(pick)-1] == "Connected":
            sent = input("  Mark follow-up DM as sent too? [y/n]: ").strip().lower()
            if sent == "y":
                log[company["name"]]["followup_sent"] = "Yes"
        
        notes = input("  Add notes (optional, press Enter to skip): ").strip()
        if notes:
            log[company["name"]]["notes"] = notes
        
        save_log(log)
        print("  ✓ Status updated.")

def open_linkedin(log):
    print("\n  Enter company name: ", end="")
    query = input().strip().lower()
    matches = [c for c in COMPANIES if query in c["name"].lower()]
    if not matches:
        print("  No match found.")
        return
    company = matches[0]
    url = get_linkedin_search_url(company)
    webbrowser.open(url)
    print(f"  ✓ Opened LinkedIn search for {company['name']}")

# ─── CLI SUPPORT ──────────────────────────────
def run_cli(log):
    """Handle --company and --list flags for non-interactive use."""
    parser = argparse.ArgumentParser(description="FachuBot v5 — AI/ML Startup Outreach")
    parser.add_argument('--company', type=str, help='Company name to target directly (e.g., "Sarvam AI")')
    parser.add_argument('--list', action='store_true', help='List all target companies')
    args = parser.parse_args()

    if args.list:
        print("\nTarget AI/ML Companies:")
        for i, c in enumerate(COMPANIES, 1):
            print(f"  {i}. {c['name']} (Tier {c['tier']}) - {c['domain']}")
        return True

    if args.company:
        match = None
        for c in COMPANIES:
            if c['name'].lower() == args.company.lower():
                match = c
                break
        if not match:
            print(f"Company '{args.company}' not found. Use --list to see available companies.")
            return True
        
        # Run directly for that company
        print_header()
        ensure_logged(log, match)
        handle_generation(log, match)
        return True

    return False

# ─── MAIN ─────────────────────────────────────
def main():
    log = load_log()
    # Pre-load all companies into log
    for c in COMPANIES:
        ensure_logged(log, c)
    save_log(log)

    # If CLI args provided, handle them and exit
    if run_cli(log):
        return

    while True:
        choice = main_menu()
        if choice == "1":
            browse_and_generate(log)
        elif choice == "2":
            view_tracker(log)
        elif choice == "3":
            mark_status(log)
        elif choice == "4":
            open_linkedin(log)
        elif choice == "5":
            print("\n  Consistent effort beats intense bursts. Keep sending. 🚀\n")
            break
        else:
            print("  Invalid choice, try again.")

if __name__ == "__main__":
    main()