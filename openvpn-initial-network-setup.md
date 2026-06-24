# OpenVPN Server + Client on FreeBSD in VMware Fusion (built from source via Git)

This guide builds OpenVPN and Easy-RSA from their Git repositories on two
FreeBSD VMs — **vpn-server** and **vpn-client** — wires them together on a
shared virtual network, generates certs, and brings up a working tunnel.

Example addressing used throughout (substitute your own where noted):

- VMware virtual LAN (the "real" network between the two VMs): `192.168.71.0/24`
  - vpn-server: `192.168.71.10`
  - vpn-client: `192.168.71.20`
- OpenVPN tunnel network: `10.8.0.0/24`
  - vpn-server tun0: `10.8.0.1`
  - vpn-client tun0: assigned from the pool (e.g. `10.8.0.6`)

---

## Part 1 — VMware Fusion network setup

1. Create two FreeBSD VMs (vpn-server, vpn-client). FreeBSD 13/14 works fine.
2. For each VM, go to **VM Settings → Network Adapter** and set it to
   **"Share with my Mac" (NAT)**. This is the simplest option:
   - Both VMs land on the same internal vmnet (commonly `192.168.71.0/24`)
     and can talk to each other directly.
   - Both still get outbound internet access, so `pkg` and `git clone` work.
3. Boot both VMs and confirm interface names and IPs:

   ```sh
   ifconfig
   ```

   Note the Ethernet interface name (often `em0` for the "Intel e1000"
   adapter type — recommended for FreeBSD compatibility — or `vtnet0`/`vmx0`
   for other adapter types). Replace `em0` everywhere below with whatever
   you actually see.

4. From vpn-client, confirm you can reach vpn-server:

   ```sh
   ping 192.168.71.10
   ```

> Optional (more "realistic" topology): instead of NAT, create a custom
> network in **VMware Fusion → Preferences → Network → "+"**, then assign
> that custom vmnet to both VMs' adapters. This isolates the two VMs on
> their own LAN, simulating client/server connected over a WAN link, with
> the VPN tunnel layered on top.