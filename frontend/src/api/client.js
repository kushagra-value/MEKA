const BASE_URL = "/api";

export async function submitQuery(query, webSearchEnabled = true) {
  const res = await fetch(`${BASE_URL}/query/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      web_search_enabled: webSearchEnabled,
      user_id: "demo_user",
    }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function submitQueryAsync(query, webSearchEnabled = true) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      web_search_enabled: webSearchEnabled,
      user_id: "demo_user",
    }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getQueryStatus(queryId) {
  const res = await fetch(`${BASE_URL}/status/${queryId}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getUserHistory() {
  const res = await fetch(`${BASE_URL}/history/demo_user`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
