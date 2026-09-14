# Publishing Guide (v2)

v2 ships **four** packages from this monorepo, published with **OIDC trusted
publishing** — no long-lived tokens anywhere. Publishing is automated by
`.github/workflows/release.yml`, triggered when you publish a GitHub Release.

| Registry | Package | Source dir |
| :--- | :--- | :--- |
| PyPI | `indian-pincode` (core) | `packages/py-core` |
| PyPI | `indian-pincode-geo` (geo) | `packages/py-geo` |
| npm | `@devzoy/indian-pincode` (core) | `packages/node-core` |
| npm | `@devzoy/indian-pincode-geo` (geo) | `packages/node-geo` |

**Publish order matters** because geo pins core to the *exact* version. The workflow
publishes **PyPI core → PyPI geo → npm core → npm geo**, and waits for each core to be
installable before publishing its geo companion.

---

## One-time setup (you must do this before the first v2 release)

### 1. PyPI Trusted Publishing (both packages)

For **each** of `indian-pincode` and `indian-pincode-geo`:

1. Sign in at https://pypi.org and open the project (or, for the first-ever upload of
   `indian-pincode-geo`, use **Publishing → Add a pending publisher**).
2. Add a **GitHub Actions** trusted publisher with:
   - **Owner:** `devzoy`
   - **Repository:** `indian-pincode`
   - **Workflow name:** `release.yml`
   - **Environment:** `pypi`
3. In this GitHub repo, create an **Environment** named `pypi`
   (Settings → Environments → New environment). Add required reviewers if you want a
   manual approval gate before publishing.

`indian-pincode` already exists on PyPI (v1.0.4, owned by you), so add the trusted
publisher on the existing project. `indian-pincode-geo` is a **new** name (confirmed
available) — use a *pending publisher* so the first OIDC publish creates it.

### 2. npm Trusted Publishing (both packages)

For **each** of `@devzoy/indian-pincode` and `@devzoy/indian-pincode-geo`:

1. Sign in at https://www.npmjs.com, open the package → **Settings → Trusted Publisher**
   → **GitHub Actions**, and set:
   - **Organization/User:** `devzoy`
   - **Repository:** `indian-pincode`
   - **Workflow filename:** `release.yml`
   - **Environment:** `npm`
2. In this GitHub repo, create an **Environment** named `npm`.
3. `@devzoy/indian-pincode` exists (v1.0.4). `@devzoy/indian-pincode-geo` is new
   (confirmed available); the first OIDC publish creates it — you may need to do the
   very first publish of the new scoped name after configuring the org to allow it.

**Do not** set `registry-url` in `actions/setup-node` for OIDC publishing — it injects
`NODE_AUTH_TOKEN` handling that breaks trusted publishing (npm/documentation#1960). The
release workflow already omits it.

### 3. Data-refresh secret

`.github/workflows/data-refresh.yml` reads the data.gov.in API key from the repo secret
**`DATA_GOV_IN_API_KEY`** (Settings → Secrets and variables → Actions). It is used only
to fetch the dataset; the pipeline never logs it or passes it as a process argument.

---

## Release checklist

1. Ensure `version.json` holds the version you want and all manifests match:
   ```bash
   python scripts/propagate_version.py --check
   ```
   To bump: `python scripts/bump_version.py {patch|minor|major}` then commit.
2. Push and open/merge the release PR. Confirm CI is green.
3. On GitHub, **Draft a new release**, tag `vX.Y.Z` (matching `version.json`), write
   notes (or reuse the CHANGELOG entry), and **Publish release**.
4. `release.yml` runs: verify → PyPI core → PyPI geo → npm core → npm geo.
5. Verify the four packages are live at the new version:
   ```bash
   pip index versions indian-pincode indian-pincode-geo
   npm view @devzoy/indian-pincode version
   npm view @devzoy/indian-pincode-geo version
   ```

## Handling a partial publish

Publishing is sequential and **stops at the first failure**, so you can always see which
packages went out from the workflow's job status (`pypi-core`, `pypi-geo`, `npm-core`,
`npm-geo` — in that order). A registry **never** lets you overwrite an existing version,
so recovery is:

1. Identify the last successful job; the failed job and everything after it did **not**
   publish.
2. Fix the cause.
3. **Bump the patch version** (you cannot re-publish the same version number), commit,
   and cut a new release. The already-published packages simply get a newer version;
   nothing is left half-published silently because each geo package refuses to work
   against a mismatched core (a runtime version-mismatch warning is emitted), and the
   `--check` gate keeps all four in lockstep.

## v1 → v2 notes

- v1 published a single package per registry using long-lived tokens
  (`PYPI_API_TOKEN`, `NPM_TOKEN`). Those secrets are **no longer used** and should be
  deleted.
- v1 published from `src/node` / the repo root; v2 publishes from `packages/*`.
