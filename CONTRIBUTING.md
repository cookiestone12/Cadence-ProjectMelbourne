# Working with the Cadence codebase

This guide is written in plain language for the people who run Cadence day-to-day. It is not a deep technical reference — it's the short list of things you need to know about source control so the project stays safe.

## Where the code lives

There are two copies of the codebase, and they should always agree:

1. **The Replit workspace** — what you see in your browser. This is the live editor and the running app.
2. **A private GitHub repository** — the off-site backup. Nobody has access to it except the people you invite.

Everything you do happens in the workspace. GitHub is just the safety copy.

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

## Branches and pull requests (for later)

Right now the workflow is "everyone works on `main`." That's the right call while it's just you and the agent. If a real second contributor joins the project, switch to:
- A `main` branch that only accepts changes through pull requests.
- Branch-protection rules requiring at least one review before merging.

That's a separate conversation when the time comes.
