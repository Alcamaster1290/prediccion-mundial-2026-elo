#!/usr/bin/env python3
"""admin_premium_codes.py - create or inspect premium access codes.

Codes are stored only as SHA-256 hashes in Supabase. Plaintext codes are
printed only when generated so the operator can send them to the buyer.
"""
import argparse
import hashlib
import os
import secrets
import string

from export_to_supabase import supabase_request


ALPHABET = string.ascii_uppercase + string.digits


def hash_code(code):
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def generate_code():
    parts = []
    for _ in range(3):
      parts.append("".join(secrets.choice(ALPHABET) for _ in range(4)))
    return "-".join(parts)


def require_env():
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not service_key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
    return supabase_url, service_key


def create_code(args):
    code = args.code or generate_code()
    row = {"code_hash": hash_code(code), "notes": args.notes}
    if args.dry_run:
        print("Dry run: would insert premium_codes hash for notes:", args.notes or "")
        if not args.code:
            print("Generated plaintext code:", code)
        return 0

    supabase_url, service_key = require_env()
    err, _ = supabase_request(supabase_url, service_key, "POST", "premium_codes", [row])
    if err:
        print(f"ERROR: {err}")
        return 1
    if not args.code:
        print("Generated plaintext code:", code)
    print("Premium code hash inserted.")
    return 0


def list_codes(args):
    supabase_url, service_key = require_env()
    path = "premium_codes?select=id,is_used,used_at,created_at,notes&order=created_at.desc"
    err, data = supabase_request(supabase_url, service_key, "GET", path, None, prefer="")
    if err:
        print(f"ERROR: {err}")
        return 1
    for row in data or []:
        print(row)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Manage premium code hashes")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create one premium code hash")
    create.add_argument("--code", help="Existing plaintext code to hash; omitted generates one")
    create.add_argument("--notes")
    create.add_argument("--dry-run", action="store_true")
    create.set_defaults(func=create_code)

    listing = sub.add_parser("list", help="List code metadata without hashes")
    listing.set_defaults(func=list_codes)

    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
