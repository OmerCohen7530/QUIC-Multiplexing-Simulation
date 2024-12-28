import socket
import os
import QUIC_API

class StreamOut:
    """
    A class representing a stream sender that connects to a QUIC client to send data in chunks.

    Attributes:
        host (str): The server's IP address.
        port (int): The port number for the stream.
        data_size (int): The size of the data to be sent for the stream, minus the header size.
        index (int): The index of this stream.
        file_path (str): The path to the file to be read and sent.
        socket (socket.socket): The UDP socket for the stream.
        client_address (tuple): Address of the connected client.
        packet_num (int): The current packet number to be sent.
        log_file (file object): The file object used for logging stream events.
    """

    def __init__(self, host, port, data_size, index):
        """
        Initializes the stream sender with server details, data size, and logging configuration.

        Parameters:
            host (str): The server's IP address.
            port (int): The port number for the stream.
            data_size (int): The size of the data to be sent, including the header size.
            index (int): The index of this stream.
        """
        self.client_address = None
        self.packet_num = 0
        self.host = host
        self.port = port
        self.index = index
        self.data_size = data_size - 8  # Deduct the header size
        self.file_path = f'out/file_{self.index}.txt'  # Path to the file to be read
        self.socket = self.create_socket()

        # Create the output directory if it doesn't exist
        os.makedirs('out', exist_ok=True)
        self.log_file = open(f'out/stream_out_{self.index}.txt', 'w')  # Open log file for writing

    def create_socket(self):
        """
        Creates and configures a UDP socket for the stream.

        Returns:
            socket.socket: A configured UDP socket for data transmission.
        """
        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        stream_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        stream_socket.bind((self.host, self.port))
        return stream_socket

    def log(self, message):
        """
        Logs a message to the stream's log file.

        Parameters:
            message (str): The message to log.
        """
        self.log_file.write(f"Stream {self.index}: {message}\n")

    def close_resources(self):
        """
        Closes the socket and log file resources.
        """
        if self.socket:
            self.socket.close()
        if self.log_file and not self.log_file.closed:
            self.log_file.close()

    def start(self):
        """
        Handles the initial connection and starts data transmission.
        """
        self.log(f"Waiting for connection on {self.host}:{self.port}")
        try:
            self.wait_for_client_syn()
            self.send_stream_size()
            self.wait_for_ack()
            self.send_data_from_file()
            self.send_eof()
        except Exception as e:
            self.log(f"Error in stream on port {self.port}: {e}")
        finally:
            self.close_resources()

    def wait_for_client_syn(self):
        """
        Listens for the SYN message from the client to establish the connection.
        """
        packet, self.client_address = self.socket.recvfrom(1000)
        packet_num, data = QUIC_API.parse_packet(packet)
        if data == "Syn":
            self.log(f"Open connection with {self.client_address}")

    def send_stream_size(self):
        """
        Sends the size of the stream to the client.
        """
        packet = QUIC_API.create_packet(self.packet_num, self.data_size)
        self.socket.sendto(packet, self.client_address)
        self.log(f"Sent data size: {self.data_size} bytes to {self.client_address}")

    def wait_for_ack(self):
        """
        Waits for an ACK from the client before proceeding.
        """
        packet, _ = self.socket.recvfrom(1000)
        self.log(f"Received ACK for packet #{self.packet_num}")
        self.packet_num += 1

    def send_data_from_file(self):
        """
        Sends data from the file to the client.
        """
        if not self.client_address:
            raise Exception("Client not connected. Cannot send data.")

        try:
            with open(self.file_path, 'r') as file:
                while True:
                    # Read `self.data_size` bytes from the file
                    packet_data = file.read(self.data_size)
                    if not packet_data:
                        break  # End of file reached
                    self.send_packet(packet_data)
                    self.wait_for_ack_with_retry(packet_data)
        except FileNotFoundError:
            self.log(f"File {self.file_path} not found.")
        except Exception as e:
            self.log(f"Error while sending data from file: {e}")

    def send_packet(self, packet_data):
        """
        Sends a packet of data to the client.

        Parameters:
            packet_data (str): The data to be sent in the packet.
        """
        packet = QUIC_API.create_packet(self.packet_num, packet_data)
        self.socket.sendto(packet, self.client_address)
        self.log(f"Sent packet #{self.packet_num} ({len(packet_data)} bytes) to {self.client_address}")

    def wait_for_ack_with_retry(self, packet_data):
        """
        Waits for an ACK from the client with retry logic in case of timeout.

        Parameters:
            packet_data (str): The data of the packet to be resent if the ACK is not received.
        """
        while True:
            try:
                self.socket.settimeout(1)  # 1-second timeout for ACK
                packet, self.client_address = self.socket.recvfrom(8)
                packet_num_received, _ = QUIC_API.parse_packet(packet)
                if packet_num_received == self.packet_num:
                    self.log(f"Received ACK for packet #{self.packet_num}")
                    self.packet_num += 1
                    break
                else:
                    self.log(f"Expected ACK for packet #{self.packet_num}, but received: {packet_num_received}")
            except socket.timeout:
                self.log(f"Timed out waiting for ACK for packet #{self.packet_num}. Resending packet.")
                self.send_packet(packet_data)  # Resend packet data in case of timeout

    def send_eof(self):
        """
        Sends an 'EOF' message to indicate the end of data transmission.
        """
        packet = QUIC_API.create_packet(self.packet_num, 'EOF')
        self.socket.sendto(packet, self.client_address)
        self.log(f"Completed sending data. Sent EOF.")
