# UI Testing Reference

**CRITICAL: ALWAYS use incognito mode for UI testing. No exceptions.**

After making UI changes, always test them using Playwright before considering the task complete:

1. Run `make npm-watch` or `make npm-build` to rebuild the frontend
2. **ALWAYS launch browser in incognito mode** - use this exact command:
   ```
   mcp__playwright__browser_navigate with launchOptions: {"args": ["--incognito"]}
   ```
3. Use Playwright browser tools to navigate to the affected page
4. Verify the fix works as expected by interacting with the UI
5. Check for any console errors using `browser_console_messages`
6. If testing requires authentication, login first then navigate to the target page

**Never skip incognito mode** - browser caching causes false positives/negatives in testing.

For login script template, see `~/.claude/skills/puppeteer-init.md`
