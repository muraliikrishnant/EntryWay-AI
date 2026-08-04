const { repoParts, githubRequest, checkPassword } = require("./_github");

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }
  if (!checkPassword(req)) {
    return res.status(401).json({ error: "Invalid password" });
  }

  let owner, name;
  try {
    ({ owner, name } = repoParts());
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }

  const { resumeFilename, keywords } = req.body || {};

  const dispatchRes = await githubRequest(
    `/repos/${owner}/${name}/actions/workflows/job-search.yml/dispatches`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ref: "main",
        inputs: {
          resume_filename: resumeFilename || "",
          keywords: keywords || "",
        },
      }),
    }
  );

  if (dispatchRes.status !== 204) {
    const details = await dispatchRes.text();
    return res.status(502).json({ error: "Failed to trigger workflow", details });
  }

  return res.status(200).json({ ok: true });
};
