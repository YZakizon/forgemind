from __future__ import annotations

import argparse
import asyncio

from app.services.store import backfill_encrypted_sensitive_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Encrypt existing plaintext memory and profile fact rows.")
    parser.add_argument("--limit", type=int, default=500, help="Maximum rows per table to encrypt in this run.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    result = await backfill_encrypted_sensitive_text(limit=args.limit)
    print(f"Encrypted {result['memories']} memory rows and {result['profile_facts']} profile fact rows.")


if __name__ == "__main__":
    asyncio.run(main())
