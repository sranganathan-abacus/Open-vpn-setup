## Part 2 — Build dependencies (on BOTH VMs)

We're compiling OpenVPN from source, so we need the build toolchain plus
its libraries. The C compiler (`cc`/clang) is already in the FreeBSD base
system; install the rest:

```sh
su -          # become root
pkg update
pkg upgrade -y
pkg install -y git gmake autoconf automake libtool pkgconf lzo2 openssl py311-docutils
```

- `gmake` — GNU make (OpenVPN's build uses GNU Makefiles, not BSD make)
- `autoconf`/`automake`/`libtool`/`pkgconf` — needed to regenerate the
  `configure` script from a git checkout
- `lzo2` — optional compression library OpenVPN can link against
- `openssl` — newer OpenSSL with pkg-config files (FreeBSD base ships
  OpenSSL too, but this avoids pkg-config detection issues)

---