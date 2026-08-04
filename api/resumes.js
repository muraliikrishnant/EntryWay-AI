const { repoParts, githubRequest, checkPassword } = require("./_github");

module.exports = async (req, res) => {
  let owner, name;
  try {
    ({ owner, name } = repoParts());
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }

  if (req.method === "GET") {
    const listRes = await githubRequest(`/repos/${owner}/${name}/contents/data/resumes`);
    if (listRes.status === 404) {
      return res.status(200).json({ resumes: [] });
    }
    if (!listRes.ok) {
      return res.status(502).json({ error: "Failed to list resumes" });
    }
    const files = await listRes.json();
    const resumes = (Array.isArray(files) ? files : [])
      .filter((f) => f.type === "file" && f.name.toLowerCase().endsWith(".pdf"))
      .map((f) => f.name)
      .sort();
    return res.status(200).json({ resumes });
  }

  if (req.method === "POST") {
    if (!checkPassword(req)) {
      return res.status(401).json({ error: "Invalid password" });
    }
    const { filename, fileBase64 } = req.body || {};
    if (!filename || !fileBase64 || !filename.toLowerCase().endsWith(".pdf")) {
      return res.status(400).json({ error: "filename (.pdf) and fileBase64 are required" });
    }
    const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, "_");
    const path = `data/resumes/${safeName}`;

    let sha;
    const existing = await githubRequest(`/repos/${owner}/${name}/contents/${path}`);
    if (existing.ok) {
      const existingJson = await existing.json();
      sha = existingJson.sha;
    }

    const putRes = await githubRequest(`/repos/${owner}/${name}/contents/${path}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: `Add/update resume: ${safeName}`,
        content: fileBase64,
        sha,
        branch: "main",
      }),
    });

    if (!putRes.ok) {
      const details = await putRes.text();
      return res.status(502).json({ error: "Failed to save resume", details });
    }
    return res.status(200).json({ ok: true, filename: safeName });
  }

  res.setHeader("Allow", "GET, POST");
  return res.status(405).json({ error: "Method not allowed" });
};
