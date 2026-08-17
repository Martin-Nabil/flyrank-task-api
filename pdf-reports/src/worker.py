import sqlite3
import json
import time
import os
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

DB_FILE = "reports.db"
POLL_INTERVAL_SECONDS = 2
OUTPUT_DIR = "output"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def load_books():
    with open("books.json", "r", encoding="utf-8") as f:
        return json.load(f)

def compute_stats(books):
    """Run the aggregation — this is the 'SQL aggregation' step, done here in-memory
    over the JSON since our book data isn't in a live SQL table; the same queries
    could run directly against Postgres if this were wired to the live task API DB."""
    prices = [b["price_gbp"] for b in books]

    by_category = {}
    by_rating = {}
    for b in books:
        cat = b.get("category", "uncategorized")
        by_category[cat] = by_category.get(cat, 0) + 1

        rating = b.get("rating_text", "unknown")
        by_rating[rating] = by_rating.get(rating, 0) + 1

    return {
        "total_books": len(books),
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": sum(prices) / len(prices),
        "by_category": by_category,
        "by_rating": by_rating
    }

def render_pdf(stats, report_id):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdf_path = os.path.join(OUTPUT_DIR, f"report-{report_id}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    y = height - inch

    c.setFont("Helvetica-Bold", 18)
    c.drawString(inch, y, "Book Catalogue Report")
    y -= 0.4 * inch

    c.setFont("Helvetica", 10)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    c.drawString(inch, y, f"Generated: {generated}")
    y -= 0.5 * inch

    c.setFont("Helvetica-Bold", 13)
    c.drawString(inch, y, "Summary")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    lines = [
        f"Total books: {stats['total_books']}",
        f"Price range: £{stats['min_price']:.2f} - £{stats['max_price']:.2f}",
        f"Average price: £{stats['avg_price']:.2f}",
    ]
    for line in lines:
        c.drawString(inch, y, line)
        y -= 0.25 * inch

    y -= 0.3 * inch
    c.setFont("Helvetica-Bold", 13)
    c.drawString(inch, y, "By rating")
    y -= 0.3 * inch
    c.setFont("Helvetica", 11)
    for rating, count in sorted(stats["by_rating"].items()):
        c.drawString(inch, y, f"{rating}: {count}")
        y -= 0.25 * inch

    c.save()
    return pdf_path

MAX_ATTEMPTS = 3

def log_alert(report_id, error, attempts):
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_id": report_id,
        "error": error,
        "attempts": attempts,
        "message": f"Report {report_id} permanently failed after {attempts} attempts"
    }
    with open("logs/alerts.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"ALERT: {entry['message']}")

def process_report(conn, report):
    now = datetime.now(timezone.utc).isoformat()
    attempts = report["attempts"] + 1

    try:
        books = load_books()
        stats = compute_stats(books)
        pdf_path = render_pdf(stats, report["id"])

        conn.execute(
            "UPDATE reports SET status = 'completed', pdf_path = ?, attempts = ?, updated_at = ? WHERE id = ?",
            (pdf_path, attempts, now, report["id"])
        )
        print(f"COMPLETED report {report['id']} -> {pdf_path}")
        conn.commit()

    except Exception as e:
        if attempts < MAX_ATTEMPTS:
            backoff = 2 ** attempts
            print(f"RETRY {attempts}/{MAX_ATTEMPTS} for report {report['id']} in {backoff}s: {e}")
            conn.execute(
                "UPDATE reports SET status = 'pending', attempts = ?, error = ?, updated_at = ? WHERE id = ?",
                (attempts, str(e), now, report["id"])
            )
            conn.commit()
            time.sleep(backoff)
            return

        conn.execute(
            "UPDATE reports SET status = 'failed', error = ?, attempts = ?, updated_at = ? WHERE id = ?",
            (str(e), attempts, now, report["id"])
        )
        conn.commit()
        log_alert(report["id"], str(e), attempts)

def claim_next_report(conn):
    row = conn.execute(
        "SELECT * FROM reports WHERE status = 'pending' ORDER BY created_at LIMIT 1"
    ).fetchone()
    if row is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE reports SET status = 'running', updated_at = ? WHERE id = ? AND status = 'pending'",
        (now, row["id"])
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM reports WHERE id = ?", (row["id"],)).fetchone()
    if updated["status"] != "running":
        return None
    return updated

def run_worker():
    print("Report worker started, polling...")
    while True:
        conn = get_db()
        report = claim_next_report(conn)
        if report:
            print(f"CLAIMED report {report['id']}")
            process_report(conn, report)
        conn.close()
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_worker()