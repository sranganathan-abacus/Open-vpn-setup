## Part 8 — Copy client files to vpn-client

You need 4 files on the client: `ca.crt`, `client1.crt`, `client1.key`,
`ta.key`. Enable `sshd` on vpn-client if it isn't already running:

```sh
sysrc sshd_enable="YES"
service sshd start
```

From vpn-server, copy the files over with `scp`:

```sh
cd /usr/local/etc/openvpn/easy-rsa
scp pki/ca.crt pki/issued/client1.crt pki/private/client1.key ta.key \
    yourClientUser@192.168.71.20:/tmp/
```

On vpn-client, move them into place:

```sh
su -
mkdir -p /usr/local/etc/openvpn
cp /tmp/ca.crt /tmp/client1.crt /tmp/client1.key /tmp/ta.key /usr/local/etc/openvpn/
chmod 600 /usr/local/etc/openvpn/client1.key /usr/local/etc/openvpn/ta.key
```

---

## Part 9 — Client configuration (on vpn-client)

Create `/usr/local/etc/openvpn/client.conf`:

```sh
cat > /usr/local/etc/openvpn/client.conf <<'CONF'
client
dev tun
proto udp
remote 192.168.71.10 1194
resolv-retry infinite
nobind

ca   ca.crt
cert client1.crt
key  client1.key
tls-auth ta.key 1

cipher AES-256-GCM
auth SHA256
persist-key
persist-tun
status /var/log/openvpn-status.log
log-append /var/log/openvpn.log
verb 3
CONF
```

(`remote 192.168.71.10` is vpn-server's address on the VMware NAT network —
update it if your IPs differ.)

If you haven't already created `/usr/local/etc/rc.d/openvpn` on this VM,
repeat the steps from **Part 7** to add it (same script content), then:

```sh
sysrc openvpn_enable="YES"
sysrc openvpn_configfile="/usr/local/etc/openvpn/client.conf"
sysrc openvpn_dir="/usr/local/etc/openvpn"

service openvpn start
```

---

## Part 10 — Verify the tunnel

On vpn-client:

```sh
ifconfig tun0          # should show an address like 10.8.0.6
tail -f /var/log/openvpn.log   # look for "Initialization Sequence Completed"
ping 10.8.0.1           # ping the server over the VPN tunnel
```

On vpn-server:

```sh
ifconfig tun0           # should show 10.8.0.1
ping 10.8.0.6           # ping the client's tunnel address (use the address it actually got)
cat /var/log/openvpn-status.log   # shows connected clients
```

If both pings succeed, the tunnel is working.

---