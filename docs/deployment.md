# Deploying Study Ledger: GitHub Actions → Docker Hub → Portainer

Push to `main`, and a few minutes later the new version is live on your server. No SSH, no manual `docker pull`.

```
 you: git push / merge PR
          │
          ▼
 GitHub Actions ──► 1. backend tests (with a real Postgres)
                    2. frontend build
                    3. build Docker image ──► push to Docker Hub  (yourname/study-ledger:latest)
                    4. POST Portainer webhook
                                   │
                                   ▼
                    Portainer (on your server) pulls :latest and restarts the stack
                                   │
                                   ▼
                          new version live, database untouched
```

| File | What it is |
|---|---|
| `.github/workflows/deploy.yml` | The pipeline: test → build → push → webhook |
| `Dockerfile` | How the image is built (React UI + FastAPI in one image) |
| `deploy/docker-compose.yml` | What runs on the server: the app image + Postgres |
| `deploy/stack.env.example` | The variables you type into Portainer |

**Why the stack is deployed "from Git":** in Portainer Community Edition, the ordinary stack webhook is a
Business Edition feature. CE gives a webhook to stacks deployed **from a Git repository** (GitOps updates).
So Portainer reads `deploy/docker-compose.yml` from GitHub, and the workflow pokes its webhook.

---

## One-time setup

### What you need
- A GitHub account and a Docker Hub account (both free).
- A server with Docker and Portainer CE running, reachable from the internet (so GitHub can call the webhook).

### A. Docker Hub (2 min)
1. Docker Hub → **Repositories → Create repository** → name `study-ledger`, **Public** (simplest; see Troubleshooting for private).
2. **Account settings → Personal access tokens → Generate new token** → access **Read & Write** → copy it (shown once).

### B. GitHub (5 min)
1. Put the finished work on `main` (it's on the `multi-user` branch right now):
   ```bash
   git checkout main
   git merge multi-user
   ```
2. GitHub → **New repository** → `study-ledger` → **don't** add a README. Then:
   ```bash
   git remote add origin https://github.com/<you>/study-ledger.git
   git push -u origin main
   ```
   Public or private both work. Nothing secret is in the repo: `.env`, `backups/` and `backend/data/` are git-ignored.
3. Repo → **Settings → Secrets and variables → Actions**:
   - **Variables** tab → `DOCKERHUB_USERNAME` = your Docker Hub username
   - **Secrets** tab → `DOCKERHUB_TOKEN` = the token from A.2
   - (`PORTAINER_WEBHOOK_URL` comes in step C.)
4. **Actions** tab → the push already started a run. Watch it: tests → frontend → build & push go green;
   **deploy** shows a notice "PORTAINER_WEBHOOK_URL isn't set yet". That's expected.
   Docker Hub now has `study-ledger:latest`.

### C. Portainer (5 min)
1. **Stacks → Add stack** → name `study-ledger` → build method **Repository**.
2. Repository URL `https://github.com/<you>/study-ledger`, reference `refs/heads/main`,
   compose path `deploy/docker-compose.yml`. Private repo: turn on **Authentication** (GitHub username + a
   fine-grained token with read access to the repo's contents).
3. **GitOps updates** → on → Mechanism **Webhook** → turn on **Re-pull image** and **Force redeployment** → **Copy link**.
   - Re-pull image: always pull `:latest` again (otherwise Docker keeps the old copy).
   - Force redeployment: redeploy even when the compose file in Git didn't change (only the image did).
4. **Environment variables** → add each line from `deploy/stack.env.example` with real values:
   `APP_IMAGE=<you>/study-ledger:latest`, a long random `POSTGRES_PASSWORD`, `APP_PORT`, `COOKIE_SECURE`.
5. **Deploy the stack.** Open `http://<server>:<APP_PORT>` → the sign-up page.
6. Back in GitHub → **Secrets** → `PORTAINER_WEBHOOK_URL` = the link from C.3.

Setup done. From now on every push to `main` deploys itself.

### D. Your account and data on the server (once)
Create your account from the old SQLite file and make it the admin (admins see your private plan and can refresh market data):
```bash
# on the server, in the folder with learning.db
docker cp learning.db study-ledger-app-1:/tmp/learning.db
docker exec -it study-ledger-app-1 python -m cli import-sqlite /tmp/learning.db \
  --email frunwindeh@gmail.com --name "Your name" --admin
```
(The container name is on Portainer's **Containers** page. Already signed up in the browser? Then just
`docker exec -it study-ledger-app-1 python -m cli make-admin you@example.com`.)

---

## The demo: watch a change go live
1. Make a visible change, e.g. the tagline in `frontend/src/views/Auth.tsx` ("A study plan you follow one step at a time.").
2. `git checkout -b new-tagline && git commit -am "New tagline" && git push -u origin new-tagline`
3. Open a pull request → only **test** and **frontend** run (nothing deploys from a PR).
4. Merge it → a new run on `main`: test → frontend → build-and-push → deploy.
5. Portainer → the stack → the app container restarts with the new image (**Containers** shows a fresh "Created" time).
6. Refresh the site → new tagline. Your data is still there: it lives in the `pgdata` volume, not in the image.

**Roll back:** in Portainer set `APP_IMAGE` to `<you>/study-ledger:sha-<commit>` (every build is also tagged with
its commit) → **Update the stack**. Set it back to `:latest` when fixed.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tests fail in Actions | Click the failed step to read the error; run `make test` locally. Nothing deploys until it's green. |
| `denied: requested access to the resource is denied` on push | `DOCKERHUB_USERNAME` must be a **variable** (not a secret) and match the account; the token needs Read & Write. |
| Deploy step: `curl: (22) ... 404` | The webhook URL changed (stack recreated). Copy it again from the stack's GitOps section. |
| Deploy step: timeout / can't connect | GitHub must reach Portainer from the internet: public URL, open port (9443), valid HTTPS. |
| Webhook works but the site shows the old version | **Re-pull image** is off in GitOps updates. Turn it on (and Force redeployment). |
| Your Portainer CE shows Re-pull image as Business-only | Use the API instead: Portainer → **My account → Access tokens**, then in the deploy step call `curl -X PUT -H "X-API-Key: $TOKEN" "https://<portainer>/api/stacks/<id>/git/redeploy?endpointId=<env>" -d '{"pullImage":true,"prune":false,"repositoryReferenceName":"refs/heads/main"}'`. Check the API docs for your Portainer version first: the body can also carry `env`, and you don't want the call to clear your stack variables. |
| `exec format error` in the app container | The server is ARM (Raspberry Pi, Oracle Ampere). In the workflow set `platforms: linux/amd64,linux/arm64`. |
| Private Docker Hub repo: `pull access denied` | Portainer → **Registries → Add registry → Docker Hub** with a read-only token. |
| Logged out after every request on HTTPS | Behind HTTPS, set `COOKIE_SECURE=true`. On plain http it must be `false`. |
| App container restarting | Portainer → container → **Logs**. Usually a missing `POSTGRES_PASSWORD`/`APP_IMAGE`. |

---

## Recording notes

### Before you hit record
- [ ] Repo pushed, variables + secrets set, one green run already done (Docker Hub has an image).
- [ ] Portainer stack deployed from Git, site loads.
- [ ] A small visible change staged on a branch (tagline).
- [ ] Tabs open: GitHub repo (Actions tab), Docker Hub repo, Portainer stack page, the live site.
- [ ] Secrets hidden: don't open the Secrets page on camera after typing them; blur the webhook URL (it's a password).

### YouTube (~8–10 min)
1. **Hook (0:00)**: "I merge a pull request and 3 minutes later it's live on my server. No SSH. Here's the whole setup."
   Show the merge → site changing (cut to the end result first).
2. **The picture (0:45)**: the diagram above. Four steps: test, build, push, webhook. Docker Hub is the hand-off point.
3. **The app in one image (1:30)**: `Dockerfile`: stage 1 builds React with Node, stage 2 is Python running FastAPI,
   which also serves the UI. Non-root user, health check. "Node isn't even in the final image."
4. **The workflow file (2:30)**: walk `.github/workflows/deploy.yml` top to bottom:
   - triggers: push to main, PRs only test
   - tests with a real Postgres as a service container
   - `needs:` makes build wait for tests: a broken commit never ships
   - two tags: `latest` to run, `sha-…` to roll back
   - the webhook step is one `curl`
5. **Secrets (4:30)**: variable vs secret (secrets get masked as `***` in logs, so the username is a variable).
6. **Portainer (5:15)**: stack from Git, why (CE has no plain stack webhook), env vars, GitOps → Webhook,
   Re-pull image + Force redeployment, copy link → GitHub secret.
7. **Live demo (6:45)**: change → PR (only tests run) → merge → Actions → Portainer restarts → refresh site.
8. **Data is safe (8:15)**: database is in a volume; redeploys replace the app container only. Rollback via `sha-` tag.
9. **Outro (8:45)**: recap the four steps; link the repo.

### TikTok / Shorts (≈60 s)
- 0–3 s: "Merge on GitHub → live on my server. Watch." (screen: click Merge)
- 3–12 s: Actions tab: tests ✓, build ✓, push ✓, deploy ✓ (sped up)
- 12–20 s: Portainer: container restarting with the new image
- 20–25 s: refresh the site → the change is live
- 25–45 s: how: "GitHub Actions tests it, builds a Docker image, pushes it to Docker Hub, then calls a Portainer
  webhook that pulls the new image." Flash the workflow file and the GitOps toggles.
- 45–55 s: the gotcha: "Portainer Community Edition only gives webhooks to stacks deployed from Git, so deploy it
  that way and turn on Re-pull image."
- 55–60 s: "Full walkthrough on YouTube."
