#!/usr/bin/env python3
import sys
from collections import deque
from pprint import pprint

# ---- Streaming byte reader (interactive-friendly) ----

class ByteStream:
    def __init__(self, f):
        self.f = f  # should be sys.stdin.buffer
        self.buf = deque()

    def _fill(self, n: int):
        # Ensure at least n bytes in buffer; block if needed.
        while len(self.buf) < n:
            chunk = self.f.read(1)
            if not chunk:
                # EOF: stop filling; caller must handle if insufficient
                break
            self.buf.append(chunk[0])

    def peek(self, n: int) -> bytes:
        self._fill(n)
        if len(self.buf) < n:
            return b""
        # Convert first n ints to bytes without consuming
        return bytes(list(self.buf)[:n])

    def read1(self) -> int:
        self._fill(1)
        if not self.buf:
            raise EOFError("stdin closed")
        return self.buf.popleft()

    def unread_bytes(self, bs: bytes):
        # Push back in reverse (so bs[0] becomes next to read)
        for b in reversed(bs):
            self.buf.appendleft(b)

# ---- Parser following the given grammar ----
# Notes on escapes:
#   - A backslash escapes the NEXT byte so it becomes literal (without the backslash).
#   - Special tokens used by the grammar are two-byte sequences:
#       b'\\('  b'\\)'  b'\\,'  b'\\:'
#     These are ONLY recognized as structure tokens when we are NOT
#     inside a "string" scan. Inside string scans, they are treated as
#     literal '(' / ')' / ',' / ':' respectively (i.e., backslash removed).
#   - b'\\\\' inside strings becomes a single backslash byte in the result.

TOK_LP = b'\\('
TOK_RP = b'\\)'
TOK_CM = b'\\,'
TOK_CL = b'\\:'

class Parser:
    def __init__(self, bs: ByteStream):
        self.bs = bs

    # ---- low-level: scan a "string" until a stop-token is encountered ----
    def parse_string_until(self, stop_tokens: set, initial: bytes = b"") -> bytes:
        """
        Scan bytes forming a 'string' (per grammar).
        Stop *before* seeing any token in stop_tokens (like b'\\,' or b'\\)').
        Handle escapes: backslash + X => literal X; backslash + backslash => single backslash.
        """
        out = bytearray(initial)
        while True:
            b0 = self.bs.read1()  # may block
            if b0 != 0x5C:  # not backslash
                out.append(b0)
                continue

            # b'\' seen; need next byte
            b1_raw = self.bs.read1()
            pair = bytes((0x5C, b1_raw))

            # If this pair is one of the stopping tokens, push it back and stop
            if pair in stop_tokens:
                self.bs.unread_bytes(pair)
                return bytes(out)

            # If it's a double backslash, emit one backslash
            if pair == b'\\\\':
                out.append(0x5C)  # literal backslash
            else:
                # Generic escape: include the escaped byte (without the backslash)
                out.append(b1_raw)

    # ---- helpers to peek/consume exact two-byte tokens ----
    def _peek_token(self) -> bytes | None:
        p = self.bs.peek(2)
        if len(p) < 2 or p[0] != 0x5C:
            return None
        if p in (TOK_LP, TOK_RP, TOK_CM, TOK_CL):
            return p
        return None

    def _consume_token(self, tok: bytes):
        got = self.bs.peek(2)
        if got != tok:
            raise ValueError(f"expected {tok!r}, got {got!r}")
        # consume two bytes
        self.bs.read1()
        self.bs.read1()

    # ---- parse an expr (list of items), where items are strings or nested groups ----
    def parse_expr(self) -> list:
        items = []
        # expr can be empty; end when next token is ')'
        while True:
            tok = self._peek_token()
            if tok == TOK_RP:
                break  # empty or end-of-list
            if tok == TOK_LP:
                # nested group
                self._consume_token(TOK_LP)
                node = self.parse_group()
                items.append(node)
            else:
                # parse a string until ',' or ')'
                s = self.parse_string_until({TOK_CM, TOK_RP})
                items.append(s)

            # After an item, either ',' continues or ')' ends
            tok = self._peek_token()
            if tok == TOK_CM:
                self._consume_token(TOK_CM)
                # allow next to be empty string (i.e., immediate comma)
                continue
            elif tok == TOK_RP:
                break
            else:
                # If we reach here, the stream provided a literal byte that
                # belongs to the previous string (e.g., user typed raw data).
                # Extend the last string by continuing scan until ',' or ')'.
                if items and isinstance(items[-1], (bytes, bytearray)):
                    more = self.parse_string_until({TOK_CM, TOK_RP})
                    items[-1] = (items[-1] + more)
                else:
                    # Shouldn't happen under the given grammar, but be tolerant.
                    pass
        return items

    # ---- parse a parenthesized group:  '\(' [string '\:' ]? expr '\)' ----
    def parse_group(self) -> dict:
        # We are called *after* consuming the leading TOK_LP.
        # Try to read optional name: scan string until '\:' or '\)'
        pre = self.parse_string_until({TOK_CL, TOK_RP})

        tok = self._peek_token()
        if tok == TOK_CL:
            # Name is specified (can be empty)
            self._consume_token(TOK_CL)
            name = pre
            data = self.parse_expr()
        else:
            # No name specified; 'pre' is actually start (or whole) of first string element
            name = None
            first_item = pre
            data = []
            # If the next token is immediately ')', expr is [first_item] or empty if also empty?
            # By grammar, expr may be empty; but since we read raw bytes into 'pre',
            # treat that as first string element (which may be b"").
            data.append(first_item)

            # Continue with rest items until ')'
            while True:
                tok2 = self._peek_token()
                if tok2 == TOK_CM:
                    self._consume_token(TOK_CM)
                    # next item: nested group or string
                    tok3 = self._peek_token()
                    if tok3 == TOK_LP:
                        self._consume_token(TOK_LP)
                        data.append(self.parse_group())
                    else:
                        s = self.parse_string_until({TOK_CM, TOK_RP})
                        data.append(s)
                elif tok2 == TOK_RP:
                    break
                else:
                    # Extend last string with more literal bytes until ',' or ')'
                    if data and isinstance(data[-1], (bytes, bytearray)):
                        more = self.parse_string_until({TOK_CM, TOK_RP})
                        data[-1] = data[-1] + more
                    else:
                        # Shouldn't happen; be tolerant
                        pass

        # Expect closing '\)'
        if self._peek_token() != TOK_RP:
            # Block until it appears (interactive input)
            while True:
                tokx = self._peek_token()
                if tokx == TOK_RP:
                    break
                # Consume any stray bytes as part of a trailing string in expr if possible
                # Otherwise, just read and discard (outside grammar).
                try:
                    _ = self.bs.read1()
                except EOFError:
                    raise EOFError("Unexpected EOF while waiting for closing b'\\)'")
        self._consume_token(TOK_RP)

        return {"name": name, "data": data}

# ---- Top-level loop: find each unescaped b'\(' and parse a group, print immediately ----

def main():
    bs = ByteStream(sys.stdin.buffer)
    p = Parser(bs)

    while True:
        try:
            # Scan until we find an unescaped '\(' (start token)
            while True:
                pair = bs.peek(2)
                if not pair:
                    # wait for more input / or EOF
                    b = bs.read1()  # will raise EOFError if closed
                    # ignore lone bytes while searching for start token
                    continue
                if pair == TOK_LP:
                    p._consume_token(TOK_LP)
                    break
                else:
                    # Consume one byte and keep searching
                    bs.read1()

            # Parse the group that starts here; print right away
            node = p.parse_group()
            pprint(node, width=100, compact=False)
            # Flush so the output appears immediately in interactive use
            sys.stdout.flush()

        except EOFError:
            # Clean exit on EOF
            break

if __name__ == "__main__":
    main()
