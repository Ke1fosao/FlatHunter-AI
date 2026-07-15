# Data source policy

Stage 1 does not connect to real housing platforms.

Future adapters must support one of these legal modes:

- official API;
- approved partner API;
- official RSS/feed;
- explicitly permitted HTML access;
- user URL import with SSRF protection;
- forwarded Telegram message;
- administrator import;
- JSON/CSV import;
- synthetic demo source.

Real-source flags remain disabled in `.env.example`. The project must never bypass CAPTCHA, authentication, robots directives, rate limits, browser fingerprinting or platform access restrictions.

The adapter contract and `Source` domain model are scheduled for Stage 3, after search profiles are implemented in Stage 2.
