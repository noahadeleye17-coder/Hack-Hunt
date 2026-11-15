import argparse
import logging
import sys
import time
from datetime import datetime, timezone

from . import email_delivery
from .config import ConfigError, load_mail_config, load_settings
from .fetchers import devpost
from .filters import basic_drop_reason, eligibility_drop_reason, reminder_due
from .models import today_lagos
from .scoring import score
from .storage import SeenStore

log = logging.getLogger("hackhunt")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hackhunt")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="fetch, filter, score and send the digest")
    run_p.add_argument("--dry-run", action="store_true", help="print the digest; send and save nothing")
    run_p.add_argument("--force", action="store_true", help="send even if nothing is new")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        return run(dry_run=args.dry_run, force=args.force)
    except ConfigError as e:
        log.error("config: %s", e)
        return 2


def run(dry_run: bool, force: bool) -> int:
    settings = load_settings()
    mail = None if dry_run else load_mail_config()  # fail before any network work
    store = SeenStore(settings.state_file)
    now = datetime.now(timezone.utc)
    today = today_lagos(now)
    session = devpost.make_session()

    listing, errors = devpost.fetch_listing(session, settings.request_delay_seconds)
    log.info("Devpost: %d open hackathons", len(listing))

    fresh, closing = [], []
    for h in listing:
        entry = store.get(h.id)
        if entry:
            store.restore(h, entry)
            if reminder_due(h, entry, today, settings.urgent_days):
                closing.append(h)
            continue
        reason = basic_drop_reason(h, settings, today)
        if reason:
            log.info("drop %s: %s", h.title, reason)
            continue
        fresh.append(h)

    candidates = []
    for i, h in enumerate(fresh):
        if i:
            time.sleep(settings.request_delay_seconds)
        err = devpost.fetch_details(session, h)
        if err:
            # Eligibility is unchecked, so leave it out and retry on the next run.
            errors.append(err)
            continue
        # Recheck with the exact deadline, then eligibility.
        reason = basic_drop_reason(h, settings, today) or eligibility_drop_reason(h, settings)
        if reason:
            log.info("drop %s: %s", h.title, reason)
            store.mark_dropped(h, reason, now)
            continue
        score(h, settings.interests, today)
        candidates.append(h)

    candidates.sort(key=lambda h: h.score, reverse=True)
    closing.sort(key=lambda h: h.days_left(today))
    top, more = candidates[:settings.top_n], candidates[settings.top_n:]
    for e in errors:
        log.warning(e)

    if not (candidates or closing or errors or force):
        log.info("nothing new, not sending")
        if not dry_run:
            store.prune(today)
            store.save()
        return 0

    subject, text, html_body = email_delivery.build_digest(top, more, closing, errors, today)
    if dry_run:
        print(subject, "\n", text, sep="\n")
        return 0

    email_delivery.send(mail, subject, text, html_body)
    log.info("sent: %s", subject)
    # Only record after a successful send, so a failed run is retried next time.
    for h in candidates:
        store.mark_digested(h, now)
    for h in closing:
        store.mark_urgent(h.id, now)
    store.prune(today)
    store.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
