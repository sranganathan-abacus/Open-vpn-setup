## Part 7 — Run OpenVPN as a service (on BOTH VMs)

Since we built from source, there's no packaged `rc.d` script — we'll add a
small one so `service openvpn start/stop/status` works the same as a
pkg-installed setup.

Create `/usr/local/etc/rc.d/openvpn`:

```sh
cat > /usr/local/etc/rc.d/openvpn <<'SCRIPT'
#!/bin/sh
#
# PROVIDE: openvpn
# REQUIRE: NETWORKING SERVERS pf
# KEYWORD: shutdown

. /etc/rc.subr

name="openvpn"
rcvar="openvpn_enable"

load_rc_config $name

: ${openvpn_enable:="NO"}
: ${openvpn_configfile:="/usr/local/etc/openvpn/server.conf"}
: ${openvpn_dir:="/usr/local/etc/openvpn"}

pidfile="/var/run/openvpn.pid"
command="/usr/local/sbin/${name}"
command_args="--daemon --cd ${openvpn_dir} --config ${openvpn_configfile} --writepid ${pidfile}"

run_rc_command "$1"
SCRIPT

chmod +x /usr/local/etc/rc.d/openvpn
```

### On vpn-server:

```sh
sysrc openvpn_enable="YES"
sysrc openvpn_configfile="/usr/local/etc/openvpn/server.conf"
sysrc openvpn_dir="/usr/local/etc/openvpn"

service openvpn start
```

Verify:

```sh
ifconfig tun0
service openvpn status
tail -f /var/log/openvpn.log
```

You should see `tun0` with address `10.8.0.1` and the log ending with
`Initialization Sequence Completed`.