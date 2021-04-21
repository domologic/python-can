import can
import socket
import select
import logging
import time

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def _compose_arbitration_id(message: can.Message) -> int:
    can_id = message.arbitration_id
    if message.is_extended_id:
        log.debug("sending an extended id type message")
        can_id |= CAN_EFF_FLAG
    if message.is_remote_frame:
        log.debug("requesting a remote frame")
        can_id |= CAN_RTR_FLAG
    if message.is_error_frame:
        log.debug("sending error frame")
        can_id |= CAN_ERR_FLAG
    return can_id


def convert_ascii_message_to_can_message(ascii_message: str) -> can.Message:
    if not ascii_message.startswith("< frame ") or not ascii_message.endswith(" >"):
        log.warning(f"Could not parse ascii message: {ascii_message}")
        return None
    else:
        frame_string = ascii_message.removeprefix("< frame ").removesuffix(" >")
        parts = frame_string.split(" ", 3)
        can_id, timestamp = int(parts[0], 16), float(parts[1])

        data = bytearray.fromhex(parts[2])
        can_dlc = len(data)
        can_message = can.Message(
            timestamp=timestamp, arbitration_id=can_id, data=data, dlc=can_dlc
        )
        return can_message


def convert_can_message_to_ascii_message(can_message: can.Message) -> str:
    # Note: socketcan bus adds extended flag, remote_frame_flag & error_flag to id
    # not sure if that is necessary here
    can_id = can_message.arbitration_id
    # Note: seems like we cannot add CANFD_BRS (bitrate_switch) and CANFD_ESI (error_state_indicator) flags
    data = can_message.data
    length = can_message.dlc
    bytes_string = " ".join("{:x}".format(x) for x in data[0:length])
    ascii_message = f"< send {can_id:X} {length:X} {bytes_string} >"
    return ascii_message


def connect_to_server(s, host, port):
    timeout_ms = 10000
    now = time.time() * 1000
    end_time = now + timeout_ms
    while now < end_time:
        try:
            s.connect((host, port))
            return
        except Exception as e:
            log.warning(f"Failed to connect to server: {type(e)} Message: {e}")
            now = time.time() * 1000
    raise TimeoutError(
        f"connect_to_server: Failed to connect server for {timeout_ms} ms"
    )


class SocketCanDaemonBus(can.BusABC):
    def __init__(self, channel, host, port, can_filters=None, **kwargs):
        self.__host = host
        self.__port = port
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_to_server(self.__socket, self.__host, self.__port)
        log.info(
            f"SocketCanDaemonBus: connected with address {self.__socket.getsockname()}"
        )
        self._tcp_send(f"< open {channel} >")
        self._tcp_send(f"< rawmode >")
        super().__init__(channel=channel, can_filters=can_filters)

    def _recv_internal(self, timeout):
        try:
            # get all sockets that are ready (can be a list with a single value
            # being self.socket or an empty list if self.socket is not ready)
            ready_receive_sockets, _, _ = select.select(
                [self.__socket], [], [], timeout
            )
        except socket.error as exc:
            # something bad happened (e.g. the interface went down)
            raise can.CanError(f"Failed to receive: {exc}")

        if ready_receive_sockets:  # not empty
            ascii_message = self.__socket.recv(1024)
            log.info(f"Received Ascii Message: {ascii_message}")
            can_message = convert_ascii_message_to_can_message(
                ascii_message.decode("ascii")
            )
            return can_message, False

        # socket wasn't readable or timeout occurred
        return None, False

    def _tcp_send(self, message: str):
        log.debug(f"Sending Tcp Message: '{message}'")
        self.__socket.sendall(message.encode("ascii"))

    def send(self, message, timeout=None):
        ascii_message = convert_can_message_to_ascii_message(message)
        self._tcp_send(ascii_message)

    def shutdown(self):
        self.stop_all_periodic_tasks()
        self.__socket.close()
