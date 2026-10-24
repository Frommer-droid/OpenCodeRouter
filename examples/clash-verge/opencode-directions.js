// Add this function to your existing Global Script, then call it inside main:
//   selectOpenCodeDirections(config, "YOUR-EXISTING-VPN-GROUP");
// Keep the existing main, process rule and diagnostic listener.
function selectOpenCodeDirections(config, sourceGroupName) {
  const groups = config["proxy-groups"] || [];
  const source = groups.find(group => group.name === sourceGroupName);
  if (!source || sourceGroupName === "OpenCode-Location") {
    throw new Error("OpenCode: choose an existing source VPN group");
  }
  const available = new Set([
    ...(config.proxies || []).filter(proxy =>
      !["direct", "reject", "dns"].includes(String(proxy.type).toLowerCase())
    ).map(proxy => proxy.name),
    ...groups.filter(group => group.name !== "OpenCode-Location").map(group => group.name)
  ]);
  const directions = [...new Set(source.proxies || [])].filter(name =>
    typeof name === "string" && /[⭐🌟🚀]/u.test(name) && available.has(name)
  );
  if (!directions.length) {
    throw new Error("OpenCode: no starred or rocket location directions in source group");
  }
  const entry = {name: "OpenCode-Location", type: "select", proxies: directions};
  const index = groups.findIndex(group => group.name === entry.name);
  if (index < 0) groups.push(entry);
  else groups[index] = entry;
  config["proxy-groups"] = groups;
  return config;
}
