const GITHUB_API = "https://api.github.com";

function repoParts() {
  const repo = (process.env.GH_REPO || "").trim();
  const [owner, name] = repo.split("/");
  if (!owner || !name) {
    throw new Error("GH_REPO env var must be set to 'owner/repo'");
  }
  return { owner, name };
}

async function githubRequest(path, options = {}) {
  const token = process.env.GH_PAT;
  if (!token) {
    throw new Error("GH_PAT env var is not set");
  }
  return fetch(`${GITHUB_API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(options.headers || {}),
    },
  });
}

function checkPassword(req) {
  const expected = process.env.SITE_PASSWORD;
  if (!expected) return false;
  const supplied =
    req.headers["x-site-password"] ||
    (req.body && req.body.password) ||
    (req.query && req.query.password);
  return supplied === expected;
}

module.exports = { repoParts, githubRequest, checkPassword };
