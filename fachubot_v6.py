"""
FachuBot v6 — AI/ML Startup LinkedIn Outreach Bot
Raktim Banerjee | NIIT University | March 2026

What's new in v6:
  - Updated DM templates with production-grade RAG description
  - 40 Indian AI/ML companies (was 25)
  - RakBot integration — imports leads from internships_tracker.csv
  - Daily reminder — shows exactly who to message today
  - Reply/no-reply tracking with follow-up due alerts
  - Preserved CLI flags from v5

Run:  python fachubot_v6.py
Deps: pip install pyperclip
"""

import csv
import os
import time
import random
import webbrowser
import argparse
import sys
from datetime import datetime, timedelta
from urllib.parse import quote

# ─── YOUR PROFILE ─────────────────────────────────────────────────────────────

MY_PROFILE = {
    "name": "Raktim",
    "credential": "Microsoft Student Ambassador",
    "project_1": "RAG Study Assistant — streaming responses, page citations, OCR fallback, pytest suite (90%+ accuracy on RTX 3050)",
    "project_2": "AI Code Review tool supporting 7 languages (Python, JS, Java, C++, TS, Go, Rust)",
    "github": "github.com/rktm0604",
    "goal": "AI/ML internship Summer 2026",
    "college": "NIIT University",
    "year": "2nd year CSE",
}

# ─── TARGET COMPANIES — 40 Indian AI/ML startups ──────────────────────────────

TARGET_COMPANIES = [
    # Language & Conversational AI
    {"name": "Sarvam AI",           "focus": "Indian language LLMs",            "location": "Bangalore"},
    {"name": "Krutrim",             "focus": "AI infrastructure for India",      "location": "Bangalore"},
    {"name": "Vernacular.ai",       "focus": "voice AI for Indian languages",    "location": "Bangalore"},
    {"name": "Haptik",              "focus": "conversational AI platform",       "location": "Mumbai"},
    {"name": "Yellow.ai",           "focus": "enterprise conversational AI",     "location": "Bangalore"},
    {"name": "Niki.ai",             "focus": "conversational commerce AI",       "location": "Bangalore"},
    {"name": "Mihup",               "focus": "voice AI and NLP",                "location": "Kolkata"},
    {"name": "Gnani.ai",            "focus": "speech AI for enterprises",        "location": "Bangalore"},
    {"name": "Observe.AI",          "focus": "AI for contact centers",           "location": "Bangalore"},
    {"name": "CoRover.ai",          "focus": "multilingual chatbot platform",    "location": "Noida"},
    # Enterprise & Analytics AI
    {"name": "Fractal Analytics",   "focus": "AI for enterprise decisions",      "location": "Mumbai"},
    {"name": "Sigmoid",             "focus": "data engineering and AI",          "location": "Bangalore"},
    {"name": "Quantiphi",           "focus": "applied AI and data science",      "location": "Mumbai"},
    {"name": "Arya.ai",             "focus": "AI for BFSI sector",              "location": "Mumbai"},
    {"name": "Leena AI",            "focus": "HR automation AI",                "location": "Bangalore"},
    {"name": "Pixis",               "focus": "codeless AI marketing",            "location": "Bangalore"},
    {"name": "Scalenut",            "focus": "AI content platform",              "location": "Chandigarh"},
    {"name": "Artivatic",           "focus": "AI for insurance",                "location": "Bangalore"},
    {"name": "Vymo",                "focus": "AI sales assistant for BFSI",      "location": "Bangalore"},
    {"name": "Locus.sh",            "focus": "AI for logistics and supply chain","location": "Bangalore"},
    # Vision & Perception AI
    {"name": "Uncanny Vision",      "focus": "computer vision AI",              "location": "Bangalore"},
    {"name": "Mad Street Den",      "focus": "retail AI via Vue.ai",             "location": "Chennai"},
    {"name": "Wobot Intelligence",  "focus": "video analytics AI",              "location": "Delhi"},
    {"name": "Entropik Tech",       "focus": "emotion and consumer insight AI",  "location": "Bangalore"},
    {"name": "SigTuple",            "focus": "AI for medical diagnostics",       "location": "Bangalore"},
    {"name": "Nference",            "focus": "biomedical AI and NLP",            "location": "Bangalore"},
    # AgriTech & Domain AI
    {"name": "Fasal",               "focus": "AI for precision agriculture",     "location": "Bangalore"},
    {"name": "CropIn",              "focus": "agri-tech AI platform",            "location": "Bangalore"},
    {"name": "Intello Labs",        "focus": "computer vision for agri quality", "location": "Gurugram"},
    {"name": "Stellapps",           "focus": "AI for dairy farming",             "location": "Bangalore"},
    # Developer Tools & Infrastructure AI
    {"name": "Hasura",              "focus": "instant GraphQL APIs",             "location": "Bangalore"},
    {"name": "Kognitos",            "focus": "natural language automation",      "location": "Remote"},
    {"name": "Augrade",             "focus": "AI for education",                "location": "Remote"},
    {"name": "Unacademy AI",        "focus": "AI-driven learning platform",      "location": "Bangalore"},
    {"name": "Springworks",         "focus": "AI HR and engagement tools",       "location": "Bangalore"},
    # E-commerce & Retail AI
    {"name": "Dukaan",              "focus": "AI-powered e-commerce",            "location": "Bangalore"},
    {"name": "Fashinza",            "focus": "AI for fashion supply chain",      "location": "Gurugram"},
    {"name": "Styleumm",            "focus": "AI fashion recommendation",        "location": "Bangalore"},
    # Fintech AI
    {"name": "Hyperface",           "focus": "credit card infrastructure AI",    "location": "Bangalore"},
    {"name": "Finarkein Analytics", "focus": "AI for financial data",            "location": "Mumbai"},
]

# ─── FILE PATHS ───────────────────────────────────────────────────────────────

BOT_DIR     = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(BOT_DIR, "fachubot_v6_log.csv")
RAKBOT_CSV  = os.path.join(BOT_DIR, "internships_tracker.csv")  # RakBot output

LOG_HEADERS = [
    "date", "source", "company", "person_name", "linkedin_url",
    "dm_sent", "reply_status", "follow_up_date", "notes"
]

REPLY_OPTIONS = ["waiting", "replied_positive", "replied_negative", "no_reply", "meeting_scheduled"]

# ─── LOG HELPERS ──────────────────────────────────────────────────────────────

def load_log() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_to_log(entry: dict):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)

def update_log_row(company: str, field: str, value: str):
    """Update a specific field for the most recent entry matching company."""
    if not os.path.exists(LOG_FILE):
        return
    rows = []
    updated = False
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in reversed(rows):
        if row["company"].lower() == company.lower() and not updated:
            row[field] = value
            updated = True
            break
    if updated:
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_HEADERS)
            writer.writeheader()
            writer.writerows(rows)

def already_messaged(company_name: str, log: list) -> bool:
    for row in log:
        if row["company"].lower() == company_name.lower() and row["dm_sent"] == "yes":
            return True
    return False

def get_pending_replies(log: list) -> list:
    """Returns entries sent 3+ days ago still marked 'waiting'."""
    today = datetime.now().date()
    pending = []
    for row in log:
        if row["dm_sent"] == "yes" and row.get("reply_status", "waiting") == "waiting":
            try:
                sent = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if (today - sent).days >= 3:
                    pending.append(row)
            except ValueError:
                pass
    return pending

# ─── RAKBOT INTEGRATION ───────────────────────────────────────────────────────

def load_rakbot_leads() -> list:
    """
    Reads internships_tracker.csv from RakBot and extracts company names
    that scored well and haven't been messaged yet in FachuBot.
    Returns list of dicts with name, title, link.
    """
    if not os.path.exists(RAKBOT_CSV):
        return []
    leads = []
    try:
        with open(RAKBOT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                score = float(row.get("score", 0) or 0)
                company = row.get("company", "").strip()
                title = row.get("title", "").strip()
                link = row.get("link", "").strip()
                status = row.get("status", "").strip().lower()
                if score >= 6 and company and status not in ["applied", "rejected", "offer"]:
                    leads.append({
                        "name": company,
                        "focus": title,
                        "location": "India",
                        "link": link,
                        "score": score,
                        "source": "rakbot"
                    })
    except Exception as e:
        print(f"  Warning: Could not read RakBot CSV — {e}")
    return leads

# ─── DM GENERATOR ─────────────────────────────────────────────────────────────

def generate_dm(company: dict, person_name: str = "") -> str:
    greeting = f"Hi {person_name}," if person_name else "Hi,"
    name = MY_PROFILE["name"]
    cred = MY_PROFILE["credential"]
    gh   = MY_PROFILE["github"]
    focus = company["focus"]
    cname = company["name"]

    templates = [
        (f"{greeting} I'm {name} — 2nd yr CSE, {cred}. Built a production RAG system "
         f"with streaming, page citations & OCR fallback (live on GitHub). "
         f"Love what {cname} is doing in {focus}. Open to summer internship. {gh}"),

        (f"{greeting} {name} here — {cred}, NIIT University. My RAG assistant "
         f"streams responses + cites exact pages, runs locally on RTX 3050. "
         f"Also built an AI code review tool for 7 languages. "
         f"Would love to intern at {cname} this summer. {gh}"),

        (f"{greeting} I'm {name}, {cred} & 2nd yr CSE. My RAG project now has "
         f"real-time streaming, pytest suite & OCR fallback — production-grade. "
         f"{cname}'s work in {focus} is exactly where I want to contribute. {gh}"),

        (f"{greeting} {name} — {cred}, NIIT Univ. Built RAG + AI code review "
         f"tools (both on GitHub, production-ready). Excited about {focus} at "
         f"{cname}. Seeking AI/ML internship, May–Aug 2026. {gh}"),
    ]

    dm = random.choice(templates)
    if len(dm) > 299:
        dm = dm[:296] + "..."
    return dm

# ─── BROWSER HELPERS ──────────────────────────────────────────────────────────

def open_linkedin_search(company: dict):
    # Try Google first — much better LinkedIn indexing
    query = f'"{company["name"]}" founder OR CTO OR "head of AI" site:linkedin.com/in'
    url = f"https://www.google.com/search?q={quote(query)}"
    print(f"\n  Opening Google search for {company['name']} leadership...")
    webbrowser.open(url)
    time.sleep(1)

def open_url(url: str):
    if url:
        webbrowser.open(url)
        time.sleep(1)

# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_header(log: list):
    sent     = sum(1 for r in log if r["dm_sent"] == "yes")
    positive = sum(1 for r in log if r.get("reply_status") == "replied_positive")
    waiting  = sum(1 for r in log if r.get("reply_status") == "waiting" and r["dm_sent"] == "yes")
    pending_fu = len(get_pending_replies(log))

    print("\n" + "=" * 60)
    print("  FachuBot v6 — AI/ML Startup Outreach")
    print(f"  {MY_PROFILE['name']} | {MY_PROFILE['college']}")
    print("=" * 60)
    print(f"  Sent: {sent}  |  Positive replies: {positive}  |  Waiting: {waiting}", end="")
    if pending_fu:
        print(f"  |  Follow-ups due: {pending_fu} !", end="")
    print("\n")

def print_company_list(log: list, companies: list, title: str = "TARGET COMPANIES"):
    print(f"\n  {title}\n")
    print(f"  {'#':<4} {'Company':<24} {'Focus':<28} {'Status'}")
    print("  " + "-" * 74)
    for i, c in enumerate(companies, 1):
        if already_messaged(c["name"], log):
            status = "messaged"
        else:
            status = "pending"
        src = " [rakbot]" if c.get("source") == "rakbot" else ""
        print(f"  {i:<4} {(c['name']+src):<24} {c['focus'][:26]:<28} {status}")

def view_log(log: list):
    if not log:
        print("\n  No entries yet.\n")
        return
    print(f"\n  {'Date':<12} {'Company':<22} {'Person':<16} {'Sent':<5} {'Reply status'}")
    print("  " + "-" * 72)
    for row in log:
        reply = row.get("reply_status", "—")
        print(f"  {row['date']:<12} {row['company']:<22} {row['person_name']:<16} {row['dm_sent']:<5} {reply}")
    print()

# ─── DAILY REMINDER ───────────────────────────────────────────────────────────

def show_daily_reminder(log: list):
    """Shows today's outreach targets and any follow-ups due."""
    today = datetime.now()
    print(f"\n  DAILY PLAN — {today.strftime('%A, %d %b %Y')}\n")

    # Follow-ups due
    due = get_pending_replies(log)
    if due:
        print(f"  FOLLOW-UPS DUE ({len(due)})")
        for row in due:
            sent = row["date"]
            print(f"    · {row['company']} — messaged {sent}, no reply yet")
        print()

    # Suggest 3 companies to message today (not yet messaged)
    not_yet = [c for c in TARGET_COMPANIES if not already_messaged(c["name"], log)]
    suggestions = random.sample(not_yet, min(3, len(not_yet))) if not_yet else []

    if suggestions:
        print(f"  SUGGESTED OUTREACH TODAY (3 companies)")
        for i, c in enumerate(suggestions, 1):
            print(f"    {i}. {c['name']} — {c['focus']} ({c['location']})")
    else:
        print("  All companies messaged! Add more or check follow-ups.")

    # Stats
    sent_this_week = sum(
        1 for r in log
        if r["dm_sent"] == "yes" and
        (today.date() - datetime.strptime(r["date"], "%Y-%m-%d").date()).days <= 7
    )
    print(f"\n  DMs sent this week: {sent_this_week}/10 (target: 10/week)")
    remaining = max(0, 10 - sent_this_week)
    if remaining:
        print(f"  {remaining} more to hit your weekly target.")
    else:
        print("  Weekly target reached!")
    print()

# ─── UPDATE REPLY STATUS ──────────────────────────────────────────────────────

def update_reply_flow(log: list) -> list:
    """Let user update reply status for any sent DM."""
    sent_entries = [r for r in log if r["dm_sent"] == "yes"]
    if not sent_entries:
        print("\n  No sent DMs to update.\n")
        return log

    print("\n  UPDATE REPLY STATUS\n")
    print(f"  {'#':<4} {'Company':<22} {'Date':<12} {'Current status'}")
    print("  " + "-" * 60)
    for i, row in enumerate(sent_entries, 1):
        print(f"  {i:<4} {row['company']:<22} {row['date']:<12} {row.get('reply_status','waiting')}")

    try:
        choice = int(input("\n  Entry number to update (0 to cancel): "))
    except ValueError:
        return log
    if choice == 0 or choice > len(sent_entries):
        return log

    row = sent_entries[choice - 1]
    print(f"\n  Company: {row['company']}")
    print("  New status:")
    for i, opt in enumerate(REPLY_OPTIONS, 1):
        print(f"    [{i}] {opt}")

    try:
        s = int(input("\n  Choice: "))
        if 1 <= s <= len(REPLY_OPTIONS):
            new_status = REPLY_OPTIONS[s - 1]
            update_log_row(row["company"], "reply_status", new_status)
            # Reload
            log = load_log()
            print(f"\n  Updated {row['company']} → {new_status}")
            if new_status == "replied_positive":
                print("  Great news! Prepare a follow-up message and research the company.")
            elif new_status == "meeting_scheduled":
                print("  Meeting scheduled! Research the company and prepare your project walkthrough.")
    except ValueError:
        pass
    return log

# ─── OUTREACH FLOW ────────────────────────────────────────────────────────────

def do_one_outreach(log: list, company: dict) -> list:
    """Perform outreach for a single company."""
    if already_messaged(company["name"], log):
        print(f"\n  Already messaged {company['name']}.")
        return log

    print(f"\n  -- {company['name']} --")
    print(f"  Focus:    {company['focus']}")
    print(f"  Location: {company['location']}")
    if company.get("link"):
        print(f"  Job link: {company['link']}")

    print("\n  Step 1: Find the right person to message.")
    print("    [1] Search LinkedIn via DuckDuckGo")
    print("    [2] I already have their LinkedIn URL")
    if company.get("link"):
        print("    [3] Open the job listing first")
    print("    [0] Skip this company")

    step = input("\n  Choice: ").strip()
    if step == "0":
        return log
    elif step == "1":
        open_linkedin_search(company)
        print("\n  Look for: Founder / CTO / Head of AI / ML Lead")
    elif step == "2":
        pass
    elif step == "3" and company.get("link"):
        open_url(company["link"])

    linkedin_url = input("\n  Their LinkedIn URL (Enter to skip): ").strip()
    person_name  = input("  Their first name (Enter to skip): ").strip()

    if linkedin_url:
        open_url(linkedin_url)

    # Generate DM
    dm = generate_dm(company, person_name)
    print("\n  -- GENERATED DM " + "-" * 44)
    print(f"\n  {dm}")
    print(f"\n  Length: {len(dm)}/299 characters")
    print("  " + "-" * 60)

    print("\n  [1] Use this DM")
    print("  [2] Regenerate")
    print("  [3] Write my own")
    print("  [0] Skip")

    action = input("\n  Choice: ").strip()
    final_dm = dm
    sent = "no"
    status = "skipped"

    if action == "2":
        final_dm = generate_dm(company, person_name)
        print(f"\n  New DM:\n  {final_dm}")
        if input("\n  Use this? [y/n]: ").strip().lower() == "y":
            action = "1"

    if action == "3":
        print("  Type your DM (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        final_dm = " ".join(lines)
        action = "1"

    if action == "1":
        try:
            import pyperclip
            pyperclip.copy(final_dm)
            print("\n  Copied to clipboard!")
        except ImportError:
            print("\n  Tip: pip install pyperclip for auto-copy")
            print(f"\n  {final_dm}\n")

        if linkedin_url:
            print("  Profile is open — paste the DM in LinkedIn messaging.")

        confirmed = input("\n  Did you send the DM? [y/n]: ").strip().lower()
        sent   = "yes" if confirmed == "y" else "no"
        status = "sent" if sent == "yes" else "opened_not_sent"

    follow_up_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d") if sent == "yes" else ""

    entry = {
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "source":          company.get("source", "manual"),
        "company":         company["name"],
        "person_name":     person_name or "unknown",
        "linkedin_url":    linkedin_url or "",
        "dm_sent":         sent,
        "reply_status":    "waiting" if sent == "yes" else "not_sent",
        "follow_up_date":  follow_up_date,
        "notes":           company["focus"],
    }
    save_to_log(entry)
    log.append(entry)

    if sent == "yes":
        print(f"\n  Logged! Follow-up reminder set for {follow_up_date}.")
        print("  Check back in 4 days — FachuBot will remind you.")
    else:
        print(f"\n  Logged as {status}.")
    return log

def outreach_flow(log: list, companies: list) -> list:
    print_company_list(log, companies)
    try:
        choice = int(input("\n  Company number (0 to cancel): "))
    except ValueError:
        print("  Invalid input.")
        return log
    if choice == 0 or choice > len(companies):
        return log

    company = companies[choice - 1]

    if already_messaged(company["name"], log):
        print(f"\n  Already messaged {company['name']}.")
        update_now = input("  Update reply status instead? [y/n]: ").strip().lower()
        if update_now == "y":
            log = update_reply_flow(log)
        return log
    
    return do_one_outreach(log, company)

# ─── RAKBOT LEADS FLOW ────────────────────────────────────────────────────────

def rakbot_leads_flow(log: list) -> list:
    leads = load_rakbot_leads()
    if not leads:
        print(f"\n  No RakBot leads found.")
        print(f"  Make sure internships_tracker.csv is in: {BOT_DIR}")
        print("  Or run RakBot first to generate it.\n")
        input("  Press Enter to continue...")
        return log

    # Deduplicate against already messaged
    new_leads = [l for l in leads if not already_messaged(l["name"], log)]
    print(f"\n  Found {len(leads)} RakBot leads — {len(new_leads)} not yet messaged.\n")

    if not new_leads:
        print("  All RakBot leads already messaged!\n")
        input("  Press Enter to continue...")
        return log

    # Sort by score
    new_leads.sort(key=lambda x: x.get("score", 0), reverse=True)
    return outreach_flow(log, new_leads)

# ─── CLI SUPPORT ──────────────────────────────────────────────────────────────
def run_cli(log: list) -> bool:
    """Handle CLI commands like --list or --company."""
    parser = argparse.ArgumentParser(description="FachuBot v6 — AI/ML Startup Outreach")
    parser.add_argument('--list', action='store_true', help='List all target companies')
    parser.add_argument('--company', type=str, help='Run outreach for a specific company')
    args = parser.parse_args()

    if args.list:
        print_company_list(log, TARGET_COMPANIES)
        return True

    if args.company:
        match = next((c for c in TARGET_COMPANIES if c["name"].lower() == args.company.lower()), None)
        if match:
            do_one_outreach(log, match)
        else:
            print(f"\n  Company '{args.company}' not found in regular list.")
            print("  Use --list to view available companies.")
        return True
    
    return False

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log = load_log()

    # CLI check
    if run_cli(log):
        return

    # Show daily reminder on startup
    clear()
    print_header(log)
    show_daily_reminder(log)
    input("  Press Enter to continue to main menu...")

    while True:
        clear()
        print_header(log)

        due_count = len(get_pending_replies(log))
        fu_label  = f" ({due_count} due!)" if due_count else ""

        print("  [1] Start outreach — pick from company list")
        print("  [2] Start outreach — from RakBot leads")
        print("  [3] Daily reminder + today's targets")
        print(f"  [4] Follow-ups{fu_label}")
        print("  [5] Update reply status")
        print("  [6] View full log")
        print("  [7] View all 40 companies")
        print("  [0] Exit\n")

        choice = input("  Choice: ").strip()

        if choice == "1":
            log = outreach_flow(log, TARGET_COMPANIES)
            input("\n  Press Enter to continue...")

        elif choice == "2":
            log = rakbot_leads_flow(log)
            input("\n  Press Enter to continue...")

        elif choice == "3":
            clear()
            show_daily_reminder(log)
            input("  Press Enter to continue...")

        elif choice == "4":
            clear()
            due = get_pending_replies(log)
            if not due:
                print("\n  No follow-ups due yet. Check back after 4 days.\n")
            else:
                print(f"\n  FOLLOW-UPS DUE ({len(due)})\n")
                for row in due:
                    print(f"  {row['company']} — messaged {row['date']}")
                    if row.get("linkedin_url"):
                        open_now = input(f"  Open {row['person_name']}'s profile? [y/n]: ").strip().lower()
                        if open_now == "y":
                            open_url(row["linkedin_url"])
                    print()
            input("  Press Enter to continue...")

        elif choice == "5":
            clear()
            log = update_reply_flow(log)
            input("\n  Press Enter to continue...")

        elif choice == "6":
            clear()
            view_log(log)
            input("  Press Enter to continue...")

        elif choice == "7":
            clear()
            print_company_list(log, TARGET_COMPANIES)
            input("\n  Press Enter to continue...")

        elif choice == "0":
            print("\n  Consistent effort beats intense bursts. Keep going, Raktim.\n")
            break

if __name__ == "__main__":
    main()