# API Tools

`tools/` contains external integration and platform utility modules.

- `auth/`: Clerk JWT verification, Clerk Backend SDK client, DRF auth integration.
- `database/`: Supabase client and configuration helpers.
- `email/`: Resend transactional email helpers.
- `storage/`: signed URL logic for Supabase Storage and S3 compatible backends.

Legacy module paths in `api/` remain as compatibility shims.
Use `tools/` paths for new code.
