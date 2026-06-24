## Part 3 — Clone & build OpenVPN from source (on BOTH VMs)

```sh
cd /usr/local/src    # or wherever you like to keep sources
git clone https://github.com/OpenVPN/openvpn.git
cd openvpn

autoreconf -i -v -f
./configure --prefix=/usr/local --sysconfdir=/usr/local/etc --disable-lz4
gmake
gmake install
```

Verify it installed and check the version:

```sh
which openvpn
openvpn --version
```

You should get `/usr/local/sbin/openvpn` and a version banner. Run this on
**both** vpn-server and vpn-client — both ends need the `openvpn` binary.

---

## Part 4 — Clone Easy-RSA & build the PKI (on vpn-server)

```sh
cd /usr/local/src
git clone https://github.com/OpenVPN/easy-rsa.git
cd easy-rsa/easyrsa3
```

Recent Easy-RSA 3.1+ scripts are plain POSIX `sh`, so `./easyrsa` should
just work. If you get an interpreter error, run it via `sh ./easyrsa ...`
or `pkg install -y bash` and use `bash ./easyrsa ...`.

Initialize the PKI and build the CA:

```sh
./easyrsa init-pki
./easyrsa build-ca nopass        # set a CA Common Name when prompted, e.g. "MyVPN-CA"
```

Server certificate:

```sh
./easyrsa gen-req server nopass        # CN: server
./easyrsa sign-req server server       # type "yes" to confirm
```

Client certificate:

```sh
./easyrsa gen-req client1 nopass       # CN: client1
./easyrsa sign-req client client1      # type "yes" to confirm
```

Diffie-Hellman params and TLS auth key:

```sh
./easyrsa gen-dh
openvpn --genkey secret ta.key
```

Move this whole easy-rsa working tree (with its freshly generated `pki/`
and `ta.key`) into the OpenVPN config area so paths in `server.conf` line
up:

```sh
mkdir -p /usr/local/etc/openvpn
cp -r /usr/local/src/easy-rsa/easyrsa3 /usr/local/etc/openvpn/easy-rsa
```

The important files now live under:

```
/usr/local/etc/openvpn/easy-rsa/pki/ca.crt
/usr/local/etc/openvpn/easy-rsa/pki/issued/server.crt
/usr/local/etc/openvpn/easy-rsa/pki/issued/client1.crt
/usr/local/etc/openvpn/easy-rsa/pki/private/server.key
/usr/local/etc/openvpn/easy-rsa/pki/private/client1.key
/usr/local/etc/openvpn/easy-rsa/pki/dh.pem
/usr/local/etc/openvpn/easy-rsa/ta.key
```

---

## Part 5 — Server configuration (on vpn-server)

Create `/usr/local/etc/openvpn/server.conf`:

```sh
cat > /usr/local/etc/openvpn/server.conf <<'CONF'
port 1194
proto udp
dev tun

ca   easy-rsa/pki/ca.crt
cert easy-rsa/pki/issued/server.crt
key  easy-rsa/pki/private/server.key
dh   easy-rsa/pki/dh.pem
tls-auth easy-rsa/ta.key 0

server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"

keepalive 10 120
cipher AES-256-GCM
auth SHA256
persist-key
persist-tun

status /var/log/openvpn-status.log
log-append /var/log/openvpn.log
verb 3
CONF
```

---

## Part 6 — Enable IP forwarding + NAT (pf) on vpn-server

```sh
sysrc gateway_enable="YES"
sysctl net.inet.ip.forwarding=1
```

Create `/etc/pf.conf` (adjust `ext_if` to your real interface name):

```sh
cat > /etc/pf.conf <<'CONF'
ext_if="em0"
tun_if="tun0"

set skip on lo

nat on $ext_if from 10.8.0.0/24 to any -> ($ext_if)

pass in on $ext_if proto udp to port 1194
pass quick on $tun_if all
pass out all keep state
CONF

sysrc pf_enable="YES"
sysrc pf_rules="/etc/pf.conf"
service pf start
```