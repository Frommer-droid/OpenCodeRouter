# Clash Verge Rev: minimal OpenCode Router integration

For subscriptions with ⭐ or 🚀 location directions, preserve those exact names,
including nested fallback groups. Do not expand countries into internal servers.
Add the function from the [Global Script example](../examples/clash-verge/opencode-directions.js)
to your existing script and call it inside `main` with your source VPN group name.
Keep the process rule and diagnostic listener. Installing Router does not apply
this script automatically.

The `PROCESS-NAME,opencode.exe,OpenCode-Location` rule follows the process name,
independently of the OpenCode version or installation folder.

[← README](../README.en.md) · [Русский](CLASH_SETUP.md)

[Configuration fragment](../examples/clash-verge/opencode.fragment.yaml)

This fragment extends an **existing working Clash Verge Rev subscription**. It is not
a complete profile. Supply your own nodes; it contains no servers, credentials or subscription URLs.
No additional rules for unrelated applications are required.

## Setup

1. Back up your profile and Global Script locally.
2. Enable the Windows service mode required for TUN, enable TUN, and select **Rule** mode in Clash Verge Rev. Confirm that your existing subscription works.
3. In the fragment, replace `YOUR-EXISTING-NODE-*` with exact concrete proxy names from your subscription. Do not use DIRECT, REJECT, automatic groups or the selector itself.
4. Append the selector to the existing `proxy-groups` and the HTTP listener to `listeners`. Insert the process rule into `rules`. Merge the `profile.store-selected` key without discarding other settings.
5. Use a persistent profile extension / Global Script so subscription updates retain your changes. The YAML describes the intended result; blindly pasting it into Merge may replace existing lists. Review the final configuration before applying it.
6. Validate and apply the resulting profile in Clash Verge Rev.

For an existing Global Script, integrate the changes into its `main(config)` before its return.
Do not add a second `main` or overwrite your script.

## Required elements

| Element | Purpose |
| --- | --- |
| TUN + Rule mode | Capture traffic and apply process routing |
| `find-process-mode: strict` | Resolve the process for PROCESS-NAME |
| `OpenCode-Location`, type `select` | Selectable concrete VPN nodes |
| `PROCESS-NAME,opencode.exe,OpenCode-Location` | Route OpenCode through that selector |
| HTTP listener at `127.0.0.1:7900` | Route Router's diagnostics directly through the selector |
| `profile.store-selected: true` | Persist the selected node |
| Local Mihomo controller API | Read nodes and change selection |

For an existing proxy provider, replace the selector's `proxies` field with `use`:

```yaml
proxy-groups:
  - name: OpenCode-Location
    type: select
    use:
      - YOUR-EXISTING-PROVIDER
```

This is an alternative definition, not a second selector with the same name. The provider
must exist and be loaded. Keep its subscription URL private. Use Router's `excludedNodes`
setting to hide unsuitable exact node names.

## Rule priority

The first matching rule wins. To route all OpenCode traffic through this selector,
place PROCESS-NAME above domain, IN-PORT and catch-all rules. Other processes continue
through your remaining rules. Keep your own final MATCH rule; do not add MATCH,DIRECT.

To preserve intentional domain exceptions for OpenCode, keep them above PROCESS-NAME.
Those requests will bypass the selector. The diagnostic listener bypasses the rule table,
so a successful Router check
cannot prove that an exception domain takes the same route.

## TUN, DNS and controller

Keep an already-working TUN stack, DNS and exclusions. The fragment's TUN block is a
starting point, not a replacement for your network setup. DNS must resolve proxy hosts
and target websites. Router requires no particular private DNS server or fake-IP filter.
Manage DNS hijacking and fake-IP through your Clash setup; do not copy another person's LAN DNS.
Do not add a second TUN listener when TUN is already enabled.

The [Router configuration example](../OpenCodeRouter.config.example.json) already uses
`group: OpenCode-Location`, `testProxy: http://127.0.0.1:7900`, and
`controllerPipe: verge-mihomo`. First run creates a complete local config from it.

With `controllerPipe: "verge-mihomo"`, Router reads the active `external-controller-pipe`
from `secretSource` for every controller request. A Clash upgrade or core-mode change that
renames the pipe does not require editing Router's local config. An explicit custom
`controllerPipe` remains authoritative. Check the effective Mihomo configuration.
Do not blindly replace Clash's pipe. Named-pipe access stays local and depends on local permissions.
The fragment does not enable a TCP controller or change its secret.
If you deliberately configure a TCP API, bind it to loopback and set Router's matching
`controller` plus an empty `controllerPipe`. Keep the local `secretSource` file private.

Port 7900 must not conflict with other listeners, mixed-port or applications. If you change
it, update both the listener and Router's `testProxy`. Keep `listen: 127.0.0.1`; local
processes can access this diagnostic proxy, and it need not be exposed to the LAN.

## Verify

From the project root after applying your configuration:

```powershell
pwsh -NoProfile -File .\OpenCodeRouter.ps1 list
pwsh -NoProfile -File .\OpenCodeRouter.ps1 status
```

Then make an OpenCode request and inspect Connections in Clash: `opencode.exe`,
PROCESS-NAME, and an `OpenCode-Location` → selected-node chain. This verifies the
application route; `status` only checks the diagnostic listener. A different binary name
or explicit HTTP(S) proxy settings may result in another route.

Run temporary `test`/`scan` checks between active requests. Committed changes close old
OpenCode connections in the dedicated group so the application reconnects.

| Symptom | Check |
| --- | --- |
| Missing group | Effective config, selector name, nonempty concrete nodes |
| Named-pipe failure | Running Clash instance, pipe name and user permissions |
| Port 7900 failure | Listener, port conflict and `testProxy` |
| status succeeds, app fails | Rule priority, actual process and client proxy settings |
| Other apps changed route | Replaced lists or changed final MATCH rule |

Apply or restore your profile explicitly through Clash Verge Rev.

## Official references

- [Clash Verge Rev scripts](https://www.clashverge.dev/guide/script.html)
- [Mihomo TUN](https://wiki.metacubex.one/config/inbound/tun/)
- [Listeners](https://wiki.metacubex.one/config/inbound/listeners/)
- [Proxy groups](https://wiki.metacubex.one/config/proxy-groups/)
- [General settings and named pipes](https://wiki.metacubex.one/config/general/)
