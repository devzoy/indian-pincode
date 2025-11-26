# Publishing Guide

This guide explains how to publish the Indian Pincode libraries to their respective package registries.

## Prerequisites

### GitHub Secrets
You need to set up the following secrets in your GitHub repository:

1. **PYPI_API_TOKEN**: PyPI API token for publishing Python packages
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Add it to GitHub Secrets as `PYPI_API_TOKEN`

2. **NPM_TOKEN**: NPM token for publishing Node.js packages
   - Run `npm login` locally
   - Run `npm token create` to generate a token
   - Add it to GitHub Secrets as `NPM_TOKEN`

## Automated Publishing (Recommended)

The repository has GitHub Actions workflows set up for automated publishing:

### CI Workflow (`ci.yml`)
Runs on every push and pull request to test all three libraries (Python, Node.js, Go).

### Publish Workflow (`publish.yml`)
Automatically publishes to PyPI and NPM when you create a new GitHub Release.

**Steps:**
1. Update version numbers in:
   - `pyproject.toml`
   - `setup.py`
   - `src/node/package.json`
2. Commit and push changes
3. Create a new release on GitHub:
   - Tag: `v1.0.0` (match the version)
   - Title: `Release v1.0.0`
   - Description: Release notes
4. Publish the release
5. GitHub Actions will automatically publish to PyPI and NPM

## Manual Publishing

### Python (PyPI)

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

### Node.js (NPM)

```bash
cd src/node

# Login to NPM (one-time)
npm login

# Publish
npm publish --access public
```

### Go (Go Modules)

Go packages are published via Git tags. No additional steps needed beyond creating a release.

```bash
# Tag the release
git tag v1.0.0
git push origin v1.0.0
```

Users can then import:
```go
go get github.com/devzoy/indian-pincode@v1.0.0
```

## Version Management

- Follow [Semantic Versioning](https://semver.org/)
- Update all version numbers consistently across all packages
- Create a git tag matching the version number

## Testing Before Publishing

Always test the packages locally before publishing:

```bash
# Python
pip install -e .
python tests/test_python_lib.py

# Node.js
cd src/node
npm install
node test.js

# Go
cd src/go
go test -v
```

## Troubleshooting

### PyPI: "File already exists"
- You cannot re-upload the same version to PyPI
- Increment the version number and try again

### NPM: "You do not have permission"
- Make sure you're logged in: `npm whoami`
- If using a scoped package (@devzoy/indian-pincode), ensure you have access to the @devzoy organization

### Go: Import not working
- Ensure the git tag exists and is pushed to GitHub
- Run `go clean -modcache` to clear the Go module cache
- Try `go get -u github.com/devzoy/indian-pincode@latest`
