# Test Credentials

## Admin Account (live DB — password unknown after live dump import)
- Email: bizchatapi@gmail.com
- Password: adminpassword (NOT working on current DB dump)

## QA Admin (created Aug 29, 2026 — use this for admin flows)
- Email: qaadmin@example.com
- Password: Admin@12345
- role: admin, dailyLimit: 100000

## QA Test User (created Aug 29, 2026 — use this for user flows)
- Email: qatest@example.com
- Password: Test@12345
- dailyLimit: 100000, BizChat creds are DUMMY (sends will fail at BizChat, campaign flow still works)

## Note (Aug 29, 2026)
- BizChat creds on qatest are dummy → actual sends fail with "Invalid Token" (expected). Prefer drip campaigns with a FUTURE start time when testing big uploads so nothing actually dispatches.
