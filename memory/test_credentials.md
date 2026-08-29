# Test Credentials

## Admin Account (live DB — password unknown after live dump import)
- Email: bizchatapi@gmail.com
- Password: adminpassword (NOT working on current DB dump)

## QA Test User (created Aug 29, 2026 — use this for testing)
- Email: qatest@example.com
- Password: Test@12345
- dailyLimit: 2000, BizChat creds are DUMMY (sends will fail at BizChat, campaign flow still works)

## Note (Aug 29, 2026)
- qatest@example.com dailyLimit was raised to 100000 so 30k-recipient campaigns can be tested.
- BizChat creds on this user are dummy → actual sends fail with "Invalid Token" (expected). Prefer drip campaigns with a FUTURE start time when testing big uploads so nothing actually dispatches.
