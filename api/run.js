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
    let hint = "";
    if (dispatchRes.status === 401) {
      hint = "GH_PAT is invalid or expired — create a new fine-grained token and update it in Vercel.";
    } else if (dispatchRes.status === 403) {
      hint = "GH_PAT lacks Actions: Read and write on this repo.";
    } else if (dispatchRes.status === 404) {
      hint = "Workflow job-search.yml or the repo wasn't found — check GH_REPO and that the workflow exists on main.";
    }
    return res.status(502).json({
      error: `Failed to trigger workflow (GitHub ${dispatchRes.status})`,
      hint,
      details: details.slice(0, 300),
    });
  }

  return res.status(200).json({ ok: true });
};
