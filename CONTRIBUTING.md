# Working with the Cadence codebase

This guide is written in plain language for the people who run Cadence day-to-day. It is not a deep technical reference — it's the short list of things you need to know about source control so the project stays safe.

## Where the code lives

There are two copies of the codebase, and they should always agree:

1. **The Replit workspace** — what you see in your browser. This is the live editor and the running app.
2. **A private GitHub repository** — the off-site backup. Nobody has access to it except the people you invite.

Everything you do happens in the workspace. GitHub is just the safety copy.

## One-time GitHub connection (your turn — ~5 minutes)

The workspace has been prepped for a GitHub mirror (`.gitignore` is tightened, scratch files are untracked, the commit history is clean). The last step requires you because it involves logging into your GitHub account in your browser — nobody, including the agent, can do that for you.

1. Open the **Git** panel in the left sidebar of Replit (the icon that looks like a branch).
2. Click **Connect to GitHub**. Replit will open a GitHub authorization page in a new tab.
3. Sign in to your GitHub account (or create one — it's free) and click **Authorize Replit**. This grants Replit permission to create and push to repositories on your behalf. You can revoke it any time from GitHub's settings.
4. Back in Replit, click **Create a new repository**.
   - Name it something like `cadence` or `cadence-app`.
   - Set the visibility to **Private**. Always private.
   - Leave the default branch as `main`.
5. Click **Create & Push**. Replit will push the entire current history (all your existing checkpoints, including the work from Task #89 and earlier) up to the new GitHub repo.
6. Open the GitHub link Replit shows you and confirm you can see the files.
7. Once the repo exists, paste its URL into `replit.md` (under the **Source Control** section) so future agents and collaborators know where it lives.

From then on the **Day-to-day** section below is all you need.

## Pre-push checklist (10-second sanity check)

Before clicking **Commit & Push**, glance over the list of changed files in the Git panel and make sure you don't see:

- Anything starting with `attached_assets/` (chat scratch — should be ignored automatically, but worth a glance)
- Anything ending in `.env` (real environment files)
- `*.pem`, `*.key`, `secrets.json` or anything that looks like a credential
- Database dumps (`*.db`, `*.sqlite`, `*.dump`, `*.sql.gz`)

If any of those appear, stop and ask the agent before pushing.

## Day-to-day: pushing your changes to GitHub

After Cadence has been working in the workspace for a while and you'd like to back up the latest version:

1. Open the **Git** panel in the left sidebar of Replit (the icon that looks like a branch).
2. You'll see a list of changed files. Type a short message in the box at the top describing what changed (for example, "Fixed login bug" or "Added royalty export"). It doesn't have to be technical.
3. Click **Commit & Push**.

That's it. Within a few seconds the new version is mirrored to GitHub.

You don't need to do this after every tiny change. A good rhythm is:
- After the agent finishes a meaningful piece of work and you've confirmed it works
- At the end of the day
- Before publishing/deploying

## If the workspace ever gets lost or corrupted

Because there's a copy on GitHub, the workspace is replaceable.

1. From your Replit dashboard, click **Create Repl** → **Import from GitHub**.
2. Pick the Cadence repository.
3. Re-add the secrets in the new workspace (see the list under **Secrets** in the Replit sidebar of the current workspace — the *names* are visible, the *values* live only in Replit's secret manager).
4. Run the workflows.

You will be back where you were, minus anything that hadn't been pushed yet. That's why pushing regularly matters.

## The one rule about secrets

**Secrets never go into the code, and never go into GitHub.** Things like API keys, database passwords, the Resend key, the OpenAI key, the Spotify keys — all of those live exclusively in Replit's **Secrets** panel. The codebase reads them from there at runtime.

The `.gitignore` file is set up to block the most common ways secrets accidentally end up in code (`.env` files, key files, dump files), but the rule above is the one that matters. If you're ever unsure whether something contains a secret, ask the agent before pushing.

## What is intentionally NOT pushed to GitHub

To keep the GitHub repo clean and small, the following are excluded automatically:

- `attached_assets/` — files you drag into the agent chat (PDFs, screenshots, voice memos). These pile up to many gigabytes and are not part of the app.
- `uploads/` — runtime user uploads. These belong in cloud storage, not source control.
- Local databases, log files, build output, and editor scratch files.
- The agent's own working notes under `.local/` (except `.local/tasks/`, which is the project task history and is kept).

If you ever need one of these files later, you'll find it in the original Replit checkpoint history.

## Automated checks on GitHub (the green/red checkmark)

Every time a push lands on GitHub, GitHub automatically runs a short series of safety checks for free. You'll see a small icon next to each commit on github.com:

- **Yellow dot** — checks are still running (usually 1–3 minutes).
- **Green check** — everything passed. Nothing to do.
- **Red X** — something failed. The latest push has a problem.

The checks that run today are:

1. **Backend compile check** — confirms every Python file in `backend/` still parses (catches typos, syntax errors, and accidentally-deleted code). It does not run the app, so it won't catch every kind of bug, but it reliably catches the "I broke a file" class of mistakes.
2. **Frontend build** — runs `npm ci && npm run build` in `frontend/` to confirm the app still compiles into something deployable.
3. **Secret scan** — scans the push for things that look like API keys, passwords, or private keys. If one is found, the check goes red so you know to rotate the leaked credential immediately.

### What to do when a check goes red

1. Click the red X on github.com — it opens the run log.
2. Scroll to the bottom of the failing step. The actual error is almost always in the last 20–30 lines (look for the word `Error`, `Failed`, or a red line).
3. Copy that error and paste it to the agent in Replit with a short note like *"the GitHub check failed with this error, please fix"*. The agent can read the log excerpt and patch the workspace.
4. Once the agent has fixed it, push again. The new commit will get its own checkmark.

If the **secret scan** went red, treat it as urgent:
- Do not push more commits trying to "remove" the secret — it's already in the history.
- Tell the agent which secret leaked. The agent will help you rotate it (generate a new key) and clean the file. The old key should be considered compromised.

## Branches and pull requests (for later)

Right now the workflow is "everyone works on `main`." That's the right call while it's just you and the agent. If a real second contributor joins the project, switch to:
- A `main` branch that only accepts changes through pull requests.
- Branch-protection rules requiring at least one review before merging.

That's a separate conversation when the time comes.
