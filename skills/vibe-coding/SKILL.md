---
name: vibe-coding
description: Vibe coding best practices for rapid prototyping and shipping - what to use and what to avoid when building fast
---

# Vibe Coding Cheatsheet

When building a new project fast (hackathon, MVP, side project, prototype), follow these rules.

## DO - Stack & Tools

- Use ready-made auth (Clerk / Supabase Auth)
- Use Tailwind + shadcn/ui for UI
- Use Zustand / Server Components for state
- Use tRPC / Server Actions for APIs
- Deploy with Vercel one-click
- Use Prisma + managed Postgres
- Validate with Zod + React Hook Form
- Use Stripe for payments
- Add Sentry / error tracking early
- Set up analytics (PostHog / Plausible)
- Store secrets in env files
- Use UploadThing / Cloudinary for files
- Set up preview deployments
- Use component libraries (Radix / shadcn)
- Write a README from Day 1
- Keep folders clean and modular
- Add onboarding + empty states
- Use Lighthouse / performance tools
- Use a monorepo or clear app structure from the start
- Document your env vars in .env.example

## DON'T - Common Traps

- Don't build auth from scratch
- Don't write raw CSS for everything
- Don't over-engineer state management
- Don't build custom APIs too early
- Don't deploy manually
- Don't write raw SQL everywhere
- Don't build your own payment system
- Don't roll your own search engine
- Don't skip logging & monitoring
- Don't hardcode API keys
- Don't DIY file uploads
- Don't push straight to main
- Don't build realtime systems alone
- Don't ignore performance
- Don't assume users "will figure it out"
- Don't postpone refactoring forever
- Don't rely on memory for decisions
- Don't chase "perfect" before shipping
- Don't skip error boundaries and fallbacks
- Don't forget a health check endpoint
