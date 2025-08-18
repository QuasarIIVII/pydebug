#!/usr/bin/env bash
set -euxo pipefail

export CFLAGS="${CFLAGS:-} -g3 -O0 -gdwarf-2 -I${PREFIX}/include"
export CPPFLAGS="${CPPFLAGS:-} -I${PREFIX}/include -I${PREFIX}/include/gdbm"
export LDFLAGS="${LDFLAGS:-} -g -rdynamic -L${PREFIX}/lib -Wl,-rpath,${PREFIX}/lib"
export LD_RUN_PATH="${PREFIX}/lib"
export PKG_CONFIG_PATH="${PREFIX}/lib/pkgconfig:${PREFIX}/share/pkgconfig:${PKG_CONFIG_PATH:-}"

TCL_CFLAGS="$(pkg-config --cflags tcl || true)"
TK_CFLAGS="$(pkg-config --cflags tk || true)"
TCL_LIBS="$(pkg-config --libs tcl || true)"
TK_LIBS="$(pkg-config --libs tk || true)"

mkdir -p build
pushd build

echo ">>> HEAD: $(git rev-parse HEAD || true)"
# echo ">>> TCL_CFLAGS: ${TCL_CFLAGS}"
# echo ">>> TK_CFLAGS:  ${TK_CFLAGS}"
# echo ">>> TCL_LIBS:   ${TCL_LIBS}"
# echo ">>> TK_LIBS:    ${TK_LIBS}"

../configure \
	--prefix="${PREFIX}" \
	--with-pydebug \
	--with-assertions \
	--enable-shared \
	--with-openssl="${PREFIX}" \
	--with-dbmliborder=gdbm:ndbm \
	--with-tcltk-includes="${TCL_CFLAGS} ${TK_CFLAGS}" \
	--with-tcltk-libs="${TCL_LIBS} ${TK_LIBS}"

make -j"${CPU_COUNT:-1}"
ln -sf python3 python
make install -j"${CPU_COUNT:-1}"

install -m 0755 -D python "${PREFIX}/bin/python" || true

popd
