from socket import AF_INET, SOCK_STREAM, socket
from pyais.messages import NMEAMessage
from typing import Iterable


class Stream:
    """
     NMEA0183 stream via socket. Refer to
     https://en.wikipedia.org/wiki/NMEA_0183
     """

    BUF_SIZE = 4096

    def __init__(self, host: str = 'ais.exploratorium.edu', port: int = 80):
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect((host, port))
        except ConnectionRefusedError as e:
            self.sock.close()
            raise ValueError(f"Failed to connect to {host}:{port}") from e

    def __enter__(self):
        # Enables use of with statement
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Enables use of with statement
        self.sock.close()

    def __iter__(self):
        return self._assemble_messages()

    def _assemble_messages(self):
        queue = []

        for line in self._recv_bytes():
            # Try to parse the message
            try:
                msg = NMEAMessage(line)
            except Exception as e:
                raise ValueError(f'Failed to parse line "{line}"') from e

            # Be gentle and just skip invalid messages
            if not msg.is_valid:
                continue

            if msg.is_single:
                yield msg

            # Assemble multiline messages
            elif msg.is_multi:
                queue.append(msg)

                if msg.index == msg.count:
                    yield msg.assemble_from_iterable(queue)
                    queue.clear()
            else:
                raise ValueError("Messages are out of order!")

    def _recv_bytes(self) -> Iterable[bytes]:
        partial = b''
        while True:
            body = self.sock.recv(self.BUF_SIZE)

            # Server closed connection
            if not body:
                return None

            lines = body.split(b'\r\n')

            line = partial + lines[0]
            if line:
                yield line

            yield from (line for line in lines[1:-1] if line)

            partial = lines[-1]