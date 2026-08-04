const { repoParts, githubRequest } = require("./_github");

module.exports = async (req, res) => {
  let owner, name;
  try {
    ({ owner, name } = repoParts());
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }

  const runsRes = await githubRequest(
    `/repos/${owner}/${name}/actions/workflows/job-search.yml/runs?per_page=1`
  );
  if (!runsRes.ok) {
    return res.status(502).json({ error: "Failed to fetch run status" });
  }
  const data = await runsRes.json();
  const run = (data.workflow_runs || [])[0];
  if (!run) {
    return res.status(200).json({ status: "none" });
  }
  return res.status(200).json({
    status: run.status,
    conclusion: run.conclusion,
    html_url: run.html_url,
    created_at: run.created_at,
    updated_at: run.updated_at,
  });
};
